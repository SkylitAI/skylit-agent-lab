"""Only local synthetic children exercise the evaluator's process limits."""

import contextlib
import errno
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from scripts import evaluation_process as process


@unittest.skipUnless(os.name == "posix", "Process groups require POSIX")
class EvaluationProcessTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def run_python(self, code, remaining=5):
        return process.run_child([sys.executable, "-X", "utf8", "-I", "-B", "-c", code],
                                 self.root, remaining)

    def test_success_nonzero_and_raw_binary_observations(self):
        result = self.run_python("import os; os.write(1, b'hello'); os.write(2, b'warning')")
        self.assertEqual(result, {"exit_code": 0, "stdout": b"hello", "stderr": b"warning", "stop_reason": "exited"})
        result = self.run_python("import os; os.write(1, b'\\xff\\x00'); os.write(2, b'\\xfe'); raise SystemExit(7)")
        self.assertEqual(result, {"exit_code": 7, "stdout": b"\xff\x00", "stderr": b"\xfe", "stop_reason": "exited"})

    def test_minimal_environment_stdin_and_working_directory(self):
        code = """import os
assert os.environ.get('SKYLIT_EVALUATION_TEST_SECRET') is None
assert os.environ.get('PATH') == os.defpath
assert os.environ.get('LC_ALL') == 'C'
assert os.read(0, 1) == b''
# macOS may add its own encoding key after process launch.
assert not os.environ.keys() - {'PATH', 'LC_ALL', '__CF_USER_TEXT_ENCODING'}
open('child-marker', 'wb').write(b'local')
print('clean')
"""
        with patch.dict(os.environ, {"SKYLIT_EVALUATION_TEST_SECRET": "never-inherit-this-marker"}):
            result = self.run_python(code)
        self.assertEqual(result["exit_code"], 0, result["stderr"])
        self.assertEqual(result["stdout"], b"clean\n")
        self.assertEqual((self.root / "child-marker").read_bytes(), b"local")

    def test_each_stream_accepts_exact_cap_and_stops_on_one_more_byte(self):
        for descriptor, stream in ((1, "stdout"), (2, "stderr")):
            for size in (65536, 65537):
                with self.subTest(stream=stream, size=size):
                    result = self.run_python(f"import os; os.write({descriptor}, b'x' * {size})")
                    self.assertEqual(result[stream], b"x" * 65536)
                    self.assertEqual(result["stop_reason"], "exited" if size == 65536 else stream + "_limit")

    def test_both_streams_drain_without_deadlock(self):
        code = """import os, threading
def emit(fd, value):
    for _ in range(16):
        os.write(fd, value * 4096)
thread = threading.Thread(target=emit, args=(1, b'a'))
thread.start()
emit(2, b'b')
thread.join()
"""
        result = self.run_python(code)
        self.assertEqual(result, {"exit_code": 0, "stdout": b"a" * 65536,
                                  "stderr": b"b" * 65536, "stop_reason": "exited"})

    def test_child_cap_and_remaining_suite_time_both_bound_execution(self):
        for child_cap, remaining in ((0.2, 5), (20, 0.2)):
            with self.subTest(child_cap=child_cap, remaining=remaining):
                started = time.monotonic()
                with patch.object(process, "CHILD_SECONDS", child_cap):
                    result = self.run_python("import time; time.sleep(60)", remaining)
                self.assertEqual(result["stop_reason"], "timeout")
                self.assertIsInstance(result["exit_code"], int)
                self.assertLess(result["exit_code"], 0)
                self.assertLess(time.monotonic() - started, 1.5)

    def test_exhausted_or_invalid_budget_does_not_start_child(self):
        code = "open('should-not-exist', 'wb').write(b'bad')"
        for remaining in (0, -1, True, float("nan"), float("inf"), "1"):
            result = self.run_python(code, remaining)
            self.assertEqual(result["stop_reason"], "timeout" if remaining == 0 else "invalid_request")
            self.assertIsNone(result["exit_code"])
            self.assertEqual(result["stdout"], result["stderr"])
            self.assertFalse((self.root / "should-not-exist").exists())

    def test_closed_streams_do_not_disable_the_deadline(self):
        started = time.monotonic()
        result = self.run_python("import os, time; os.close(1); os.close(2); time.sleep(60)", 0.2)
        self.assertEqual(result["stop_reason"], "timeout")
        self.assertLess(result["exit_code"], 0)
        self.assertLess(time.monotonic() - started, 1.5)

    def test_launch_errors_are_fixed_and_never_printed(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            for argv, cwd in (([str(self.root / "private-marker")], self.root),
                              ([sys.executable], self.root / "private-marker")):
                result = process.run_child(argv, cwd, 5)
                self.assertEqual(result, {"exit_code": None, "stdout": b"", "stderr": b"", "stop_reason": "launch_failed"})
        self.assertEqual(output.getvalue(), "")

    def test_cleanup_errors_do_not_escape_or_invent_an_exit(self):
        real_popen = subprocess.Popen
        for failure in ("close", "wait"):
            children = []

            def launch(*args, **kwargs):
                child = real_popen(*args, **kwargs)
                children.append((child, child.stdout.close, child.wait))
                if failure == "close":
                    child.stdout.close = Mock(side_effect=OSError("private-marker"))
                else:
                    child.wait = Mock(side_effect=subprocess.TimeoutExpired("private-marker", 1))
                return child

            try:
                with patch.object(process.subprocess, "Popen", side_effect=launch):
                    result = self.run_python("pass")
                self.assertEqual(result["stop_reason"], "cleanup_failed")
                self.assertEqual(result["exit_code"], None if failure == "wait" else 0)
                self.assertNotIn(b"private-marker", result["stderr"])
            finally:
                for child, close, wait in children:
                    child.stdout.close, child.wait = close, wait
                    close()
                    wait(timeout=2)

    def descendant_parent(self, close_pipes):
        descendant = """import os, signal, time
signal.signal(signal.SIGTERM, signal.SIG_IGN)
print(os.getpid(), flush=True)
if CLOSE_PIPES:
    os.close(1)
    os.close(2)
deadline = time.monotonic() + 3
while time.monotonic() < deadline:
    with open('heartbeat', 'w') as target:
        target.write(str(time.monotonic_ns()))
    time.sleep(0.02)
""".replace("CLOSE_PIPES", repr(close_pipes))
        return f"""import subprocess, sys, time
from pathlib import Path
subprocess.Popen([sys.executable, '-X', 'utf8', '-I', '-B', '-c', {descendant!r}])
while not Path('heartbeat').exists():
    time.sleep(0.005)
"""

    def assert_descendant_stopped(self, result):
        # Only probe the identifier emitted by this test's synthetic descendant.
        pid = int(result["stdout"].splitlines()[0])
        self.assertGreater(pid, 1)
        deadline = time.monotonic() + 0.5
        while time.monotonic() < deadline:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                break
            if sys.platform.startswith("linux"):
                try:
                    state = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0]
                except (FileNotFoundError, ProcessLookupError):
                    break
                if state == "Z":  # Orphan reaping belongs to the container's init.
                    break
            time.sleep(0.01)
        else:
            self.fail("Synthetic descendant remained running after cleanup")
        heartbeat = (self.root / "heartbeat").read_bytes()
        time.sleep(0.15)
        self.assertEqual((self.root / "heartbeat").read_bytes(), heartbeat)

    def test_descendant_retaining_pipes_and_ignoring_term_is_killed(self):
        started = time.monotonic()
        result = self.run_python(self.descendant_parent(close_pipes=False), 0.5)
        self.assertEqual(result["stop_reason"], "timeout")
        self.assertEqual(result["exit_code"], 0)
        self.assertLess(time.monotonic() - started, 1.5)
        self.assert_descendant_stopped(result)

    def test_proc_disappearance_is_terminal_but_permission_denial_is_not(self):
        heartbeat = self.root / "heartbeat"
        heartbeat.write_bytes(b"stable synthetic heartbeat")
        errors = (FileNotFoundError(errno.ENOENT, "Synthetic process removed"),
                  ProcessLookupError(errno.ESRCH, "Synthetic process disappeared during read"),
                  PermissionError(errno.EACCES, "Synthetic permission denial"))
        for error in errors:
            with self.subTest(error=type(error).__name__), \
                    patch.object(sys, "platform", "linux"), patch.object(os, "kill") as probe, \
                    patch.object(Path, "read_text", autospec=True, side_effect=error) as read, \
                    patch.object(time, "sleep"):
                if isinstance(error, PermissionError):
                    with self.assertRaises(PermissionError) as caught:
                        self.assert_descendant_stopped({"stdout": b"999999\n"})
                    self.assertIs(caught.exception, error)
                else:
                    self.assert_descendant_stopped({"stdout": b"999999\n"})
                probe.assert_called_once_with(999999, 0)
                read.assert_called_once_with(Path("/proc/999999/stat"))
                self.assertEqual(heartbeat.read_bytes(), b"stable synthetic heartbeat")

    def test_normal_leader_exit_also_kills_descendant_with_closed_pipes(self):
        result = self.run_python(self.descendant_parent(close_pipes=True), 2)
        self.assertEqual(result["stop_reason"], "exited")
        self.assertEqual(result["exit_code"], 0)
        self.assert_descendant_stopped(result)

    def test_output_overflow_kills_the_descendant_group(self):
        code = self.descendant_parent(close_pipes=False) + "import os; os.write(1, b'x' * 65537)\n"
        result = self.run_python(code)
        self.assertEqual(result["stop_reason"], "stdout_limit")
        self.assertEqual(len(result["stdout"]), 65536)
        self.assert_descendant_stopped(result)


if __name__ == "__main__":
    unittest.main()
