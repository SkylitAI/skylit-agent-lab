"""Read-only Git evidence belongs to the exact requested checkout root."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from scripts import git_provenance as provenance


class CheckoutTests(unittest.TestCase):
    def make_repository(self, root):
        env = {"PATH": os.defpath, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
        def git(*args):
            return subprocess.run(["git", "-C", str(root), *args], env=env, check=True,
                                  capture_output=True, text=True).stdout.strip()
        root.mkdir()
        git("init", "--quiet")
        (root / "fixture.txt").write_text("Synthetic fixture.\n")
        git("add", "fixture.txt")
        git("-c", "user.name=Synthetic Test", "-c", "user.email=test@example.invalid",
            "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "Synthetic fixture")
        return git("rev-parse", "HEAD")

    def test_clean_tracked_and_untracked_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            revision = self.make_repository(root)
            self.assertEqual(provenance.inspect_checkout(root), {"revision": revision, "state": "clean"})
            (root / "fixture.txt").write_text("Changed synthetic fixture.\n")
            self.assertEqual(provenance.inspect_checkout(root), {"revision": revision, "state": "dirty"})
            (root / "fixture.txt").write_text("Synthetic fixture.\n")
            (root / "untracked.txt").write_text("New synthetic fixture.\n")
            self.assertEqual(provenance.inspect_checkout(root), {"revision": revision, "state": "dirty"})

    def test_non_repository_and_nested_copy_do_not_inherit_parent_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            self.make_repository(root)
            nested = root / "copied-lab"
            nested.mkdir()
            for path in (Path(directory), nested, root / "missing"):
                self.assertEqual(provenance.inspect_checkout(path), {"revision": None, "state": "unknown"})

    def test_environment_git_overrides_cannot_redirect_or_hide_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root, other = Path(directory) / "wanted", Path(directory) / "other"
            revision = self.make_repository(root)
            self.make_repository(other)
            (root / "untracked.txt").write_text("Must remain visible.\n")
            overrides = {"GIT_DIR": str(other / ".git"), "GIT_WORK_TREE": str(other),
                         "GIT_INDEX_FILE": str(other / ".git" / "index"), "GIT_CONFIG_COUNT": "1",
                         "GIT_CONFIG_KEY_0": "status.showUntrackedFiles", "GIT_CONFIG_VALUE_0": "no",
                         "GIT_CONFIG_PARAMETERS": "malformed inherited config", "GIT_CONFIG_GLOBAL": "missing-config"}
            with mock.patch.dict(os.environ, overrides):
                self.assertEqual(provenance.inspect_checkout(root), {"revision": revision, "state": "dirty"})

    def test_failures_and_timeouts_are_unknown_without_raw_diagnostics(self):
        for failure in (FileNotFoundError("private path"), subprocess.CalledProcessError(1, "private command"),
                        subprocess.TimeoutExpired("private command", 5)):
            with self.subTest(failure=type(failure).__name__), mock.patch.object(provenance.subprocess, "run", side_effect=failure):
                self.assertEqual(provenance.inspect_checkout(Path.cwd()), {"revision": None, "state": "unknown"})

    def test_known_head_survives_failed_status_and_git_calls_are_bounded(self):
        root = Path.cwd().resolve()
        responses = [subprocess.CompletedProcess([], 0, str(root) + "\n"),
                     subprocess.CompletedProcess([], 0, "a" * 40 + "\n"),
                     subprocess.TimeoutExpired("private command", 5)]
        with mock.patch.object(provenance.subprocess, "run", side_effect=responses) as run:
            self.assertEqual(provenance.inspect_checkout(root), {"revision": "a" * 40, "state": "unknown"})
        for call in run.call_args_list:
            self.assertGreater(call.kwargs["timeout"], 0)
            self.assertLessEqual(call.kwargs["timeout"], 5)
            self.assertEqual(call.kwargs["stdin"], subprocess.DEVNULL)
            self.assertEqual(call.kwargs["env"]["GIT_OPTIONAL_LOCKS"], "0")


if __name__ == "__main__":
    unittest.main()
