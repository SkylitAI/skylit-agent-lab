"""Stage tracked Lab sources plus this reviewed prototype; never copy ignored files."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.run_isolated import stage_checkout
from scripts.probe_kit_watchlist import KIT_REVISION

PROTOTYPE = (
    "scripts/watchlist_desk.py", "tests/test_watchlist_desk.py",
    "prototypes/watchlist-desk/README.md", "prototypes/watchlist-desk/Dockerfile",
    "prototypes/watchlist-desk/prepare.py",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New staging directory")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    observed = stage_checkout(args.kit, args.output / "kit")
    if observed != KIT_REVISION:
        raise ValueError("Use the exact clean Kit pin; staged context is incomplete.")
    tracked = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z"],
                             capture_output=True, check=True).stdout.decode().split("\0")
    hashes = {}
    for name in sorted(set(filter(None, tracked)) | set(PROTOTYPE)):
        source = ROOT / name
        if source.is_symlink() or not source.is_file() or not source.resolve().is_relative_to(ROOT):
            raise ValueError("Only regular repository source files can be staged.")
        content = source.read_bytes()
        destination = args.output / "lab" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        hashes[name] = hashlib.sha256(content).hexdigest()
    revision = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    manifest = {"lab_base_revision": revision, "source_state": "working tree snapshot; see exact file hashes",
                "kit_revision": observed, "files": hashes}
    (args.output / "lab/source-snapshot.json").write_text(json.dumps(manifest, indent=2) + "\n")
    shutil.copyfile(ROOT / "prototypes/watchlist-desk/Dockerfile", args.output / "Dockerfile")
    print(args.output.resolve())


if __name__ == "__main__":
    main()
