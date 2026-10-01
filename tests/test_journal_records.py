"""Actual offline Journal commands emit bounded private provenance, never CSV details."""

from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import tempfile
import unittest

from scripts.git_provenance import inspect_checkout
from scripts.run_records import parse_record
from test_journal_runner import FIXTURE, ROOT, run_package


class JournalRecordTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.output = self.root / "reports" / "review.md"

    def record(self, output=None):
        output = output or self.output
        sidecar = Path(str(output) + ".run.json")
        content = sidecar.read_bytes()
        for forbidden in (b"private-sentinel", str(self.root).encode(), b"LABA", b"LABB", b"2.7125", b"notes", b"fees"):
            self.assertNotIn(forbidden, content)
        if os.name != "nt":
            self.assertEqual(sidecar.stat().st_mode & 0o777, 0o600)
        return parse_record(content)

    def assert_stopped(self, result, reason, output=None):
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertNotIn("Traceback", result.stderr)
        self.assertNotIn("private-sentinel", result.stderr)
        record = self.record(output)
        self.assertEqual(record["outcome"], {"status": "stopped", "reason": reason})
        self.assertIsNotNone(record["execution"]["finished_at"])
        return record

    def test_default_completed_record_matches_exact_input_report_and_real_times(self):
        lab = inspect_checkout(ROOT)
        before = datetime.now(timezone.utc)
        result = run_package("--output", self.output)
        after = datetime.now(timezone.utc)
        self.assertEqual(result.returncode, 0, result.stderr)
        record = self.record()
        self.assertEqual(record["mode"], "offline_synthetic")
        self.assertEqual(record["lab"], lab)
        self.assertIsNone(record["kit"])
        self.assertEqual(record["parameters"], {})
        self.assertEqual(record["inputs"], [{"role": "journal_csv", "sha256": hashlib.sha256(FIXTURE.read_bytes()).hexdigest(), "hash_state": "complete"}])
        self.assertEqual(record["outputs"], [{"role": "report", "filename": "review.md", "sha256": hashlib.sha256(self.output.read_bytes()).hexdigest(), "state": "complete"}])
        self.assertEqual(record["source_time"], {"basis": "supplied_trade_times", "trade_count": 2,
                         "first_entry_at": "2026-10-01T13:30:00+00:00", "last_exit_at": "2026-10-01T15:00:00+00:00"})
        self.assertEqual(record["usage"], {"scope": "python_process", "basis": "known_offline_path", "requests_attempted": 0,
                         "credits_reserved": 0, "observed_billing": None, "model": {"mode": "none", "provider": None, "tokens": None}})
        self.assertEqual(record["limits"], {"input_bytes": 1048576, "rows": 1000, "requests": 0, "credits": 0,
                         "model_calls": 0, "output_no_overwrite": True})
        self.assertEqual(record["outcome"], {"status": "completed", "reason": "completed"})
        for stamp in record["execution"].values():
            self.assertLessEqual(before, datetime.fromisoformat(stamp))
            self.assertLessEqual(datetime.fromisoformat(stamp), after)
        self.assertIn(str(self.output) + ".run.json", result.stdout)

    def test_custom_bytes_are_hashed_once_before_parsing_and_times_use_extrema(self):
        header, first, second = FIXTURE.read_bytes().splitlines()
        content = b"\r\n".join((header, second, first)) + b"\r\n"
        content = content.replace(b",0.10,", b",1.10,").replace(b"Fictional long paper trade.", b"private-sentinel note")
        source = self.root / "private-sentinel.csv"
        source.write_bytes(content)
        # Mutating the source at parse entry proves the record/report use the consumed buffer.
        injection = f"""
from pathlib import Path
sys.path.insert(0, {str(ROOT / 'scripts')!r})
import paper_journal
original_parse = paper_journal.parse_journal
def parse_and_replace(content):
    Path(sys.argv[sys.argv.index('--input') + 1]).write_bytes(b'changed after read')
    return original_parse(content)
paper_journal.parse_journal = parse_and_replace
"""
        result = run_package("--input", source, "--output", self.output, injection=injection)
        self.assertEqual(result.returncode, 0, result.stderr)
        record = self.record()
        self.assertEqual(record["mode"], "offline_supplied")
        self.assertEqual(record["inputs"][0]["sha256"], hashlib.sha256(content).hexdigest())
        self.assertEqual(source.read_bytes(), b"changed after read")
        self.assertIn("Total net (USD): 3.76", self.output.read_text())
        self.assertEqual(record["source_time"]["first_entry_at"], "2026-10-01T13:30:00+00:00")
        self.assertEqual(record["source_time"]["last_exit_at"], "2026-10-01T15:00:00+00:00")

    def test_empty_journal_completes_with_no_invented_source_times(self):
        source = self.root / "empty.csv"
        source.write_bytes(FIXTURE.read_bytes().splitlines(keepends=True)[0])
        result = run_package("--input", source, "--output", self.output)
        self.assertEqual(result.returncode, 0, result.stderr)
        record = self.record()
        self.assertEqual(record["source_time"], {"basis": "supplied_trade_times", "trade_count": 0,
                         "first_entry_at": None, "last_exit_at": None})
        self.assertEqual(record["outcome"]["status"], "completed")

    def test_invalid_complete_input_retains_its_hash_without_a_report(self):
        source = self.root / "private-sentinel.csv"
        content = b"private-sentinel\xff"
        source.write_bytes(content)
        result = run_package("--input", source, "--output", self.output)
        record = self.assert_stopped(result, "invalid_journal")
        self.assertEqual(record["inputs"][0], {"role": "journal_csv", "sha256": hashlib.sha256(content).hexdigest(), "hash_state": "complete"})
        self.assertIsNone(record["source_time"])
        self.assertEqual(record["outputs"][0]["state"], "not_written")
        self.assertIsNone(record["outputs"][0]["sha256"])
        self.assertFalse(self.output.exists())

    def test_unreadable_special_and_oversized_inputs_keep_hash_unknown(self):
        huge = self.root / "huge.csv"
        huge.write_bytes(b"x" * (1048576 + 1))
        cases = [(self.root / "missing.csv", "input_unreadable", "read_failed"),
                 (self.root, "input_unreadable", "read_failed"), (huge, "input_too_large", "too_large")]
        if hasattr(os, "mkfifo"):
            fifo = self.root / "pipe.csv"
            os.mkfifo(fifo)
            cases.append((fifo, "input_unreadable", "read_failed"))
        for index, (source, reason, state) in enumerate(cases):
            with self.subTest(reason=reason, index=index):
                output = self.root / f"case-{index}.md"
                result = run_package("--input", source, "--output", output)
                record = self.assert_stopped(result, reason, output)
                self.assertEqual(record["inputs"][0], {"role": "journal_csv", "sha256": None, "hash_state": state})
                self.assertIsNone(record["source_time"])
                self.assertFalse(output.exists())

    def test_existing_report_retains_bytes_with_an_unhashed_stopped_record(self):
        self.output.parent.mkdir()
        self.output.write_bytes(b"Existing private report")
        result = run_package("--output", self.output)
        record = self.assert_stopped(result, "output_exists")
        self.assertEqual(self.output.read_bytes(), b"Existing private report")
        self.assertEqual(record["outputs"][0], {"role": "report", "filename": "review.md", "sha256": None, "state": "not_written"})

    def test_existing_record_file_symlink_and_hardlink_prevent_report_creation(self):
        target = self.root / "prior-record.json"
        target.write_bytes(b"Preserve existing private content")
        for kind in ("file", "symlink", "hardlink"):
            with self.subTest(kind=kind):
                output = self.root / f"{kind}.md"
                sidecar = Path(str(output) + ".run.json")
                if kind == "file":
                    sidecar.write_bytes(target.read_bytes())
                elif kind == "symlink":
                    sidecar.symlink_to(target)
                else:
                    os.link(target, sidecar)
                result = run_package("--output", output)
                self.assertEqual(result.returncode, 1)
                self.assertIn("Run record already exists", result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertFalse(output.exists())
                self.assertEqual(sidecar.read_bytes(), b"Preserve existing private content")
                self.assertEqual(target.read_bytes(), b"Preserve existing private content")

    def test_input_alias_at_sidecar_is_never_replaced(self):
        self.output.parent.mkdir()
        source = Path(str(self.output) + ".run.json")
        source.write_bytes(FIXTURE.read_bytes())
        result = run_package("--input", source, "--output", self.output)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Run record already exists", result.stderr)
        self.assertEqual(source.read_bytes(), FIXTURE.read_bytes())
        self.assertFalse(self.output.exists())

    def test_record_fsync_and_rewrite_failure_still_exit_nonzero_after_complete_json(self):
        injection = """
import os
original_fsync = os.fsync
calls = 0
def fail_record_sync(fd):
    global calls
    calls += 1
    if calls == 2:
        raise OSError('private-sentinel')
    return original_fsync(fd)
def fail_rewrite(*args):
    raise OSError('private-sentinel')
os.fsync = fail_record_sync
os.lseek = fail_rewrite
"""
        result = run_package("--output", self.output, injection=injection)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("Run record finalization failed", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertNotIn("private-sentinel", result.stderr)
        self.assertEqual(result.stdout, "")
        record = self.record()
        self.assertEqual(record["outcome"]["status"], "completed")  # Exit status remains essential evidence.
        self.assertEqual(record["outputs"][0]["sha256"], hashlib.sha256(self.output.read_bytes()).hexdigest())

    def test_record_write_failure_reports_error_even_if_stopped_rewrite_succeeds(self):
        injection = """
import os
original_write = os.write
failed = False
def fail_first_record(fd, content):
    global failed
    if content.startswith(b'{') and not failed:
        failed = True
        original_write(fd, content[:7])
        raise OSError('private-sentinel')
    return original_write(fd, content)
os.write = fail_first_record
"""
        result = run_package("--output", self.output, injection=injection)
        record = self.assert_stopped(result, "record_write_failed")
        self.assertEqual(record["outputs"][0]["state"], "complete")
        self.assertEqual(record["outputs"][0]["sha256"], hashlib.sha256(self.output.read_bytes()).hexdigest())

    def test_record_filename_preflight_stops_before_any_artifact(self):
        for name in ("private-sentinel:report.md", "private-sentinel\\report.md", "x" * 256):
            result = run_package("--output", self.root / "new" / name)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertIn("filename", result.stderr)
            self.assertNotIn("private-sentinel", result.stderr)
            self.assertFalse((self.root / "new").exists())


if __name__ == "__main__":
    unittest.main()
