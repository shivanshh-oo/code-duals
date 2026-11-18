from unittest.mock import patch
from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from django.core.cache import cache


class InterviewTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user('interviewer', password='testing123')
        self.client.force_login(self.user)

    def test_page_and_validation(self):
        self.assertContains(self.client.get('/interview/'), 'Practice interview')
        self.assertEqual(self.client.post('/interview/evaluate/', data='{}', content_type='application/json').status_code, 400)

    @override_settings(GROQ_API_KEY='test-key')
    @patch('accounts.interviews.requests.post')
    def test_feedback_and_throttle(self, post):
        post.return_value.json.return_value = {'choices': [{'message': {'content': 'Rating: 7/10. Practice edge cases.'}}]}
        data = {'topic': 'DSA', 'answers': ['Use a hash map', 'Use slow and fast pointers', 'Use BFS']}
        response = self.client.post('/interview/evaluate/', data=data, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('7/10', response.json()['feedback'])
        request_payload = post.call_args.kwargs['json']
        import json
        transcript = json.loads(request_payload['messages'][1]['content'])['transcript']
        self.assertEqual(transcript[0]['answer'], data['answers'][0])
        self.assertIn('rating from 0 to 10', request_payload['messages'][0]['content'])
        self.assertEqual(self.client.post('/interview/evaluate/', data=data, content_type='application/json').status_code, 429)

    def test_anonymous_denied(self):
        self.client.logout()
        self.assertEqual(self.client.post('/interview/evaluate/').status_code, 302)

    @override_settings(GROQ_API_KEY='invalid-test-key')
    @patch('accounts.interviews.requests.post')
    def test_invalid_key_explained(self, post):
        post.return_value.status_code = 401
        response = self.client.post('/interview/evaluate/', data={'topic': 'DSA', 'answers': ['a', 'b', 'c']}, content_type='application/json')
        self.assertEqual(response.status_code, 503)
        self.assertIn('contact the site administrator', response.json()['error'])

    def test_bank_access_before_placement(self):
        from problems.models import Problem
        problem = Problem.objects.create(title='Local question', statement='Solve locally', category='DSA', difficulty='Easy')
        self.assertContains(self.client.get('/problems/'), 'Local question')
        self.assertEqual(self.client.get('/problems/api/').json()['problems'][0]['url'], f'/problems/{problem.pk}/')

