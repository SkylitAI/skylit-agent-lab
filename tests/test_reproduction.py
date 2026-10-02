"""Pin checks stage synthetic Git sources but never contact Docker."""

import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, sentinel

from scripts import run_isolated as wrapper


class ExpectedLabTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.source = Path(self.temporary.name).resolve() / "source"
        self.source.mkdir()
        wrapper.git("init", "--quiet", self.source)
        (self.source / "fixture.txt").write_text("Synthetic committed input.\n", encoding="utf-8")
        wrapper.git("-C", self.source, "add", "fixture.txt")
        wrapper.git("-C", self.source, "-c", "user.name=Synthetic Test", "-c", "user.email=test@example.invalid",
                    "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "Synthetic source")
        self.revision = wrapper.git("-C", self.source, "rev-parse", "HEAD")

    def inspect_staged_run(self, stage, client, without_kit, evaluate):
        self.assertIs(client, sentinel.client)
        self.assertTrue(without_kit)
        self.assertTrue(evaluate)
        self.assertEqual(wrapper.git("-C", stage / "lab", "rev-parse", "HEAD"), self.revision)
        self.assertEqual(wrapper.git("-C", stage / "lab", "status", "--porcelain=v1"), "")
        return 0

    def invoke(self, *arguments):
        output = io.StringIO()
        with patch.object(sys, "argv", ["run_isolated.py", "--without-kit", *arguments]), \
                patch.object(wrapper, "ROOT", self.source), \
                patch.object(wrapper, "docker_client", return_value=sentinel.client) as discovery, \
                patch.object(wrapper, "run_probe", side_effect=self.inspect_staged_run) as run, \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            try:
                code = wrapper.main()
            except SystemExit as error:
                code = error.code
        return code, output.getvalue(), discovery, run

    def assert_no_docker(self, discovery, run):
        discovery.assert_not_called()
        run.assert_not_called()

    def test_matching_revision_reaches_evaluation_with_actual_staged_commit(self):
        code, output, discovery, run = self.invoke("--evaluate", "--expected-lab", self.revision)
        self.assertEqual(code, 0, output)
        discovery.assert_called_once()
        run.assert_called_once()
        self.assertIn("Committed Lab: " + self.revision, output)

    def test_mismatch_reports_only_validated_expected_and_observed_revisions(self):
        expected = "0" * 40
        code, output, discovery, run = self.invoke("--evaluate", "--expected-lab", expected)
        self.assertEqual(code, 1)
        self.assert_no_docker(discovery, run)
        self.assertIn("expected " + expected, output)
        self.assertIn("observed " + self.revision, output)
        self.assertIn("clean checkout", output)
        self.assertNotIn(str(self.source), output)

    def test_invalid_revision_is_not_echoed_and_stops_before_staging_or_docker(self):
        invalid = ("main", "A" * 40, "a" * 39, "a" * 41, "g" * 40,
                   "private-marker\n\x1b[31m", "a" * 40 + "\n", "private-marker\x00")
        for value in invalid:
            with self.subTest(value=repr(value)), \
                    patch.object(wrapper, "stage_checkout", side_effect=AssertionError("No staging")):
                code, output, discovery, run = self.invoke("--evaluate", "--expected-lab=" + value)
                self.assertEqual(code, 2)
                self.assert_no_docker(discovery, run)
                self.assertNotIn(value, output)
                self.assertIn("40 lowercase hexadecimal", output)

    def test_expected_revision_requires_evaluate_before_staging_or_docker(self):
        with patch.object(wrapper, "stage_checkout", side_effect=AssertionError("No staging")):
            code, output, discovery, run = self.invoke("--expected-lab", self.revision)
        self.assertEqual(code, 2)
        self.assertIn("--expected-lab requires --evaluate", output)
        self.assert_no_docker(discovery, run)

    def test_matching_pin_does_not_bypass_dirty_source_rejection(self):
        for state in ("tracked", "staged", "untracked"):
            with self.subTest(state=state):
                target = self.source / ("new.txt" if state == "untracked" else "fixture.txt")
                target.write_text("Changed synthetic input.\n", encoding="utf-8")
                if state == "staged":
                    wrapper.git("-C", self.source, "add", "fixture.txt")
                code, output, discovery, run = self.invoke("--evaluate", "--expected-lab", self.revision)
                self.assertEqual(code, 1)
                self.assertIn("local changes", output)
                self.assert_no_docker(discovery, run)
                if state == "untracked":
                    target.unlink()
                else:
                    wrapper.git("-C", self.source, "reset", "--quiet", "HEAD", "--", "fixture.txt")
                    wrapper.git("-C", self.source, "checkout", "--", "fixture.txt")

    def test_omitting_optional_pin_preserves_the_existing_evaluation_route(self):
        code, output, discovery, run = self.invoke("--evaluate")
        self.assertEqual(code, 0, output)
        discovery.assert_called_once()
        run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
