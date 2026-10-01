"""Local setup refuses invalid sources and never repurposes existing paths."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import setup_watchlist as setup


class SetupPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="watchlist setup ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.lab = self.root / "lab"
        self.kit = self.root / "kit"
        self.dest = self.root / "new workspace"
        self.make_repo(self.lab, "experiments/watchlist-investigator/run.py")
        self.pin = self.make_repo(self.kit, "skylit_agent_kit/watchlist.py")
        self.pin_patch = patch.object(setup, "KIT_REVISION", self.pin)
        self.pin_patch.start()
        self.addCleanup(self.pin_patch.stop)

    def command(self, *args, cwd=None):
        return subprocess.run(
            ["git", *map(str, args)], cwd=cwd, check=True, capture_output=True,
            env=setup.local_environment(), text=True,
        ).stdout.strip()

    def make_repo(self, path, required):
        path.mkdir()
        self.command("-c", "init.templateDir=", "init", "-q", path)
        target = path / required
        target.parent.mkdir(parents=True)
        target.write_text("# Synthetic test repository.\n", encoding="utf-8")
        self.command("add", ".", cwd=path)
        self.command("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                     "commit", "-qm", "synthetic fixture", cwd=path)
        return self.command("rev-parse", "HEAD", cwd=path)

    def validate(self, **values):
        return setup.validate_sources(values.get("lab", self.lab), values.get("kit", self.kit),
                                      values.get("destination", self.dest))

    def test_valid_local_inputs_make_no_destination(self):
        result = self.validate()
        self.assertEqual(result[:3], (self.lab.resolve(), self.kit.resolve(), self.dest.resolve()))
        self.assertFalse(self.dest.exists())

    def test_missing_git_and_missing_checkout_are_actionable(self):
        with patch.object(setup.shutil, "which", return_value=None):
            with self.assertRaisesRegex(setup.SetupError, "Git is required"):
                self.validate()
        with self.assertRaisesRegex(setup.SetupError, "Kit checkout is missing"):
            self.validate(kit=self.root / "missing")
        self.assertFalse(self.dest.exists())

    def test_wrong_pin_and_dirty_sources_refuse_before_writing(self):
        with patch.object(setup, "KIT_REVISION", "0" * 40):
            with self.assertRaisesRegex(setup.SetupError, "Kit revision must be"):
                self.validate()
        for root in (self.lab, self.kit):
            extra = root / "local-work.txt"
            extra.write_text("preserve me")
            with self.assertRaisesRegex(setup.SetupError, "checkout must be clean"):
                self.validate()
            self.assertEqual(extra.read_text(), "preserve me")
            extra.unlink()
        self.assertFalse(self.dest.exists())

    def test_existing_destinations_and_broken_symlinks_are_preserved(self):
        self.dest.mkdir()
        (self.dest / "keep").write_text("original")
        with self.assertRaisesRegex(setup.SetupError, "already exists"):
            self.validate()
        self.assertEqual((self.dest / "keep").read_text(), "original")
        link = self.root / "broken"
        link.symlink_to(self.root / "absent")
        with self.assertRaisesRegex(setup.SetupError, "already exists"):
            self.validate(destination=link)
        self.assertTrue(link.is_symlink())

    def test_nested_sources_and_missing_parent_are_refused(self):
        with self.assertRaisesRegex(setup.SetupError, "repository root"):
            self.validate(kit=self.kit / "skylit_agent_kit")
        with self.assertRaisesRegex(setup.SetupError, "parent must already"):
            self.validate(destination=self.root / "missing" / "new")
        with self.assertRaisesRegex(setup.SetupError, "outside both"):
            self.validate(destination=self.kit / "new")
        self.assertFalse((self.kit / "new").exists())

    def test_subprocess_environment_excludes_keys(self):
        with patch.dict(os.environ, {"SKYLIT_API_KEY": "synthetic-test-key", "OPENAI_API_KEY": "synthetic"}):
            env = setup.local_environment()
        self.assertNotIn("SKYLIT_API_KEY", env)
        self.assertNotIn("OPENAI_API_KEY", env)
        self.assertEqual(env["GIT_TERMINAL_PROMPT"], "0")
