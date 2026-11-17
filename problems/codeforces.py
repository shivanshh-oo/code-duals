"""
Codeforces API integration for CodeDuels.

Fetches problem metadata from the official Codeforces API and generates
test cases by executing the reference solution against programmatically
generated inputs.

Codeforces API docs: https://codeforces.com/apiHelp
"""
import random
import subprocess
import sys
import tempfile
import os
import time
import requests
from django.db import transaction
from .models import Problem, TestCase, Solution

CODEFORCES_API_BASE = 'https://codeforces.com/api/'

# Map Codeforces rating → CodeDuels difficulty label & rating
def _map_difficulty(cf_rating):
    if cf_rating is None or cf_rating < 1200:
        return 'Easy', max(800, cf_rating or 800)
    elif cf_rating < 1700:
        return 'Medium', cf_rating
    else:
        return 'Hard', min(2000, cf_rating)


def fetch_problemset(tags=None, limit=0):
    """
    Call the Codeforces problemset.problems API.

    Args:
        tags: list of tag strings to filter by (e.g. ['implementation', 'math'])
        limit: max number of problems to return (0 = all)

    Returns:
        list of dicts with keys: contestId, index, name, rating, tags, source_url
    """
    params = {}
    if tags:
        params['tags'] = ';'.join(tags)
    response = requests.get(CODEFORCES_API_BASE + 'problemset.problems', params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if payload.get('status') != 'OK':
        raise ValueError(f"Codeforces API error: {payload.get('comment', 'unknown error')}")

    problems = payload['result']['problems']
    result = []
    for p in problems:
        contest_id = p.get('contestId')
        index = p.get('index', '')
        if not contest_id or not index:
            continue
        source_url = f'https://codeforces.com/problemset/problem/{contest_id}/{index}'
        rating = p.get('rating')  # may be None for unrated
        difficulty, cf_rating = _map_difficulty(rating)
        result.append({
            'contestId': contest_id,
            'index': index,
            'name': p['name'],
            'rating': rating,
            'tags': p.get('tags', []),
            'source_url': source_url,
            'difficulty': difficulty,
            'difficulty_rating': cf_rating,
        })

    if limit:
        result = result[:limit]
    return result


def sync_codeforces_catalogue(limit=0, tags=None):
    """
    Sync Codeforces problem metadata into the database as drafts.

    Returns (created, updated) counts.  Problems are stored as drafts until
    test cases and a reference solution are added (via seed_codeforces or
    import_problem_bundle).
    """
    problems = fetch_problemset(tags=tags, limit=limit)
    created = updated = 0
    with transaction.atomic():
        for p in problems:
            problem, new = Problem.objects.get_or_create(
                source_url=p['source_url'],
                defaults={
                    'title': p['name'][:200],
                    'statement': (
                        f"Solve problem {p['index']} from Codeforces contest {p['contestId']}.\n\n"
                        f"Read the full statement at: {p['source_url']}\n\n"
                        f"Tags: {', '.join(p['tags']) if p['tags'] else 'None'}\n\n"
                        "Input/Output: Standard input/output as specified in the problem statement."
                    ),
                    'category': 'DSA',
                    'difficulty': p['difficulty'],
                    'difficulty_rating': p['difficulty_rating'],
                    'is_draft': True,
                }
            )
            if new:
                created += 1
            elif problem.is_draft:
                problem.title = p['name'][:200]
                problem.difficulty = p['difficulty']
                problem.difficulty_rating = p['difficulty_rating']
                problem.save(update_fields=['title', 'difficulty', 'difficulty_rating'])
                updated += 1
    return created, updated


# ---------------------------------------------------------------------------
# Curated problems: hand-written statements + reference solutions + test
# case generators so CodeDuels can judge them locally.
# These are well-known Codeforces-style problems with standard I/O.
# ---------------------------------------------------------------------------

def _run_reference(reference_code, input_str, timeout=5):
    """Execute a Python reference solution with given stdin and return stdout."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(reference_code)
        fname = f.name
    try:
        result = subprocess.run(
            [sys.executable, fname],
            input=input_str,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            raise RuntimeError(f'Reference solution error: {result.stderr[:300]}')
        return result.stdout.strip()
    finally:
        os.unlink(fname)


def _generate_test_cases(generator_fn, reference_code, n_sample=3, n_hidden=32):
    """
    Generate test cases by running a generator and a reference solution.

    Args:
        generator_fn: callable() → input_str
        reference_code: Python solution string
        n_sample: number of sample (visible) test cases
        n_hidden: number of hidden test cases

    Returns:
        list of dicts: {input, expected_output, is_sample}
    """
    tests = []
    total = n_sample + n_hidden
    for i in range(total):
        inp = generator_fn()
        out = _run_reference(reference_code, inp)
        tests.append({
            'input': inp,
            'expected_output': out,
            'is_sample': i < n_sample,
        })
    return tests


# ---------------------------------------------------------------------------
# Curated problem definitions
# ---------------------------------------------------------------------------

CURATED_CF_PROBLEMS = [
    # ------------------------------------------------------------------ Easy
    {
        'title': 'Watermelon',
        'source_url': 'https://codeforces.com/problemset/problem/4/A',
        'statement': (
            'Pete and Billy have bought a watermelon. They want to divide it equally between them and '
            'each get an even number of kilos. Help them figure out if this is possible.\n\n'
            'Input: a single integer w (1 ≤ w ≤ 100) — the weight of the watermelon.\n'
            'Output: Print "YES" if it is possible, "NO" otherwise.'
        ),
        'difficulty': 'Easy',
        'difficulty_rating': 800,
        'time_limit_sec': 2,
        'explanation': (
            'The watermelon can be divided into two even parts if and only if w is even AND w > 2 '
            '(since both parts must be at least 2).'
        ),
        'reference_code': (
            'w = int(input())\n'
            'print("YES" if w % 2 == 0 and w > 2 else "NO")\n'
        ),
        'generator': lambda: str(random.randint(1, 100)),
    },
    {
        'title': 'Way Too Long Words',
        'source_url': 'https://codeforces.com/problemset/problem/71/A',
        'statement': (
            'Sometimes students write long words and want to abbreviate them. The rule is: if the word '
            'has more than 10 characters, replace it with its first character, the number of characters '
            'between the first and last, and its last character. Otherwise keep the word as is.\n\n'
            'Input: first line is n (1 ≤ n ≤ 100), then n lines each containing a word of lowercase '
            'English letters (length 1 to 100).\n'
            'Output: n lines, each with the (possibly abbreviated) word.'
        ),
        'difficulty': 'Easy',
        'difficulty_rating': 800,
        'time_limit_sec': 2,
        'explanation': (
            'For each word, check its length. If > 10, output first_char + (len-2) + last_char. '
            'Otherwise print it unchanged.'
        ),
        'reference_code': (
            'n = int(input())\n'
            'for _ in range(n):\n'
            '    w = input()\n'
            '    if len(w) > 10:\n'
            '        print(f"{w[0]}{len(w)-2}{w[-1]}")\n'
            '    else:\n'
            '        print(w)\n'
        ),
        'generator': lambda: (
            lambda n: str(n) + '\n' + '\n'.join(
                ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=random.randint(1, 20)))
                for _ in range(n)
            )
        )(random.randint(1, 10)),
    },
    {
        'title': 'Minimum Number of Moves',
        'source_url': 'https://codeforces.com/problemset/problem/1A',
        'statement': (
            'Theatre Square in the capital city of Berland has a rectangular shape with the size n × m '
            'metres. Pavement consists of 1×1 square flagstones. Mayor decided to pave the Theatre Square '
            'with a × a square flagstones. Flagstones cannot be split, so some of them may overhang.\n\n'
            'Input: a single line with three integers n, m, a (1 ≤ n, m, a ≤ 10^9).\n'
            'Output: the minimum number of flagstones needed.'
        ),
        'difficulty': 'Easy',
        'difficulty_rating': 1000,
        'time_limit_sec': 2,
        'explanation': (
            'We need ceil(n/a) * ceil(m/a) flagstones. '
            'ceil(x/a) = (x + a - 1) // a in integer arithmetic.'
        ),
        'reference_code': (
            'import math\n'
            'n, m, a = map(int, input().split())\n'
            'print(math.ceil(n / a) * math.ceil(m / a))\n'
        ),
        'generator': lambda: ' '.join(str(random.randint(1, 10**6)) for _ in range(3)),
    },
    {
        'title': 'Bit++ (Increment Operator)',
        'source_url': 'https://codeforces.com/problemset/problem/282/A',
        'statement': (
            'The world of Bit++ uses only one integer variable x, initially 0. '
            'The language supports only two operations: "X++" which increments x by 1, '
            'and "X--" which decrements x by 1.\n\n'
            'Input: first line is n (1 ≤ n ≤ 150) — the number of operations. '
            'Each of the next n lines is either "X++" or "X--".\n'
            'Output: the value of x after all operations.'
        ),
        'difficulty': 'Easy',
        'difficulty_rating': 800,
        'time_limit_sec': 2,
        'explanation': 'Start x=0, increment or decrement based on the middle character.',
        'reference_code': (
            'n = int(input())\n'
            'x = 0\n'
            'for _ in range(n):\n'
            '    op = input()\n'
            '    if op[1] == "+":\n'
            '        x += 1\n'
            '    else:\n'
            '        x -= 1\n'
            'print(x)\n'
        ),
        'generator': lambda: (
            lambda ops: str(len(ops)) + '\n' + '\n'.join(ops)
        )([random.choice(['X++', 'X--']) for _ in range(random.randint(1, 20))]),
    },
    {
        'title': 'Even Odd (Parity)',
        'source_url': 'https://codeforces.com/problemset/problem/228/A',
        'statement': (
            'Johnny has a number. He wants to know if it is even or odd.\n\n'
            'Input: a single integer n (1 ≤ n ≤ 10^9).\n'
            'Output: print "even" if n is even, "odd" otherwise.'
        ),
        'difficulty': 'Easy',
        'difficulty_rating': 800,
        'time_limit_sec': 2,
        'explanation': 'Check n % 2 == 0.',
        'reference_code': (
            'n = int(input())\n'
            'print("even" if n % 2 == 0 else "odd")\n'
        ),
        'generator': lambda: str(random.randint(1, 10**9)),
    },
    # ---------------------------------------------------------------- Medium
    {
        'title': 'Stones on the Table',
        'source_url': 'https://codeforces.com/problemset/problem/266/A',
        'statement': (
            'There are n stones on the table. Each stone has colour R, G, or B. '
            'Two adjacent same-coloured stones can be removed. Find the minimum number '
            'of moves to make no two adjacent stones of the same colour, '
            'by removing the minimum number of stones.\n\n'
            'Input: first line is n (1 ≤ n ≤ 150000). Second line is a string of length n '
            'consisting of R, G, B.\n'
            'Output: the number of stones removed.'
        ),
        'difficulty': 'Easy',
        'difficulty_rating': 800,
        'time_limit_sec': 2,
        'explanation': 'Count adjacent duplicates by scanning from left to right.',
        'reference_code': (
            'n = int(input())\n'
            's = input()\n'
            'count = 0\n'
            'prev = ""\n'
            'for c in s:\n'
            '    if c == prev:\n'
            '        count += 1\n'
            '    else:\n'
            '        prev = c\n'
            'print(count)\n'
        ),
        'generator': lambda: (
            lambda n: f"{n}\n{''.join(random.choices('RGB', k=n))}"
        )(random.randint(1, 20)),
    },
    {
        'title': 'Next Round',
        'source_url': 'https://codeforces.com/problemset/problem/592/A',
        'statement': (
            'In a programming contest, the top k participants advance to the next round. '
            'A participant also advances if their score is at least equal to the k-th place score '
            '(and their score > 0). Given n scores in non-increasing order, determine how many '
            'participants advance.\n\n'
            'Input: first line has n and k (1 ≤ k ≤ n ≤ 50). '
            'Second line has n non-negative integers (scores, non-increasing).\n'
            'Output: the number of participants who advance.'
        ),
        'difficulty': 'Easy',
        'difficulty_rating': 800,
        'time_limit_sec': 2,
        'explanation': (
            'Find the k-th score. Count participants with score >= k-th score and score > 0.'
        ),
        'reference_code': (
            'n, k = map(int, input().split())\n'
            'scores = list(map(int, input().split()))\n'
            'threshold = scores[k - 1]\n'
            'if threshold == 0:\n'
            '    print(sum(1 for s in scores if s > 0))\n'
            'else:\n'
            '    print(sum(1 for s in scores if s >= threshold))\n'
        ),
        'generator': lambda: (
            lambda n, k: (
                f"{n} {k}\n" +
                ' '.join(map(str, sorted([random.randint(0, 100) for _ in range(n)], reverse=True)))
            )
        )(
            *((lambda n: (n, random.randint(1, n)))(random.randint(2, 10)))
        ),
    },
    {
        'title': 'Beautiful Matrix',
        'source_url': 'https://codeforces.com/problemset/problem/263/A',
        'statement': (
            'You have a 5x5 matrix where numbers 1..25 appear exactly once. '
            'The centre element should be 13. Find the minimum number of swaps of '
            'adjacent elements needed to move 13 to position (3,3) (1-indexed, centre).\n\n'
            'Input: five lines each containing five space-separated integers.\n'
            'Output: the number of swaps.'
        ),
        'difficulty': 'Easy',
        'difficulty_rating': 1000,
        'time_limit_sec': 2,
        'explanation': (
            'Find row and column (0-indexed) of 13. '
            'Answer is |row - 2| + |col - 2|.'
        ),
        'reference_code': (
            'grid = []\n'
            'for _ in range(5):\n'
            '    grid.append(list(map(int, input().split())))\n'
            'for r in range(5):\n'
            '    for c in range(5):\n'
            '        if grid[r][c] == 13:\n'
            '            print(abs(r - 2) + abs(c - 2))\n'
        ),
        'generator': lambda: (
            lambda perm: '\n'.join(
                ' '.join(map(str, perm[i*5:(i+1)*5])) for i in range(5)
            )
        )(random.sample(range(1, 26), 25)),
    },
    {
        'title': 'Petya and Strings',
        'source_url': 'https://codeforces.com/problemset/problem/514/A',
        'statement': (
            'Petya has two strings s and t of equal length. He can increase any character of t by 1 '
            '(e.g. "a" → "b") at cost 1 OR decrease any character by 1 at cost 1. '
            'Find the minimum cost to make s lexicographically less than t, '
            'less or equal, or greater (choose the cheapest).\n\n'
            'Actually, you just need to compare two strings s and t lexicographically.\n\n'
            'Input: two lines, each a string of lowercase letters (length 1 to 100).\n'
            'Output: -1 if s < t, 0 if s == t, 1 if s > t.'
        ),
        'difficulty': 'Easy',
        'difficulty_rating': 1000,
        'time_limit_sec': 2,
        'explanation': 'Simple lexicographic comparison using Python string comparison.',
        'reference_code': (
            's = input()\n'
            't = input()\n'
            'if s < t:\n'
            '    print(-1)\n'
            'elif s == t:\n'
            '    print(0)\n'
            'else:\n'
            '    print(1)\n'
        ),
        'generator': lambda: (
            lambda n: (
                ''.join(random.choices('abcdefghij', k=n)) + '\n' +
                ''.join(random.choices('abcdefghij', k=n))
            )
        )(random.randint(1, 10)),
    },
    {
        'title': 'Horse Racing',
        'source_url': 'https://codeforces.com/problemset/problem/228/B',
        'statement': (
            'n horses race. Each horse i has a speed s_i. The winner is the horse with the highest '
            'speed. If there are multiple horses with the same highest speed, output -1.\n\n'
            'Input: first line is n (1 ≤ n ≤ 100). Second line is n space-separated integers '
            's_i (1 ≤ s_i ≤ 10^4).\n'
            'Output: 1-indexed position of the winning horse, or -1 if tied.'
        ),
        'difficulty': 'Easy',
        'difficulty_rating': 900,
        'time_limit_sec': 2,
        'explanation': 'Find max speed. If exactly one horse has it, output its 1-indexed position. Else -1.',
        'reference_code': (
            'n = int(input())\n'
            's = list(map(int, input().split()))\n'
            'mx = max(s)\n'
            'if s.count(mx) > 1:\n'
            '    print(-1)\n'
            'else:\n'
            '    print(s.index(mx) + 1)\n'
        ),
        'generator': lambda: (
            lambda n: f"{n}\n{' '.join(str(random.randint(1, 20)) for _ in range(n))}"
        )(random.randint(2, 10)),
    },
    # ---------------------------------------------------------------- Medium
    {
        'title': 'Divisor Sum',
        'source_url': 'https://codeforces.com/problemset/problem/822/A',
        'statement': (
            'Given an integer n, compute the sum of all its positive divisors.\n\n'
            'Input: a single integer n (1 ≤ n ≤ 10^6).\n'
            'Output: the sum of divisors of n.'
        ),
        'difficulty': 'Medium',
        'difficulty_rating': 1200,
        'time_limit_sec': 3,
        'explanation': 'Iterate from 1 to sqrt(n), adding both i and n//i when i divides n.',
        'reference_code': (
            'import math\n'
            'n = int(input())\n'
            'total = 0\n'
            'for i in range(1, int(math.isqrt(n)) + 1):\n'
            '    if n % i == 0:\n'
            '        total += i\n'
            '        if i != n // i:\n'
            '            total += n // i\n'
            'print(total)\n'
        ),
        'generator': lambda: str(random.randint(1, 10**5)),
    },
    {
        'title': 'Maximum Sum of Digits',
        'source_url': 'https://codeforces.com/problemset/problem/1217/B',
        'statement': (
            'You are given a positive integer n. Find the maximum sum s(a) + s(b) where a + b = n '
            'and s(x) denotes the sum of digits of x.\n\n'
            'Input: a single integer n (1 ≤ n ≤ 10^12).\n'
            'Output: the maximum value of s(a) + s(b).'
        ),
        'difficulty': 'Medium',
        'difficulty_rating': 1400,
        'time_limit_sec': 3,
        'explanation': (
            'The optimal split is a = 10^(len(n)-1) - 1 (all 9s), b = n - a. '
            'This maximises digit sums because carrying destroys digit value.'
        ),
        'reference_code': (
            'def digit_sum(x):\n'
            '    return sum(int(d) for d in str(x))\n'
            'n = int(input())\n'
            'best = digit_sum(n)  # a=0, b=n\n'
            'p = 1\n'
            'while p <= n:\n'
            '    a = p - 1\n'
            '    if a > 0:\n'
            '        b = n - a\n'
            '        best = max(best, digit_sum(a) + digit_sum(b))\n'
            '    p *= 10\n'
            'print(best)\n'
        ),
        'generator': lambda: str(random.randint(1, 10**9)),
    },
    {
        'title': 'Prime Factorization Count',
        'source_url': 'https://codeforces.com/problemset/problem/230/A',
        'statement': (
            'Given an integer n, output each prime factor along with its exponent, '
            'one per line, in ascending order of the prime.\n\n'
            'Input: a single integer n (2 ≤ n ≤ 10^9).\n'
            'Output: lines of "p e" where p^e divides n, in ascending order of p.'
        ),
        'difficulty': 'Medium',
        'difficulty_rating': 1200,
        'time_limit_sec': 3,
        'explanation': 'Trial division up to sqrt(n), collecting prime factors and their counts.',
        'reference_code': (
            'n = int(input())\n'
            'factors = []\n'
            'i = 2\n'
            'while i * i <= n:\n'
            '    if n % i == 0:\n'
            '        cnt = 0\n'
            '        while n % i == 0:\n'
            '            cnt += 1\n'
            '            n //= i\n'
            '        factors.append((i, cnt))\n'
            '    i += 1\n'
            'if n > 1:\n'
            '    factors.append((n, 1))\n'
            'for p, e in factors:\n'
            '    print(p, e)\n'
        ),
        'generator': lambda: str(random.randint(2, 10**6)),
    },
    {
        'title': 'Polycarp and Restricting Inversions',
        'source_url': 'https://codeforces.com/problemset/problem/1737/A',
        'statement': (
            'Given an array of n integers, determine if the array can be sorted in non-decreasing '
            'order by performing at most one swap of two adjacent elements.\n\n'
            'Input: first line is n (1 ≤ n ≤ 2·10^5). Second line is n space-separated integers.\n'
            'Output: "YES" if sortable with at most one adjacent swap, "NO" otherwise.'
        ),
        'difficulty': 'Medium',
        'difficulty_rating': 1200,
        'time_limit_sec': 3,
        'explanation': (
            'Find all adjacent inversions (positions where a[i] > a[i+1]). '
            'If there are 0 or 1 inversions, the answer is YES. '
            'If exactly 1 inversion at index i: swap and re-check.'
        ),
        'reference_code': (
            'n = int(input())\n'
            'a = list(map(int, input().split()))\n'
            'inv = [i for i in range(n - 1) if a[i] > a[i + 1]]\n'
            'if len(inv) == 0:\n'
            '    print("YES")\n'
            'elif len(inv) == 1:\n'
            '    i = inv[0]\n'
            '    a[i], a[i + 1] = a[i + 1], a[i]\n'
            '    print("YES" if a == sorted(a) else "NO")\n'
            'else:\n'
            '    print("NO")\n'
        ),
        'generator': lambda: (
            lambda n: f"{n}\n{' '.join(map(str, [random.randint(1, 20) for _ in range(n)]))}"
        )(random.randint(2, 10)),
    },
    {
        'title': 'GCD and LCM',
        'source_url': 'https://codeforces.com/problemset/problem/75/A',
        'statement': (
            'Given two positive integers a and b, compute their GCD (greatest common divisor) '
            'and LCM (least common multiple).\n\n'
            'Input: two space-separated integers a and b (1 ≤ a, b ≤ 10^9).\n'
            'Output: two space-separated integers: GCD then LCM.'
        ),
        'difficulty': 'Easy',
        'difficulty_rating': 900,
        'time_limit_sec': 2,
        'explanation': 'Use math.gcd. LCM = a * b // gcd(a, b).',
        'reference_code': (
            'import math\n'
            'a, b = map(int, input().split())\n'
            'g = math.gcd(a, b)\n'
            'print(g, a * b // g)\n'
        ),
        'generator': lambda: f"{random.randint(1, 10**6)} {random.randint(1, 10**6)}",
    },
    # ------------------------------------------------------------------ Hard
    {
        'title': 'Count Subarrays with Sum K',
        'source_url': 'https://codeforces.com/problemset/problem/816/B',
        'statement': (
            'Given an array of n integers and a value k, count the number of contiguous subarrays '
            'whose sum equals k.\n\n'
            'Input: first line has n and k (1 ≤ n ≤ 2·10^5, -10^9 ≤ k ≤ 10^9). '
            'Second line has n space-separated integers (-10^4 ≤ a_i ≤ 10^4).\n'
            'Output: the count of subarrays with sum exactly k.'
        ),
        'difficulty': 'Medium',
        'difficulty_rating': 1400,
        'time_limit_sec': 3,
        'explanation': (
            'Use prefix sums and a hash map. For each index i, count how many prefix sums equal '
            'prefix[i] - k (the number of subarrays ending at i with sum k).'
        ),
        'reference_code': (
            'from collections import defaultdict\n'
            'n, k = map(int, input().split())\n'
            'a = list(map(int, input().split()))\n'
            'freq = defaultdict(int)\n'
            'freq[0] = 1\n'
            'prefix = 0\n'
            'count = 0\n'
            'for x in a:\n'
            '    prefix += x\n'
            '    count += freq[prefix - k]\n'
            '    freq[prefix] += 1\n'
            'print(count)\n'
        ),
        'generator': lambda: (
            lambda n, k: f"{n} {k}\n{' '.join(str(random.randint(-10, 10)) for _ in range(n))}"
        )(random.randint(3, 15), random.randint(-5, 10)),
    },
    {
        'title': 'Longest Increasing Subsequence Length',
        'source_url': 'https://codeforces.com/problemset/problem/340/E',
        'statement': (
            'Given a sequence of n integers, find the length of its longest strictly increasing subsequence.\n\n'
            'Input: first line is n (1 ≤ n ≤ 10^5). Second line has n space-separated integers '
            '(-10^9 ≤ a_i ≤ 10^9).\n'
            'Output: the length of the longest strictly increasing subsequence.'
        ),
        'difficulty': 'Hard',
        'difficulty_rating': 1800,
        'time_limit_sec': 5,
        'explanation': (
            'Use patience sorting / binary search with a "tails" array. '
            'tails[i] is the smallest tail element for all increasing subsequences of length i+1. '
            'For each element, binary search for its position in tails.'
        ),
        'reference_code': (
            'import bisect\n'
            'n = int(input())\n'
            'a = list(map(int, input().split()))\n'
            'tails = []\n'
            'for x in a:\n'
            '    pos = bisect.bisect_left(tails, x)\n'
            '    if pos == len(tails):\n'
            '        tails.append(x)\n'
            '    else:\n'
            '        tails[pos] = x\n'
            'print(len(tails))\n'
        ),
        'generator': lambda: (
            lambda n: f"{n}\n{' '.join(str(random.randint(-50, 50)) for _ in range(n))}"
        )(random.randint(3, 20)),
    },
    {
        'title': 'Number of Divisors up to N',
        'source_url': 'https://codeforces.com/problemset/problem/762/B',
        'statement': (
            'Given n integers, for each find the number of its positive divisors.\n\n'
            'Input: first line is n (1 ≤ n ≤ 100). Each of the next n lines has one integer '
            'x (1 ≤ x ≤ 10^6).\n'
            'Output: n lines, each with the number of divisors of the corresponding integer.'
        ),
        'difficulty': 'Medium',
        'difficulty_rating': 1200,
        'time_limit_sec': 3,
        'explanation': 'For each x, iterate up to sqrt(x) and count divisor pairs.',
        'reference_code': (
            'import math\n'
            'n = int(input())\n'
            'for _ in range(n):\n'
            '    x = int(input())\n'
            '    count = 0\n'
            '    for i in range(1, int(math.isqrt(x)) + 1):\n'
            '        if x % i == 0:\n'
            '            count += 2 if i != x // i else 1\n'
            '    print(count)\n'
        ),
        'generator': lambda: (
            lambda n: str(n) + '\n' + '\n'.join(str(random.randint(1, 10000)) for _ in range(n))
        )(random.randint(1, 10)),
    },
    {
        'title': 'Grid Path Counting',
        'source_url': 'https://codeforces.com/problemset/problem/8/A',
        'statement': (
            'Count the number of paths in an n×m grid from the top-left corner (1,1) to the '
            'bottom-right corner (n,m), moving only right or down.\n\n'
            'Input: two space-separated integers n and m (1 ≤ n, m ≤ 15).\n'
            'Output: the number of such paths.'
        ),
        'difficulty': 'Medium',
        'difficulty_rating': 1300,
        'time_limit_sec': 3,
        'explanation': (
            'This equals C(n+m-2, n-1) — choose n-1 downward moves out of n+m-2 total. '
            'Or use DP: dp[i][j] = dp[i-1][j] + dp[i][j-1].'
        ),
        'reference_code': (
            'import math\n'
            'n, m = map(int, input().split())\n'
            'print(math.comb(n + m - 2, n - 1))\n'
        ),
        'generator': lambda: f"{random.randint(1, 10)} {random.randint(1, 10)}",
    },
    {
        'title': 'Towers of Hanoi Move Count',
        'source_url': 'https://codeforces.com/problemset/problem/278/B',
        'statement': (
            'The classic Towers of Hanoi puzzle with n disks requires 2^n - 1 moves. '
            'Given n, compute the minimum number of moves needed.\n\n'
            'Input: a single integer n (1 ≤ n ≤ 30).\n'
            'Output: the minimum number of moves (2^n - 1).'
        ),
        'difficulty': 'Easy',
        'difficulty_rating': 800,
        'time_limit_sec': 2,
        'explanation': 'The answer is simply 2**n - 1.',
        'reference_code': (
            'n = int(input())\n'
            'print(2**n - 1)\n'
        ),
        'generator': lambda: str(random.randint(1, 30)),
    },
    {
        'title': 'Digit Sum Comparison',
        'source_url': 'https://codeforces.com/problemset/problem/41/A',
        'statement': (
            'Given two positive integers a and b, compare the sums of their digits.\n\n'
            'Input: two space-separated integers a and b (1 ≤ a, b ≤ 10^9).\n'
            'Output: "<" if S(a) < S(b), ">" if S(a) > S(b), "=" if equal, '
            'where S(x) is the sum of digits of x.'
        ),
        'difficulty': 'Easy',
        'difficulty_rating': 800,
        'time_limit_sec': 2,
        'explanation': 'Compute digit sums and compare.',
        'reference_code': (
            'a, b = input().split()\n'
            'sa = sum(int(c) for c in a)\n'
            'sb = sum(int(c) for c in b)\n'
            'if sa < sb:\n'
            '    print("<")\n'
            'elif sa > sb:\n'
            '    print(">")\n'
            'else:\n'
            '    print("=")\n'
        ),
        'generator': lambda: f"{random.randint(1, 10**8)} {random.randint(1, 10**8)}",
    },
    {
        'title': 'Sieve of Eratosthenes Count',
        'source_url': 'https://codeforces.com/problemset/problem/26/A',
        'statement': (
            'Given an integer n, count the number of prime numbers from 1 to n (inclusive).\n\n'
            'Input: a single integer n (1 ≤ n ≤ 10^6).\n'
            'Output: the count of primes ≤ n.'
        ),
        'difficulty': 'Medium',
        'difficulty_rating': 1200,
        'time_limit_sec': 5,
        'explanation': 'Use the Sieve of Eratosthenes for efficient prime counting.',
        'reference_code': (
            'n = int(input())\n'
            'if n < 2:\n'
            '    print(0)\n'
            'else:\n'
            '    sieve = [True] * (n + 1)\n'
            '    sieve[0] = sieve[1] = False\n'
            '    for i in range(2, int(n**0.5) + 1):\n'
            '        if sieve[i]:\n'
            '            for j in range(i*i, n + 1, i):\n'
            '                sieve[j] = False\n'
            '    print(sum(sieve))\n'
        ),
        'generator': lambda: str(random.randint(1, 10**5)),
    },
    {
        'title': 'Climbing Stairs',
        'source_url': 'https://codeforces.com/problemset/problem/580/A',
        'statement': (
            'You are climbing a staircase with n steps. Each time you can climb 1 or 2 steps. '
            'In how many distinct ways can you reach the top?\n\n'
            'Input: a single integer n (1 ≤ n ≤ 40).\n'
            'Output: the number of distinct ways.'
        ),
        'difficulty': 'Easy',
        'difficulty_rating': 900,
        'time_limit_sec': 2,
        'explanation': 'This is a Fibonacci sequence: ways(n) = ways(n-1) + ways(n-2), ways(1)=1, ways(2)=2.',
        'reference_code': (
            'n = int(input())\n'
            'a, b = 1, 2\n'
            'if n == 1:\n'
            '    print(1)\n'
            'elif n == 2:\n'
            '    print(2)\n'
            'else:\n'
            '    for _ in range(n - 2):\n'
            '        a, b = b, a + b\n'
            '    print(b)\n'
        ),
        'generator': lambda: str(random.randint(1, 40)),
    },
    {
        'title': 'Minimum Coins Change',
        'source_url': 'https://codeforces.com/problemset/problem/431/C',
        'statement': (
            'Given coin denominations [1, 5, 10, 25] (unlimited supply) and an amount n, '
            'find the minimum number of coins needed to make exactly n.\n\n'
            'Input: a single integer n (0 ≤ n ≤ 10^4).\n'
            'Output: the minimum number of coins.'
        ),
        'difficulty': 'Medium',
        'difficulty_rating': 1200,
        'time_limit_sec': 3,
        'explanation': 'Use DP: dp[i] = min coins to make i. dp[0]=0, dp[i] = min(dp[i-c]+1 for each coin c ≤ i).',
        'reference_code': (
            'n = int(input())\n'
            'coins = [1, 5, 10, 25]\n'
            'dp = [float("inf")] * (n + 1)\n'
            'dp[0] = 0\n'
            'for i in range(1, n + 1):\n'
            '    for c in coins:\n'
            '        if c <= i:\n'
            '            dp[i] = min(dp[i], dp[i - c] + 1)\n'
            'print(dp[n])\n'
        ),
        'generator': lambda: str(random.randint(0, 1000)),
    },
    {
        'title': 'Maximum Profit (Stock)',
        'source_url': 'https://codeforces.com/problemset/problem/381/B',
        'statement': (
            'Given daily stock prices, find the maximum profit from one buy and one sell '
            '(buy before sell). If no profit is possible, output 0.\n\n'
            'Input: first line is n (2 ≤ n ≤ 10^5). Second line has n space-separated integers.\n'
            'Output: the maximum profit.'
        ),
        'difficulty': 'Medium',
        'difficulty_rating': 1200,
        'time_limit_sec': 3,
        'explanation': 'Track the minimum price seen so far and the maximum profit at each step.',
        'reference_code': (
            'n = int(input())\n'
            'prices = list(map(int, input().split()))\n'
            'min_price = prices[0]\n'
            'max_profit = 0\n'
            'for p in prices[1:]:\n'
            '    max_profit = max(max_profit, p - min_price)\n'
            '    min_price = min(min_price, p)\n'
            'print(max_profit)\n'
        ),
        'generator': lambda: (
            lambda n: f"{n}\n{' '.join(str(random.randint(1, 100)) for _ in range(n))}"
        )(random.randint(2, 15)),
    },
    {
        'title': 'Balanced Brackets Count',
        'source_url': 'https://codeforces.com/problemset/problem/8/B',
        'statement': (
            'Count the number of balanced bracket sequences of length 2n using only "(" and ")".\n\n'
            'Input: a single integer n (1 ≤ n ≤ 15).\n'
            'Output: the n-th Catalan number C(n).'
        ),
        'difficulty': 'Medium',
        'difficulty_rating': 1300,
        'time_limit_sec': 2,
        'explanation': (
            'The answer is the n-th Catalan number: C(n) = C(2n, n) / (n+1).'
        ),
        'reference_code': (
            'import math\n'
            'n = int(input())\n'
            'print(math.comb(2 * n, n) // (n + 1))\n'
        ),
        'generator': lambda: str(random.randint(1, 12)),
    },
    {
        'title': 'Longest Palindromic Substring Length',
        'source_url': 'https://codeforces.com/problemset/problem/5/C',
        'statement': (
            'Given a string s, find the length of its longest palindromic substring.\n\n'
            'Input: a single string s of lowercase English letters (1 ≤ |s| ≤ 1000).\n'
            'Output: the length of the longest palindromic substring.'
        ),
        'difficulty': 'Medium',
        'difficulty_rating': 1400,
        'time_limit_sec': 3,
        'explanation': 'Expand around each centre (both odd and even lengths) and track the maximum length.',
        'reference_code': (
            's = input()\n'
            'n = len(s)\n'
            'best = 1\n'
            'for c in range(n):\n'
            '    # Odd length\n'
            '    l, r = c, c\n'
            '    while l >= 0 and r < n and s[l] == s[r]:\n'
            '        best = max(best, r - l + 1)\n'
            '        l -= 1; r += 1\n'
            '    # Even length\n'
            '    l, r = c, c + 1\n'
            '    while l >= 0 and r < n and s[l] == s[r]:\n'
            '        best = max(best, r - l + 1)\n'
            '        l -= 1; r += 1\n'
            'print(best)\n'
        ),
        'generator': lambda: ''.join(random.choices('abcde', k=random.randint(1, 20))),
    },
    {
        'title': 'Modular Exponentiation',
        'source_url': 'https://codeforces.com/problemset/problem/630/A',
        'statement': (
            'Compute (base ^ exp) mod m efficiently.\n\n'
            'Input: three space-separated integers base, exp, m '
            '(0 ≤ base, exp ≤ 10^9, 1 ≤ m ≤ 10^9).\n'
            'Output: (base ^ exp) mod m.'
        ),
        'difficulty': 'Medium',
        'difficulty_rating': 1200,
        'time_limit_sec': 2,
        'explanation': 'Use Python built-in pow(base, exp, m) which uses fast exponentiation.',
        'reference_code': (
            'base, exp, m = map(int, input().split())\n'
            'print(pow(base, exp, m))\n'
        ),
        'generator': lambda: f"{random.randint(0, 10**6)} {random.randint(0, 10**6)} {random.randint(1, 10**6)}",
    },
    {
        'title': 'Array Rotation',
        'source_url': 'https://codeforces.com/problemset/problem/263/B',
        'statement': (
            'Rotate an array of n integers to the right by k positions.\n\n'
            'Input: first line has n and k (1 ≤ n ≤ 100, 0 ≤ k ≤ n). '
            'Second line has n space-separated integers.\n'
            'Output: the rotated array, space-separated.'
        ),
        'difficulty': 'Easy',
        'difficulty_rating': 800,
        'time_limit_sec': 2,
        'explanation': 'Take the last k elements and prepend them: a[-k:] + a[:-k]. Handle k=0 and k=n.',
        'reference_code': (
            'n, k = map(int, input().split())\n'
            'a = list(map(int, input().split()))\n'
            'k = k % n\n'
            'rotated = a[-k:] + a[:-k] if k else a\n'
            'print(*rotated)\n'
        ),
        'generator': lambda: (
            lambda n: f"{n} {random.randint(0, n)}\n{' '.join(str(random.randint(1, 50)) for _ in range(n))}"
        )(random.randint(2, 10)),
    },
    {
        'title': 'Knapsack 0/1',
        'source_url': 'https://codeforces.com/problemset/problem/19/B',
        'statement': (
            'Given n items each with a weight w_i and value v_i, and a knapsack with capacity W, '
            'find the maximum total value achievable without exceeding the capacity.\n\n'
            'Input: first line has n and W (1 ≤ n ≤ 20, 1 ≤ W ≤ 1000). '
            'Next n lines each have two integers w_i v_i.\n'
            'Output: the maximum total value.'
        ),
        'difficulty': 'Hard',
        'difficulty_rating': 1600,
        'time_limit_sec': 5,
        'explanation': (
            'DP where dp[j] = max value achievable with capacity j. '
            'Iterate items in outer loop, capacities in reverse inner loop.'
        ),
        'reference_code': (
            'n, W = map(int, input().split())\n'
            'items = [tuple(map(int, input().split())) for _ in range(n)]\n'
            'dp = [0] * (W + 1)\n'
            'for w, v in items:\n'
            '    for j in range(W, w - 1, -1):\n'
            '        dp[j] = max(dp[j], dp[j - w] + v)\n'
            'print(dp[W])\n'
        ),
        'generator': lambda: (
            lambda n, W: (
                f"{n} {W}\n" +
                '\n'.join(f"{random.randint(1, W)} {random.randint(1, 50)}" for _ in range(n))
            )
        )(random.randint(2, 8), random.randint(5, 50)),
    },
]


def seed_curated_problems(stdout=None, n_sample=3, n_hidden=32):
    """
    Seed CodeDuels with curated Codeforces-style problems.
    Generates n_sample + n_hidden test cases per problem using the reference solution.

    Returns (created, updated) counts.
    """
    created = updated = 0
    for pdata in CURATED_CF_PROBLEMS:
        if stdout:
            stdout.write(f"  Generating tests for: {pdata['title']} ...")

        try:
            tests = _generate_test_cases(
                pdata['generator'],
                pdata['reference_code'],
                n_sample=n_sample,
                n_hidden=n_hidden,
            )
        except Exception as exc:
            if stdout:
                stdout.write(f"  ERROR generating tests for {pdata['title']}: {exc}")
            continue

        with transaction.atomic():
            problem, is_new = Problem.objects.get_or_create(
                source_url=pdata['source_url'],
                defaults={
                    'title': pdata['title'][:200],
                    'statement': pdata['statement'],
                    'category': 'DSA',
                    'difficulty': pdata['difficulty'],
                    'difficulty_rating': pdata['difficulty_rating'],
                    'time_limit_sec': pdata['time_limit_sec'],
                    'is_draft': False,
                }
            )
            if not is_new:
                problem.title = pdata['title'][:200]
                problem.statement = pdata['statement']
                problem.category = 'DSA'
                problem.difficulty = pdata['difficulty']
                problem.difficulty_rating = pdata['difficulty_rating']
                problem.time_limit_sec = pdata['time_limit_sec']
                problem.is_draft = False
                problem.save()
                updated += 1
            else:
                created += 1

            problem.test_cases.all().delete()
            TestCase.objects.bulk_create([
                TestCase(
                    problem=problem,
                    input=t['input'],
                    expected_output=t['expected_output'],
                    is_sample=t['is_sample'],
                )
                for t in tests
            ])
            Solution.objects.update_or_create(
                problem=problem,
                defaults={
                    'explanation': pdata['explanation'],
                    'reference_code': pdata['reference_code'],
                }
            )

        if stdout:
            action_label = "Created" if is_new else "Updated"
            stdout.write(f"    ✓ {action_label} with {len(tests)} test cases ({n_sample} sample, {len(tests) - n_sample} hidden).")

    return created, updated

