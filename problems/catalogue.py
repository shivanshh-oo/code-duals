import re
import requests
from django.db import transaction
from .models import Problem


def sync_catalogue(source, limit=0):
    if source != 'leetcode':
        raise ValueError('Only LeetCode catalogue sync is supported.')
    url = 'https://leetcode.com/api/problems/all/'
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    payload = response.json()
    records = []
    if source == 'leetcode':
        for item in payload['stat_status_pairs']:
            if item.get('paid_only'):
                continue
            stat = item['stat']
            slug = stat['question__title_slug']
            if not re.fullmatch(r'[a-z0-9-]+', slug):
                raise ValueError('Invalid LeetCode slug')
            difficulty, rating = {1: ('Easy', 1000), 2: ('Medium', 1500), 3: ('Hard', 2000)}[int(item['difficulty']['level'])]
            records.append((f'https://leetcode.com/problems/{slug}/', stat['question__title'], rating, difficulty))
    created = updated = 0
    with transaction.atomic():
        for url, title, rating, difficulty in (records[:limit] if limit else records):
            problem, new = Problem.objects.get_or_create(source_url=url, defaults={
                'title': title[:200], 'statement': f'Open the original problem on {source}.',
                'category': 'DSA', 'difficulty_rating': rating, 'difficulty': difficulty, 'is_draft': True,
            })
            if new:
                created += 1
            elif problem.is_draft:
                problem.title, problem.difficulty_rating, problem.difficulty = title[:200], rating, difficulty
                problem.save(update_fields=['title', 'difficulty_rating', 'difficulty'])
                updated += 1
    return created, updated
