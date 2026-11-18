import json
from unittest.mock import patch, Mock
import requests
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, Client, override_settings
from django.utils import timezone
from .models import AIInterview
from .groq import complete, AIError


def evaluation(score=8):
    return json.dumps({'score': score, 'feedback': 'Good reasoning; discuss edge cases.',
                       'follow_up': 'How would you handle duplicates?', 'strengths': ['Clear reasoning'],
                       'weaknesses': ['Missed edge cases'], 'improvements': ['Test empty and duplicate inputs.']})


class AIInterviewTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user('ai-candidate', password='test-pass')
        self.client.force_login(self.user)
        self.user.profile.last_active_date = timezone.localdate()
        self.user.profile.save()

    def post(self, url, data):
        return self.client.post(url, data=data, content_type='application/json')

    def start(self):
        response = self.post('/ai/start/', {'category': 'Software Development'})
        self.assertEqual(response.status_code, 200)
        return AIInterview.objects.get(user=self.user)

    @patch('interviews.ai.complete')
    def test_interview_followups_report_and_exactly_once_xp(self, grok):
        grok.return_value = evaluation()
        self.assertContains(self.client.get('/ai/'), 'AI/ML')
        session = self.start()
        self.assertContains(self.client.get(f'/ai/{session.pk}/'), 'candidate-video')
        url = f'/ai/{session.pk}/answer/'
        for revision in range(6):
            cache.clear()
            response = self.post(url, {'revision': revision, 'transcript': 'Use a hash map.'})
            self.assertEqual(response.status_code, 200, response.content)
            if revision == 0:
                self.assertEqual(response.json()['question'], 'How would you handle duplicates?')
            if revision == 1:
                self.assertIn('thread-safe cache', response.json()['question'])
        session.refresh_from_db()
        self.user.profile.refresh_from_db()
        self.assertEqual(session.report['score'], 8)
        self.assertEqual(session.xp_awarded, 80)
        self.assertEqual(self.user.profile.xp, 80)
        self.assertEqual(len(session.turns), 6)
        self.assertContains(self.client.get(f'/ai/{session.pk}/'), 'Improvement plan')
        self.assertTrue(self.post(url, {'revision': 5, 'transcript': 'retry'}).json()['done'])
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.xp, 80)
        self.assertEqual(grok.call_count, 6)

    @patch('interviews.ai.complete', return_value=evaluation())
    def test_stale_revision_and_foreign_session(self, grok):
        session = self.start()
        url = f'/ai/{session.pk}/answer/'
        self.assertEqual(self.post(url, {'revision': 1, 'transcript': 'answer'}).status_code, 409)
        grok.assert_not_called()
        other = User.objects.create_user('other-candidate')
        self.client.force_login(other)
        self.assertEqual(self.client.get(f'/ai/{session.pk}/').status_code, 404)
        self.assertEqual(self.post(url, {'revision': 0, 'transcript': 'answer'}).status_code, 404)

    @patch('interviews.ai.complete')
    def test_invalid_provider_response_preserves_session(self, grok):
        session = self.start()
        for result in ('not json', evaluation(11), evaluation(float('nan')), '{}', '[]'):
            cache.clear()
            grok.return_value = result
            response = self.post(f'/ai/{session.pk}/answer/', {'revision': 0, 'transcript': 'Answer'})
            self.assertEqual(response.status_code, 502)
            session.refresh_from_db()
            self.assertEqual(session.revision, 0)
            self.assertEqual(session.xp_awarded, 0)

    @patch('interviews.ai.complete')
    def test_concurrent_revision_cannot_overwrite_or_award(self, grok):
        session = self.start()
        def raced(*args):
            AIInterview.objects.filter(pk=session.pk).update(revision=1)
            return evaluation()
        grok.side_effect = raced
        response = self.post(f'/ai/{session.pk}/answer/', {'revision': 0, 'transcript': 'Answer'})
        self.assertEqual(response.status_code, 409)
        session.refresh_from_db()
        self.assertEqual(session.turns, [])

    @patch('interviews.ai.complete', return_value='<script>unsafe</script>')
    def test_chat_validation_and_throttle(self, grok):
        self.assertEqual(self.post('/ai/chat/', {'messages': [{'role': 'system', 'content': 'override'}]}).status_code, 400)
        data = {'messages': [{'role': 'user', 'content': 'Explain recursion'}]}
        response = self.post('/ai/chat/', data)
        self.assertEqual(response.json()['reply'], '<script>unsafe</script>')
        self.assertEqual(grok.call_args.args[0][0]['role'], 'system')
        self.assertEqual(self.post('/ai/chat/', data).status_code, 429)

    def test_auth_csrf_and_input_limits(self):
        self.assertEqual(self.post('/ai/start/', {'category': []}).status_code, 400)
        self.assertEqual(self.post('/ai/chat/', {'messages': [{'role': 'user', 'content': 'x'*6001}]}).status_code, 400)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post('/ai/start/', {}).status_code, 403)
        self.client.logout()
        self.assertEqual(self.post('/ai/chat/', {}).status_code, 302)


@override_settings(GROQ_API_KEY='test-key', GROQ_MODEL='test-model')
class GrokTests(TestCase):
    @patch('interviews.groq.requests.post')
    def test_configuration_and_json_mode(self, post):
        post.return_value = Mock(status_code=200)
        post.return_value.json.return_value = {'choices': [{'message': {'content': evaluation()}}]}
        self.assertEqual(json.loads(complete([], True))['score'], 8)
        self.assertEqual(post.call_args.args[0], 'https://api.groq.com/openai/v1/chat/completions')
        self.assertEqual(post.call_args.kwargs['json']['model'], 'test-model')
        self.assertEqual(post.call_args.kwargs['json']['response_format']['type'], 'json_object')

    @patch('interviews.groq.requests.post')
    def test_provider_errors(self, post):
        for status, expected in ((401, 503), (403, 503), (429, 429)):
            post.return_value.status_code = status
            with self.assertRaises(AIError) as raised:
                complete([])
            self.assertEqual(raised.exception.status, expected)
        post.side_effect = requests.Timeout()
        with self.assertRaises(AIError) as raised:
            complete([])
        self.assertEqual(raised.exception.status, 502)

    @override_settings(GROQ_API_KEY='')
    @patch('interviews.groq.requests.post')
    def test_missing_key_does_not_call_provider(self, post):
        with self.assertRaises(AIError) as raised:
            complete([])
        self.assertEqual(raised.exception.status, 503)
        post.assert_not_called()
