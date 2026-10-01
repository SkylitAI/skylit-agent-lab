"""Prepare an offline Watchlist workspace from existing local Git checkouts."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from probe_kit_watchlist import KIT_REVISION


ROOT = Path(__file__).resolve().parents[1]


class SetupError(ValueError):
    """An actionable setup failure, safe to show without subprocess output."""


def local_environment():
    """Do not pass service keys or user Git configuration to child processes."""
    return {
        "PATH": os.environ.get("PATH", os.defpath),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_ALLOW_PROTOCOL": "file",
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
    config = git(["-C", root, "config", "--includes", "--null", "--list"], git_path=git_path)
    for entry in config.split("\0"):
        key = entry.partition("\n")[0].lower()
        if key.startswith("filter.") and key.endswith((".clean", ".process")):
            raise SetupError(f"{label} config contains content filters; choose a checkout without configured clean/process filters.")
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


LAUNCHER = '''"""Run the synthetic example, or explicitly select a bounded Kit dry/live path."""
import os
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parent
if sys.version_info < (3, 11):
    sys.exit("error: Python 3.11 or newer is required.")
if (root / ".setup-incomplete").exists():
    sys.exit("error: Setup did not finish; prepare a new workspace.")
env = {"PATH": os.environ.get("PATH", os.defpath), "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
       "GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0", "GIT_ALLOW_PROTOCOL": "file"}
command = [sys.executable, "-X", "utf8", "-I", "-B",
           str(root / "lab/experiments/watchlist-investigator/run.py"),
           "--output", str(root / "reports/watchlist.md"), *sys.argv[1:],
           "--kit", str(root / "kit")]
live = "--live" in sys.argv[1:]
if live or "--dry-run" in sys.argv[1:]:
    command = [sys.executable, "-X", "utf8", "-I", "-B",
               str(root / "lab/scripts/watchlist_live.py"), *sys.argv[1:], "--kit", str(root / "kit")]
    if live and "SKYLIT_API_KEY" in os.environ:
        env["SKYLIT_API_KEY"] = os.environ["SKYLIT_API_KEY"]
sys.exit(subprocess.call(command, env=env, stdin=None if live else subprocess.DEVNULL))
'''


def prepare_workspace(lab, kit, destination):
    lab, kit, destination, revision, git_path = validate_sources(lab, kit, destination)
    message = f"Prepared local workspace: {destination}\nSaved synthetic report: {destination / 'reports/watchlist.md'}"
    try:
        message.encode(sys.stdout.encoding or "utf-8")
    except UnicodeError:
        raise SetupError("Destination cannot be displayed; rerun Python with -X utf8 or choose an ASCII path.") from None
    try:
        destination.mkdir(mode=0o700)
    except FileExistsError:
        raise SetupError("Destination already exists; choose a new directory.") from None
    except OSError:
        raise SetupError("Cannot create destination; check its parent directory and permissions.") from None
    marker = destination / ".setup-incomplete"
    try:
        marker.write_text("Setup incomplete. Preserve any files and choose a new destination.\n", encoding="utf-8")
        for name, source, pin in (("lab", lab, revision), ("kit", kit, KIT_REVISION)):
            target = destination / name
            git(["-c", "init.templateDir=", "clone", "--local", "--no-hardlinks", "--dissociate", "--no-checkout",
                 "--", source, target], git_path=git_path)
            git(["-C", target, "checkout", "--detach", pin], git_path=git_path)
            if checkout_revision(target, name.title(), git_path=git_path) != pin:
                raise SetupError("Copied checkout did not match the selected revision.")
        result = subprocess.run(
            [sys.executable, "-X", "utf8", "-I", "-B",
             str(destination / "lab/experiments/watchlist-investigator/run.py"),
             "--kit", str(destination / "kit"), "--output", str(destination / "reports/watchlist.md")],
            env=local_environment(), stdin=subprocess.DEVNULL,
            capture_output=True, encoding="utf-8", errors="replace", timeout=60,
        )
        if result.returncode:
            raise SetupError("Synthetic Watchlist failed; check the selected Lab/Kit compatibility and output permissions.")
        (destination / "run_watchlist.py").write_text(LAUNCHER, encoding="utf-8")
        (destination / "setup.json").write_text(json.dumps({
            "lab_revision": revision, "kit_revision": KIT_REVISION,
            "mode": "offline_synthetic", "report": "reports/watchlist.md",
        }, indent=2) + "\n", encoding="utf-8")
        marker.unlink()
    except SetupError as error:
        raise SetupError(f"{error} The private incomplete destination is retained; choose a new destination after fixing the cause.") from None
    except (OSError, subprocess.TimeoutExpired):
        raise SetupError("Setup did not finish. The private incomplete destination is retained; check paths and permissions, then choose a new destination.") from None
    return message


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kit", required=True, type=Path, help="Existing clean Kit checkout at the exact documented pin")
    parser.add_argument("--destination", required=True, type=Path, help="New directory outside both checkouts, with an existing parent")
    args = parser.parse_args()
    if sys.version_info < (3, 11):
        print("error: Python 3.11 or newer is required.", file=sys.stderr)
        return 1
    try:
        message = prepare_workspace(ROOT, args.kit, args.destination)
    except SetupError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(message)
    print("Rerun from that workspace: python3 run_watchlist.py --output reports/another.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
