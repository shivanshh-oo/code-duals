from django.core.management.base import BaseCommand
from problems.models import Problem, TestCase, Solution


PROBLEMS_DATA = [
    # --- PLACEMENT PROBLEMS (6) ---
    {
        'title': 'Two Sum',
        'statement': 'Given a list of integers and a target, return the indices of two numbers that add up to the target.\n\nInput: first line is the target, second line is space-separated integers.\nOutput: two space-separated indices (0-based).',
        'category': 'DSA', 'difficulty': 'Easy', 'difficulty_rating': 800, 'is_placement': True,
        'time_limit_sec': 5,
        'tests': [
            {'input': '9\n2 7 11 15', 'expected_output': '0 1', 'is_sample': True},
            {'input': '6\n3 2 4', 'expected_output': '1 2', 'is_sample': False},
            {'input': '6\n3 3', 'expected_output': '0 1', 'is_sample': False},
        ],
        'solution': {
            'explanation': 'Use a hash map to store each number and its index. For each number, check if target - number exists in the map.',
            'reference_code': 'target = int(input())\nnums = list(map(int, input().split()))\nseen = {}\nfor i, n in enumerate(nums):\n    comp = target - n\n    if comp in seen:\n        print(seen[comp], i)\n        break\n    seen[n] = i',
        },
    },
    {
        'title': 'Reverse String',
        'statement': 'Given a string, return it reversed.\n\nInput: a single string.\nOutput: the reversed string.',
        'category': 'DSA', 'difficulty': 'Easy', 'difficulty_rating': 800, 'is_placement': True,
        'time_limit_sec': 5,
        'tests': [
            {'input': 'hello', 'expected_output': 'olleh', 'is_sample': True},
            {'input': 'Python', 'expected_output': 'nohtyP', 'is_sample': False},
            {'input': 'a', 'expected_output': 'a', 'is_sample': False},
        ],
        'solution': {
            'explanation': 'Use Python slicing [::-1] to reverse the string.',
            'reference_code': 'print(input()[::-1])',
        },
    },
    {
        'title': 'FizzBuzz',
        'statement': 'Given n, print numbers from 1 to n. For multiples of 3 print "Fizz", for multiples of 5 print "Buzz", for both print "FizzBuzz".\n\nInput: a single integer n.\nOutput: one value per line.',
        'category': 'DSA', 'difficulty': 'Easy', 'difficulty_rating': 900, 'is_placement': True,
        'time_limit_sec': 5,
        'tests': [
            {'input': '5', 'expected_output': '1\n2\nFizz\n4\nBuzz', 'is_sample': True},
            {'input': '15', 'expected_output': '1\n2\nFizz\n4\nBuzz\nFizz\n7\n8\nFizz\nBuzz\n11\nFizz\n13\n14\nFizzBuzz', 'is_sample': False},
        ],
        'solution': {
            'explanation': 'Loop 1..n checking divisibility by 15, 3, and 5 in that order.',
            'reference_code': 'n = int(input())\nfor i in range(1, n+1):\n    if i % 15 == 0: print("FizzBuzz")\n    elif i % 3 == 0: print("Fizz")\n    elif i % 5 == 0: print("Buzz")\n    else: print(i)',
        },
    },
    {
        'title': 'Palindrome Check',
        'statement': 'Given a string, determine if it is a palindrome (reads the same forwards and backwards). Ignore case.\n\nInput: a single string.\nOutput: "Yes" or "No".',
        'category': 'DSA', 'difficulty': 'Easy', 'difficulty_rating': 900, 'is_placement': True,
        'time_limit_sec': 5,
        'tests': [
            {'input': 'racecar', 'expected_output': 'Yes', 'is_sample': True},
            {'input': 'Hello', 'expected_output': 'No', 'is_sample': True},
            {'input': 'Madam', 'expected_output': 'Yes', 'is_sample': False},
        ],
        'solution': {
            'explanation': 'Convert to lowercase, compare with its reverse.',
            'reference_code': 's = input().lower()\nprint("Yes" if s == s[::-1] else "No")',
        },
    },
    {
        'title': 'Binary Search',
        'statement': 'Given a sorted list of integers and a target, return the index of the target or -1 if not found.\n\nInput: first line is the target, second line is space-separated sorted integers.\nOutput: the index (0-based) or -1.',
        'category': 'DSA', 'difficulty': 'Medium', 'difficulty_rating': 1200, 'is_placement': True,
        'time_limit_sec': 5,
        'tests': [
            {'input': '5\n1 3 5 7 9', 'expected_output': '2', 'is_sample': True},
            {'input': '6\n1 3 5 7 9', 'expected_output': '-1', 'is_sample': True},
            {'input': '1\n1', 'expected_output': '0', 'is_sample': False},
        ],
        'solution': {
            'explanation': 'Use two pointers (lo, hi) and check the middle element each iteration.',
            'reference_code': 'target = int(input())\nnums = list(map(int, input().split()))\nlo, hi = 0, len(nums) - 1\nresult = -1\nwhile lo <= hi:\n    mid = (lo + hi) // 2\n    if nums[mid] == target:\n        result = mid\n        break\n    elif nums[mid] < target:\n        lo = mid + 1\n    else:\n        hi = mid - 1\nprint(result)',
        },
    },
    {
        'title': 'Longest Common Subsequence',
        'statement': 'Given two strings, find the length of their longest common subsequence.\n\nInput: two lines, each a string.\nOutput: a single integer.',
        'category': 'DSA', 'difficulty': 'Hard', 'difficulty_rating': 1600, 'is_placement': True,
        'time_limit_sec': 5,
        'tests': [
            {'input': 'abcde\nace', 'expected_output': '3', 'is_sample': True},
            {'input': 'abc\nabc', 'expected_output': '3', 'is_sample': False},
            {'input': 'abc\ndef', 'expected_output': '0', 'is_sample': False},
        ],
        'solution': {
            'explanation': 'Use dynamic programming with a 2D table. dp[i][j] = LCS of first i chars and first j chars.',
            'reference_code': 'a = input()\nb = input()\nm, n = len(a), len(b)\ndp = [[0]*(n+1) for _ in range(m+1)]\nfor i in range(1, m+1):\n    for j in range(1, n+1):\n        if a[i-1] == b[j-1]:\n            dp[i][j] = dp[i-1][j-1] + 1\n        else:\n            dp[i][j] = max(dp[i-1][j], dp[i][j-1])\nprint(dp[m][n])',
        },
    },
    # --- REGULAR PROBLEMS (14 more) ---
    {
        'title': 'Sum of Array',
        'statement': 'Given a list of integers, print their sum.\n\nInput: space-separated integers.\nOutput: a single integer.',
        'category': 'DSA', 'difficulty': 'Easy', 'difficulty_rating': 800,
        'time_limit_sec': 5,
        'tests': [
            {'input': '1 2 3 4 5', 'expected_output': '15', 'is_sample': True},
            {'input': '10 -3 7', 'expected_output': '14', 'is_sample': False},
        ],
        'solution': {
            'explanation': 'Use the built-in sum() function.',
            'reference_code': 'print(sum(map(int, input().split())))',
        },
    },
    {
        'title': 'Count Vowels',
        'statement': 'Given a string, count the number of vowels (a, e, i, o, u, case-insensitive).\n\nInput: a single string.\nOutput: the count.',
        'category': 'DSA', 'difficulty': 'Easy', 'difficulty_rating': 850,
        'time_limit_sec': 5,
        'tests': [
            {'input': 'Hello World', 'expected_output': '3', 'is_sample': True},
            {'input': 'aeiou', 'expected_output': '5', 'is_sample': False},
            {'input': 'xyz', 'expected_output': '0', 'is_sample': False},
        ],
        'solution': {
            'explanation': 'Iterate through the string, check if each character is a vowel.',
            'reference_code': 's = input().lower()\nprint(sum(1 for c in s if c in "aeiou"))',
        },
    },
    {
        'title': 'Factorial',
        'statement': 'Given a non-negative integer n, compute n! (factorial).\n\nInput: a single integer n (0 <= n <= 20).\nOutput: n!',
        'category': 'DSA', 'difficulty': 'Easy', 'difficulty_rating': 850,
        'time_limit_sec': 5,
        'tests': [
            {'input': '5', 'expected_output': '120', 'is_sample': True},
            {'input': '0', 'expected_output': '1', 'is_sample': True},
            {'input': '10', 'expected_output': '3628800', 'is_sample': False},
        ],
        'solution': {
            'explanation': 'Use a loop or math.factorial.',
            'reference_code': 'import math\nprint(math.factorial(int(input())))',
        },
    },
    {
        'title': 'Maximum Subarray Sum',
        'statement': 'Given a list of integers, find the contiguous subarray with the largest sum.\n\nInput: space-separated integers.\nOutput: the maximum sum.',
        'category': 'DSA', 'difficulty': 'Medium', 'difficulty_rating': 1100,
        'time_limit_sec': 5,
        'tests': [
            {'input': '-2 1 -3 4 -1 2 1 -5 4', 'expected_output': '6', 'is_sample': True},
            {'input': '1', 'expected_output': '1', 'is_sample': False},
            {'input': '-1 -2 -3', 'expected_output': '-1', 'is_sample': False},
        ],
        'solution': {
            'explanation': "Use Kadane's algorithm: track current sum and max sum.",
            'reference_code': 'nums = list(map(int, input().split()))\ncur = mx = nums[0]\nfor n in nums[1:]:\n    cur = max(n, cur + n)\n    mx = max(mx, cur)\nprint(mx)',
        },
    },
    {
        'title': 'Valid Parentheses',
        'statement': 'Given a string containing only parentheses (){}[], determine if the input is valid.\n\nInput: a single string.\nOutput: "Yes" or "No".',
        'category': 'DSA', 'difficulty': 'Medium', 'difficulty_rating': 1100,
        'time_limit_sec': 5,
        'tests': [
            {'input': '()[]{}', 'expected_output': 'Yes', 'is_sample': True},
            {'input': '(]', 'expected_output': 'No', 'is_sample': True},
            {'input': '{[]}', 'expected_output': 'Yes', 'is_sample': False},
        ],
        'solution': {
            'explanation': 'Use a stack. Push opening brackets, pop on closing brackets and check match.',
            'reference_code': 's = input()\nstack = []\npairs = {")":"(", "]":"[", "}":"{"}\nvalid = True\nfor c in s:\n    if c in "([{":\n        stack.append(c)\n    elif not stack or stack.pop() != pairs[c]:\n        valid = False\n        break\nif stack: valid = False\nprint("Yes" if valid else "No")',
        },
    },
    {
        'title': 'Merge Sorted Arrays',
        'statement': 'Given two sorted arrays, merge them into one sorted array.\n\nInput: first line is space-separated integers (array 1), second line is space-separated integers (array 2).\nOutput: space-separated merged sorted integers.',
        'category': 'DSA', 'difficulty': 'Medium', 'difficulty_rating': 1200,
        'time_limit_sec': 5,
        'tests': [
            {'input': '1 3 5\n2 4 6', 'expected_output': '1 2 3 4 5 6', 'is_sample': True},
            {'input': '1 2 3\n4 5 6', 'expected_output': '1 2 3 4 5 6', 'is_sample': False},
        ],
        'solution': {
            'explanation': 'Use two pointers to merge in O(n+m) time.',
            'reference_code': 'a = list(map(int, input().split()))\nb = list(map(int, input().split()))\nresult = []\ni = j = 0\nwhile i < len(a) and j < len(b):\n    if a[i] <= b[j]:\n        result.append(a[i]); i += 1\n    else:\n        result.append(b[j]); j += 1\nresult.extend(a[i:])\nresult.extend(b[j:])\nprint(" ".join(map(str, result)))',
        },
    },
    {
        'title': 'Matrix Transpose',
        'statement': 'Given an NxM matrix, print its transpose.\n\nInput: first line is N and M. Next N lines each have M space-separated integers.\nOutput: the transposed matrix, each row on one line.',
        'category': 'DSA', 'difficulty': 'Medium', 'difficulty_rating': 1150,
        'time_limit_sec': 5,
        'tests': [
            {'input': '2 3\n1 2 3\n4 5 6', 'expected_output': '1 4\n2 5\n3 6', 'is_sample': True},
            {'input': '1 3\n7 8 9', 'expected_output': '7\n8\n9', 'is_sample': False},
        ],
        'solution': {
            'explanation': 'Use zip(*matrix) to transpose.',
            'reference_code': 'n, m = map(int, input().split())\nmatrix = [list(map(int, input().split())) for _ in range(n)]\nfor row in zip(*matrix):\n    print(" ".join(map(str, row)))',
        },
    },
    {
        'title': 'Word Frequency Counter',
        'statement': 'Given a sentence, count the frequency of each word (case-insensitive) and print them sorted alphabetically.\n\nInput: a single line of text.\nOutput: one line per word in format "word count", sorted alphabetically.',
        'category': 'Web Dev', 'difficulty': 'Easy', 'difficulty_rating': 900,
        'time_limit_sec': 5,
        'tests': [
            {'input': 'the cat sat on the mat', 'expected_output': 'cat 1\nmat 1\non 1\nsat 1\nthe 2', 'is_sample': True},
            {'input': 'Hello hello HELLO', 'expected_output': 'hello 3', 'is_sample': False},
        ],
        'solution': {
            'explanation': 'Split by spaces, convert to lowercase, use a dict to count, then sort.',
            'reference_code': 'from collections import Counter\nwords = input().lower().split()\ncounts = Counter(words)\nfor w in sorted(counts):\n    print(f"{w} {counts[w]}")',
        },
    },
    {
        'title': 'JSON Key Extractor',
        'statement': 'Given a JSON object as a string, extract and print all keys sorted alphabetically.\n\nInput: a valid JSON object string.\nOutput: keys one per line, sorted.',
        'category': 'Web Dev', 'difficulty': 'Easy', 'difficulty_rating': 900,
        'time_limit_sec': 5,
        'tests': [
            {'input': '{"name": "Alice", "age": 30, "city": "NYC"}', 'expected_output': 'age\ncity\nname', 'is_sample': True},
            {'input': '{"z": 1, "a": 2}', 'expected_output': 'a\nz', 'is_sample': False},
        ],
        'solution': {
            'explanation': 'Parse with json.loads, get keys, sort them.',
            'reference_code': 'import json\ndata = json.loads(input())\nfor key in sorted(data.keys()):\n    print(key)',
        },
    },
    {
        'title': 'CSV Row Parser',
        'statement': 'Given a CSV header row and a data row, output each field as "header: value".\n\nInput: first line is comma-separated headers, second line is comma-separated values.\nOutput: one line per field.',
        'category': 'Web Dev', 'difficulty': 'Medium', 'difficulty_rating': 1050,
        'time_limit_sec': 5,
        'tests': [
            {'input': 'name,age,city\nAlice,30,NYC', 'expected_output': 'name: Alice\nage: 30\ncity: NYC', 'is_sample': True},
        ],
        'solution': {
            'explanation': 'Split both lines by comma, zip them together.',
            'reference_code': 'headers = input().split(",")\nvalues = input().split(",")\nfor h, v in zip(headers, values):\n    print(f"{h}: {v}")',
        },
    },
    {
        'title': 'Mean Squared Error',
        'statement': 'Given two lists of numbers (actual and predicted), compute the Mean Squared Error.\n\nInput: first line is space-separated actual values, second line is space-separated predicted values.\nOutput: MSE rounded to 4 decimal places.',
        'category': 'AI-ML', 'difficulty': 'Easy', 'difficulty_rating': 950,
        'time_limit_sec': 5,
        'tests': [
            {'input': '1 2 3 4\n1.1 2.2 2.8 4.1', 'expected_output': '0.0225', 'is_sample': True},
            {'input': '5 5 5\n5 5 5', 'expected_output': '0.0', 'is_sample': False},
        ],
        'solution': {
            'explanation': 'Compute the average of squared differences.',
            'reference_code': 'actual = list(map(float, input().split()))\npredicted = list(map(float, input().split()))\nmse = sum((a - p) ** 2 for a, p in zip(actual, predicted)) / len(actual)\nprint(round(mse, 4))',
        },
    },
    {
        'title': 'Normalize Data',
        'statement': 'Given a list of numbers, apply min-max normalization to scale them to [0, 1].\n\nInput: space-separated numbers.\nOutput: space-separated normalized values rounded to 4 decimal places.',
        'category': 'AI-ML', 'difficulty': 'Easy', 'difficulty_rating': 950,
        'time_limit_sec': 5,
        'tests': [
            {'input': '1 2 3 4 5', 'expected_output': '0.0 0.25 0.5 0.75 1.0', 'is_sample': True},
            {'input': '10 20 30', 'expected_output': '0.0 0.5 1.0', 'is_sample': False},
        ],
        'solution': {
            'explanation': 'Subtract min, divide by (max - min).',
            'reference_code': 'nums = list(map(float, input().split()))\nlo, hi = min(nums), max(nums)\nif hi == lo:\n    print(" ".join(["0.0"] * len(nums)))\nelse:\n    norm = [(x - lo) / (hi - lo) for x in nums]\n    print(" ".join(str(round(v, 4)) for v in norm))',
        },
    },
    {
        'title': 'Graph BFS Shortest Path',
        'statement': 'Given an unweighted undirected graph, find the shortest path length from node 0 to node N-1.\n\nInput: first line is N (nodes) and E (edges). Next E lines each have two integers u v (an edge). \nOutput: shortest path length, or -1 if unreachable.',
        'category': 'DSA', 'difficulty': 'Hard', 'difficulty_rating': 1500,
        'time_limit_sec': 5,
        'tests': [
            {'input': '4 4\n0 1\n1 2\n2 3\n0 3', 'expected_output': '1', 'is_sample': True},
            {'input': '3 1\n0 1', 'expected_output': '-1', 'is_sample': True},
            {'input': '2 1\n0 1', 'expected_output': '1', 'is_sample': False},
        ],
        'solution': {
            'explanation': 'Use BFS from node 0, tracking distances.',
            'reference_code': 'from collections import deque\nn, e = map(int, input().split())\nadj = [[] for _ in range(n)]\nfor _ in range(e):\n    u, v = map(int, input().split())\n    adj[u].append(v)\n    adj[v].append(u)\ndist = [-1] * n\ndist[0] = 0\nq = deque([0])\nwhile q:\n    u = q.popleft()\n    for v in adj[u]:\n        if dist[v] == -1:\n            dist[v] = dist[u] + 1\n            q.append(v)\nprint(dist[n-1])',
        },
    },
]


class Command(BaseCommand):
    help = 'Seed the database with ~20 sample problems including 6 placement problems.'

    def handle(self, *args, **options):
        created_count = 0
        for pdata in PROBLEMS_DATA:
            if Problem.objects.filter(title=pdata['title']).exists():
                self.stdout.write(f"  Skipping (exists): {pdata['title']}")
                continue

            problem = Problem.objects.create(
                title=pdata['title'],
                statement=pdata['statement'],
                category=pdata['category'],
                difficulty=pdata['difficulty'],
                difficulty_rating=pdata['difficulty_rating'],
                time_limit_sec=pdata['time_limit_sec'],
                is_placement=pdata.get('is_placement', False),
            )

            for tc in pdata['tests']:
                TestCase.objects.create(
                    problem=problem,
                    input=tc['input'],
                    expected_output=tc['expected_output'],
                    is_sample=tc['is_sample'],
                )

            sol = pdata['solution']
            Solution.objects.create(
                problem=problem,
                explanation=sol['explanation'],
                reference_code=sol['reference_code'],
            )

            created_count += 1
            self.stdout.write(f"  Created: {pdata['title']}")

        self.stdout.write(self.style.SUCCESS(f'\nDone! Created {created_count} problems.'))
