"""Build committed local sources, then run a fixed probe with Docker networking off."""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import uuid


ROOT = Path(__file__).resolve().parents[1]
GIT_ENV = {"PATH": os.environ.get("PATH", os.defpath), "LC_ALL": "C",
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
           "GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0"}


def git(*args):
    return subprocess.run(
        ["git", "-c", "core.fsmonitor=false", "-c", "core.untrackedCache=false",
         "-c", "core.hooksPath=/dev/null", "-c", "init.templateDir=", *map(str, args)],
        env=GIT_ENV, stdin=subprocess.DEVNULL, check=True, capture_output=True,
        text=True, timeout=60,
    ).stdout.strip()


def stage_checkout(source, destination):
    source = source.resolve(strict=True)
    if Path(git("-C", source, "rev-parse", "--show-toplevel")).resolve() != source:
        raise ValueError("Supply an exact repository root.")
    if git("-C", source, "status", "--porcelain=v1", "--untracked-files=all", "--ignore-submodules=none"):
        raise ValueError("Commit or remove local changes before testing the committed source.")
    revision = git("-C", source, "rev-parse", "--verify", "HEAD")
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Expected a full Git commit revision.")
    # Local transport copies Git objects, not the source's config, ignored files or hooks.
    git("clone", "--no-local", "--no-checkout", source, destination)
    git("-C", destination, "checkout", "--detach", revision)
    # Retain only the metadata needed to observe the actual commit and clean tree.
    (destination / ".git/config").write_text("[core]\n\trepositoryformatversion = 0\n\tfilemode = true\n\tbare = false\n")
    for name in ("hooks", "logs"):
        shutil.rmtree(destination / ".git" / name, ignore_errors=True)
    if git("-C", destination, "status", "--porcelain=v1", "--untracked-files=all"):
        raise ValueError("Staged checkout does not match its committed source.")
    return revision


def docker_client(config):
    # Read endpoint/plugin metadata only; never copy the user's Docker config.
    context = os.environ.get("DOCKER_CONTEXT")
    endpoint = os.environ.get("DOCKER_HOST") if not context else None
    if not endpoint:
        command = ["docker", "context", "inspect", "--format", "{{.Endpoints.docker.Host}}"]
        if context:
            command += ["--", context]
        endpoint = subprocess.run(
            command,
            check=True, capture_output=True, text=True, timeout=15,
        ).stdout.strip()
    if not endpoint.startswith("unix://") or not Path(endpoint[7:]).is_absolute():
        raise ValueError("Use a local Docker Engine through a Unix socket.")
    discovery_env = {key: value for key, value in os.environ.items()
                     if not key.startswith("DOCKER_") or key == "DOCKER_CONFIG"}
    plugins = json.loads(subprocess.run(
        ["docker", "--host", endpoint, "info", "--format", "{{json .ClientInfo.Plugins}}"],
        env=discovery_env, check=True, capture_output=True, text=True, timeout=15,
    ).stdout)
    config.mkdir()
    (config / "config.json").write_text("{}\n")
    for plugin in plugins or []:
        if plugin.get("Name") == "buildx":
            executable = Path(plugin["Path"]).resolve(strict=True)
            (config / "cli-plugins").mkdir()
            (config / "cli-plugins/docker-buildx").symlink_to(executable)
            break
    else:
        raise ValueError("Docker Buildx is required; install it through your Docker distribution.")
    command = ["docker", "--config", str(config), "--host", endpoint]
    env = {"PATH": os.environ.get("PATH", os.defpath), "LC_ALL": "C", "DOCKER_CONFIG": str(config)}

    def run(*args, **kwargs):
        return subprocess.run([*command, *map(str, args)], env=env, stdin=subprocess.DEVNULL, **kwargs)

    return run


def run_probe(stage, client, without_kit):
    container = "skylit-lab-check-" + uuid.uuid4().hex
    image = None
    try:
        client("build", "--file", stage / "lab/evaluations/Dockerfile",
               "--iidfile", stage / "image-id", stage, check=True, timeout=600)
        image = (stage / "image-id").read_text().strip()
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", image):
            image = None
            raise ValueError("Docker did not return a valid image ID.")
        print(f"Local image: {image}", flush=True)
        command = ["run", "--rm", "--pull", "never", "--name", container,
                   "--network", "none", "--read-only", "--cap-drop", "ALL",
                   "--security-opt", "no-new-privileges", "--user", "65534:65534",
                   "--pids-limit", "64", "--memory", "256m", "--cpus", "1",
                   "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=128m,mode=1777", image]
        if without_kit:
            command.append("--without-kit")
        client(*command, check=True, timeout=120)
    finally:
        # Names identify only this invocation; the temporary client config still exists.
        commands = [["rm", "--force", container]]
        if image:
            commands.append(["image", "rm", image])
        for command in commands:
            try:
                client(*command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=15, check=False)
            except (OSError, subprocess.SubprocessError):
                print("Docker cleanup was incomplete; inspect this run's local resources.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--kit", type=Path, help="Clean local checkout at the experiment's pinned Kit revision")
    mode.add_argument("--without-kit", action="store_true", help="Check isolation and independent seeds only; Watchlist remains unverified")
    args = parser.parse_args()
    try:
        with tempfile.TemporaryDirectory(prefix="skylit-lab-isolation-") as directory:
            base = Path(directory)
            stage = base / "context"
            stage.mkdir()
            lab_revision = stage_checkout(ROOT, stage / "lab")
            if args.kit is not None:
                kit_revision = stage_checkout(args.kit, stage / "kit")
                print(f"Committed Lab: {lab_revision}; Kit: {kit_revision}", flush=True)
            else:
                (stage / "kit").mkdir()
                (stage / "kit/unverified.txt").write_text("Kit was explicitly omitted.\n")
                print(f"Committed Lab: {lab_revision}; Kit: UNVERIFIED (explicitly omitted)", flush=True)
            client = docker_client(base / "client")
            run_probe(stage, client, args.without_kit)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        reason = str(error).rstrip(".") if isinstance(error, ValueError) else type(error).__name__
        print(f"Isolation check failed: {reason}. Check source paths, Git and Docker availability.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
