from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Problem, Solution
from django.db.models import Q


def problem_list(request):
    """Question bank page - renders the template."""
    return render(request, 'problems/problem_list.html')


def problem_list_api(request):
    """JSON endpoint for fetching problems with search and filter."""
    problems = Problem.objects.filter(Q(is_draft=False) | Q(is_draft=True, test_cases__is_sample=True)).distinct()

    search = request.GET.get('search', '').strip()
    category = request.GET.get('category', '').strip()
    difficulty = request.GET.get('difficulty', '').strip()

    if search:
        problems = problems.filter(title__icontains=search)
    if category:
        problems = problems.filter(category=category)
    if difficulty:
        problems = problems.filter(difficulty=difficulty)

    data = []
    for p in problems:
        data.append({
            'id': p.id,
            'source': 'Codeforces' if (p.source_url or '').startswith('https://codeforces.com/') else 'LeetCode' if (p.source_url or '').startswith('https://leetcode.com/') else 'CodeDuels',
            'url': f'/problems/{p.id}/',
            'title': p.title,
            'category': p.category,
            'difficulty': p.difficulty,
            'difficulty_rating': p.difficulty_rating,
        })
    return JsonResponse({'problems': data})


def problem_detail(request, pk):
    """Problem detail page with statement and sample test cases."""
    problem = get_object_or_404(Problem.objects.filter(Q(is_draft=False) | Q(is_draft=True, test_cases__is_sample=True)).distinct(), pk=pk)
    sample_tests = problem.test_cases.filter(is_sample=True)
    total_tests_count = problem.test_cases.count()
    hidden_tests_count = total_tests_count - sample_tests.count()

    # Check if user can see the solution
    can_see_solution = False
    if request.user.is_authenticated:
        can_see_solution = _user_can_see_solution(request.user, problem)

    solution = None
    if can_see_solution:
        try:
            solution = problem.solution
        except Solution.DoesNotExist:
            solution = None

    return render(request, 'problems/problem_detail.html', {
        'problem': problem,
        'sample_tests': sample_tests,
        'total_tests_count': total_tests_count,
        'hidden_tests_count': hidden_tests_count,
        'can_see_solution': can_see_solution,
        'solution': solution,
    })


def _user_can_see_solution(user, problem):
    """Check if user has solved this problem or finished a match containing it.
    Returns True only if:
      - User has an Accepted submission in practice, OR
      - User participated in a finished match that contained this problem.
    """
    # Import here to avoid circular imports
    from duels.models import Submission, MatchProblem, Participant

    # Check practice submissions (Accepted verdict)
    has_accepted = Submission.objects.filter(
        participant__user=user,
        problem=problem,
        verdict='Accepted'
    ).exists()
    if has_accepted:
        return True

    # Check finished matches that contain this problem
    match_problem_ids = MatchProblem.objects.filter(problem=problem).values_list('match_id', flat=True)
    participated_in_finished = Participant.objects.filter(
        user=user,
        match_id__in=match_problem_ids,
        match__status='finished',
        match__duration_minutes__gt=0
    ).exists()
    return participated_in_finished
