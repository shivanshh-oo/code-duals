from django.test import TestCase, Client
from django.contrib.auth.models import User
from problems.models import Problem, TestCase as ProblemTestCase
from interviews.models import InterviewTrack, TrackProblem, InterviewSession, InterviewSubmission


class InterviewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('candidate', password='pwd')
        self.user.profile.placement_done = True
        self.user.profile.save()

        self.client = Client()
        self.client.force_login(self.user)

        self.prob = Problem.objects.create(
            title='Sample Interview Task',
            statement='Read and print',
            difficulty='Easy',
            category='DSA',
            is_draft=False
        )
        ProblemTestCase.objects.create(problem=self.prob, input='test', expected_output='test', is_sample=True)
        ProblemTestCase.objects.create(problem=self.prob, input='hidden', expected_output='hidden', is_sample=False)

        self.track = InterviewTrack.objects.create(
            title='Test Backend SWE',
            target_role='Backend Engineer',
            difficulty='Entry',
            time_limit_minutes=30,
            description='Test track'
        )
        TrackProblem.objects.create(track=self.track, problem=self.prob, order=1, phase_label='Phase 1')

    def test_interview_lifecycle_and_report(self):
        # 1. View track list
        resp = self.client.get('/interviews/')
        self.assertEqual(resp.status_code, 200)

        # 2. Start session
        start_resp = self.client.post(f'/interviews/start/{self.track.id}/')
        self.assertEqual(start_resp.status_code, 302)

        session = InterviewSession.objects.get(user=self.user, track=self.track)
        self.assertEqual(session.status, 'in_progress')

        # 3. View session room
        room_resp = self.client.get(f'/interviews/session/{session.id}/')
        self.assertEqual(room_resp.status_code, 200)

        # 4. Submit problem
        submit_url = f'/interviews/session/{session.id}/submit/{self.prob.id}/'
        sub_resp = self.client.post(submit_url, {'code': 'print(input())'})
        self.assertEqual(sub_resp.status_code, 200)
        self.assertEqual(sub_resp.json()['verdict'], 'Accepted')
        self.assertEqual(sub_resp.json()['tests_passed'], 2)

        # 5. Finish interview
        fin_resp = self.client.post(f'/interviews/session/{session.id}/finish/')
        self.assertEqual(fin_resp.status_code, 302)

        session.refresh_from_db()
        self.assertEqual(session.status, 'completed')
        self.assertEqual(session.total_score, 100.0)

        # 6. View Diagnostic Comparison Report
        rep_resp = self.client.get(f'/interviews/session/{session.id}/report/')
        self.assertEqual(rep_resp.status_code, 200)
        self.assertContains(rep_resp, 'CANDIDATE COMPARISON REPORT')
        self.assertContains(rep_resp, 'Top 85% Percentile')
