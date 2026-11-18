from django.core.management.base import BaseCommand
from problems.models import Problem
from interviews.models import InterviewTrack, TrackProblem


TRACKS_DATA = [
    {
        'title': 'Junior Backend Developer',
        'target_role': 'Backend Engineer (Python / Distributed Services)',
        'difficulty': 'Entry',
        'time_limit_minutes': 45,
        'description': 'Designed for entry-level backend engineers. Covers string parsing, hash map lookups, frequency counting, and fundamentals of dynamic problem solving.',
        'problems': [
            {'title': 'Reverse String', 'phase': 'Phase 1: Warm-up & I/O'},
            {'title': 'Two Sum', 'phase': 'Phase 2: Core Hashing & Lookup'},
            {'title': 'Climbing Stairs', 'phase': 'Phase 3: State Transition & Basic DP'},
        ]
    },
    {
        'title': 'Core Algorithms & Data Structures',
        'target_role': 'Software Engineer (Generalist / Infra)',
        'difficulty': 'Mid',
        'time_limit_minutes': 50,
        'description': 'Comprehensive algorithms screening focusing on two-pointer searches, logarithmic searches, and graph traversal methodologies.',
        'problems': [
            {'title': 'Palindrome Check', 'phase': 'Phase 1: Two-Pointer Verification'},
            {'title': 'Binary Search', 'phase': 'Phase 2: Logarithmic Search Bounds'},
            {'title': 'Graph BFS Shortest Path', 'phase': 'Phase 3: Graph Traversal & Shortest Path'},
        ]
    },
    {
        'title': 'Data Engineering & Systems',
        'target_role': 'Data Platform / Systems SWE',
        'difficulty': 'Mid',
        'time_limit_minutes': 50,
        'description': 'Tests data pipeline transformation logic, multidimensional matrix reshaping, frequency aggregations, and data normalization.',
        'problems': [
            {'title': 'Matrix Transpose', 'phase': 'Phase 1: 2D Matrix Inversion'},
            {'title': 'Word Frequency Counter', 'phase': 'Phase 2: Streaming Stream Aggregation'},
            {'title': 'Normalize Data', 'phase': 'Phase 3: Data Range Scaling'},
        ]
    },
    {
        'title': 'Full Stack Problem Solving',
        'target_role': 'Full Stack Engineer (API & Data Flow)',
        'difficulty': 'Mid',
        'time_limit_minutes': 45,
        'description': 'Realistic engineering challenges testing JSON payload parsing, structured CSV row serialization, and balanced syntax validation.',
        'problems': [
            {'title': 'JSON Key Extractor', 'phase': 'Phase 1: Schema & Key Extraction'},
            {'title': 'Valid Parentheses', 'phase': 'Phase 2: Syntax & Stack Balancing'},
            {'title': 'CSV Row Parser', 'phase': 'Phase 3: Delimiter Processing'},
        ]
    },
    {
        'title': 'High Performance SWE',
        'target_role': 'Senior Software Engineer (Algorithms & Optimization)',
        'difficulty': 'Senior',
        'time_limit_minutes': 60,
        'description': 'Rigorous technical interview evaluating dynamic programming, prefix sum optimization, and complex state space exploration.',
        'problems': [
            {'title': 'Maximum Subarray Sum', 'phase': "Phase 1: Kadane's Linear Optimization"},
            {'title': 'Longest Common Subsequence', 'phase': 'Phase 2: 2D Dynamic Programming'},
            {'title': 'Knapsack 0/1', 'phase': 'Phase 3: Constrained Resource Optimization'},
        ]
    },
]


class Command(BaseCommand):
    help = 'Seed 5 realistic software developer role interview tracks.'

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        for tdata in TRACKS_DATA:
            track, is_new = InterviewTrack.objects.get_or_create(
                title=tdata['title'],
                defaults={
                    'target_role': tdata['target_role'],
                    'difficulty': tdata['difficulty'],
                    'time_limit_minutes': tdata['time_limit_minutes'],
                    'description': tdata['description'],
                }
            )
            if not is_new:
                track.target_role = tdata['target_role']
                track.difficulty = tdata['difficulty']
                track.time_limit_minutes = tdata['time_limit_minutes']
                track.description = tdata['description']
                track.save()
                updated_count += 1
            else:
                created_count += 1

            # Populate track problems
            TrackProblem.objects.filter(track=track).delete()
            for idx, pinfo in enumerate(tdata['problems'], 1):
                prob = Problem.objects.filter(title=pinfo['title']).first()
                if not prob:
                    # Fallback to any published problem
                    prob = Problem.objects.filter(is_draft=False).exclude(pk__in=TrackProblem.objects.filter(track=track).values_list('problem_id', flat=True)).first()
                if prob and not TrackProblem.objects.filter(track=track, problem=prob).exists():
                    TrackProblem.objects.create(
                        track=track,
                        problem=prob,
                        order=idx,
                        phase_label=pinfo['phase']
                    )

            action = 'Created' if is_new else 'Updated'
            self.stdout.write(f'  {action}: {track.title} ({track.target_role}) with {track.trackproblem_set.count()} challenges')

        self.stdout.write(self.style.SUCCESS(f'\nDone! Seeded {created_count} new, updated {updated_count} interview tracks.'))

