"""Run the real journal package in isolated subprocesses without network or prompts."""

import json
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "experiments" / "journal-reviewer"
FIXTURE = ROOT / "examples" / "paper-journal-synthetic.csv"
GUARD = """
import builtins, getpass, runpy, socket, sys
def forbidden(*args, **kwargs):
    raise AssertionError('Network and credential prompts are forbidden')
socket.socket = socket.create_connection = forbidden
builtins.input = getpass.getpass = forbidden
"""


def run_package(*options, script=PACKAGE / "run.py", cwd=ROOT, injection="", utf8=True):
    code = GUARD + injection + "\nsys.argv = sys.argv[1:]\nrunpy.run_path(sys.argv[0], run_name='__main__')\n"
    return subprocess.run(
        [sys.executable, "-X", "utf8" if utf8 else "utf8=0", "-I", "-B", "-c", code, str(script), *map(str, options)],
        cwd=cwd, env={"PATH": os.defpath, "LC_ALL": "C"}, stdin=subprocess.DEVNULL,
        capture_output=True, text=True, encoding="utf-8", check=False, timeout=10,
    )


class JournalRunnerTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.output = self.root / "new" / "review.md"

    def copy_package(self):
        package = self.root / "lab" / "experiments" / "journal-reviewer"
        package.mkdir(parents=True)
        scripts = self.root / "lab" / "scripts"
        scripts.mkdir()
        for name in ("run.py", "fixture.csv"):
            shutil.copy2(PACKAGE / name, package / name)
        for name in ("paper_journal.py", "journal_report.py", "git_provenance.py", "record_files.py", "run_records.py"):
            shutil.copy2(ROOT / "scripts" / name, scripts / name)
        return package

    def assert_failure(self, result, text):
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn(text, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertNotIn("private-sentinel", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_default_is_private_exact_golden_and_independent_of_working_directory(self):
        package = self.copy_package()
        result = run_package(script=package / "run.py", cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = package / "reports" / "journal.md"
        self.assertEqual(output.read_bytes(), (ROOT / "examples" / "paper-journal-expected.md").read_bytes())
        self.assertIn(str(output), result.stdout)
        self.assertEqual(result.stderr, "")
        sidecar = Path(str(output) + ".run.json")
        self.assertEqual(set(output.parent.iterdir()), {output, sidecar})
        self.assertEqual(json.loads(sidecar.read_bytes())["lab"], {"revision": None, "state": "unknown"})
        if os.name != "nt":
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
        again = run_package(script=package / "run.py", cwd=self.root)
        self.assert_failure(again, "already exists")
        self.assertEqual(output.read_bytes(), (ROOT / "examples" / "paper-journal-expected.md").read_bytes())

    def test_manifest_declares_real_fixture_and_no_kit_or_host_certification(self):
        manifest = json.loads((PACKAGE / "experiment.json").read_text())
        self.assertIsNone(manifest["kit"])
        self.assertEqual(manifest["inputs"], ["fixture.csv"])
        self.assertEqual(manifest["outputs"], ["reports/journal.md", "reports/journal.md.run.json"])
        self.assertEqual(manifest["tested_hosts"], [])
        self.assertEqual(manifest["status"], "experimental")
        self.assertEqual(manifest["command"], ["python3", "-X", "utf8", "-I", "-B", "run.py"])
        self.assertEqual((PACKAGE / "fixture.csv").read_bytes(), FIXTURE.read_bytes())

    def test_explicit_input_is_supplied_even_when_it_is_the_bundled_fixture(self):
        result = run_package("--input", PACKAGE / "fixture.csv", "--output", self.output, cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        text = self.output.read_text()
        self.assertIn("Source: supplied paper-trade input.", text)
        self.assertNotIn("Source: caller-declared fictional fixture.", text)
        self.assertEqual(json.loads(Path(str(self.output) + ".run.json").read_bytes())["mode"], "offline_supplied")

    def test_changed_fees_affect_the_report_and_custom_paths_use_cwd(self):
        content = FIXTURE.read_bytes().replace(b",0.10,", b",1.10,")
        (self.root / "custom.csv").write_bytes(content)
        result = run_package("--input", "custom.csv", "--output", "review.md", cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        text = (self.root / "review.md").read_text()
        self.assertIn("Total net (USD): 3.76", text)
        self.assertIn("Entered fees (USD): 1.10", text)
        self.assertIn("Net (USD): 1.71", text)

    def test_empty_valid_journal_reports_unavailable_aggregate(self):
        source = self.root / "empty.csv"
        source.write_bytes(FIXTURE.read_bytes().splitlines(keepends=True)[0])
        result = run_package("--input", source, "--output", self.output)
        self.assertEqual(result.returncode, 0, result.stderr)
        text = self.output.read_text()
        self.assertIn("Trade count: 0", text)
        self.assertIn("Aggregate net P&L: unavailable", text)
        self.assertNotIn("0.00", text)

    def test_invalid_inputs_create_only_stopped_records_and_preserve_existing_output(self):
        source = self.root / "private-sentinel.csv"
        existing = self.root / "old.md"
        existing.write_bytes(b"Keep existing report.")
        for content in (b"private-sentinel\xff", b"", FIXTURE.read_bytes().replace(b",2.5,", b",NaN,")):
            source.write_bytes(content)
            for output in (self.output, existing):
                result = run_package("--input", source, "--output", output)
                self.assert_failure(result, "CSV contract")
                self.assertFalse(self.output.exists())
                self.assertEqual(existing.read_bytes(), b"Keep existing report.")
                sidecar = Path(str(output) + ".run.json")
                self.assertEqual(json.loads(sidecar.read_bytes())["outcome"]["reason"], "invalid_journal")
                sidecar.unlink()  # Each malformed-input case gets a fresh private record.

    def test_file_byte_cap_and_nonregular_or_missing_inputs_fail_safely(self):
        source = self.root / "private-sentinel.csv"
        source.write_bytes(b"x" * (1048576 + 1))
        self.assert_failure(run_package("--input", source, "--output", self.output), "1 MiB")
        source.write_bytes(b"x" * 1048576)
        self.assert_failure(run_package("--input", source, "--output", self.output), "CSV contract")
        for path in (self.root, self.root / "missing-private-sentinel.csv"):
            self.assert_failure(run_package("--input", path, "--output", self.output), "regular readable")
        self.assertFalse(self.output.exists())
        self.assertTrue(Path(str(self.output) + ".run.json").is_file())

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO support required")
    def test_fifo_input_refuses_without_blocking(self):
        fifo = self.root / "source.csv"
        os.mkfifo(fifo)
        self.assert_failure(run_package("--input", fifo, "--output", self.output), "regular readable")
        self.assertFalse(self.output.exists())
        self.assertTrue(Path(str(self.output) + ".run.json").is_file())

    def test_existing_file_symlink_hardlink_and_input_aliases_are_preserved(self):
        source = self.root / "source.csv"
        source.write_bytes(FIXTURE.read_bytes())
        before = source.read_bytes()
        aliases = [source, source.parent / "." / source.name]
        symlink, hardlink = self.root / "linked.md", self.root / "hard.md"
        symlink.symlink_to(source)
        os.link(source, hardlink)
        aliases += [symlink, hardlink]
        for output in aliases:
            self.assert_failure(run_package("--input", source, "--output", output), "already exists")
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(output.read_bytes(), before)
        dangling = self.root / "dangling.md"
        dangling.symlink_to(self.root / "absent.md")
        self.assert_failure(run_package("--output", dangling), "already exists")
        self.assertTrue(dangling.is_symlink())
        self.assertFalse((self.root / "absent.md").exists())

    def test_changed_default_fixture_cannot_keep_fictional_label(self):
        package = self.copy_package()
        source = package / "fixture.csv"
        source.write_bytes(source.read_bytes().replace(b",0.10,", b",1.10,"))
        result = run_package(script=package / "run.py", cwd=self.root)
        self.assert_failure(result, "Bundled fixture changed")
        self.assertIn("--input", result.stderr)
        sidecar = package / "reports" / "journal.md.run.json"
        record = json.loads(sidecar.read_bytes())
        self.assertEqual(record["outcome"]["reason"], "fixture_changed")
        self.assertEqual(record["inputs"][0]["hash_state"], "complete")
        self.assertEqual(record["inputs"][0]["sha256"], hashlib.sha256(source.read_bytes()).hexdigest())
        self.assertIsNone(record["source_time"])
        self.assertEqual(list(sidecar.parent.iterdir()), [sidecar])

    def test_non_ascii_notes_are_utf8_even_under_ascii_locale(self):
        source = self.root / "unicode.csv"
        source.write_bytes(FIXTURE.read_bytes().replace(b"Fictional long paper trade.", "Note: café 🌓".encode()))
        result = run_package("--input", source, "--output", self.output, utf8=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("café 🌓".encode(), self.output.read_bytes())

    def test_unprintable_stdout_path_is_rejected_before_writing(self):
        output = self.root / "new" / "café.md"
        result = run_package("--output", output, injection="sys.stdout.reconfigure(encoding='ascii')\n")
        self.assert_failure(result, "UTF-8 stdout")
        self.assertFalse(output.parent.exists())

    def test_output_control_characters_are_rejected_before_any_artifact(self):
        for character in ("\n", "\x1b", "\t", "\u202e"):
            with self.subTest(character=repr(character)):
                output = self.root / "new" / f"private-sentinel{character}.md"
                result = run_package("--output", output)
                self.assert_failure(result, "printable characters")
                self.assertFalse(output.parent.exists())
        output = self.root / "new" / "café.md"
        result = run_package("--output", output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(str(output), result.stdout)
        self.assertEqual(output.read_bytes(), (ROOT / "examples" / "paper-journal-expected.md").read_bytes())

    def test_input_with_embedded_nul_has_fixed_read_diagnostic(self):
        injection = "sys.argv[sys.argv.index('--input') + 1] = 'private-sentinel\\x00.csv'\n"
        result = run_package("--input", "placeholder.csv", "--output", self.output, injection=injection)
        self.assert_failure(result, "regular readable")
        self.assertNotIn("null", result.stderr.lower())
        self.assertFalse(self.output.exists())
        self.assertEqual(json.loads(Path(str(self.output) + ".run.json").read_bytes())["outcome"]["reason"], "input_unreadable")

    def test_failed_write_never_reports_success_or_echoes_private_exception(self):
        injection = """
import os
original_write = os.write
def partial_write(fd, content):
    if content.startswith(b'# Paper'):
        original_write(fd, content[:7])
        raise OSError('private-sentinel')
    return original_write(fd, content)
os.write = partial_write
"""
        result = run_package("--output", self.output, injection=injection)
        self.assert_failure(result, "partial report may exist")
        self.assertEqual(self.output.read_bytes(), b"# Paper")
        record = json.loads(Path(str(self.output) + ".run.json").read_bytes())
        self.assertEqual(record["outcome"]["reason"], "output_write_failed")
        self.assertIsNone(record["outputs"][0]["sha256"])

    def test_closed_stdout_reports_saved_artifact_without_shutdown_traceback(self):
        process = subprocess.Popen(
            [sys.executable, "-X", "utf8", "-I", "-B", "-c",
             GUARD + "\nsys.argv = sys.argv[1:]\nrunpy.run_path(sys.argv[0], run_name='__main__')\n",
             str(PACKAGE / "run.py"), "--output", str(self.output)],
            env={"PATH": os.defpath}, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        process.stdout.close()
        error = process.stderr.read().decode("utf-8")
        process.stderr.close()
        self.assertEqual(process.wait(timeout=10), 1, error)
        self.assertIn("Report was saved", error)
        self.assertNotIn("Traceback", error)
        self.assertEqual(self.output.read_bytes(), (ROOT / "examples" / "paper-journal-expected.md").read_bytes())

    def test_parent_file_bad_arguments_and_missing_helpers_are_controlled(self):
        self.output.parent.write_bytes(b"Keep parent file.")
        self.assert_failure(run_package("--output", self.output), "Cannot reserve a private run record")
        self.assertEqual(self.output.parent.read_bytes(), b"Keep parent file.")
        result = run_package("--unknown", "private-sentinel")
        self.assertEqual(result.returncode, 2)
        self.assertIn("--help", result.stderr)
        self.assertNotIn("private-sentinel", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        package = self.copy_package()
        (package.parents[1] / "scripts" / "paper_journal.py").unlink()
        self.assert_failure(run_package(script=package / "run.py"), "complete Lab checkout")

    def test_lab_observation_precedes_creation_of_unignored_artifacts(self):
        package = self.copy_package()
        lab = package.parents[1]
        env = {"PATH": os.defpath, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}

        def git(*args):
            return subprocess.run(["git", "-C", str(lab), *args], env=env, check=True,
                                  capture_output=True, text=True, timeout=10).stdout.strip()

        git("init", "-q")
        git("add", ".")
        git("-c", "user.name=Local synthetic test", "-c", "user.email=test@example.invalid", "commit", "-qm", "synthetic checkout")
        revision = git("rev-parse", "HEAD")
        output = lab / "unignored.md"
        result = run_package("--output", output, script=package / "run.py", cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        record = json.loads(Path(str(output) + ".run.json").read_bytes())
        self.assertEqual(record["lab"], {"revision": revision, "state": "clean"})
        self.assertTrue(git("status", "--porcelain"))


if __name__ == "__main__":
    unittest.main()
