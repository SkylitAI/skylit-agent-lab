"""Market Brief behavior uses fictional bytes and blocked or mocked network."""

import contextlib
import hashlib
import html
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "experiments/market-brief"
SCRIPT = PACKAGE / "run.py"
SPEC = importlib.util.spec_from_file_location("market_brief_runner", SCRIPT)
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)
FIXTURE = (PACKAGE / "fixture.xml").read_bytes()
GUARD = """
import runpy, sys
def audit(event, args):
    if event.startswith('socket.'):
        raise AssertionError('Offline run attempted network')
sys.addaudithook(audit)
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name='__main__')
"""


class MarketBriefTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name).resolve()
        self.output = self.folder / "brief.md"

    def command(self, *args, output=None, env=None, utf8=True):
        interpreter = [sys.executable] + (["-X", f"utf8={int(utf8)}"] if utf8 is not None else [])
        return subprocess.run(
            [*interpreter, "-I", "-B", "-c", GUARD, str(SCRIPT),
             "--output", str(output or self.output), *map(str, args)],
            cwd=self.folder, env=env, capture_output=True, text=True, timeout=5, check=False,
        )

    def input_file(self, raw=FIXTURE):
        path = self.folder / "input.xml"
        path.write_bytes(raw)
        return path

    def assert_no_report(self, result):
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertFalse(self.output.exists())
        self.assertNotIn("Traceback", result.stderr)

    def test_default_offline_matches_readme_golden_from_any_directory(self):
        result = self.command()
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = (PACKAGE / "README.md").read_text(encoding="utf-8").split(
            "<!-- expected-start -->\n```markdown\n", 1)[1].split("```\n<!-- expected-end -->", 1)[0]
        self.assertEqual(self.output.read_text(encoding="utf-8"), expected)
        self.assertIn(str(self.output), result.stdout)
        self.assertTrue(Path(str(self.output) + ".run.json").is_file())
        if os.name == "posix":
            self.assertEqual(self.output.stat().st_mode & 0o777, 0o600)

    def test_fixture_and_manifest_declare_actual_offline_input(self):
        self.assertEqual(FIXTURE, (ROOT / "examples/fed-press-synthetic.xml").read_bytes())
        manifest = json.loads((PACKAGE / "experiment.json").read_text())
        self.assertEqual(manifest["inputs"], ["fixture.xml"])
        self.assertEqual(manifest["outputs"], ["reports/brief.md", "reports/brief.md.run.json"])
        self.assertIsNone(manifest["kit"])
        self.assertEqual(manifest["tested_hosts"], [])

    def test_changed_default_requires_explicit_supplied_input_provenance(self):
        changed = self.folder / "fixture.xml"
        changed.write_bytes(FIXTURE.replace(b"paper kites", b"changed words"))
        with patch.object(RUNNER, "PACKAGE", self.folder), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as stderr:
            code = RUNNER.main(["--output", str(self.output)])
        self.assertEqual(code, 1)
        self.assertFalse(self.output.exists())
        self.assertIn("--input", stderr.getvalue())
        Path(str(self.output) + ".run.json").unlink()
        result = self.command("--input", changed)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Caller-supplied saved feed", self.output.read_text())

    def test_broken_stdout_after_save_has_controlled_exit_and_saved_notice(self):
        read_fd, write_fd = os.pipe()
        os.close(read_fd)
        try:
            result = subprocess.run(
                [sys.executable, "-X", "utf8", "-I", "-B", "-c", GUARD,
                 str(SCRIPT), "--output", str(self.output)],
                stdout=write_fd, stderr=subprocess.PIPE, text=True, timeout=5, check=False,
            )
        finally:
            os.close(write_fd)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertTrue(self.output.is_file())
        self.assertTrue(Path(str(self.output) + ".run.json").is_file())
        self.assertIn("was saved", result.stderr)
        self.assertIn(str(self.output), result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_write_failure_discloses_a_possible_partial_report(self):
        def fail_after_partial_write(path, report):
            path.write_bytes(b"partial")
            raise OSError("private-marker")
        with patch.object(RUNNER, "_save", side_effect=fail_after_partial_write), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as stderr:
            code = RUNNER.main(["--output", str(self.output)])
        self.assertEqual(code, 1)
        self.assertEqual(self.output.read_bytes(), b"partial")
        self.assertIn("partial report may", stderr.getvalue())
        self.assertNotIn("private-marker", stderr.getvalue())

    def test_saved_input_and_limit_preserve_caller_supplied_provenance(self):
        path = self.input_file(FIXTURE.replace(b"paper kites", b"changed fictional wording"))
        result = self.command("--input", path, "--limit", "1")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = self.output.read_text()
        self.assertIn("Caller-supplied saved feed", report)
        self.assertIn("Actual retrieval (UTC): unknown (offline input)", report)
        self.assertIn("Showing 1 of 2", report)
        self.assertIn("changed fictional wording", report)
        self.assertIn("2020-01-01T12:00:00+00:00", report)
        self.assertNotIn("imaginary meeting room", report)
        self.assertIn("Unverified input URL", report)
        self.assertNotIn("](https://", report)
        self.assertIn(hashlib.sha256(path.read_bytes()).hexdigest(), report)

    def test_empty_feed_is_a_successful_explicit_gap(self):
        raw = b"<rss version='2.0'><channel><title>Fictional</title><link>https://www.federalreserve.gov/feeds/feeds.htm</link><description>Fictional</description></channel></rss>"
        result = self.command("--input", self.input_file(raw))
        self.assertEqual(result.returncode, 0, result.stderr)
        report = self.output.read_text()
        self.assertIn("Source status: empty", report)
        self.assertIn("No releases were present in this feed", report)
        self.assertNotIn("### Published", report)

    def test_malformed_and_invalid_utf8_inputs_save_failure_briefs(self):
        for raw in (b"not xml: private-marker", b"\xff", FIXTURE.replace(b"<pubDate>", b"<wrong>")):
            with self.subTest(raw=raw[:20]):
                self.output.unlink(missing_ok=True)
                Path(str(self.output) + ".run.json").unlink(missing_ok=True)
                result = self.command("--input", self.input_file(raw))
                self.assertEqual(result.returncode, 1, result.stderr)
                report = self.output.read_text()
                self.assertIn("Source status: invalid", report)
                self.assertIn("No usable releases", report)
                self.assertNotIn("private-marker", report + result.stderr)
                self.assertNotIn("### Published", report)

    def test_missing_directory_and_oversized_input_save_no_report(self):
        for source in (self.folder / "missing.xml", self.folder, self.input_file(b"x" * (512 * 1024 + 1))):
            with self.subTest(source=source.name):
                Path(str(self.output) + ".run.json").unlink(missing_ok=True)
                result = self.command("--input", source)
                self.assert_no_report(result)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO input check requires POSIX")
    def test_fifo_is_rejected_without_blocking(self):
        path = self.folder / "input.pipe"
        os.mkfifo(path)
        self.assert_no_report(self.command("--input", path))

    def test_input_symlink_is_rejected(self):
        link = self.folder / "input-link.xml"
        link.symlink_to(self.input_file())
        self.assert_no_report(self.command("--input", link))

    def test_invalid_cli_creates_no_directory_or_network_request(self):
        output = self.folder / "not-created" / "brief.md"
        for args in (("--limit", "0"), ("--fetch", "--limit", "0"), ("--limit", "21"), ("--limit", "no"),
                     ("--limit", "1.5"), ("--fetch", "--input", "input.xml"), ("--unknown",)):
            with self.subTest(args=args):
                result = self.command(*args, output=output)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertFalse(output.parent.exists())
                self.assertNotIn("Traceback", result.stderr)

    def test_existing_files_and_input_aliases_are_not_overwritten(self):
        source = self.input_file()
        for alias in ("existing", "same", "hardlink", "symlink", "broken-symlink"):
            with self.subTest(alias=alias):
                self.output.unlink(missing_ok=True)
                Path(str(self.output) + ".run.json").unlink(missing_ok=True)
                output = self.output
                if alias == "existing":
                    output.write_bytes(b"keep me")
                elif alias == "same":
                    output = source
                elif alias == "hardlink":
                    os.link(source, output)
                else:
                    output.symlink_to(source if alias == "symlink" else self.folder / "absent")
                result = self.command("--input", source, output=output)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(source.read_bytes(), FIXTURE)
                if alias == "existing":
                    self.assertEqual(output.read_bytes(), b"keep me")
                self.assertNotIn("Traceback", result.stderr)

    def test_output_symlink_parent_is_refused(self):
        target = self.folder / "target"
        target.mkdir()
        link = self.folder / "alias"
        link.symlink_to(target, target_is_directory=True)
        result = self.command(output=link / "brief.md")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(list(target.iterdir()), [])

    def test_titles_cannot_inject_markdown_images_or_links_and_utf8_is_explicit(self):
        title = "Fictional café ![image](https://evil.example)\n# injected & note"
        raw = FIXTURE.replace(b"Fictional notice: paper kites &amp; sample calendars", html.escape(title).encode())
        result = self.command("--input", self.input_file(raw), utf8=False,
                              env={"PATH": os.defpath, "LC_ALL": "C"})
        self.assertEqual(result.returncode, 0, result.stderr)
        report = self.output.read_bytes().decode("utf-8")
        self.assertNotIn("![image]", report)
        self.assertNotIn("\n# injected", report)
        self.assertNotIn("https://evil.example", report)
        self.assertIn(title.replace("\n", r"\u000a"), html.unescape(report))

    def test_supplied_title_displays_controls_as_visible_code_points(self):
        title = "Fictional café \u202eoverride\tcolumn\nnext line"
        raw = FIXTURE.replace(b"Fictional notice: paper kites &amp; sample calendars", title.encode())
        result = self.command("--input", self.input_file(raw))
        self.assertEqual(result.returncode, 0, result.stderr)
        report = self.output.read_text(encoding="utf-8")
        self.assertIn(r"Fictional café \u202eoverride\u0009column\u000anext line", html.unescape(report))
        self.assertNotIn("\u202e", html.unescape(report))
        self.assertNotIn("\t", html.unescape(report))
        self.assertNotIn("override\tcolumn\nnext", html.unescape(report))

    def call_fetch(self, record, *args):
        with patch.object(RUNNER.feed, "fetch_feed", return_value=record) as fetch, \
             contextlib.redirect_stdout(io.StringIO()) as stdout, \
             contextlib.redirect_stderr(io.StringIO()) as stderr:
            code = RUNNER.main(["--fetch", "--output", str(self.output), *args])
        return code, fetch.call_count, stdout.getvalue(), stderr.getvalue()

    def test_mocked_fetch_keeps_observed_retrieval_separate_from_publication(self):
        record = RUNNER.feed.parse_feed(FIXTURE)
        record.update(retrieved_at="2026-10-01T22:40:00+00:00", requests_attempted=1)
        code, count, _, _ = self.call_fetch(record, "--limit", "1")
        self.assertEqual((code, count), (0, 1))
        report = self.output.read_text()
        self.assertIn("Actual retrieval (UTC): 2026-10-01T22:40:00+00:00", report)
        self.assertIn("Published (UTC): 2020-01-01T12:00:00+00:00", report)
        self.assertIn("Requests attempted: 1", report)
        self.assertIn("[Board release](https://www.federalreserve.gov/", report)

    def test_mocked_unavailable_fetch_saves_a_gap_and_returns_failure(self):
        record = {"source_url": RUNNER.feed.SOURCE_URL, "status": "unavailable", "items": [],
                  "retrieved_at": None, "sha256": None, "requests_attempted": 1,
                  "error": "Feed request timed out; no retry sent."}
        code, count, _, _ = self.call_fetch(record)
        self.assertEqual((code, count), (1, 1))
        report = self.output.read_text()
        self.assertIn("Source status: unavailable", report)
        self.assertIn("Actual retrieval (UTC): unavailable (fetch incomplete)", report)
        self.assertIn("No usable releases", report)
        self.assertNotIn("### Published", report)

    def test_mocked_empty_and_invalid_fetches_keep_actual_retrieval(self):
        empty = b"<rss version='2.0'><channel><title>Fictional</title><link>https://www.federalreserve.gov/feeds/feeds.htm</link><description>Fictional</description></channel></rss>"
        for raw, status, expected_code in ((empty, "empty", 0), (b"not xml", "invalid", 1)):
            with self.subTest(status=status):
                self.output.unlink(missing_ok=True)
                Path(str(self.output) + ".run.json").unlink(missing_ok=True)
                record = RUNNER.feed.parse_feed(raw)
                record.update(retrieved_at="2026-10-01T22:40:00+00:00", requests_attempted=1)
                code, count, _, _ = self.call_fetch(record)
                self.assertEqual((code, count), (expected_code, 1))
                report = self.output.read_text()
                self.assertIn(f"Source status: {status}", report)
                self.assertIn("Actual retrieval (UTC): 2026-10-01T22:40:00+00:00", report)
                self.assertNotIn("### Published", report)

    def test_output_collision_stops_before_fetch(self):
        self.output.write_text("keep me")
        code, count, _, _ = self.call_fetch({})
        self.assertEqual((code, count), (1, 0))
        self.assertEqual(self.output.read_text(), "keep me")


if __name__ == "__main__":
    unittest.main()
