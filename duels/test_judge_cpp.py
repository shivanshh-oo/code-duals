from django.test import SimpleTestCase
from unittest.mock import patch
from .judge import judge_submission
from types import SimpleNamespace
import os


class CppJudgeTests(SimpleTestCase):
    @patch('duels.judge._find_cpp_compiler', return_value=None)
    def test_missing_compiler_message_is_actionable(self, _compiler):
        result = judge_submission('int main(){}', [], language='cpp')
        self.assertIn('Install MSYS2', result['error'])

    @patch('duels.judge._run_single_test', return_value={'passed': True, 'status': 'Accepted', 'runtime_ms': 1})
    @patch('duels.judge.subprocess.run')
    @patch('duels.judge._find_cpp_compiler', return_value=r'C:\msys64\ucrt64\bin\g++.exe')
    def test_compile_and_execution_receive_compiler_runtime_path(self, compiler, run, execute):
        run.return_value.returncode = 0
        result = judge_submission('int main(){}', [SimpleNamespace(input='', expected_output='')], language='cpp')
        self.assertEqual(result['verdict'], 'Accepted')
        environment = run.call_args.kwargs['env']
        self.assertTrue(environment['PATH'].startswith(os.path.dirname(compiler.return_value) + os.pathsep))
        self.assertEqual(execute.call_args.kwargs['environment'], environment)
