from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponseBadRequest
from django.utils import timezone
from duels.judge import judge_submission
from problems.models import Problem
from .models import InterviewTrack, TrackProblem, InterviewSession, InterviewSubmission


@login_required
def track_list(request):
    """Catalog of interview tracks with candidate history."""
    tracks = InterviewTrack.objects.prefetch_related('trackproblem_set__problem').all()
    user_sessions = InterviewSession.objects.filter(user=request.user).order_by('-started_at')

    # Map track_id to latest session
    latest_sessions = {}
    for s in user_sessions:
        if s.track_id not in latest_sessions:
            latest_sessions[s.track_id] = s

    track_data = []
    for t in tracks:
        track_data.append({
            'track': t,
            'problem_count': t.trackproblem_set.count(),
            'last_session': latest_sessions.get(t.id),
        })

    return render(request, 'interviews/track_list.html', {
        'track_data': track_data,
    })


@login_required
@require_POST
def start_interview(request, track_id):
    """Start a new interview session."""
    track = get_object_or_404(InterviewTrack, pk=track_id)
    # If there is an active session in progress, resume it
    existing = InterviewSession.objects.filter(
        user=request.user, track=track, status='in_progress'
    ).first()
    if existing:
        return redirect('interview_session', session_id=existing.id)

    session = InterviewSession.objects.create(
        user=request.user,
        track=track,
        status='in_progress',
    )
    return redirect('interview_session', session_id=session.id)


@login_required
def interview_session(request, session_id):
    """The distraction-free interview exam room."""
    session = get_object_or_404(InterviewSession, pk=session_id, user=request.user)
    if session.status != 'in_progress':
        return redirect('interview_report', session_id=session.id)

    track_problems = session.track.trackproblem_set.select_related('problem').all()
    # Check if time expired
    now = timezone.now()
    duration_secs = session.track.time_limit_minutes * 60
    elapsed = (now - session.started_at).total_seconds()
    if elapsed >= duration_secs:
        _finalize_session(session)
        return redirect('interview_report', session_id=session.id)

    time_remaining_seconds = max(0, int(duration_secs - elapsed))

    # Collect latest submission per problem for this session
    user_subs = {}
    for sub in session.submissions.all().order_by('submitted_at'):
        user_subs[sub.problem_id] = sub

    problem_items = []
    for tp in track_problems:
        sample_tests = tp.problem.test_cases.filter(is_sample=True)
        total_tests = tp.problem.test_cases.count()
        problem_items.append({
            'track_problem': tp,
            'problem': tp.problem,
            'sample_tests': sample_tests,
            'total_tests': total_tests,
            'hidden_tests': total_tests - sample_tests.count(),
            'latest_submission': user_subs.get(tp.problem_id),
        })

    return render(request, 'interviews/session_room.html', {
        'session': session,
        'track': session.track,
        'problem_items': problem_items,
        'time_remaining_seconds': time_remaining_seconds,
    })


@login_required
@require_POST
def submit_interview_problem(request, session_id, problem_id):
    """Submit code for an interview problem."""
    session = get_object_or_404(InterviewSession, pk=session_id, user=request.user)
    if session.status != 'in_progress':
        return JsonResponse({'error': 'Interview session has ended'}, status=400)

    problem = get_object_or_404(Problem, pk=problem_id)
    code = request.POST.get('code', '')
    if not code.strip():
        return JsonResponse({'error': 'No code provided'}, status=400)

    all_tests = problem.test_cases.all()
    language = request.POST.get('language', 'python')
    result = judge_submission(code, all_tests, problem.time_limit_sec, language)
    if result.get('error'):
        return JsonResponse({'error': result['error']}, status=400)

    time_taken = (timezone.now() - session.started_at).total_seconds()

    submission = InterviewSubmission.objects.create(
        session=session,
        problem=problem,
        code=code,
        verdict=result['verdict'],
        tests_passed=result['tests_passed'],
        tests_total=result['tests_total'],
        time_taken=time_taken,
        runtime_ms=result['runtime_ms'],
    )

    sample_count = problem.test_cases.filter(is_sample=True).count()
    hidden_count = all_tests.count() - sample_count

    return JsonResponse({
        'verdict': result['verdict'],
        'tests_passed': result['tests_passed'],
        'tests_total': result['tests_total'],
        'sample_tests_count': sample_count,
        'hidden_tests_count': hidden_count,
    })


@login_required
@require_POST
def finish_interview(request, session_id):
    """End the interview session early or on completion."""
    session = get_object_or_404(InterviewSession, pk=session_id, user=request.user)
    if session.status == 'in_progress':
        _finalize_session(session)
    return redirect('interview_report', session_id=session.id)


def _finalize_session(session):
    """Calculate aggregate score, tests ratio, and complete the session."""
    session.status = 'completed'
    session.completed_at = timezone.now()
    session.time_spent_seconds = int((session.completed_at - session.started_at).total_seconds())

    track_problems = session.track.trackproblem_set.all()
    total_problems = track_problems.count()

    total_tests = 0
    passed_tests = 0
    solved_count = 0

    for tp in track_problems:
        latest = session.submissions.filter(problem=tp.problem).order_by('-submitted_at').first()
        if latest:
            passed_tests += latest.tests_passed
            total_tests += latest.tests_total
            if latest.verdict == 'Accepted':
                solved_count += 1
        else:
            total_tests += tp.problem.test_cases.count()

    ratio = (passed_tests / total_tests) if total_tests > 0 else 0
    # Score out of 100 based on problems solved, correctness, and time efficiency
    score = (solved_count / max(1, total_problems)) * 70 + (ratio * 30)
    session.total_score = round(score, 1)
    session.tests_passed_ratio = round(ratio, 3)
    session.save()


@login_required
def interview_report(request, session_id):
    """Post-interview diagnostic performance comparison report."""
    session = get_object_or_404(InterviewSession, pk=session_id, user=request.user)
    if session.status == 'in_progress':
        # Auto-finish if time has expired
        duration_secs = session.track.time_limit_minutes * 60
        if (timezone.now() - session.started_at).total_seconds() >= duration_secs:
            _finalize_session(session)
        else:
            return redirect('interview_session', session_id=session.id)

    track = session.track
    # Calculate historical comparison metrics among all completed attempts for this track
    all_sessions = InterviewTrack.objects.get(pk=track.pk).sessions.filter(status='completed')
    total_attempts = all_sessions.count()

    # Percentile calculation
    if total_attempts > 1:
        lower_scores = all_sessions.filter(total_score__lt=session.total_score).count()
        equal_scores = all_sessions.filter(total_score=session.total_score).count()
        percentile = round(((lower_scores + (0.5 * equal_scores)) / total_attempts) * 100)
    else:
        percentile = 85  # Default benchmark when first attempt

    # Average metrics
    avg_score = round(sum(s.total_score for s in all_sessions) / max(1, total_attempts), 1)
    avg_time = round(sum(s.time_spent_seconds for s in all_sessions) / max(1, total_attempts))

    # Per-problem scorecard
    track_problems = track.trackproblem_set.select_related('problem').all()
    scorecard = []
    total_runtime = 0

    for tp in track_problems:
        prob = tp.problem
        subs = session.submissions.filter(problem=prob).order_by('-submitted_at')
        latest = subs.first()
        sample_count = prob.test_cases.filter(is_sample=True).count()
        total_count = prob.test_cases.count()

        if latest:
            total_runtime += latest.runtime_ms
            scorecard.append({
                'order': tp.order,
                'phase': tp.phase_label,
                'title': prob.title,
                'difficulty': prob.difficulty,
                'verdict': latest.verdict,
                'tests_passed': latest.tests_passed,
                'tests_total': latest.tests_total,
                'sample_count': sample_count,
                'hidden_count': total_count - sample_count,
                'runtime_ms': latest.runtime_ms,
                'time_taken': int(latest.time_taken),
                'attempts': subs.count(),
            })
        else:
            scorecard.append({
                'order': tp.order,
                'phase': tp.phase_label,
                'title': prob.title,
                'difficulty': prob.difficulty,
                'verdict': 'Unattempted',
                'tests_passed': 0,
                'tests_total': total_count,
                'sample_count': sample_count,
                'hidden_count': total_count - sample_count,
                'runtime_ms': 0,
                'time_taken': 0,
                'attempts': 0,
            })

    # Skill dimensions (0 - 100%)
    edge_cases = round(session.tests_passed_ratio * 100)
    time_limit_sec = track.time_limit_minutes * 60
    speed_factor = max(10, min(100, round((1.0 - (session.time_spent_seconds / max(1, time_limit_sec))) * 100)))
    optimization = 90 if total_runtime < 500 else 75 if total_runtime < 2000 else 55

    return render(request, 'interviews/report.html', {
        'session': session,
        'track': track,
        'percentile': percentile,
        'total_attempts': total_attempts,
        'avg_score': avg_score,
        'avg_time_minutes': round(avg_time / 60, 1),
        'user_time_minutes': round(session.time_spent_seconds / 60, 1),
        'scorecard': scorecard,
        'skill_edge_cases': edge_cases,
        'skill_speed': speed_factor,
        'skill_optimization': optimization,
    })
