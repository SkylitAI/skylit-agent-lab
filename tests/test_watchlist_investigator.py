"""The experiment renders through real Kit and saves without replacing reports."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from test_kit_consumer import GUARD, KIT, ROOT


PACKAGE = ROOT / "experiments" / "watchlist-investigator"


def run_experiment(*options, script=PACKAGE / "run.py", cwd=ROOT, utf8=True, ascii_stdout=False):
    guard = ("import sys; sys.stdout.reconfigure(encoding='ascii')\n" if ascii_stdout else "") + GUARD
    return subprocess.run(
        [sys.executable, "-X", "utf8" if utf8 else "utf8=0", "-I", "-B", "-c", guard, str(script), *map(str, options)],
        cwd=cwd, env={"PATH": os.defpath, "LC_ALL": "C"}, stdin=subprocess.DEVNULL,
        capture_output=True, text=True, encoding="utf-8", check=False,
    )


class PackageSetupTests(unittest.TestCase):
    def test_invalid_time_options_preserve_output_and_do_not_create_parents(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "new" / "report.md"
            existing = Path(directory) / "existing.md"
            existing.write_text("Keep this report.\n")
            for option, value in (("--reference-time", "2026-10-01T14:01:00"),
                                  ("--max-age-seconds", "nan"), ("--max-age-seconds", "86401")):
                for destination in (output, existing):
                    result = run_experiment("--kit", directory, option, value, "--output", destination)
                    self.assertEqual(result.returncode, 1)
                    self.assertIn(option, result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertEqual(result.stdout, "")
                    self.assertFalse(output.parent.exists())
                    self.assertEqual(existing.read_text(), "Keep this report.\n")

    def test_kit_path_is_explicit_and_bad_checkout_error_is_actionable(self):
        result = run_experiment()
        self.assertEqual(result.returncode, 2)
        self.assertIn("--kit", result.stderr)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.md"
            result = run_experiment("--kit", Path(directory) / "missing", "--output", output)
            self.assertEqual(result.returncode, 1)
            self.assertIn("--kit", result.stderr)
            self.assertIn("Git", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertFalse(output.exists())

    def test_manifest_pin_matches_the_consumed_kit_revision(self):
        from scripts.probe_kit_watchlist import KIT_REVISION
        manifest = json.loads((PACKAGE / "experiment.json").read_text())
        self.assertEqual(manifest["kit"]["revision"], KIT_REVISION)
        self.assertEqual(manifest["status"], "experimental")
        self.assertEqual(manifest["tested_hosts"], [])
        self.assertEqual(manifest["command"][:5], ["python3", "-X", "utf8", "-I", "-B"])


@unittest.skipUnless(KIT.is_dir(), "Kit integration unverified: set SKYLIT_AGENT_KIT to the pinned checkout")
class WatchlistInvestigatorTests(unittest.TestCase):
    def test_ascii_locale_refuses_before_creating_output_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "new-reports" / "watchlist.md"
            result = run_experiment("--kit", KIT.resolve(), "--output", output, utf8=False)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(output.parent.exists(), "ASCII refusal must not create a file or parent directory")
            self.assertIn("UTF-8", result.stderr)
            self.assertIn("python3 -X utf8 -I -B", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(result.stdout, "")

    def test_utf8_mode_under_ascii_locale_preserves_exact_bytes_and_existing_report(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "new-reports" / "watchlist.md"
            result = run_experiment("--kit", KIT.resolve(), "--output", output)
            self.assertEqual(result.returncode, 0, result.stderr)
            content = output.read_bytes()
            self.assertIn("Skylit watchlist · GEX / VEX / recent flow".encode("utf-8"), content)
            self.assertIn("Fictional data only", content.decode("utf-8"))
            if os.name != "nt":
                self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            again = run_experiment("--kit", KIT.resolve(), "--output", output)
            self.assertEqual(again.returncode, 1)
            self.assertIn("already exists", again.stderr)
            self.assertEqual(output.read_bytes(), content)

    def test_non_ascii_path_with_ascii_stdout_refuses_before_creating_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "new-reports" / "r\u00e9sum\u00e9.md"
            result = run_experiment("--kit", KIT.resolve(), "--output", output, ascii_stdout=True)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(output.parent.exists(), "An unprintable saved path must be rejected before writing")
            self.assertIn("stdout", result.stderr)
            self.assertIn("UTF-8", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_default_report_is_private_and_independent_of_working_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            copied = root / "lab" / "experiments" / "watchlist-investigator"
            copied.mkdir(parents=True)
            scripts = root / "lab" / "scripts"
            scripts.mkdir()
            for name in ("run.py", "fixture.json"):
                shutil.copy2(PACKAGE / name, copied / name)
            for name in ("probe_kit_watchlist.py", "watchlist_time.py", "git_provenance.py"):
                shutil.copy2(ROOT / "scripts" / name, scripts)
            result = run_experiment("--kit", KIT.resolve(), script=copied / "run.py", cwd=root)
            self.assertEqual(result.returncode, 0, result.stderr)
            output = copied / "reports" / "watchlist.md"
            report = output.read_text()
            self.assertTrue(report.startswith("# Watchlist Investigator\n"))
            self.assertIn("Fictional data only", report)
            self.assertIn("0 requests attempted; 0 documented credits", report)
            self.assertIn(str(output), result.stdout)
            self.assertEqual(result.stderr, "")
            if os.name != "nt":
                self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            again = run_experiment("--kit", KIT.resolve(), script=copied / "run.py", cwd=root)
            self.assertEqual(again.returncode, 1)
            self.assertIn("already exists", again.stderr)
            self.assertEqual(output.read_text(), report)

    def test_changed_symbols_change_report_and_preserve_missing_components(self):
        with tempfile.TemporaryDirectory() as directory:
            first, second = Path(directory) / "spy.md", Path(directory) / "gaps.md"
            for output, symbols in ((first, "SPY"), (second, "qqq,SPXW,qqq")):
                result = run_experiment("--kit", KIT.resolve(), "--symbols", symbols, "--output", output)
                self.assertEqual(result.returncode, 0, result.stderr)
            spy, gaps = first.read_text(), second.read_text()
            self.assertIn("source king: 110 / -180", spy)
            self.assertNotIn("## QQQ\n", spy)
            self.assertNotIn("## SPY\n", gaps)
            self.assertEqual(gaps.count("## QQQ\n"), 1)
            self.assertIn("## SPXW\n", gaps)
            self.assertNotIn("## SPX\n", gaps)
            self.assertIn("missing from heatmap response", gaps)
            self.assertIn("missing from synthetic fixture", gaps)
            self.assertNotIn("0 trades; $0", gaps)

    def test_changed_fixture_value_reaches_the_saved_report(self):
        fixture = json.loads((PACKAGE / "fixture.json").read_text())
        fixture["gamma"]["data"]["symbols"][0]["strikes"][0]["value"] = -199
        with tempfile.TemporaryDirectory() as directory:
            path, output = Path(directory) / "fixture.json", Path(directory) / "report.md"
            path.write_text(json.dumps(fixture))
            result = run_experiment("--kit", KIT.resolve(), "--fixture", path, "--output", output)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("source king: 110 / -199", output.read_text())
            self.assertNotIn("-180", output.read_text())

    def test_source_time_evidence_preserves_kit_gaps_and_compares_explicit_reference(self):
        fixture = json.loads((PACKAGE / "fixture.json").read_text())
        fixture["gamma"]["data"]["symbols"][0]["asOf"] = "invalid"
        fixture["vanna"]["data"]["symbols"][0]["asOf"] = "2026-10-01T14:01:00+02:00"
        fixture["flow"]["SPY"]["meta"]["timestamp"] = "2026-10-01T14:02:00Z"
        fixture["flow"]["SPY"]["data"]["trades"][0]["timestamp"] = "2026-10-01T13:55:30"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json"
            path.write_text(json.dumps(fixture))
            for minute, age in (("01", "-60 | future"), ("03", "60 | within threshold")):
                output = Path(directory) / f"report-{minute}.md"
                result = run_experiment("--kit", KIT.resolve(), "--fixture", path, "--output", output,
                                        "--symbols", "SPY,QQQ,SPXW", "--max-age-seconds", "60",
                                        "--reference-time", f"2026-10-01T14:{minute}:00Z")
                self.assertEqual(result.returncode, 0, result.stderr)
                report = output.read_text()
                self.assertIn("| SPY | flow.generated_at | 2026-10-01T14:02:00+00:00 | " + age + " |", report)
                self.assertIn("| SPY | gamma.as_of | unavailable | unavailable | timestamp missing or invalid; invalid or missing heatmap fields |", report)
                self.assertIn("timestamp missing or invalid; partial: 1 invalid trades", report)
                self.assertIn("| QQQ | vanna.as_of | unavailable | unavailable | timestamp missing or invalid; missing from heatmap response |", report)
                self.assertIn("| SPXW | flow.latest_trade | unavailable | unavailable | timestamp missing or invalid; missing from synthetic fixture |", report)
                self.assertIn("observed timestamp span 7260 seconds across 2 valid fields", report)
                self.assertIn("| stale |", report)
                self.assertNotIn("source king: 110 / -180", report)
                self.assertIn("largest returned magnitude: 115 / 60", report)

    def test_invalid_input_never_creates_or_truncates_report(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture, output = Path(directory) / "bad.json", Path(directory) / "report.md"
            for contents in (b"not JSON", b"[]", b" " * 65537, b"\xff"):
                for previous in (False, True):
                    with self.subTest(contents=contents[:20], previous=previous):
                        output.unlink(missing_ok=True)
                        if previous:
                            output.write_text("Keep this report.\n")
                        fixture.write_bytes(contents)
                        result = run_experiment("--kit", KIT.resolve(), "--fixture", fixture, "--output", output)
                        self.assertEqual(result.returncode, 1)
                        self.assertIn("error:", result.stderr)
                        self.assertNotIn("Traceback", result.stderr)
                        self.assertEqual(result.stdout, "")
                        if previous:
                            self.assertEqual(output.read_text(), "Keep this report.\n")
                        else:
                            self.assertFalse(output.exists())

    def test_existing_symlink_output_and_invalid_symbols_are_not_written(self):
        with tempfile.TemporaryDirectory() as directory:
            target, output = Path(directory) / "original.md", Path(directory) / "link.md"
            target.write_text("Original report.\n")
            output.symlink_to(target)
            result = run_experiment("--kit", KIT.resolve(), "--output", output)
            self.assertEqual(result.returncode, 1)
            self.assertIn("already exists", result.stderr)
            self.assertEqual(target.read_text(), "Original report.\n")
            result = run_experiment("--kit", KIT.resolve(), "--output", target, "--symbols", "SPY,!")
            self.assertEqual(result.returncode, 1)
            self.assertIn("ticker symbols", result.stderr)
            self.assertEqual(target.read_text(), "Original report.\n")


if __name__ == "__main__":
    unittest.main()
