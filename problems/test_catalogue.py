from unittest.mock import patch, Mock
from io import StringIO
import requests
from django.test import TestCase
from django.core.management import call_command, CommandError
from .catalogue import sync_catalogue
from .models import Problem


class CatalogueTests(TestCase):
    @patch('problems.catalogue.requests.get')
    def test_leetcode_and_bank(self, get):
        get.return_value.json.return_value = {'stat_status_pairs': [
            {'paid_only': False, 'stat': {'question__title_slug': 'two-sum', 'question__title': 'Two Sum'}, 'difficulty': {'level': 1}},
            {'paid_only': True},
        ]}
        self.assertEqual(sync_catalogue('leetcode'), (1, 0))
        response = self.client.get('/problems/api/').json()['problems']
        self.assertEqual(response, [])
        self.assertEqual(self.client.get(f'/problems/{Problem.objects.get().pk}/').status_code, 404)

    @patch('problems.management.commands.import_problems.sync_catalogue')
    def test_source_failure_does_not_skip_other_source(self, sync):
        sync.side_effect = [requests.HTTPError('Unavailable'), (1, 0)]
        with self.assertRaises(CommandError):
            call_command('import_problems', stdout=StringIO(), stderr=StringIO())
        self.assertEqual(sync.call_count, 1)

    @patch('problems.management.commands.import_problems.time.sleep', side_effect=KeyboardInterrupt)
    @patch('problems.management.commands.import_problems.sync_catalogue', return_value=(0, 0))
    def test_watch_runs_then_waits(self, sync, sleep):
        call_command('import_problems', watch=True, interval=600, stdout=StringIO())
        self.assertEqual(sync.call_count, 1)
        sleep.assert_called_once_with(600)
