"""Local setup refuses invalid sources and never repurposes existing paths."""

import io
import json
import os
import shlex
import runpy
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

    def commit(self, root):
        self.command("add", ".", cwd=root)
        self.command("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                     "commit", "-qm", "synthetic setup behavior", cwd=root)

    def add_synthetic_runner(self, *, fail=False):
        code = "import sys\nsys.exit(1)\n" if fail else '''import os, sys
from pathlib import Path
assert sys.flags.utf8_mode == 1
assert 'SKYLIT_API_KEY' not in os.environ
assert 'OPENAI_API_KEY' not in os.environ
out = Path(sys.argv[sys.argv.index('--output') + 1])
out.parent.mkdir(parents=True, exist_ok=True)
with out.open('x', encoding='utf-8') as stream:
    stream.write('Synthetic café — no credentials or service calls.\\n')
'''
        (self.lab / "experiments/watchlist-investigator/run.py").write_text(code, encoding="utf-8")
        (self.lab / ".gitignore").write_text(".env\nreports/\n", encoding="utf-8")
        self.commit(self.lab)

    def test_complete_workspace_uses_commits_utf8_and_excludes_ignored_inputs(self):
        self.add_synthetic_runner()
        (self.lab / ".env").write_text("synthetic private sentinel")
        (self.lab / "reports").mkdir()
        (self.lab / "reports/private.md").write_text("synthetic report sentinel")
        with patch.dict(os.environ, {"SKYLIT_API_KEY": "synthetic-test-key", "OPENAI_API_KEY": "synthetic"}):
            message = setup.prepare_workspace(self.lab, self.kit, self.dest)
        self.assertIn("Prepared local workspace", message)
        self.assertFalse((self.dest / ".setup-incomplete").exists())
        self.assertFalse((self.dest / "lab/.env").exists())
        self.assertFalse((self.dest / "lab/reports/private.md").exists())
        report = self.dest / "reports/watchlist.md"
        self.assertEqual(report.read_text(encoding="utf-8"), "Synthetic café — no credentials or service calls.\n")
        metadata = json.loads((self.dest / "setup.json").read_text())
        self.assertEqual(metadata["kit_revision"], self.pin)
        self.assertEqual(metadata["lab_revision"], self.command("rev-parse", "HEAD", cwd=self.lab))
        self.assertEqual(self.command("rev-parse", "HEAD", cwd=self.dest / "kit"), self.pin)
        self.assertEqual(self.command("status", "--porcelain", cwd=self.lab), "")
        self.assertEqual(self.command("status", "--porcelain", cwd=self.kit), "")
        self.assertEqual((self.lab / ".env").read_text(), "synthetic private sentinel")
        if os.name != "nt":
            self.assertEqual(self.dest.stat().st_mode & 0o777, 0o700)

    def test_incomplete_clone_and_renderer_failure_are_marked_and_never_reused(self):
        self.add_synthetic_runner(fail=True)
        with self.assertRaisesRegex(setup.SetupError, "private incomplete destination is retained"):
            setup.prepare_workspace(self.lab, self.kit, self.dest)
        self.assertTrue((self.dest / ".setup-incomplete").is_file())
        self.assertFalse((self.dest / "run_watchlist.py").exists())
        self.assertFalse((self.dest / "setup.json").exists())
        with self.assertRaisesRegex(setup.SetupError, "already exists"):
            setup.prepare_workspace(self.lab, self.kit, self.dest)
        original_git = setup.git
        def fail_clone(args, **kwargs):
            if "clone" in args:
                raise setup.SetupError("Local clone failed")
            return original_git(args, **kwargs)
        other = self.root / "failed clone"
        with patch.object(setup, "git", side_effect=fail_clone):
            with self.assertRaisesRegex(setup.SetupError, "Local clone failed.*incomplete"):
                setup.prepare_workspace(self.lab, self.kit, other)
        self.assertTrue((other / ".setup-incomplete").is_file())

    def test_unprintable_destination_and_creation_race_preserve_paths(self):
        output = io.TextIOWrapper(io.BytesIO(), encoding="ascii")
        unicode_dest = self.root / "café"
        with patch.object(setup.sys, "stdout", output):
            with self.assertRaisesRegex(setup.SetupError, "cannot be displayed"):
                setup.prepare_workspace(self.lab, self.kit, unicode_dest)
        self.assertFalse(unicode_dest.exists())
        validated = self.validate()
        self.dest.mkdir()
        with patch.object(setup, "validate_sources", return_value=validated):
            with self.assertRaisesRegex(setup.SetupError, "already exists"):
                setup.prepare_workspace(self.lab, self.kit, self.dest)
        self.assertEqual(list(self.dest.iterdir()), [])

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
        tracked = self.kit / "skylit_agent_kit/watchlist.py"
        tracked.write_text("# Changed synthetic module.\n")
        with self.assertRaisesRegex(setup.SetupError, "checkout must be clean"):
            self.validate()
        self.command("add", ".", cwd=self.kit)
        with self.assertRaisesRegex(setup.SetupError, "checkout must be clean"):
            self.validate()
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

    def test_repository_and_included_filters_are_rejected_before_status_executes_them(self):
        sentinel = self.root / "filter-executed"
        filter_script = self.lab / ".git/synthetic-filter.py"
        filter_script.write_text(
            "import sys\nfrom pathlib import Path\n"
            f"Path({str(sentinel)!r}).write_text('executed')\n"
            "sys.stdout.write(sys.stdin.read())\n", encoding="utf-8")
        (self.lab / ".gitattributes").write_text("*.py filter=synthetic\n")
        self.commit(self.lab)
        command = shlex.join([sys.executable, str(filter_script)])
        for kind in ("clean", "process"):
            self.command("config", f"filter.synthetic.{kind}", command, cwd=self.lab)
            os.utime(self.lab / "experiments/watchlist-investigator/run.py", None)
            with self.assertRaisesRegex(setup.SetupError, "config contains content filters"):
                self.validate()
            self.assertFalse(sentinel.exists())
            self.command("config", "--unset", f"filter.synthetic.{kind}", cwd=self.lab)
        included = self.lab / ".git/filter-config"
        self.command("config", "--file", included, "filter.synthetic.clean", command)
        self.command("config", "include.path", included, cwd=self.lab)
        with self.assertRaisesRegex(setup.SetupError, "config contains content filters"):
            self.validate()
        self.assertFalse(sentinel.exists())
        self.assertFalse(self.dest.exists())

    def test_workspace_dissociates_sources_with_borrowed_objects(self):
        self.add_synthetic_runner()
        borrowed_lab = self.root / "borrowed lab"
        borrowed_kit = self.root / "borrowed kit"
        for source, target in ((self.lab, borrowed_lab), (self.kit, borrowed_kit)):
            self.command("-c", "init.templateDir=", "clone", "--shared", source, target)
            self.assertTrue((target / ".git/objects/info/alternates").is_file())
        setup.prepare_workspace(borrowed_lab, borrowed_kit, self.dest)
        self.lab.rename(self.root / "relocated lab donor")
        self.kit.rename(self.root / "relocated kit donor")
        for name in ("lab", "kit"):
            copied = self.dest / name
            self.assertFalse((copied / ".git/objects/info/alternates").exists())
            self.command("cat-file", "-e", "HEAD", cwd=copied)
            self.assertEqual(self.command("status", "--porcelain", cwd=copied), "")


KIT = Path(os.environ.get("SKYLIT_AGENT_KIT", ROOT.parent / "skylit-agent-kit"))


@unittest.skipUnless(KIT.is_dir(), "Setup integration unverified: set SKYLIT_AGENT_KIT to the pinned checkout")
class RealWorkspaceTests(unittest.TestCase):
    def test_real_workspace_and_reusable_launcher_preserve_outputs(self):
        with tempfile.TemporaryDirectory(prefix="real Watchlist café ") as directory:
            root = Path(directory)
            lab = root / "source lab"
            git_path = setup.shutil.which("git")
            setup.git(["-c", "init.templateDir=", "clone", "--local", "--no-hardlinks", "--", ROOT, lab], git_path=git_path)
            workspace = root / "workspace"
            setup.prepare_workspace(lab, KIT, workspace)
            report = workspace / "reports/watchlist.md"
            first = report.read_bytes()
            self.assertIn("Skylit watchlist · GEX / VEX / recent flow".encode(), first)
            self.assertIn(b"Fictional data only", first)
            self.assertIn(b"QQQ", first)
            self.assertIn(b"missing", first)
            self.assertIn(b"0 requests attempted", first)
            if os.name != "nt":
                self.assertEqual(report.stat().st_mode & 0o777, 0o600)
            launcher = workspace / "run_watchlist.py"
            def run(*args):
                return subprocess.run(
                    [sys.executable, "-X", "utf8=0", str(launcher), *map(str, args)], cwd=root,
                    env={"PATH": os.defpath, "LC_ALL": "C", "SKYLIT_API_KEY": "synthetic-unused-key"},
                    stdin=subprocess.DEVNULL, capture_output=True, encoding="utf-8",
                )
            collision = run()
            self.assertEqual(collision.returncode, 1)
            self.assertIn("already exists", collision.stderr)
            self.assertEqual(report.read_bytes(), first)
            second = root / "second café.md"
            rerun = run("--symbols", "QQQ", "--output", second)
            self.assertEqual(rerun.returncode, 0, rerun.stderr)
            self.assertIn(b"QQQ", second.read_bytes())
            self.assertNotIn(b"## SPY", second.read_bytes())
            invalid = run("--symbols", "?", "--output", root / "invalid.md")
            self.assertNotEqual(invalid.returncode, 0)
            self.assertFalse((root / "invalid.md").exists())
            link = root / "link.md"
            link.symlink_to(report)
            blocked = run("--output", link)
            self.assertNotEqual(blocked.returncode, 0)
            self.assertEqual(report.read_bytes(), first)


class LauncherRoutingTests(unittest.TestCase):
    def test_only_explicit_live_forwards_key_and_interactive_stdin(self):
        with tempfile.TemporaryDirectory() as directory:
            launcher = Path(directory) / "run_watchlist.py"
            launcher.write_text(setup.LAUNCHER, encoding="utf-8")
            for args in ([], ["--dry-run"], ["--live"]):
                with patch.object(sys, "argv", [str(launcher), *args]), \
                     patch.dict(os.environ, {"SKYLIT_API_KEY": "synthetic-forwarding-sentinel"}), \
                     patch.object(subprocess, "call", return_value=0) as call:
                    with self.assertRaises(SystemExit) as exit_result:
                        runpy.run_path(str(launcher), run_name="__main__")
                self.assertEqual(exit_result.exception.code, 0)
                command = call.call_args.args[0]
                env = call.call_args.kwargs["env"]
                self.assertEqual("SKYLIT_API_KEY" in env, args == ["--live"])
                self.assertNotIn("synthetic-forwarding-sentinel", " ".join(command))
                self.assertEqual(call.call_args.kwargs["stdin"], None if args == ["--live"] else subprocess.DEVNULL)
                self.assertEqual("watchlist_live.py" in command[5], bool(args))
