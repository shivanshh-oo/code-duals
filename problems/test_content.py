from unittest.mock import patch
from io import StringIO
from django.test import TestCase
from django.core.management import call_command, CommandError
from problems.models import Problem, TestCase as ProblemTest


class ContentTests(TestCase):
    def test_imported_content_uses_local_page_but_cannot_be_judged(self):
        problem = Problem.objects.create(title='Imported', statement='Add', category='DSA', difficulty='Easy', is_draft=True, source_url='https://codeforces.com/problemset/problem/1/A')
        ProblemTest.objects.create(problem=problem, input='1 2', expected_output='3', is_sample=True)
        self.assertEqual(self.client.get('/problems/api/').json()['problems'][0]['url'], f'/problems/{problem.id}/')
        self.assertContains(self.client.get(f'/problems/{problem.id}/'), 'Add')
        self.assertFalse(Problem.objects.filter(is_draft=False, pk=problem.pk).exists())

    @patch('problems.management.commands.run_lan.socket.getaddrinfo', return_value=[(None, None, None, None, ('192.168.1.5', 0))])
    @patch('problems.management.commands.run_lan.call_command')
    def test_lan_command(self, run, addresses):
        output = StringIO()
        call_command('run_lan', stdout=output)
        self.assertIn('http://192.168.1.5:8000/', output.getvalue())
        run.assert_called_once_with('runserver', '0.0.0.0:8000', use_reloader=False)
