from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .forms import RegisterForm
from problems.models import Problem
from duels.judge import judge_submission


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, 'Registration successful! Welcome to CodeDuels.')
            return redirect('placement')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Redirect to placement if not done
            if not user.profile.placement_done:
                return redirect('placement')
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'accounts/login.html')


def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def profile(request):
    return render(request, 'accounts/profile.html')


@login_required
def placement(request):
    """Placement test page."""
    if request.user.profile.placement_done:
        messages.info(request, 'You have already completed the placement test.')
        return redirect('profile')

    problems = Problem.objects.filter(
        is_placement=True, is_draft=False
    ).order_by('difficulty_rating')

    return render(request, 'accounts/placement.html', {
        'problems': problems,
        'total_problems': problems.count(),
    })


@login_required
@require_POST
def placement_submit(request):
    """Handle placement test submission. Expects JSON with answers for each problem."""
    if request.user.profile.placement_done:
        return JsonResponse({'error': 'Placement already completed'}, status=400)

    problems = Problem.objects.filter(
        is_placement=True, is_draft=False
    ).order_by('difficulty_rating')

    total_score = 0
    max_score = 0
    results = []

    for problem in problems:
        code = request.POST.get(f'code_{problem.id}', '').strip()
        language = request.POST.get(f'language_{problem.id}', 'python')
        max_score += 1

        sample_count = problem.test_cases.filter(is_sample=True).count()
        total_count = problem.test_cases.count()
        hidden_count = total_count - sample_count

        if code:
            all_tests = problem.test_cases.all()
            result = judge_submission(code, all_tests, problem.time_limit_sec, language=language)
            if result['verdict'] == 'Accepted':
                total_score += 1
            results.append({
                'problem': problem.title,
                'verdict': result['verdict'],
                'tests_passed': result['tests_passed'],
                'tests_total': result['tests_total'],
                'sample_tests_count': sample_count,
                'hidden_tests_count': hidden_count,
            })
        else:
            results.append({
                'problem': problem.title,
                'verdict': 'Not Submitted',
                'tests_passed': 0,
                'tests_total': total_count,
                'sample_tests_count': sample_count,
                'hidden_tests_count': hidden_count,
            })

    # Calculate rating: 800 + 1200 * (score / max_score)
    if max_score > 0:
        rating = round(800 + 1200 * (total_score / max_score))
    else:
        rating = 1000

    # Save to profile
    profile = request.user.profile
    profile.rating = rating
    profile.placement_done = True
    profile.save()

    return JsonResponse({
        'rating': rating,
        'score': total_score,
        'max_score': max_score,
        'results': results,
    })
