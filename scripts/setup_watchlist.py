"""Prepare an offline Watchlist workspace from existing local Git checkouts."""

import os
from pathlib import Path
import shutil
import subprocess

from probe_kit_watchlist import KIT_REVISION


ROOT = Path(__file__).resolve().parents[1]


class SetupError(ValueError):
    """An actionable setup failure, safe to show without subprocess output."""


def local_environment():
    """Do not pass service keys or user Git configuration to child processes."""
    return {
        "PATH": os.defpath,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_OPTIONAL_LOCKS": "0",
    }


def git(arguments, *, git_path):
    try:
        result = subprocess.run(
            [git_path, "-c", "core.hooksPath=" + os.devnull,
             "-c", "core.fsmonitor=false", "-c", "protocol.allow=never",
             "-c", "protocol.file.allow=always", *map(str, arguments)],
            env=local_environment(), stdin=subprocess.DEVNULL,
            capture_output=True, encoding="utf-8", errors="replace", timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise SetupError("Local Git operation failed; check Git, paths and permissions.") from None
    if result.returncode:
        raise SetupError("Local Git operation failed; supply readable repository roots and check permissions.")
    return result.stdout.strip()


def checkout_revision(root, label, *, git_path):
    if not root.is_dir():
        raise SetupError(f"{label} checkout is missing; supply its local repository root.")
    top = git(["-C", root, "rev-parse", "--show-toplevel"], git_path=git_path)
    if Path(top).resolve() != root:
        raise SetupError(f"{label} path must be the repository root.")
    revision = git(["-C", root, "rev-parse", "HEAD"], git_path=git_path)
    changes = git(["-C", root, "status", "--porcelain", "--untracked-files=all"], git_path=git_path)
    if changes:
        raise SetupError(f"{label} checkout must be clean; preserve local work and choose a clean checkout.")
    return revision


def validate_sources(lab, kit, destination):
    git_path = shutil.which("git")
    if not git_path:
        raise SetupError("Git is required; install Git before preparing a local workspace.")
    lab, kit = Path(lab).resolve(), Path(kit).resolve()
    lab_revision = checkout_revision(lab, "Lab", git_path=git_path)
    kit_revision = checkout_revision(kit, "Kit", git_path=git_path)
    if kit_revision != KIT_REVISION:
        raise SetupError(f"Kit revision must be {KIT_REVISION}; choose the documented pinned checkout.")
    if not (lab / "experiments/watchlist-investigator/run.py").is_file():
        raise SetupError("Lab checkout lacks the Watchlist runner.")
    if not (kit / "skylit_agent_kit/watchlist.py").is_file():
        raise SetupError("Kit checkout lacks its Watchlist module.")
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise SetupError("Destination already exists; choose a new directory.")
    if not destination.parent.is_dir():
        raise SetupError("Destination parent must already be a directory.")
    destination = destination.parent.resolve() / destination.name
    if any(destination.is_relative_to(source) for source in (lab, kit)):
        raise SetupError("Destination must be outside both source checkouts.")
    return lab, kit, destination, lab_revision, git_path
