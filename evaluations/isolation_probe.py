"""Check Docker isolation and fixed offline samples; never execute manifest commands."""

import argparse
import errno
import hashlib
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.git_provenance import inspect_checkout
from scripts.run_records import parse_record


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--without-kit", action="store_true")
    parser.add_argument("--evaluate", action="store_true")
    args = parser.parse_args(argv)
    require(os.geteuid() != 0, "Expected a non-root process.")
    status = Path("/proc/self/status").read_text()
    require("NoNewPrivs:\t1\n" in status and "CapEff:\t0000000000000000\n" in status,
            "Expected no-new-privileges and no effective capabilities.")
    with socket.socket() as connection:
        connection.settimeout(2)
        result = connection.connect_ex(("1.1.1.1", 443))
    require(result == errno.ENETUNREACH, "Expected an unreachable external network, not a timeout or connection.")
    try:
        with open(ROOT / ".isolation-write-probe", "xb"):
            pass
    except OSError as error:
        require(error.errno == errno.EROFS, "Expected a read-only source filesystem.")
    else:
        (ROOT / ".isolation-write-probe").unlink()
        raise ValueError("Source filesystem was writable.")
    lab = inspect_checkout(ROOT)
    require(lab["state"] == "clean", "Expected clean, attributable Lab source.")
    require(not any(key.endswith(("_API_KEY", "_TOKEN")) for key in os.environ),
            "Unexpected credential environment variable.")
    if args.evaluate:
        from scripts.evaluate import run_suite
        summary = run_suite(kit_root=None if args.without_kit else Path("/work/kit"))
        print(json.dumps({"isolation": "passed", "evaluation": summary}, indent=2))
        return 0 if summary["status"] == "passed" else 1
    completed = []
    with tempfile.TemporaryDirectory(prefix="offline-samples-") as directory:
        output = Path(directory)
        sample = output / "template.md"
        subprocess.run([sys.executable, "-X", "utf8", "-I", "-B", str(ROOT / "templates/experiment/run.py"),
                        "--output", str(sample)], check=True, timeout=20)
        require(sample.read_bytes() == (ROOT / "templates/experiment/expected.md").read_bytes(), "Template output mismatch.")
        seeds = [("journal-reviewer", "fixture.csv"), ("market-brief", "fixture.xml")]
        if not args.without_kit:
            seeds.append(("watchlist-investigator", "fixture.json"))
        for slug, fixture in seeds:
            package = ROOT / "experiments" / slug
            fixture_hash = hashlib.sha256((package / fixture).read_bytes()).hexdigest()
            report = output / (slug + ".md")
            command = [sys.executable, "-X", "utf8", "-I", "-B", str(package / "run.py"), "--output", str(report)]
            if slug == "watchlist-investigator":
                command += ["--kit", "/work/kit"]
            subprocess.run(command, check=True, timeout=30)
            sidecar = Path(str(report) + ".run.json")
            record = parse_record(sidecar.read_bytes())
            require(record["outcome"] == {"status": "completed", "reason": "completed"}, "Seed did not complete.")
            require(record["lab"] == lab, "Lab provenance mismatch.")
            require(record["inputs"][0]["sha256"] == fixture_hash, "Input hash mismatch.")
            require(record["outputs"][0]["sha256"] == hashlib.sha256(report.read_bytes()).hexdigest(), "Output hash mismatch.")
            require(all(stat.S_IMODE(path.stat().st_mode) == 0o600 for path in (report, sidecar)), "Outputs must be private.")
            require(record["usage"]["requests_attempted"] == record["usage"]["credits_reserved"] == 0
                    and record["usage"]["model"]["mode"] == "none", "Offline usage mismatch.")
            completed.append(slug)
    print(json.dumps({"isolation": "passed", "lab": lab, "python": sys.version.split()[0],
                      "git": subprocess.check_output(["git", "--version"], text=True).strip(),
                      "network_errno": result, "template": "passed", "seeds_completed": completed,
                      "watchlist": "unverified" if args.without_kit else "passed",
                      "scope": "isolation and clean samples; semantic evaluation is a separate gate"}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"Isolation probe failed: {error}", file=sys.stderr)
        raise SystemExit(1)
