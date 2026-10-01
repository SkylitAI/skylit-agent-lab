"""Exclusive local report/record writes preserve old files and disclose failures."""

import copy
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from scripts import record_files, run_records
from test_run_records import sample_record


def private_report(path, text):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(text)


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.output = self.root / "reports" / "fictional.md"
        self.sidecar = Path(str(self.output) + ".run.json")

    def saved_record(self):
        return run_records.parse_record(self.sidecar.read_bytes())

    def assert_failure(self, code, writer=private_report):
        with self.assertRaises(record_files.PersistenceError) as caught:
            record_files.save_run(self.output, "Fictional report.\n", sample_record(), writer)
        self.assertEqual(caught.exception.code, code)
        self.assertNotIn("private failure detail", str(caught.exception))
        return caught.exception

    def test_helper_imports_from_the_workflow_scripts_path_in_isolated_python(self):
        scripts = Path(__file__).resolve().parents[1] / "scripts"
        result = subprocess.run(
            [sys.executable, "-I", "-B", "-c", "import sys; sys.path.insert(0, sys.argv[1]); from record_files import save_run", str(scripts)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_success_reserves_sidecar_first_and_hashes_exact_private_report(self):
        original = sample_record()
        unchanged = copy.deepcopy(original)
        text = "Fictional · report\nsecond line\r\n"
        before = datetime.now(timezone.utc)

        def writer(path, content):
            self.assertTrue(self.sidecar.is_file())
            self.assertEqual(self.sidecar.read_bytes(), b"")
            private_report(path, content)

        final = record_files.save_run(self.output, text, original, writer)
        after = datetime.now(timezone.utc)
        self.assertEqual(original, unchanged)
        self.assertEqual(final, self.saved_record())
        self.assertEqual(final["outcome"], {"status": "completed", "reason": "completed"})
        self.assertEqual(final["outputs"][0]["sha256"], hashlib.sha256(self.output.read_bytes()).hexdigest())
        self.assertEqual(final["outputs"][0]["filename"], self.output.name)
        finished = datetime.fromisoformat(final["execution"]["finished_at"])
        self.assertLessEqual(before, finished)
        self.assertLessEqual(finished, after)
        if os.name != "nt":
            self.assertEqual(self.output.stat().st_mode & 0o777, 0o600)
            self.assertEqual(self.sidecar.stat().st_mode & 0o777, 0o600)

    def test_windows_newline_translation_is_included_in_hash(self):
        def translated_writer(path, text):
            with path.open("xb") as stream:
                stream.write(text.replace("\n", "\r\n").encode("utf-8"))

        with mock.patch.object(record_files.os, "linesep", "\r\n"):
            record_files.save_run(self.output, "line\nexisting\r\n", sample_record(), translated_writer)
        self.assertEqual(self.output.read_bytes(), b"line\r\nexisting\r\r\n")
        self.assertEqual(self.saved_record()["outputs"][0]["sha256"], hashlib.sha256(self.output.read_bytes()).hexdigest())

    def test_stopped_computation_saves_record_without_calling_report_writer(self):
        record = sample_record()
        record["outcome"] = {"status": "stopped", "reason": "invalid_fixture"}
        record["parameters"] = record["source_time"] = None
        writer = mock.Mock(side_effect=AssertionError("Report writer must not run"))
        final = record_files.save_run(self.output, None, record, writer)
        self.assertEqual(final["outcome"], record["outcome"])
        self.assertEqual(final["outputs"][0]["state"], "not_written")
        self.assertIsNone(final["outputs"][0]["sha256"])
        self.assertFalse(self.output.exists())
        self.assertEqual(self.saved_record(), final)

    def test_invalid_record_or_report_is_rejected_before_parent_creation(self):
        for invalid in ("record", "report"):
            record = sample_record()
            if invalid == "record":
                record["unexpected"] = "private failure detail"
            with self.subTest(invalid=invalid):
                with self.assertRaises(record_files.PersistenceError) as caught:
                    record_files.save_run(self.output, "\ud800" if invalid == "report" else "text", record, private_report)
                self.assertEqual(caught.exception.code, "invalid_" + invalid)
                self.assertFalse(self.output.parent.exists())

    def test_existing_file_symlink_and_hardlink_sidecars_stop_before_report(self):
        self.sidecar.parent.mkdir()
        original = self.root / "original.json"
        original.write_bytes(b"Keep this private record.")
        for kind in ("file", "symlink", "hardlink"):
            with self.subTest(kind=kind):
                if kind == "file":
                    self.sidecar.write_bytes(original.read_bytes())
                elif kind == "symlink":
                    self.sidecar.symlink_to(original)
                else:
                    os.link(original, self.sidecar)
                self.assert_failure("record_exists", mock.Mock(side_effect=AssertionError("Writer ran")))
                self.assertEqual(self.sidecar.read_bytes(), b"Keep this private record.")
                self.assertEqual(original.read_bytes(), b"Keep this private record.")
                self.assertFalse(self.output.exists())
                self.sidecar.unlink()

    def test_unwritable_sidecar_stops_before_report(self):
        with mock.patch.object(record_files.os, "open", side_effect=PermissionError("private failure detail")):
            self.assert_failure("record_unavailable", mock.Mock(side_effect=AssertionError("Writer ran")))
        self.assertFalse(self.output.exists())
        self.assertFalse(self.sidecar.exists())

    def test_parent_file_is_unavailable_rather_than_an_existing_sidecar(self):
        self.output.parent.write_text("Keep this file.\n")
        self.assert_failure("record_unavailable", mock.Mock(side_effect=AssertionError("Writer ran")))
        self.assertEqual(self.output.parent.read_text(), "Keep this file.\n")
        self.assertFalse(self.sidecar.exists())

    def test_failed_stopped_rewrite_still_raises_when_complete_json_remains(self):
        with mock.patch.object(record_files.os, "fsync", side_effect=OSError("private failure detail")), \
             mock.patch.object(record_files.os, "lseek", side_effect=OSError("private failure detail")):
            self.assert_failure("record_write_failed")
        self.assertEqual(self.saved_record()["outcome"]["status"], "completed")
        self.assertTrue(self.output.exists())

    def test_existing_file_symlink_and_hardlink_reports_are_untouched(self):
        self.output.parent.mkdir()
        original = self.root / "original.md"
        original.write_bytes(b"Keep this private report.")
        for kind in ("file", "symlink", "hardlink"):
            with self.subTest(kind=kind):
                if kind == "file":
                    self.output.write_bytes(original.read_bytes())
                elif kind == "symlink":
                    self.output.symlink_to(original)
                else:
                    os.link(original, self.output)
                self.assert_failure("output_exists")
                final = self.saved_record()
                self.assertEqual(final["outcome"], {"status": "stopped", "reason": "output_exists"})
                self.assertEqual(final["outputs"][0]["state"], "not_written")
                self.assertIsNone(final["outputs"][0]["sha256"])
                self.assertEqual(self.output.read_bytes(), b"Keep this private report.")
                self.assertEqual(original.read_bytes(), b"Keep this private report.")
                self.output.unlink()
                self.sidecar.unlink()

    def test_partial_report_failure_records_unknown_hash_and_keeps_partial_file(self):
        def partial_writer(path, text):
            private_report(path, "Partial data.")
            raise OSError("private failure detail")

        self.assert_failure("output_write_failed", partial_writer)
        final = self.saved_record()
        self.assertEqual(final["outcome"], {"status": "stopped", "reason": "output_write_failed"})
        self.assertEqual(final["outputs"][0]["state"], "write_failed")
        self.assertIsNone(final["outputs"][0]["sha256"])
        self.assertEqual(self.output.read_text(), "Partial data.")

    def test_short_record_write_gets_one_stopped_rewrite(self):
        original_write = os.write
        calls = []

        def short_once(descriptor, payload):
            calls.append(len(payload))
            return original_write(descriptor, payload[:10] if len(calls) == 1 else payload)

        with mock.patch.object(record_files.os, "write", side_effect=short_once):
            self.assert_failure("record_write_failed")
        self.assertEqual(len(calls), 2)
        final = self.saved_record()
        self.assertEqual(final["outcome"], {"status": "stopped", "reason": "record_write_failed"})
        self.assertEqual(final["outputs"][0]["state"], "complete")
        self.assertEqual(final["outputs"][0]["sha256"], hashlib.sha256(self.output.read_bytes()).hexdigest())

    def test_record_flush_failure_never_reports_success(self):
        with mock.patch.object(record_files.os, "fsync", side_effect=[OSError("private failure detail"), None]) as flush:
            self.assert_failure("record_write_failed")
        self.assertEqual(flush.call_count, 2)
        self.assertEqual(self.saved_record()["outcome"], {"status": "stopped", "reason": "record_write_failed"})
        self.assertTrue(self.output.exists())

    def test_late_serialization_failure_is_not_reported_as_success(self):
        original_payload = record_files._payload
        calls = []

        def fail_at_finalization(record):
            calls.append(record["outcome"]["reason"])
            if len(calls) == 2:
                raise run_records.RecordError("private failure detail")
            return original_payload(record)

        with mock.patch.object(record_files, "_payload", side_effect=fail_at_finalization):
            self.assert_failure("record_write_failed")
        self.assertEqual(calls, ["completed", "completed", "record_write_failed"])
        self.assertEqual(self.saved_record()["outcome"]["reason"], "record_write_failed")
        self.assertEqual(self.saved_record()["outputs"][0]["sha256"], hashlib.sha256(self.output.read_bytes()).hexdigest())

    def test_persistent_record_failure_stops_after_one_rewrite_without_deleting_report(self):
        with mock.patch.object(record_files.os, "write", side_effect=OSError("private failure detail")) as write:
            self.assert_failure("record_write_failed")
        self.assertEqual(write.call_count, 2)
        self.assertEqual(self.sidecar.read_bytes(), b"")
        self.assertEqual(self.output.read_text(), "Fictional report.\n")

    @unittest.skipUnless(Path(os.environ.get("SKYLIT_AGENT_KIT", Path(__file__).resolve().parents[2] / "skylit-agent-kit")).is_dir(), "Pinned local Kit required")
    def test_real_pinned_kit_writer_matches_record_hash(self):
        from scripts.probe_kit_watchlist import load_kit
        kit = Path(os.environ.get("SKYLIT_AGENT_KIT", Path(__file__).resolve().parents[2] / "skylit-agent-kit"))
        load_kit(kit)
        from skylit_agent_kit.watchlist_cli import save_private
        record_files.save_run(self.output, "Fictional · report\n", sample_record(), save_private)
        self.assertEqual(self.saved_record()["outputs"][0]["sha256"], hashlib.sha256(self.output.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
