"""Local synthetic Git fixtures and mocked Docker; no daemon or network required."""

import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import run_isolated as wrapper


class StagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name).resolve()
        self.env = {"PATH": os.defpath, "LC_ALL": "C",
                    "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                    "GIT_TERMINAL_PROMPT": "0", "GIT_ALLOW_PROTOCOL": "file"}
        self.source = self.folder / "source"
        self.source.mkdir()
        self.git(self.source, "init", "--quiet")
        (self.source / ".gitignore").write_text(".env\nreports/\n", encoding="utf-8")
        (self.source / "fixture.txt").write_text("Synthetic committed bytes.\n", encoding="utf-8")
        self.git(self.source, "add", ".")
        self.git(self.source, "-c", "user.name=Synthetic Test", "-c", "user.email=test@example.invalid",
                 "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "Synthetic fixture")
        self.revision = self.git(self.source, "rev-parse", "HEAD")

    def git(self, root, *args):
        return subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-c", "init.templateDir=",
                               "-C", str(root), *args], env=self.env, check=True,
                              capture_output=True, text=True, timeout=10).stdout.strip()

    def test_stage_keeps_commit_but_excludes_ignored_files_and_private_git_metadata(self):
        (self.source / ".env").write_text("SYNTHETIC_KEY=fixture-only\n", encoding="utf-8")
        (self.source / "reports").mkdir()
        (self.source / "reports/private.md").write_text("Synthetic private report.\n", encoding="utf-8")
        self.git(self.source, "config", "http.extraHeader", "Authorization: SYNTHETIC-GIT-TOKEN")
        self.git(self.source, "remote", "add", "origin", "https://SYNTHETIC-GIT-TOKEN@example.invalid/repo")
        hooks = self.source / ".git/hooks"
        hooks.mkdir(exist_ok=True)
        (hooks / "synthetic-hook").write_text("Synthetic private hook contents.\n", encoding="utf-8")
        self.assertTrue((self.source / ".git/logs/HEAD").is_file())
        destination = self.folder / "staged"
        with patch.object(wrapper, "GIT_ENV", self.env):
            revision = wrapper.stage_checkout(self.source, destination)
        self.assertEqual(revision, self.revision)
        self.assertEqual(self.git(destination, "rev-parse", "HEAD"), self.revision)
        self.assertEqual((destination / "fixture.txt").read_bytes(), (self.source / "fixture.txt").read_bytes())
        self.assertEqual(self.git(destination, "status", "--porcelain=v1", "--untracked-files=all"), "")
        for name in (".env", "reports", ".git/hooks", ".git/logs"):
            self.assertFalse((destination / name).exists(), name)
        self.assertEqual(self.git(destination, "remote"), "")
        config = (destination / ".git/config").read_text(encoding="utf-8")
        for private in ("SYNTHETIC-GIT-TOKEN", "extraHeader", str(self.source)):
            self.assertNotIn(private, config)
        self.assertIn("SYNTHETIC-GIT-TOKEN", (self.source / ".git/config").read_text())
        self.assertTrue((self.source / ".env").exists())

    def test_tracked_and_untracked_dirt_are_rejected_before_staging(self):
        for dirty in ("tracked", "staged", "untracked"):
            with self.subTest(dirty=dirty):
                path = self.source / ("new.txt" if dirty == "untracked" else "fixture.txt")
                path.write_text("Uncommitted synthetic change.\n", encoding="utf-8")
                if dirty == "staged":
                    self.git(self.source, "add", "fixture.txt")
                destination = self.folder / dirty
                with patch.object(wrapper, "GIT_ENV", self.env), self.assertRaisesRegex(ValueError, "local changes"):
                    wrapper.stage_checkout(self.source, destination)
                self.assertFalse(destination.exists())
                if dirty == "untracked":
                    path.unlink()
                else:
                    self.git(self.source, "reset", "--quiet", "HEAD", "--", "fixture.txt")
                    self.git(self.source, "checkout", "--", "fixture.txt")


class DockerClientTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name).resolve()
        self.config = self.folder / "isolated-client"
        self.original = self.folder / "synthetic-user-config"
        self.original.mkdir()
        self.original_bytes = json.dumps({"auths": {"registry.example.invalid": {"auth": "SYNTHETIC-AUTH"}},
            "credsStore": "synthetic-helper", "proxies": {"default": {"httpsProxy": "SYNTHETIC-PROXY"}}}).encode()
        (self.original / "config.json").write_bytes(self.original_bytes)
        self.plugin = self.folder / "synthetic-buildx"
        self.plugin.write_text("Not executable; metadata-only fixture.\n", encoding="utf-8")
        self.endpoint = "unix://" + str(self.folder / "synthetic-docker.sock")
        self.env = {"PATH": os.defpath, "TASK_PRIVATE_ROOT": str(self.folder / "synthetic-private-root"),
            "DOCKER_CONTEXT": "synthetic-local", "DOCKER_HOST": "tcp://remote.example.invalid:2375",
            "DOCKER_CONFIG": str(self.original), "DOCKER_AUTH_CONFIG": "SYNTHETIC-AUTH-CONFIG",
            "DOCKER_TLS_VERIFY": "SYNTHETIC-TLS", "DOCKER_CERT_PATH": "SYNTHETIC-CERT-PATH",
            "HTTP_PROXY": "http://SYNTHETIC-PROXY.example.invalid", "HTTPS_PROXY": "https://SYNTHETIC-PROXY.example.invalid",
            "ALL_PROXY": "SYNTHETIC-ALL-PROXY", "NO_PROXY": "SYNTHETIC-NO-PROXY",
            "OPENAI_API_KEY": "SYNTHETIC-API-KEY", "SKYLIT_API_TOKEN": "SYNTHETIC-API-TOKEN"}
        self.calls = []
        self.image = "sha256:" + "a" * 64
        self.child_failure = None
        self.cleanup_failure = False

    def docker(self, command, **kwargs):
        # Every Docker subprocess, including discovery and cleanup, terminates here.
        self.assertEqual(command[0], "docker")
        effective = dict(kwargs.get("env", os.environ))
        self.calls.append((list(command), effective))
        if command[1:3] == ["context", "inspect"]:
            selected = command[-2:] == ["--", "synthetic-local"]
            endpoint = self.endpoint if selected else "tcp://default-remote.example.invalid:2375"
            return subprocess.CompletedProcess(command, 0, endpoint + "\n")
        if "info" in command:
            self.assertIn("--host", command, "Plugin discovery must use the validated local endpoint")
            self.assertEqual(command[command.index("--host") + 1], self.endpoint)
            self.assertNotIn("DOCKER_CONTEXT", effective)
            self.assertNotIn("DOCKER_HOST", effective)
            return subprocess.CompletedProcess(command, 0, json.dumps([{"Name": "buildx", "Path": str(self.plugin)}]))
        operation = command[command.index("--host") + 2]
        if operation == "build":
            Path(command[command.index("--iidfile") + 1]).write_text(self.image + "\n", encoding="utf-8")
        elif operation == "run" and self.child_failure is not None:
            raise self.child_failure
        elif operation == "rm" and self.cleanup_failure:
            raise OSError("Synthetic cleanup failure")
        return subprocess.CompletedProcess(command, 0)

    def client_calls(self):
        return [(command, env) for command, env in self.calls if "--config" in command]

    def test_explicit_context_wins_over_conflicting_host_for_discovery_and_client(self):
        with patch.dict(os.environ, self.env, clear=True), patch.object(wrapper.subprocess, "run", side_effect=self.docker):
            client = wrapper.docker_client(self.config)
            client("version", check=True)
        self.assertEqual(self.calls[0][0][-2:], ["--", "synthetic-local"])
        self.assertEqual(len(self.client_calls()), 1)
        command, _ = self.client_calls()[0]
        self.assertEqual(command[command.index("--host") + 1], self.endpoint)

    def test_remote_context_or_host_is_refused_before_plugin_discovery_or_build(self):
        for context in ("synthetic-remote", None):
            with self.subTest(context=context):
                self.calls.clear()
                env = dict(self.env)
                if context is None:
                    del env["DOCKER_CONTEXT"]
                else:
                    env["DOCKER_CONTEXT"] = context
                with patch.dict(os.environ, env, clear=True), patch.object(wrapper.subprocess, "run", side_effect=self.docker), \
                        self.assertRaisesRegex(ValueError, "local Docker Engine"):
                    wrapper.docker_client(self.config)
                self.assertEqual(len(self.calls), 0 if context is None else 1)
                self.assertFalse(self.config.exists())

    def test_build_run_and_cleanup_exclude_inherited_credentials_proxies_and_config(self):
        stage = self.folder / "stage"
        stage.mkdir()
        with patch.dict(os.environ, self.env, clear=True), patch.object(wrapper.subprocess, "run", side_effect=self.docker), \
                contextlib.redirect_stdout(io.StringIO()):
            wrapper.run_probe(stage, wrapper.docker_client(self.config), without_kit=True)
        self.assertEqual(json.loads((self.config / "config.json").read_text()), {})
        self.assertEqual((self.original / "config.json").read_bytes(), self.original_bytes)
        self.assertEqual((self.config / "cli-plugins/docker-buildx").resolve(), self.plugin)
        self.assertEqual(len(self.client_calls()), 4)  # Build, run, container cleanup, image cleanup.
        for command, env in self.client_calls():
            self.assertEqual(command[command.index("--config") + 1], str(self.config))
            self.assertEqual(env.get("DOCKER_CONFIG"), str(self.config))
            for key, value in self.env.items():
                if key not in {"PATH", "DOCKER_CONFIG"}:
                    self.assertNotIn(key, env)
                    self.assertNotIn(value, command)
            self.assertNotIn(str(self.original), command)

    def test_child_failure_still_attempts_own_container_and_image_cleanup(self):
        stage = self.folder / "stage"
        stage.mkdir()
        self.child_failure = subprocess.CalledProcessError(23, "synthetic child")
        self.cleanup_failure = True
        with patch.dict(os.environ, self.env, clear=True), patch.object(wrapper.subprocess, "run", side_effect=self.docker), \
                contextlib.redirect_stdout(io.StringIO()), self.assertRaises(subprocess.CalledProcessError) as caught:
            wrapper.run_probe(stage, wrapper.docker_client(self.config), without_kit=True)
        self.assertIs(caught.exception, self.child_failure)
        commands = [command[command.index("--host") + 2:] for command, _ in self.client_calls()]
        run = next(command for command in commands if command[0] == "run")
        container = run[run.index("--name") + 1]
        self.assertTrue(container.startswith("skylit-lab-check-"))
        self.assertEqual(commands[-2:], [["rm", "--force", container], ["image", "rm", self.image]])


if __name__ == "__main__":
    unittest.main()
