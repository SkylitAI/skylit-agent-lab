"""Qualified Git observations; neither a file snapshot nor an OS sandbox."""

import os
from pathlib import Path
import re
import subprocess


def inspect_checkout(path):
    """Inspect the exact worktree root, returning no paths or Git diagnostics."""
    evidence = {"revision": None, "state": "unknown"}
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
    try:
        root = Path(path).resolve()

        def git(*args):
            return subprocess.run(
                ["git", "-c", "core.fsmonitor=false", "-c", "core.untrackedCache=false", "-C", str(root), *args],
                env=env, stdin=subprocess.DEVNULL, check=True, capture_output=True,
                text=True, encoding="utf-8", timeout=5,
            ).stdout

        top = git("rev-parse", "--show-toplevel").removesuffix("\n")
        if Path(top).resolve() != root:
            return evidence
        revision = git("rev-parse", "--verify", "HEAD").strip()
        if not re.fullmatch(r"[0-9a-f]{40}", revision):
            return evidence
        evidence["revision"] = revision
        changes = git("status", "--porcelain=v1", "--untracked-files=all", "--ignore-submodules=none")
        evidence["state"] = "dirty" if changes else "clean"
    except (OSError, ValueError, TypeError, RuntimeError, subprocess.SubprocessError):
        pass
    return evidence
