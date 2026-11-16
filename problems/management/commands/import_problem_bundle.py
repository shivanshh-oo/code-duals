import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.db import transaction
from problems.models import Problem, TestCase, Solution


class Command(BaseCommand):
    help = 'Import a local JSON problem with statement, reference solution and full tests.'

    def add_arguments(self, parser):
        parser.add_argument('file')

    def handle(self, *args, **options):
        try:
            data = json.loads(Path(options['file']).read_text(encoding='utf-8'))
            for key in ['title', 'statement', 'source_url', 'explanation', 'reference_code']:
                if not isinstance(data[key], str) or not data[key].strip():
                    raise ValueError(f'{key} must be nonempty text')
            URLValidator(schemes=['https'])(data['source_url'])
            if len(data['title']) > 200 or len(data['source_url']) > 200:
                raise ValueError('Title or source URL exceeds 200 characters')
            tests = data['tests']
            if not isinstance(tests, list) or not tests:
                raise ValueError('Tests are required')
            for test in tests:
                if not isinstance(test['input'], str) or not isinstance(test['expected_output'], str) or type(test['is_sample']) is not bool:
                    raise ValueError('Invalid test format')
            if not any(not test['is_sample'] for test in tests):
                raise ValueError('At least one hidden test is required; samples alone cannot publish a problem')
            difficulty = data.get('difficulty', 'Medium')
            seconds = data.get('time_limit_sec', 5)
            if difficulty not in ('Easy', 'Medium', 'Hard') or type(seconds) is not int or not 1 <= seconds <= 30:
                raise ValueError('Invalid difficulty or time limit (1–30 seconds)')
            with transaction.atomic():
                problem, created = Problem.objects.get_or_create(source_url=data['source_url'], defaults={
                    'title': data['title'], 'statement': data['statement'], 'category': 'DSA',
                    'difficulty': difficulty, 'is_draft': True,
                })
                if not created and not problem.is_draft:
                    raise ValueError('Published problem already exists; edit it in Admin instead')
                problem.title, problem.statement = data['title'], data['statement']
                problem.difficulty, problem.time_limit_sec = difficulty, seconds
                problem.is_draft = False
                problem.save()
                problem.test_cases.all().delete()
                TestCase.objects.bulk_create([TestCase(problem=problem, **{key: test[key] for key in ('input', 'expected_output', 'is_sample')}) for test in tests])
                Solution.objects.update_or_create(problem=problem, defaults={
                    'explanation': data['explanation'], 'reference_code': data['reference_code'],
                })
            self.stdout.write(f'Published local problem: {problem.title}')
        except (OSError, ValueError, KeyError, TypeError, ValidationError) as error:
            raise CommandError(str(error)) from error
