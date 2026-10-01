"""Actual Market Brief records with synthetic bytes and blocked/mocked network."""

import contextlib
from datetime import datetime, timezone
import hashlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import record_files
from scripts.run_records import parse_record
from test_market_brief_runner import FIXTURE, GUARD, PACKAGE, ROOT, RUNNER, SCRIPT


EMPTY = b"<rss version='2.0'><channel><title>Fictional</title><link>https://www.federalreserve.gov/feeds/feeds.htm</link><description>Fictional</description></channel></rss>"


def sidecar(output):
    return Path(str(output) + ".run.json")


class MarketRecordTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name).resolve()
        self.output = self.folder / "brief.md"

    def command(self, *args, script=SCRIPT, output=None):
        return subprocess.run([sys.executable, "-X", "utf8", "-I", "-B", "-c", GUARD,
                               str(script), "--output", str(output or self.output), *map(str, args)],
                              capture_output=True, text=True, timeout=10, check=False)

    def read_record(self, output=None):
        return parse_record(sidecar(output or self.output).read_bytes())

    def invoke(self, *args):
        with contextlib.redirect_stdout(io.StringIO()) as stdout, contextlib.redirect_stderr(io.StringIO()) as stderr:
            code = RUNNER.main(["--output", str(self.output), *map(str, args)])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_actual_default_record_hashes_times_usage_and_permissions(self):
        before = datetime.now(timezone.utc)
        result = self.command("--limit", 1)
        after = datetime.now(timezone.utc)
        self.assertEqual(result.returncode, 0, result.stderr)
        record = self.read_record()
        self.assertEqual((record["experiment_id"], record["mode"], record["kit"]),
                         ("market-brief", "offline_synthetic", None))
        self.assertEqual(record["inputs"], [{"role": "fed_press_xml", "hash_state": "complete",
                                           "sha256": hashlib.sha256(FIXTURE).hexdigest()}])
        self.assertEqual(record["parameters"], {"limit": 1})
        self.assertEqual(record["source_time"], {"status": "available", "retrieved_at": None,
                                               "published_at": ["2020-01-01T12:00:00+00:00"]})
        self.assertEqual(record["outcome"], {"status": "completed", "reason": "completed"})
        self.assertEqual(record["outputs"][0], {"role": "report", "filename": "brief.md",
            "state": "complete", "sha256": hashlib.sha256(self.output.read_bytes()).hexdigest()})
        self.assertEqual(record["usage"], {"scope": "python_process", "basis": "known_offline_path",
            "requests_attempted": 0, "credits_reserved": 0, "observed_billing": None,
            "model": {"mode": "none", "provider": None, "tokens": None}})
        self.assertEqual(record["limits"], {"input_bytes": 524288, "items": 100, "display_items": 20,
            "requests": 0, "fetch_timeout_seconds": None, "credits": 0, "model_calls": 0,
            "output_no_overwrite": True})
        for stamp in record["execution"].values():
            self.assertLessEqual(before, datetime.fromisoformat(stamp))
            self.assertLessEqual(datetime.fromisoformat(stamp), after)
        for artifact in (self.output, sidecar(self.output)):
            self.assertIn(str(artifact), result.stdout)
            if os.name == "posix":
                self.assertEqual(artifact.stat().st_mode & 0o777, 0o600)

    def test_supplied_record_excludes_input_path_titles_urls_and_raw_errors(self):
        source = self.folder / "PRIVATE-PATH.xml"
        source.write_bytes(FIXTURE.replace(b"paper kites", "PRIVATE-TITLE café".encode()))
        result = self.command("--input", source)
        self.assertEqual(result.returncode, 0, result.stderr)
        record = self.read_record()
        self.assertEqual(record["mode"], "offline_supplied")
        self.assertEqual(record["inputs"][0]["sha256"], hashlib.sha256(source.read_bytes()).hexdigest())
        content = sidecar(self.output).read_text(encoding="utf-8")
        for value in ("PRIVATE-PATH", "PRIVATE-TITLE", str(self.folder), "https://", "fictional20200101a"):
            self.assertNotIn(value, content)

    def test_empty_completes_and_invalid_bytes_save_hashed_stopped_gaps(self):
        source = self.folder / "private.xml"
        for raw, status, reason in ((EMPTY, "empty", "completed"), (b"PRIVATE-ERROR", "invalid", "invalid_feed"),
                                    (b"\xff", "invalid", "invalid_feed")):
            with self.subTest(status=status, raw=raw[:12]):
                self.output.unlink(missing_ok=True)
                sidecar(self.output).unlink(missing_ok=True)
                source.write_bytes(raw)
                result = self.command("--input", source)
                self.assertEqual(result.returncode, 0 if reason == "completed" else 1, result.stderr)
                record = self.read_record()
                self.assertEqual(record["outcome"]["reason"], reason)
                self.assertEqual(record["source_time"], {"status": status, "retrieved_at": None, "published_at": []})
                self.assertEqual(record["inputs"][0]["sha256"], hashlib.sha256(raw).hexdigest())
                self.assertEqual(record["outputs"][0]["sha256"], hashlib.sha256(self.output.read_bytes()).hexdigest())
                self.assertNotIn("PRIVATE-ERROR", sidecar(self.output).read_text())

    def test_unreadable_oversize_and_changed_default_save_only_stopped_records(self):
        for index, (raw, reason, state) in enumerate(((None, "input_unreadable", "read_failed"),
                                                      (b" " * 524289, "input_too_large", "too_large"))):
            source = self.folder / f"PRIVATE-PATH-{index}.xml"
            output = self.folder / f"stopped-{index}.md"
            if raw is not None:
                source.write_bytes(raw)
            result = self.command("--input", source, output=output)
            self.assertEqual(result.returncode, 1, result.stderr)
            record = self.read_record(output)
            self.assertEqual(record["outcome"], {"status": "stopped", "reason": reason})
            self.assertEqual(record["inputs"][0]["hash_state"], state)
            self.assertIsNone(record["inputs"][0]["sha256"])
            self.assertIsNone(record["source_time"])
            self.assertEqual(record["outputs"][0]["state"], "not_written")
            self.assertFalse(output.exists())
        raw = FIXTURE + b"\n"
        (self.folder / "fixture.xml").write_bytes(raw)
        with patch.object(RUNNER, "PACKAGE", self.folder):
            code, _, stderr = self.invoke()
        self.assertEqual(code, 1, stderr)
        record = self.read_record()
        self.assertEqual(record["outcome"]["reason"], "fixture_changed")
        self.assertEqual(record["inputs"][0]["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertIsNone(record["source_time"])
        self.assertFalse(self.output.exists())

    def test_hash_is_of_consumed_buffer_even_if_input_changes_after_read(self):
        source = self.folder / "supplied.xml"
        source.write_bytes(FIXTURE)
        original = RUNNER._load_input
        def replace_after_read(path):
            raw = original(path)
            path.write_bytes(b"replacement")
            return raw
        with patch.object(RUNNER, "_load_input", side_effect=replace_after_read):
            code, _, stderr = self.invoke("--input", source)
        self.assertEqual(code, 0, stderr)
        self.assertEqual(self.read_record()["inputs"][0]["sha256"], hashlib.sha256(FIXTURE).hexdigest())

    def test_invalid_os_input_path_saves_safe_unreadable_record(self):
        code, stdout, stderr = self.invoke("--input", "PRIVATE-PATH\x00marker")
        self.assertEqual(code, 1, stderr)
        self.assertEqual(stdout, "")
        self.assertFalse(self.output.exists())
        record = self.read_record()
        self.assertEqual(record["outcome"], {"status": "stopped", "reason": "input_unreadable"})
        self.assertEqual(record["inputs"], [{"role": "fed_press_xml", "hash_state": "read_failed", "sha256": None}])
        self.assertIsNone(record["source_time"])
        self.assertIn("Choose a readable regular file for --input.", stderr)
        for value in ("PRIVATE-PATH", "marker", "embedded null", "Traceback"):
            self.assertNotIn(value, stderr + sidecar(self.output).read_text())

    def test_invalid_cli_and_output_names_create_neither_artifact_nor_request(self):
        for name, args in (("brief.md", ("--limit", "0")), ("bad:name.md", ("--fetch",)),
                           ("bad\\name.md", ("--fetch",)), ("a" * 247, ("--fetch",))):
            output = self.folder / "absent" / name
            result = self.command(*args, output=output)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertFalse(output.parent.exists())
            self.assertNotIn("Traceback", result.stderr)

    def test_report_and_sidecar_collisions_stop_before_fetch(self):
        for target in (self.output, sidecar(self.output)):
            for kind in ("file", "symlink", "hardlink"):
                with self.subTest(target=target.name, kind=kind):
                    keeper = self.folder / "keeper"
                    keeper.write_bytes(b"keep")
                    if kind == "symlink":
                        target.symlink_to(keeper)
                    elif kind == "hardlink":
                        os.link(keeper, target)
                    else:
                        target.write_bytes(b"keep")
                    with patch.object(RUNNER.feed, "fetch_feed") as fetch:
                        code, _, stderr = self.invoke("--fetch")
                    self.assertEqual(code, 1, stderr)
                    fetch.assert_not_called()
                    self.assertEqual(target.read_bytes(), b"keep")
                    other = self.output if target == sidecar(self.output) else sidecar(self.output)
                    self.assertFalse(other.exists())
                    target.unlink()

    def test_mocked_one_request_fetch_outcomes_preserve_source_and_gap_evidence(self):
        for raw, status, reason in ((FIXTURE, "available", "completed"), (EMPTY, "empty", "completed"),
                                    (b"PRIVATE-ERROR", "invalid", "invalid_feed"), (None, "unavailable", "source_unavailable")):
            with self.subTest(status=status):
                self.output.unlink(missing_ok=True)
                sidecar(self.output).unlink(missing_ok=True)
                feed = RUNNER.feed.parse_feed(raw) if raw is not None else {
                    "source_url": RUNNER.feed.SOURCE_URL, "status": "unavailable", "items": [],
                    "sha256": None, "error": "Feed request timed out; no retry sent."}
                feed.update(requests_attempted=1, retrieved_at="2026-10-01T22:40:00+00:00" if raw is not None else None)
                with patch.object(RUNNER.feed, "fetch_feed", return_value=feed) as fetch:
                    code, _, stderr = self.invoke("--fetch", "--limit", 1)
                self.assertEqual(code, 0 if reason == "completed" else 1, stderr)
                self.assertEqual(fetch.call_count, 1)
                record = self.read_record()
                self.assertEqual(record["mode"], "public_fetch")
                self.assertEqual(record["usage"]["basis"], "known_public_fetch")
                self.assertEqual(record["usage"]["requests_attempted"], 1)
                self.assertEqual(record["limits"]["requests"], 1)
                self.assertEqual(record["limits"]["fetch_timeout_seconds"], 10)
                self.assertEqual(record["source_time"]["retrieved_at"], feed["retrieved_at"])
                self.assertEqual(record["source_time"]["published_at"],
                                 ["2020-01-01T12:00:00+00:00"] if status == "available" else [])
                self.assertEqual(record["outcome"]["reason"], reason)
                self.assertEqual(record["inputs"][0]["hash_state"], "complete" if raw is not None else "read_failed")
                self.assertEqual(record["inputs"][0]["sha256"], hashlib.sha256(raw).hexdigest() if raw is not None else None)
                self.assertEqual(record["outputs"][0]["sha256"], hashlib.sha256(self.output.read_bytes()).hexdigest())

    def test_report_collision_after_preflight_keeps_existing_bytes_and_stopped_record(self):
        original = RUNNER._save
        def collide(path, content):
            path.write_bytes(b"other writer")
            original(path, content)
        with patch.object(RUNNER, "_save", side_effect=collide):
            code, _, stderr = self.invoke()
        self.assertEqual(code, 1, stderr)
        self.assertEqual(self.output.read_bytes(), b"other writer")
        record = self.read_record()
        self.assertEqual(record["outcome"]["reason"], "output_exists")
        self.assertEqual(record["outputs"][0]["state"], "not_written")
        self.assertIsNone(record["outputs"][0]["sha256"])

    def test_partial_report_failure_and_record_finalization_failure_stay_nonzero(self):
        def fail(path, content):
            self.assertIs(type(content), bytes)
            path.write_bytes(content[:12])
            raise OSError("PRIVATE-ERROR")
        with patch.object(RUNNER, "_save", side_effect=fail):
            code, stdout, stderr = self.invoke()
        self.assertEqual(code, 1, stderr)
        self.assertEqual(stdout, "")
        record = self.read_record()
        self.assertEqual(record["outcome"]["reason"], "output_write_failed")
        self.assertIsNone(record["outputs"][0]["sha256"])
        self.assertIn("partial report", stderr)
        self.assertNotIn("PRIVATE-ERROR", stderr + sidecar(self.output).read_text())
        self.output.unlink()
        sidecar(self.output).unlink()
        with patch.object(record_files.os, "fsync", side_effect=OSError("PRIVATE-ERROR")):
            code, stdout, stderr = self.invoke()
        self.assertEqual(code, 1, stderr)
        self.assertEqual(stdout, "")
        self.assertTrue(self.output.exists())
        self.assertIn("finalization failed", stderr)
        self.assertNotIn("PRIVATE-ERROR", stderr + sidecar(self.output).read_text())

    def test_actual_clean_dirty_and_unknown_lab_before_output_creation(self):
        clone = self.folder / "lab"
        for name in ("scripts/git_provenance.py", "scripts/run_records.py", "scripts/record_files.py",
                     "scripts/fed_press_feed.py", "experiments/market-brief/run.py", "experiments/market-brief/fixture.xml"):
            target = clone / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
        def git(*args):
            return subprocess.run(["git", "-C", str(clone), *args], check=True, capture_output=True, text=True,
                env={"PATH": os.defpath, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}).stdout.strip()
        git("init", "-q")
        git("add", ".")
        git("-c", "user.name=Synthetic test", "-c", "user.email=test@example.invalid", "-c", "core.hooksPath=/dev/null",
            "commit", "-qm", "Synthetic Market runner")
        revision = git("rev-parse", "HEAD")
        for state in ("clean", "dirty", "unknown"):
            if state == "unknown":
                copied = self.folder / "copy"
                shutil.copytree(clone, copied, ignore=shutil.ignore_patterns(".git"))
                clone = copied
            # First output is unignored: the second invocation must observe dirty.
            output = clone / f"{state}.md"
            result = self.command(script=clone / "experiments/market-brief/run.py", output=output)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(self.read_record(output)["lab"], {"revision": None if state == "unknown" else revision, "state": state})


if __name__ == "__main__":
    unittest.main()
