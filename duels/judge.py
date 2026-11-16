"""
Judge module: runs submitted Python code against test cases.
Uses subprocess.run with a timeout. Returns verdict and test results.
"""
import subprocess
import sys
import tempfile
import os
import time
import shutil


def judge_submission(code, test_cases, time_limit_sec=5, language='python'):
    """
    Run code against test cases and return the verdict.

    Args:
        code: Python source code string
        test_cases: queryset or list of TestCase objects with .input and .expected_output
        time_limit_sec: max seconds per test case

    Returns:
        dict with keys: verdict, tests_passed, tests_total, details (list of per-test results)
    """
    test_cases = list(test_cases)
    tests_total = len(test_cases)
    if language not in ('python', 'cpp'):
        return {'verdict': 'Error', 'tests_passed': 0, 'tests_total': tests_total, 'runtime_ms': 0, 'details': [], 'error': 'Unsupported language'}
    if language == 'cpp':
        compiler = shutil.which('g++')
        if not compiler:
            return {'verdict': 'Error', 'tests_passed': 0, 'tests_total': tests_total, 'runtime_ms': 0, 'details': [], 'error': 'C++ requires g++ on the server PATH.'}
        with tempfile.TemporaryDirectory() as directory:
            source = os.path.join(directory, 'main.cpp')
            executable = os.path.join(directory, 'main.exe' if os.name == 'nt' else 'main')
            with open(source, 'w', encoding='utf-8') as stream:
                stream.write(code)
            try:
                compiled = subprocess.run([compiler, '-std=c++17', '-O2', source, '-o', executable], capture_output=True, text=True, timeout=30)
                if compiled.returncode:
                    raise ValueError(compiled.stderr[:2000])
            except (OSError, ValueError, subprocess.TimeoutExpired) as error:
                return {'verdict': 'Error', 'tests_passed': 0, 'tests_total': tests_total, 'runtime_ms': 0, 'details': [], 'error': 'Compilation failed: ' + str(error)}
            details = [_run_single_test(executable, tc.input, tc.expected_output, time_limit_sec, native=True) for tc in test_cases]
            passed = sum(item['passed'] for item in details)
            verdict = 'Accepted' if tests_total and passed == tests_total else 'Time Limit' if any(item['status'] == 'Time Limit' for item in details) else 'Error' if not tests_total or any(item['status'] == 'Error' for item in details) else 'Wrong Answer'
            return {'verdict': verdict, 'tests_passed': passed, 'tests_total': tests_total, 'runtime_ms': sum(item['runtime_ms'] for item in details), 'details': details}
    if not tests_total:
        return {'verdict': 'Error', 'tests_passed': 0, 'tests_total': 0, 'runtime_ms': 0, 'details': []}
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
        'runtime_ms': sum(d.get('runtime_ms', 0) for d in details),
        'details': details,
    }


def _run_single_test(code_path, input_data, expected_output, time_limit_sec, native=False):
    """Run code against a single test case."""
    try:
        started = time.perf_counter()
        result = subprocess.run(
            [code_path] if native else [sys.executable, code_path],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=time_limit_sec,
        )

        runtime_ms = max(1, round((time.perf_counter() - started) * 1000))
        if result.returncode != 0:
            return {
                'passed': False,
                'status': 'Error',
                'output': result.stderr[:500],
                'expected': expected_output,
                'runtime_ms': runtime_ms,
            }

        actual_output = result.stdout.strip()
        expected_clean = expected_output.strip()

        if actual_output == expected_clean:
            return {
                'passed': True,
                'status': 'Accepted',
                'output': actual_output,
                'expected': expected_clean,
                'runtime_ms': runtime_ms,
            }
        else:
            return {
                'passed': False,
                'status': 'Wrong Answer',
                'output': actual_output,
                'expected': expected_clean,
                'runtime_ms': runtime_ms,
            }

    except subprocess.TimeoutExpired:
        return {
            'passed': False,
            'status': 'Time Limit',
            'output': 'Time Limit Exceeded',
            'expected': expected_output.strip(),
            'runtime_ms': max(1, round(time_limit_sec * 1000)),
        }
    except Exception as e:
        return {
            'passed': False,
            'status': 'Error',
            'output': str(e)[:500],
            'expected': expected_output.strip(),
            'runtime_ms': 0,
        }
