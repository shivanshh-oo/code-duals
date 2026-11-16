from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone
from problems.models import Problem
from .models import (Match, Participant, Submission, MatchProblem, Friendship,
                     Notification, Achievement, UserAchievement)
from .judge import judge_submission
from .matching import WaitingList, create_private_match, _pick_problems


@login_required
def play(request):
    """Play page with quick match and create private match options."""
    notifications = request.user.duel_notifications.filter(is_read=False)[:5]
    friends = _friends(request.user)
    return render(request, 'duels/play.html', {'notifications': notifications, 'friends': friends})


def leaderboard(request):
    from accounts.models import Profile
    return render(request, 'duels/leaderboard.html', {'players': Profile.objects.filter(placement_done=True).select_related('user').order_by('-rating', 'user__username')})


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
    result = judge_submission(code, all_tests, problem.time_limit_sec, request.POST.get('language', 'python'))
    if result.get('error'):
        return JsonResponse({'error': result['error']}, status=400)

    # Save submission for unlock tracking
    practice_match, _ = Match.objects.get_or_create(
        invite_code=f'PRACTICE-{request.user.id}',
        defaults={'status': 'finished', 'difficulty': problem.difficulty, 'duration_minutes': 0}
    )
    participant, _ = Participant.objects.get_or_create(match=practice_match, user=request.user)
    MatchProblem.objects.get_or_create(match=practice_match, problem=problem)

    submission = Submission.objects.create(
        participant=participant, problem=problem, code=code,
        verdict=result['verdict'], tests_passed=result['tests_passed'],
        tests_total=result['tests_total'], runtime_ms=result['runtime_ms'],
    )
    _after_submission(submission)

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
    try:
        duration = int(request.POST.get('duration', 30))
    except ValueError:
        return JsonResponse({'error': 'Invalid duration'}, status=400)
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
    problem = get_object_or_404(Problem, pk=problem_id, is_draft=False, matchproblem__match=match)

    # Check match is still active
    _check_match_end(match)
    if match.status != 'active':
        return JsonResponse({'error': 'Match has ended'}, status=400)

    code = request.POST.get('code', '')
    if not code.strip():
        return JsonResponse({'error': 'No code submitted'}, status=400)

    # Judge
    all_tests = problem.test_cases.all()
    result = judge_submission(code, all_tests, problem.time_limit_sec, request.POST.get('language', 'python'))
    if result.get('error'):
        return JsonResponse({'error': result['error']}, status=400)

    # Calculate time taken since match start
    time_taken = 0
    if match.started_at:
        time_taken = (timezone.now() - match.started_at).total_seconds()

    submission = Submission.objects.create(
        participant=participant, problem=problem, code=code,
        verdict=result['verdict'], tests_passed=result['tests_passed'],
        tests_total=result['tests_total'], time_taken=time_taken, runtime_ms=result['runtime_ms'],
    )
    _after_submission(submission)

    # Update solved count
    if result['verdict'] == 'Accepted':
        # Check if this problem wasn't already solved
        already_solved = Submission.objects.filter(
            participant=participant, problem=problem, verdict='Accepted'
        ).count()
        if already_solved == 1:  # The one we just created
            participant.problems_solved += 1
            participant.save()

    broadcast(match, 'opponent_progress')
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
        if p1.abandoned:
            match.winner = p2.user
        elif p2.abandoned:
            match.winner = p1.user
        elif p1.problems_solved > p2.problems_solved:
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
        if match.winner:
            _award(match.winner, 'first_win', 'First Victory', 'Won a coding duel', 'W', 200)

    for p in participants:
        if not p.finished_at:
            p.finished_at = timezone.now()
            p.save()

    match.save()
    broadcast(match, 'match_finished')


def _total_time(participant):
    """Sum of time_taken for accepted submissions."""
    accepted = participant.submissions.filter(verdict='Accepted')
    return sum(s.time_taken for s in accepted)


# --- Match Result ---

@login_required
def match_result(request, match_id):
    """Show match result with rating changes."""
    match = get_object_or_404(Match, pk=match_id, status='finished')
    get_object_or_404(Participant, match=match, user=request.user)
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


@login_required
def join_match(request, invite_code):
    from django.db import transaction
    match = get_object_or_404(Match, invite_code=invite_code, is_private=True)
    if request.method == 'POST':
        with transaction.atomic():
            match = Match.objects.select_for_update().get(pk=match.pk)
            if not match.participants.filter(user=request.user).exists():
                if match.status != 'waiting' or match.participants.count() >= 2:
                    return JsonResponse({'error': 'Room unavailable'}, status=400)
                Participant.objects.create(match=match, user=request.user)
                broadcast(match, 'player_joined')
        return redirect('match_arena', match_id=match.pk)
    return render(request, 'duels/join.html', {'match': match})


def broadcast(match, event):
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    async_to_sync(get_channel_layer().group_send)(f'duel_{match.invite_code}', {'type': 'duel.event', 'event': event})


@login_required
@require_POST
def ready_match(request, match_id):
    from django.db import transaction
    with transaction.atomic():
        match = get_object_or_404(Match.objects.select_for_update(), pk=match_id)
        player = get_object_or_404(Participant, match=match, user=request.user)
        if match.status == 'waiting':
            player.is_ready = not player.is_ready
            player.save()
            broadcast(match, 'player_ready')
            if match.participants.count() == 2 and not match.participants.filter(is_ready=False).exists():
                problems = _pick_problems(match.difficulty, request.user.profile.rating)
                if not problems:
                    return JsonResponse({'error': 'No problems available'}, status=400)
                for problem in problems:
                    MatchProblem.objects.get_or_create(match=match, problem=problem)
                match.status = 'active'
                match.started_at = timezone.now()
                match.ends_at = match.started_at + timezone.timedelta(minutes=match.duration_minutes)
                match.save()
                broadcast(match, 'match_started')
    return redirect('match_arena', match_id=match.pk)


def leaderboard_csv(request):
    import csv
    from django.http import HttpResponse
    from accounts.models import Profile
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="leaderboard.csv"'
    writer = csv.writer(response)
    writer.writerow(['Rank', 'Player', 'Rating'])
    for rank, p in enumerate(Profile.objects.filter(placement_done=True).select_related('user').order_by('-rating', 'user__username'), 1):
        name = p.user.username
        if name.startswith(('=', '+', '-', '@')):
            name = "'" + name
        writer.writerow([rank, name, p.rating])
    return response


def _friends(user):
    ids = list(Friendship.objects.filter(sender=user, status='accepted').values_list('receiver_id', flat=True))
    ids += list(Friendship.objects.filter(receiver=user, status='accepted').values_list('sender_id', flat=True))
    from django.contrib.auth.models import User
    return User.objects.filter(id__in=ids).select_related('profile')


def _after_submission(submission):
    """Award progress and flag obvious copied accepted solutions."""
    if submission.verdict == 'Accepted':
        profile = submission.participant.user.profile
        profile.xp += 50
        profile.save(update_fields=['xp'])
        _award(submission.participant.user, 'first_solve', 'First Solve', 'Solved a coding problem', 'OK', 100)
        normalized = ''.join(submission.code.split())
        for other in Submission.objects.filter(problem=submission.problem, verdict='Accepted').exclude(pk=submission.pk).only('code'):
            other_code = ''.join(other.code.split())
            if normalized and normalized == other_code:
                submission.similarity_percent = 100
                submission.is_flagged = True
                submission.save(update_fields=['similarity_percent', 'is_flagged'])
                break


def _award(user, code, name, description, icon, xp_reward):
    achievement, _ = Achievement.objects.get_or_create(code=code, defaults={
        'name': name, 'description': description, 'icon': icon, 'xp_reward': xp_reward})
    _, created = UserAchievement.objects.get_or_create(user=user, achievement=achievement)
    if created:
        user.profile.xp += achievement.xp_reward
        user.profile.save(update_fields=['xp'])
        Notification.objects.create(user=user, message=f'Badge earned: {achievement.name}', url='/accounts/profile/')


@login_required
def submission_history(request):
    items = Submission.objects.filter(participant__user=request.user).select_related('problem', 'participant__match').order_by('-submitted_at')
    return render(request, 'duels/submission_history.html', {'submissions': items})


@login_required
def match_history(request):
    items = Participant.objects.filter(user=request.user, match__status='finished', match__duration_minutes__gt=0).select_related('match', 'match__winner').order_by('-match__created_at')
    return render(request, 'duels/match_history.html', {'participations': items})


@login_required
def friends(request):
    pending = Friendship.objects.filter(receiver=request.user, status='pending').select_related('sender')
    return render(request, 'duels/friends.html', {'friends': _friends(request.user), 'pending': pending})


@login_required
@require_POST
def add_friend(request):
    from django.contrib.auth.models import User
    target = get_object_or_404(User, username=request.POST.get('username', '').strip())
    if target == request.user:
        return JsonResponse({'error': 'You cannot add yourself'}, status=400)
    relation, created = Friendship.objects.get_or_create(sender=request.user, receiver=target)
    if created:
        Notification.objects.create(user=target, message=f'{request.user.username} sent you a friend request', url='/duels/friends/')
    return redirect('friends')


@login_required
@require_POST
def accept_friend(request, friendship_id):
    relation = get_object_or_404(Friendship, pk=friendship_id, receiver=request.user, status='pending')
    relation.status = 'accepted'; relation.save(update_fields=['status'])
    Notification.objects.create(user=relation.sender, message=f'{request.user.username} accepted your friend request', url='/duels/friends/')
    return redirect('friends')


@login_required
@require_POST
def challenge_friend(request, user_id):
    friend = get_object_or_404(_friends(request.user), pk=user_id)
    match = create_private_match(request.user, request.POST.get('difficulty', 'Medium'), 30)
    Notification.objects.create(user=friend, message=f'{request.user.username} challenged you to a duel', url=f'/duels/join/{match.invite_code}/')
    return redirect('match_arena', match_id=match.pk)


@login_required
def notifications(request):
    items = request.user.duel_notifications.order_by('-created_at')
    items.update(is_read=True)
    return render(request, 'duels/notifications.html', {'notifications': items})


@login_required
@require_POST
def rematch(request, match_id):
    old = get_object_or_404(Match, pk=match_id, status='finished', participants__user=request.user)
    opponent = old.participants.exclude(user=request.user).first()
    match = create_private_match(request.user, old.difficulty, old.duration_minutes)
    match.rematch_of = old; match.save(update_fields=['rematch_of'])
    if opponent:
        Notification.objects.create(user=opponent.user, message=f'{request.user.username} requested a rematch', url=f'/duels/join/{match.invite_code}/')
    return redirect('match_arena', match_id=match.pk)


def spectate(request, match_id):
    match = get_object_or_404(Match, pk=match_id)
    participants = match.participants.select_related('user')
    # Spectators receive score data only; code is never included.
    return render(request, 'duels/spectate.html', {'match': match, 'participants': participants})


def spectator_status(request, match_id):
    match = get_object_or_404(Match, pk=match_id)
    data = [{'name': p.user.username, 'solved': p.problems_solved} for p in match.participants.select_related('user')]
    return JsonResponse({'status': match.status, 'players': data})


@login_required
def daily_challenge(request):
    from datetime import date, timedelta
    profile = request.user.profile
    today = date.today()
    if profile.last_active_date != today:
        profile.login_streak = profile.login_streak + 1 if profile.last_active_date == today - timedelta(days=1) else 1
        profile.last_active_date = today
        profile.xp += 10
        profile.save(update_fields=['login_streak', 'last_active_date', 'xp'])
        if profile.login_streak >= 7:
            _award(request.user, 'week_streak', 'Seven Day Streak', 'Logged in seven days in a row', '7', 250)
    candidates = list(Problem.objects.filter(is_draft=False, is_placement=False))
    problem = candidates[today.toordinal() % len(candidates)] if candidates else None
    return render(request, 'duels/daily.html', {'problem': problem})


@login_required
@require_POST
def abandon_match(request, match_id):
    match = get_object_or_404(Match, pk=match_id, status='active')
    participant = get_object_or_404(Participant, match=match, user=request.user)
    participant.abandoned = True
    participant.save(update_fields=['abandoned'])
    profile = request.user.profile
    profile.queue_dodges += 1
    profile.rating = max(100, profile.rating - min(30, 5 * profile.queue_dodges))
    profile.save(update_fields=['queue_dodges', 'rating'])
    opponent = match.participants.exclude(user=request.user).first()
    if opponent:
        match.winner = opponent.user
    _finish_match(match)
    return redirect('match_result', match_id=match.pk)
