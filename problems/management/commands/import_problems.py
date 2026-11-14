import requests
from django.core.management.base import BaseCommand, CommandError
from problems.models import Problem


class Command(BaseCommand):
    help = 'Import Codeforces metadata as drafts; add statements and tests before publishing.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=100)

    def handle(self, *args, **options):
        try:
            response = requests.get('https://codeforces.com/api/problemset.problems', timeout=30)
            response.raise_for_status()
            data = response.json()
            if data.get('status') != 'OK':
                raise ValueError('Codeforces API failed')
            items = data['result']['problems']
        except (requests.RequestException, ValueError, KeyError) as error:
            raise CommandError(str(error))
        count = 0
        for item in items[:max(0, options['limit'])]:
            if 'contestId' not in item:
                continue
            url = f"https://codeforces.com/problemset/problem/{item['contestId']}/{item['index']}"
            rating = item.get('rating', 1000)
            _, created = Problem.objects.get_or_create(source_url=url, defaults={
                'title': item['name'][:200], 'statement': 'Add statement and tests. Tags: ' + ', '.join(item.get('tags', [])),
                'category': 'DSA', 'difficulty_rating': rating, 'is_draft': True,
                'difficulty': 'Easy' if rating < 1200 else 'Medium' if rating < 1800 else 'Hard',
            })
            count += created
        self.stdout.write(f'Imported {count} drafts')
