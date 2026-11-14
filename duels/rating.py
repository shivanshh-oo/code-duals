"""
Rating module: Elo with speed bonus.
"""


def update_ratings(match, p1, p2):
    """Update ratings for both participants after a match ends. Called once."""
    if p1.rating_change != 0 or p2.rating_change != 0:
        return  # Already updated

    r1 = p1.user.profile.rating
    r2 = p2.user.profile.rating
    total_problems = match.match_problems.count()
    time_limit = match.duration_minutes * 60  # in seconds

    perf1 = _performance(p1, total_problems, time_limit)
    perf2 = _performance(p2, total_problems, time_limit)

    # Expected scores (Elo)
    exp1 = 1 / (1 + 10 ** ((r2 - r1) / 400))
    exp2 = 1 / (1 + 10 ** ((r1 - r2) / 400))

    # Actual scores based on performance
    if perf1 + perf2 > 0:
        score1 = perf1 / (perf1 + perf2)
        score2 = perf2 / (perf1 + perf2)
    else:
        score1 = 0.5
        score2 = 0.5

    change1 = round(32 * (score1 - exp1))
    change2 = round(32 * (score2 - exp2))

    # Winner must gain at least +1, loser must lose at least 1
    if match.winner:
        if match.winner == p1.user:
            change1 = max(1, change1)
            change2 = min(-1, change2)
        elif match.winner == p2.user:
            change2 = max(1, change2)
            change1 = min(-1, change1)

    # Apply changes
    p1.rating_change = change1
    p2.rating_change = change2
    p1.save()
    p2.save()

    profile1 = p1.user.profile
    profile2 = p2.user.profile
    profile1.rating = max(100, profile1.rating + change1)  # Min rating = 100
    profile2.rating = max(100, profile2.rating + change2)
    profile1.save()
    profile2.save()


def _performance(participant, total_problems, time_limit):
    """Calculate performance = 0.7 * correctness + 0.3 * speed."""
    if total_problems == 0:
        return 0

    # Correctness: tests_passed / tests_total across all submissions
    total_tests_passed = 0
    total_tests_total = 0
    for sub in participant.submissions.all():
        total_tests_passed += sub.tests_passed
        total_tests_total += sub.tests_total

    correctness = total_tests_passed / total_tests_total if total_tests_total > 0 else 0

    # Speed: 1 - (avg_time_taken / time_limit), minimum 0
    accepted_subs = participant.submissions.filter(verdict='Accepted')
    if accepted_subs.exists() and time_limit > 0:
        avg_time = sum(s.time_taken for s in accepted_subs) / accepted_subs.count()
        speed = max(0, 1 - avg_time / time_limit)
    else:
        speed = 0

    return 0.7 * correctness + 0.3 * speed
