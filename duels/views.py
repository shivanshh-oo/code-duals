from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone
from problems.models import Problem
from .models import Match, Participant, Submission, MatchProblem
from .judge import judge_submission
from .matching import WaitingList, create_private_match, _pick_problems


@login_required
def play(request):
    """Play page with quick match and create private match options."""
    return render(request, 'duels/play.html')


def leaderboard(request):
    return render(request, 'duels/leaderboard.html')


@login_required
def practice(request, problem_id):
    problem = get_object_or_404(Problem, pk=problem_id, is_draft=False)
    sample_tests = problem.test_cases.filter(is_sample=True)
    return render(request, 'duels/practice.html', {
        'problem': problem,
        'sample_tests': sample_tests,
    })


@login_required
@require_POST
def practice_submit(request, problem_id):
    """Handle practice submission."""
    problem = get_object_or_404(Problem, pk=problem_id, is_draft=False)
    code = request.POST.get('code', '')

    if not code.strip():
        return JsonResponse({'error': 'No code submitted'}, status=400)

    all_tests = problem.test_cases.all()
    result = judge_submission(code, all_tests, problem.time_limit_sec)

    # Save submission for unlock tracking
    practice_match, _ = Match.objects.get_or_create(
        invite_code=f'PRACTICE-{request.user.id}',
        defaults={'status': 'finished', 'difficulty': problem.difficulty, 'duration_minutes': 0}
    )
    participant, _ = Participant.objects.get_or_create(match=practice_match, user=request.user)
    MatchProblem.objects.get_or_create(match=practice_match, problem=problem)

    Submission.objects.create(
        participant=participant, problem=problem, code=code,
        verdict=result['verdict'], tests_passed=result['tests_passed'],
        tests_total=result['tests_total'],
    )

    sample_ids = set(problem.test_cases.filter(is_sample=True).values_list('id', flat=True))
    safe_details = []
    for i, tc in enumerate(all_tests):
        detail = result['details'][i]
        if tc.id in sample_ids:
            safe_details.append({
                'test': i + 1, 'status': detail['status'], 'is_sample': True,
                'output': detail['output'][:200], 'expected': detail['expected'][:200],
            })
        else:
            safe_details.append({'test': i + 1, 'status': detail['status'], 'is_sample': False})

    return JsonResponse({
        'verdict': result['verdict'], 'tests_passed': result['tests_passed'],
        'tests_total': result['tests_total'], 'details': safe_details,
    })


# --- Quick Match ---

@login_required
@require_POST
def quick_match_join(request):
    """Join the quick match waiting list."""
    difficulty = request.POST.get('difficulty', 'Medium')
    if difficulty not in ('Easy', 'Medium', 'Hard'):
        difficulty = 'Medium'
    WaitingList.add(request.user, difficulty)
    return JsonResponse({'status': 'waiting'})


@login_required
def quick_match_poll(request):
    """Poll for a match. Returns match_id if matched, or 'waiting'."""
    user_id = request.user.id

    # Check if already in an active match
    active = Participant.objects.filter(
        user=request.user, match__status='active'
    ).select_related('match').first()
    if active:
        WaitingList.remove(user_id)
        return JsonResponse({'status': 'matched', 'match_id': active.match.id})

    if not WaitingList.is_waiting(user_id):
        return JsonResponse({'status': 'not_waiting'})

    match = WaitingList.find_match(user_id)
    if match:
        return JsonResponse({'status': 'matched', 'match_id': match.id})

    return JsonResponse({'status': 'waiting'})


@login_required
@require_POST
def quick_match_cancel(request):
    """Cancel waiting for quick match."""
    WaitingList.remove(request.user.id)
    return JsonResponse({'status': 'cancelled'})


# --- Create Private Match ---

@login_required
@require_POST
def create_match(request):
    """Create a private match with invite code."""
    difficulty = request.POST.get('difficulty', 'Medium')
    duration = int(request.POST.get('duration', 30))
    if difficulty not in ('Easy', 'Medium', 'Hard'):
        difficulty = 'Medium'
    duration = max(10, min(60, duration))

    match = create_private_match(request.user, difficulty, duration)
    return JsonResponse({
        'match_id': match.id,
        'invite_code': match.invite_code,
    })


# --- Match Arena ---

@login_required
def match_arena(request, match_id):
    """The match arena page where players solve problems."""
    match = get_object_or_404(Match, pk=match_id)
    participant = get_object_or_404(Participant, match=match, user=request.user)

    match_problems = match.match_problems.select_related('problem').all()
    problems_data = []
    for mp in match_problems:
        sample_tests = mp.problem.test_cases.filter(is_sample=True)
        problems_data.append({
            'problem': mp.problem,
            'sample_tests': sample_tests,
        })

    return render(request, 'duels/match_arena.html', {
        'match': match,
        'participant': participant,
        'problems_data': problems_data,
    })


@login_required
def match_status_api(request, match_id):
    """JSON endpoint: time left, your solved count, opponent's solved count."""
    match = get_object_or_404(Match, pk=match_id)
    participant = get_object_or_404(Participant, match=match, user=request.user)

    # Check if match should end
    _check_match_end(match)

    now = timezone.now()
    time_left = 0
    if match.ends_at and match.status == 'active':
        time_left = max(0, (match.ends_at - now).total_seconds())

    # Get opponent info (solved count only, never code)
    opponent = match.participants.exclude(user=request.user).first()
    opp_solved = opponent.problems_solved if opponent else 0

    return JsonResponse({
        'status': match.status,
        'time_left': int(time_left),
        'my_solved': participant.problems_solved,
        'opp_solved': opp_solved,
        'winner': match.winner.username if match.winner else None,
    })


@login_required
@require_POST
def match_submit(request, match_id, problem_id):
    """Submit code for a problem in a match."""
    match = get_object_or_404(Match, pk=match_id)
    participant = get_object_or_404(Participant, match=match, user=request.user)
    problem = get_object_or_404(Problem, pk=problem_id)

    # Check match is still active
    _check_match_end(match)
    if match.status != 'active':
        return JsonResponse({'error': 'Match has ended'}, status=400)

    code = request.POST.get('code', '')
    if not code.strip():
        return JsonResponse({'error': 'No code submitted'}, status=400)

    # Judge
    all_tests = problem.test_cases.all()
    result = judge_submission(code, all_tests, problem.time_limit_sec)

    # Calculate time taken since match start
    time_taken = 0
    if match.started_at:
        time_taken = (timezone.now() - match.started_at).total_seconds()

    Submission.objects.create(
        participant=participant, problem=problem, code=code,
        verdict=result['verdict'], tests_passed=result['tests_passed'],
        tests_total=result['tests_total'], time_taken=time_taken,
    )

    # Update solved count
    if result['verdict'] == 'Accepted':
        # Check if this problem wasn't already solved
        already_solved = Submission.objects.filter(
            participant=participant, problem=problem, verdict='Accepted'
        ).count()
        if already_solved == 1:  # The one we just created
            participant.problems_solved += 1
            participant.save()

    # Check if both finished all problems
    total_problems = match.match_problems.count()
    all_participants = match.participants.all()
    if all(p.problems_solved >= total_problems for p in all_participants):
        _finish_match(match)

    return JsonResponse({
        'verdict': result['verdict'],
        'tests_passed': result['tests_passed'],
        'tests_total': result['tests_total'],
    })


def _check_match_end(match):
    """End match if time is up."""
    if match.status != 'active':
        return
    if match.ends_at and timezone.now() >= match.ends_at:
        _finish_match(match)


def _finish_match(match):
    """Finalize a match: determine winner, update status."""
    if match.status == 'finished':
        return

    match.status = 'finished'
    participants = list(match.participants.all())

    if len(participants) == 2:
        p1, p2 = participants
        if p1.problems_solved > p2.problems_solved:
            match.winner = p1.user
        elif p2.problems_solved > p1.problems_solved:
            match.winner = p2.user
        else:
            # Tie-break by total time of accepted submissions
            t1 = _total_time(p1)
            t2 = _total_time(p2)
            if t1 < t2:
                match.winner = p1.user
            elif t2 < t1:
                match.winner = p2.user
            # else true tie, no winner

        # Apply rating changes
        from .rating import update_ratings
        update_ratings(match, p1, p2)

    for p in participants:
        if not p.finished_at:
            p.finished_at = timezone.now()
            p.save()

    match.save()


def _total_time(participant):
    """Sum of time_taken for accepted submissions."""
    accepted = participant.submissions.filter(verdict='Accepted')
    return sum(s.time_taken for s in accepted)


# --- Match Result ---

@login_required
def match_result(request, match_id):
    """Show match result with rating changes."""
    match = get_object_or_404(Match, pk=match_id, status='finished')
    participants = match.participants.select_related('user', 'user__profile').all()

    my_participant = None
    opp_participant = None
    for p in participants:
        if p.user == request.user:
            my_participant = p
        else:
            opp_participant = p

    # Get problems for solution unlock
    match_problems = match.match_problems.select_related('problem').all()

    return render(request, 'duels/match_result.html', {
        'match': match,
        'my_participant': my_participant,
        'opp_participant': opp_participant,
        'match_problems': match_problems,
    })
