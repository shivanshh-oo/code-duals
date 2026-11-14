"""
Judge module: runs submitted Python code against test cases.
Uses subprocess.run with a timeout. Returns verdict and test results.
"""
import subprocess
import sys
import tempfile
import os


def judge_submission(code, test_cases, time_limit_sec=5):
    """
    Run code against test cases and return the verdict.

    Args:
        code: Python source code string
        test_cases: queryset or list of TestCase objects with .input and .expected_output
        time_limit_sec: max seconds per test case

    Returns:
        dict with keys: verdict, tests_passed, tests_total, details (list of per-test results)
    """
    tests_total = len(test_cases) if not hasattr(test_cases, 'count') else test_cases.count()
    tests_passed = 0
    details = []

    # Write code to a temp file
    tmp_file = None
    try:
        tmp_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.py', delete=False, encoding='utf-8'
        )
        tmp_file.write(code)
        tmp_file.close()

        for tc in test_cases:
            result = _run_single_test(tmp_file.name, tc.input, tc.expected_output, time_limit_sec)
            details.append(result)
            if result['passed']:
                tests_passed += 1
    finally:
        if tmp_file and os.path.exists(tmp_file.name):
            os.unlink(tmp_file.name)

    # Determine overall verdict
    if tests_passed == tests_total:
        verdict = 'Accepted'
    elif any(d['status'] == 'Time Limit' for d in details):
        verdict = 'Time Limit'
    elif any(d['status'] == 'Error' for d in details):
        verdict = 'Error'
    else:
        verdict = 'Wrong Answer'

    return {
        'verdict': verdict,
        'tests_passed': tests_passed,
        'tests_total': tests_total,
        'details': details,
    }


def _run_single_test(code_path, input_data, expected_output, time_limit_sec):
    """Run code against a single test case."""
    try:
        result = subprocess.run(
            [sys.executable, code_path],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=time_limit_sec,
        )

        if result.returncode != 0:
            return {
                'passed': False,
                'status': 'Error',
                'output': result.stderr[:500],
                'expected': expected_output,
            }

        actual_output = result.stdout.strip()
        expected_clean = expected_output.strip()

        if actual_output == expected_clean:
            return {
                'passed': True,
                'status': 'Accepted',
                'output': actual_output,
                'expected': expected_clean,
            }
        else:
            return {
                'passed': False,
                'status': 'Wrong Answer',
                'output': actual_output,
                'expected': expected_clean,
            }

    except subprocess.TimeoutExpired:
        return {
            'passed': False,
            'status': 'Time Limit',
            'output': 'Time Limit Exceeded',
            'expected': expected_output.strip(),
        }
    except Exception as e:
        return {
            'passed': False,
            'status': 'Error',
            'output': str(e)[:500],
            'expected': expected_output.strip(),
        }
