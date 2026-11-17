"""
Rating module: Elo with speed bonus.
"""


def update_ratings(match, p1, p2):
    """Update ratings for both participants after a 1v1 match ends. Called once."""
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


def update_ratings_2v2(match, team_a_participants, team_b_participants, winning_team):
    """
    Update Elo ratings for 2v2 match.
    Team average rating determines expected outcome.
    Winning team members gain points adjusted for individual performance,
    and losing members lose points accordingly.
    """
    if any(p.rating_change != 0 for p in team_a_participants + team_b_participants):
        return  # Already updated

    total_problems = match.match_problems.count()
    time_limit = match.duration_minutes * 60

    rA = sum(p.user.profile.rating for p in team_a_participants) / max(1, len(team_a_participants))
    rB = sum(p.user.profile.rating for p in team_b_participants) / max(1, len(team_b_participants))

    expA = 1 / (1 + 10 ** ((rB - rA) / 400))
    expB = 1 / (1 + 10 ** ((rA - rB) / 400))

    perf_map = {}
    for p in team_a_participants + team_b_participants:
        perf_map[p.id] = _performance(p, total_problems, time_limit)

    perfA = sum(perf_map[p.id] for p in team_a_participants)
    perfB = sum(perf_map[p.id] for p in team_b_participants)

    if winning_team == 'team_a':
        scoreA, scoreB = 1.0, 0.0
    elif winning_team == 'team_b':
        scoreA, scoreB = 0.0, 1.0
    else:
        scoreA = (perfA / (perfA + perfB)) if (perfA + perfB) > 0 else 0.5
        scoreB = 1.0 - scoreA

    team_change_A = 32 * (scoreA - expA)
    team_change_B = 32 * (scoreB - expB)

    # Distribute within Team A
    total_perf_a = sum(perf_map[p.id] for p in team_a_participants)
    for p in team_a_participants:
        weight = (perf_map[p.id] / total_perf_a) if total_perf_a > 0 else 0.5
        # Individual adjustment relative to equal split
        ind_change = round(team_change_A * (0.6 + 0.8 * weight))
        if winning_team == 'team_a':
            ind_change = max(1, ind_change)
        elif winning_team == 'team_b':
            ind_change = min(-1, ind_change)
        p.rating_change = ind_change
        p.save(update_fields=['rating_change'])
        profile = p.user.profile
        profile.rating = max(100, profile.rating + ind_change)
        profile.save(update_fields=['rating'])

    # Distribute within Team B
    total_perf_b = sum(perf_map[p.id] for p in team_b_participants)
    for p in team_b_participants:
        weight = (perf_map[p.id] / total_perf_b) if total_perf_b > 0 else 0.5
        ind_change = round(team_change_B * (0.6 + 0.8 * weight))
        if winning_team == 'team_b':
            ind_change = max(1, ind_change)
        elif winning_team == 'team_a':
            ind_change = min(-1, ind_change)
        p.rating_change = ind_change
        p.save(update_fields=['rating_change'])
        profile = p.user.profile
        profile.rating = max(100, profile.rating + ind_change)
        profile.save(update_fields=['rating'])


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
