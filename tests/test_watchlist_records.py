"""Observe actual CLI records without service access or credential prompts."""

from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from scripts.run_records import parse_record
from scripts.probe_kit_watchlist import KIT_REVISION
from test_watchlist_investigator import KIT, PACKAGE, ROOT, GUARD, run_experiment


def sidecar(output):
    return Path(str(output) + ".run.json")


def read_record(output):
    return parse_record(sidecar(output).read_bytes())


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True,
                          text=True, env={"PATH": os.defpath, "GIT_CONFIG_NOSYSTEM": "1",
                                          "GIT_CONFIG_GLOBAL": os.devnull}).stdout.strip()


class StoppedRecordTests(unittest.TestCase):
    def test_missing_and_wrong_kit_record_not_read_input(self):
        with tempfile.TemporaryDirectory() as directory:
            for index, (kit, code, state) in enumerate(((Path(directory) / "missing", "kit_unavailable", "read_failed"),
                                                       (ROOT, "kit_mismatch", "revision_mismatch"))):
                output = Path(directory) / f"report-{index}.md"
                result = run_experiment("--kit", kit, "--fixture", "PRIVATE-MARKER", "--output", output)
                self.assertEqual(result.returncode, 1, result.stderr)
                record = read_record(output)
                self.assertEqual(record["outcome"], {"status": "stopped", "reason": code})
                self.assertEqual(record["kit"]["verification"], state)
                self.assertEqual(record["inputs"][0]["hash_state"], "not_read")
                self.assertIsNone(record["inputs"][0]["sha256"])
                self.assertIsNone(record["parameters"])
                self.assertIsNone(record["source_time"])
                self.assertFalse(output.exists())
                self.assertNotIn("PRIVATE-MARKER", sidecar(output).read_text())
                self.assertNotIn(str(directory), sidecar(output).read_text())

    def test_unsafe_basename_is_preflight_without_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            for name in ("bad:name.md", "bad\\name.md", "bad\nname.md", "a" * 256):
                output = Path(directory) / "new" / name
                result = run_experiment("--kit", directory, "--output", output)
                self.assertEqual(result.returncode, 1)
                self.assertIn("filename", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertFalse(output.parent.exists())


@unittest.skipUnless(KIT.is_dir(), "Kit integration unverified: set SKYLIT_AGENT_KIT to the pinned checkout")
class WorkflowRecordTests(unittest.TestCase):
    def test_default_and_custom_record_matches_consumed_bytes_times_and_usage(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / "PRIVATE-MARKER.json"
            fixture.write_bytes((PACKAGE / "fixture.json").read_bytes() + b" \n")
            for index, options in enumerate(((), ("--fixture", fixture, "--symbols", "qqq,SPY,qqq",
                                                    "--reference-time", "2026-10-01T16:10:00+02:00", "--max-age-seconds", "300"))):
                output = Path(directory) / f"report-{index}.md"
                before = datetime.now(timezone.utc)
                result = run_experiment("--kit", KIT, "--output", output, *options)
                after = datetime.now(timezone.utc)
                self.assertEqual(result.returncode, 0, result.stderr)
                record = read_record(output)
                self.assertEqual(record["outcome"], {"status": "completed", "reason": "completed"})
                self.assertEqual(record["kit"], {"required_revision": KIT_REVISION, "observed_revision": KIT_REVISION, "verification": "verified"})
                consumed = fixture if index else PACKAGE / "fixture.json"
                self.assertEqual(record["inputs"][0]["sha256"], hashlib.sha256(consumed.read_bytes()).hexdigest())
                self.assertEqual(record["outputs"][0]["sha256"], hashlib.sha256(output.read_bytes()).hexdigest())
                self.assertEqual(record["parameters"], {"symbols": ["QQQ", "SPY"] if index else ["SPY", "QQQ"],
                    "reference_time": "2026-10-01T14:10:00+00:00" if index else "2026-10-01T14:01:00+00:00", "max_age_seconds": 300 if index else 900})
                for stamp in record["execution"].values():
                    self.assertLessEqual(before, datetime.fromisoformat(stamp))
                    self.assertLessEqual(datetime.fromisoformat(stamp), after)
                self.assertNotEqual(record["execution"]["started_at"], record["parameters"]["reference_time"])
                self.assertEqual(record["source_time"]["spans"]["SPY"], {"seconds": 120.0, "valid_fields": 4})
                self.assertEqual(record["source_time"]["rows"]["SPY"]["gamma.as_of"]["age_seconds"], 900 if index else 360)
                self.assertEqual(record["usage"], {"scope": "python_process", "basis": "known_offline_path", "requests_attempted": 0,
                    "credits_reserved": 0, "observed_billing": None, "model": {"mode": "none", "provider": None, "tokens": None}})
                for artifact in (output, sidecar(output)):
                    self.assertIn(str(artifact), result.stdout)
                    if os.name != "nt":
                        self.assertEqual(artifact.stat().st_mode & 0o777, 0o600)
                self.assertNotIn("PRIVATE-MARKER", sidecar(output).read_text())
                self.assertNotIn(str(directory), sidecar(output).read_text())

    def test_invalid_input_and_symbols_keep_truthful_provenance(self):
        cases = [(b"PRIVATE-MARKER", "invalid_fixture", "complete"), (b"\xff", "invalid_fixture", "complete"),
                 (b"[]", "invalid_fixture", "complete"), (b"[" * 2000, "invalid_fixture", "complete"), (b" " * 65537, "input_too_large", "too_large"),
                 (None, "input_unreadable", "read_failed")]
        with tempfile.TemporaryDirectory() as directory:
            for index, (content, code, state) in enumerate(cases):
                fixture = Path(directory) / f"PRIVATE-MARKER-{index}.json"
                if content is not None:
                    fixture.write_bytes(content)
                output = Path(directory) / f"report-{index}.md"
                result = run_experiment("--kit", KIT, "--fixture", fixture, "--output", output)
                self.assertEqual(result.returncode, 1, result.stderr)
                record = read_record(output)
                self.assertEqual(record["outcome"]["reason"], code)
                self.assertEqual(record["inputs"][0]["hash_state"], state)
                self.assertEqual(record["inputs"][0]["sha256"], hashlib.sha256(content).hexdigest() if state == "complete" else None)
                self.assertIsNone(record["source_time"])
                self.assertFalse(output.exists())
                self.assertNotIn("PRIVATE-MARKER", sidecar(output).read_text())
            output = Path(directory) / "symbols.md"
            result = run_experiment("--kit", KIT, "--symbols", "SPY,!", "--output", output)
            self.assertEqual(result.returncode, 1)
            record = read_record(output)
            self.assertEqual(record["outcome"]["reason"], "invalid_parameters")
            self.assertIsNone(record["parameters"])
            self.assertEqual(record["inputs"][0]["hash_state"], "not_read")

    def test_existing_sidecar_and_report_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.md"
            sidecar(output).write_bytes(b"Keep record")
            result = run_experiment("--kit", KIT, "--output", output)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(sidecar(output).read_bytes(), b"Keep record")
            self.assertFalse(output.exists())
            sidecar(output).unlink()
            output.write_bytes(b"Keep report")
            result = run_experiment("--kit", KIT, "--output", output)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(output.read_bytes(), b"Keep report")
            record = read_record(output)
            self.assertIn(str(sidecar(output)), result.stderr)
            self.assertEqual(record["outcome"]["reason"], "output_exists")
            self.assertIsNone(record["outputs"][0]["sha256"])

    def test_dirty_kit_stops_before_reading_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            clone = Path(directory) / "kit"
            git(Path(directory), "clone", "--local", "--no-hardlinks", str(KIT.resolve()), str(clone))
            (clone / "synthetic-untracked.txt").write_text("fictional")
            output = Path(directory) / "report.md"
            result = run_experiment("--kit", clone, "--output", output)
            self.assertEqual(result.returncode, 1, result.stderr)
            record = read_record(output)
            self.assertEqual(record["kit"]["verification"], "dirty")
            self.assertEqual(record["outcome"]["reason"], "kit_dirty")
            self.assertEqual(record["inputs"][0]["hash_state"], "not_read")

    def test_actual_clean_dirty_and_non_git_lab_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            clone = Path(directory) / "lab"
            git(Path(directory), "clone", "--local", "--no-hardlinks", str(ROOT), str(clone))
            # Include the candidate runner and ignore rules even before its commit.
            for name in ("experiments/watchlist-investigator/run.py", ".gitignore"):
                shutil.copy2(ROOT / name, clone / name)
            git(clone, "add", ".")
            git(clone, "-c", "user.name=Synthetic test", "-c", "user.email=test@example.invalid", "-c", "core.hooksPath=/dev/null",
                "commit", "--allow-empty", "-m", "Synthetic candidate fixture")
            revision = git(clone, "rev-parse", "HEAD")
            for index, state in enumerate(("clean", "dirty", "unknown")):
                if state == "dirty":
                    (clone / "synthetic-untracked.txt").write_text("fictional")
                if state == "unknown":
                    copied = Path(directory) / "copy"
                    shutil.copytree(clone, copied, ignore=shutil.ignore_patterns(".git"))
                    clone = copied
                output = clone / "experiments/watchlist-investigator/reports/watchlist.md" if state == "clean" else Path(directory) / f"report-{index}.md"
                options = () if state == "clean" else ("--output", output)
                result = run_experiment("--kit", KIT, *options,
                                        script=clone / "experiments/watchlist-investigator/run.py")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(read_record(output)["lab"], {"state": state, "revision": None if state == "unknown" else revision})

    def test_report_write_failure_leaves_stopped_record(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.md"
            injected = (f"import sys; sys.path.insert(0, {str(KIT.resolve())!r})\n"
                        "import skylit_agent_kit.watchlist_cli as cli\n"
                        "def fail(*args): raise OSError('PRIVATE-MARKER')\n"
                        "cli.save_private = fail\n" + GUARD)
            result = subprocess.run([sys.executable, "-X", "utf8", "-I", "-B", "-c", injected,
                                     str(PACKAGE / "run.py"), "--kit", str(KIT), "--output", str(output)],
                                    env={"PATH": os.defpath}, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            record = read_record(output)
            self.assertEqual(record["outcome"]["reason"], "output_write_failed")
            self.assertIsNone(record["outputs"][0]["sha256"])
            self.assertFalse(output.exists())
            self.assertNotIn("PRIVATE-MARKER", result.stderr + sidecar(output).read_text())

    def test_finalization_failure_is_nonzero_even_when_report_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.md"
            injected = (f"import sys; sys.path.insert(0, {str(ROOT / 'scripts')!r})\n"
                        "import record_files\ndef fail(*args): raise OSError('PRIVATE-MARKER')\n"
                        "record_files.os.fsync = fail\n" + GUARD)
            result = subprocess.run([sys.executable, "-X", "utf8", "-I", "-B", "-c", injected,
                                     str(PACKAGE / "run.py"), "--kit", str(KIT), "--output", str(output)],
                                    env={"PATH": os.defpath}, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertTrue(output.exists())
            self.assertIn("finalization failed", result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertNotIn("PRIVATE-MARKER", result.stderr + sidecar(output).read_text())


if __name__ == "__main__":
    unittest.main()
