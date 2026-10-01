"""The copyable example must produce real, clearly fictional output."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "experiment"


class TemplateTests(unittest.TestCase):
    def run_example(self, fixture_bytes=None, previous_report=None):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        folder = Path(directory.name)
        output = folder / "report.md"
        if previous_report is not None:
            output.write_text(previous_report)
        command = [sys.executable, str(TEMPLATE / "run.py"), "--output", str(output)]
        if fixture_bytes is not None:
            fixture = folder / "fixture.json"
            fixture.write_bytes(fixture_bytes)
            command += ["--fixture", str(fixture)]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        return result, output

    def test_example_matches_expected_report(self):
        result, output = self.run_example()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output.read_text(), (TEMPLATE / "expected.md").read_text())
        self.assertIn(str(output), result.stdout)

    def test_changed_note_changes_report(self):
        fixture = {"observations": [{"symbol": "DEMO", "note": "A different fictional note."}]}
        result, output = self.run_example(json.dumps(fixture).encode())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("A different fictional note.", output.read_text())
        self.assertNotIn("SAMPLE", output.read_text())

    def test_missing_note_stays_visible(self):
        for note in (None, "", " \n\t "):
            with self.subTest(note=note):
                fixture = {"observations": [{"symbol": "DEMO", "note": note}]}
                result, output = self.run_example(json.dumps(fixture).encode())
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("DEMO: Not provided", output.read_text())

    def test_invalid_inputs_fail_without_creating_output(self):
        for contents in (b"not json", b"\xff", b"[]", b'{"observations": []}',
                         b'{"observations": [{"symbol": "DEMO", "note": 3}]}',
                         b"[" * 2000 + b"]" * 2000,
                         b'{"observations": [{"symbol": "DEMO", "note": "\\ud800"}]}',
                         b" " * 65537):
            with self.subTest(contents=contents[:60]):
                result, output = self.run_example(contents)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(output.exists())
                self.assertIn("error:", result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_invalid_encoding_preserves_existing_report(self):
        fixture = {"observations": [{"symbol": "DEMO", "note": "\ud800"}]}
        result, output = self.run_example(json.dumps(fixture).encode(), "Previous report.\n")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(output.read_text(), "Previous report.\n")

    def test_output_cannot_replace_fixture_through_same_path_or_alias(self):
        for alias in ("same", "symlink", "hardlink"):
            with self.subTest(alias=alias), tempfile.TemporaryDirectory() as directory:
                folder = Path(directory)
                fixture = folder / "fixture.json"
                original = (TEMPLATE / "fixture.json").read_bytes()
                fixture.write_bytes(original)
                output = folder / "report.md"
                if alias == "same":
                    output = fixture
                elif alias == "symlink":
                    output.symlink_to(fixture)
                else:
                    os.link(fixture, output)
                result = subprocess.run(
                    [sys.executable, str(TEMPLATE / "run.py"),
                     "--fixture", str(fixture), "--output", str(output)],
                    capture_output=True, text=True, check=False,
                )
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertIn("--output must differ from --fixture", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual(fixture.read_bytes(), original)

    def test_observation_text_is_not_active_markdown(self):
        fixture = {"observations": [{"symbol": "DEMO", "note": "![image](https://example.com) <b>"}]}
        result, output = self.run_example(json.dumps(fixture).encode())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("![image]", output.read_text())
        self.assertNotIn("<b>", output.read_text())


if __name__ == "__main__":
    unittest.main()
