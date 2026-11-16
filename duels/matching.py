"""
Matching logic: pairs users by rating for quick matches.
"""
from django.utils import timezone
from django.db.models import Q
from problems.models import Problem
from .models import Match, MatchProblem, Participant
import random


class WaitingList:
    """In-memory waiting list for quick match. Maps user_id -> {user, rating, difficulty, joined_at}."""
    _waiting = {}

    @classmethod
    def add(cls, user, difficulty):
        cls._waiting[user.id] = {
            'user': user,
            'rating': user.profile.rating,
            'difficulty': difficulty,
            'joined_at': timezone.now(),
        }

    @classmethod
    def remove(cls, user_id):
        cls._waiting.pop(user_id, None)

    @classmethod
    def find_match(cls, user_id):
        """Try to find a match for the given user. Returns Match or None."""
        if user_id not in cls._waiting:
            return None

        me = cls._waiting[user_id]
        now = timezone.now()
        wait_seconds = (now - me['joined_at']).total_seconds()

        # Rating gap widens over time: starts at 100, grows by 50 every 5 seconds
        max_gap = 100 + (wait_seconds // 5) * 50

        best_match = None
        best_gap = float('inf')

        for uid, entry in cls._waiting.items():
            if uid == user_id:
                continue
            if entry['difficulty'] != me['difficulty']:
                continue

            gap = abs(entry['rating'] - me['rating'])
            their_wait = (now - entry['joined_at']).total_seconds()
            their_max_gap = 100 + (their_wait // 5) * 50
            effective_gap = min(max_gap, their_max_gap)

            if gap <= effective_gap and gap < best_gap:
                best_gap = gap
                best_match = uid

        if best_match is None:
            return None

        opp = cls._waiting[best_match]
        # Remove both from waiting list
        cls.remove(user_id)
        cls.remove(best_match)

        # Create match
        match = _create_quick_match(me, opp)
        return match

    @classmethod
    def is_waiting(cls, user_id):
        return user_id in cls._waiting

    @classmethod
    def get_info(cls, user_id):
        return cls._waiting.get(user_id)


def _create_quick_match(player1_info, player2_info):
    """Create a Match with problems and participants."""
    difficulty = player1_info['difficulty']
    avg_rating = (player1_info['rating'] + player2_info['rating']) // 2

    match = Match.objects.create(
        status='active',
        difficulty=difficulty,
        duration_minutes=30,
        started_at=timezone.now(),
        ends_at=timezone.now() + timezone.timedelta(minutes=30),
    )

    # Pick 2-3 problems near the average rating
    problems = _pick_problems(difficulty, avg_rating, count=3)
    for p in problems:
        MatchProblem.objects.create(match=match, problem=p)

    Participant.objects.create(match=match, user=player1_info['user'])
    Participant.objects.create(match=match, user=player2_info['user'])

    return match


def _pick_problems(difficulty, target_rating, count=3):
    """Pick problems near the target rating for the given difficulty."""
    problems = Problem.objects.filter(
        difficulty=difficulty,
        is_draft=False,
        is_placement=False,
    ).order_by('difficulty_rating')

    if problems.count() == 0:
        # Fallback: any non-draft, non-placement problems
        problems = Problem.objects.filter(is_draft=False, is_placement=False).order_by('difficulty_rating')

    if problems.count() == 0:
        return []

    # Sort by distance from target rating
    sorted_problems = sorted(problems, key=lambda p: abs(p.difficulty_rating - target_rating))
    selected = sorted_problems[:min(count, len(sorted_problems))]
    return selected


def create_private_match(creator, difficulty, duration_minutes, match_type='1v1'):
    """Create a private match waiting for an opponent / team players."""
    match = Match.objects.create(
        status='waiting',
        difficulty=difficulty,
        duration_minutes=duration_minutes,
        is_private=True,
        match_type=match_type,
    )
    initial_team = 'team_a' if match_type == '2v2' else 'none'
    Participant.objects.create(match=match, user=creator, team=initial_team)
    return match
