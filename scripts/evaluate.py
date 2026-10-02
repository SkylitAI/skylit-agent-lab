"""Fixed offline cases; call run_suite only after the isolation probe's guards."""

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
if not __package__:
    sys.path.insert(0, str(ROOT))
from scripts.evaluation_cases import CaseError, IDENTITIES, load_cases
from scripts.evaluation_process import run_child
from scripts.evaluation_results import MAX_REPORT_BYTES, compare_workflow
from scripts.git_provenance import inspect_checkout
from scripts.probe_kit_watchlist import KIT_REVISION
from scripts.run_records import RecordError, decode_record

SOURCES = {
    "watchlist-bundled": ("experiments/watchlist-investigator/fixture.json", "b9ae44413ef960b973737839737f853947bfaf470d78a4fab8fcad71ec25a1b0"),
    "journal-bundled": ("experiments/journal-reviewer/fixture.csv", "e8214adc68ede5949d71aaaf0729311fa1919c5c541f5bf71e109690131432d8"),
    "market-bundled": ("experiments/market-brief/fixture.xml", "e2fc20b0b4aa3c7361250ba9f699355eddc28deb860b5a082bafc4a988bb0121"),
}
WATCHLIST_GOLDEN_HASH = "437ff4b1dfd8d3b9aa09c52279fe1f510c139f17f155f594a5f895140f2d5feb"
SUITE_SECONDS = 90


class SetupError(ValueError):
    """A fixed setup reason; never submitted content or an operating-system error."""


def _read(path):
    try:
        if any(part.is_symlink() for part in (path, *path.parents)):
            raise SetupError("setup_file_invalid")
        def opener(name, flags):
            return os.open(name, flags | os.O_NONBLOCK | os.O_NOFOLLOW)
        with open(path, "rb", opener=opener) as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                raise SetupError("setup_file_invalid")
            raw = source.read(1048577)
        if len(raw) > 1048576:
            raise SetupError("setup_file_invalid")
        raw.decode("utf-8")
        return raw
    except (OSError, UnicodeError):
        raise SetupError("setup_file_invalid") from None


def replace_once(raw, old, new):
    if raw.count(old) != 1:
        raise SetupError("setup_marker_invalid")
    return raw.replace(old, new)


def _golden_block(raw, name=None):
    suffix = b": " + name.encode("ascii") if name else b""
    start = b"<!-- expected-start" + suffix + b" -->\n```markdown\n"
    end = b"```\n<!-- expected-end" + suffix + b" -->"
    if raw.count(start) != 1 or raw.count(end) != 1:
        raise SetupError("setup_golden_invalid")
    before, block = raw.split(start)
    if end in before or end not in block:
        raise SetupError("setup_golden_invalid")
    return block.split(end)[0]


def prepare_suite(root):
    """Validate every case, source digest, transform and whole golden before launch."""
    cases = {case["id"]: case for case in load_cases(root / "evaluations/cases.json")["cases"]}
    inputs = {}
    for name, (filename, digest) in SOURCES.items():
        raw = _read(root / filename)
        if hashlib.sha256(raw).hexdigest() != digest:
            raise SetupError("setup_fixture_hash")
        inputs[name] = raw
    # Hash-verified source fixes this JSON shape and the intended first SPY rows.
    changed = json.loads(inputs["watchlist-bundled"])
    changed["gamma"]["data"]["symbols"][0]["strikes"][0]["value"] = -199
    changed["gamma"]["data"]["symbols"][0]["asOf"] = "2026-10-01T13:44:00Z"
    changed["vanna"]["data"]["symbols"][0]["asOf"] = "2026-10-01T14:02:00Z"
    del changed["flow"]["SPY"]["data"]["trades"][0]["timestamp"]
    journal, market = inputs["journal-bundled"], inputs["market-bundled"]
    inputs.update({
        "watchlist-changed-evidence": (json.dumps(changed, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"),
        "invalid-json": b"not JSON\n",
        "journal-fees-gap": replace_once(replace_once(journal, b",0.10,", b",1.10,"), b"Fictional long paper trade.", b""),
        "journal-header-only": journal.splitlines(keepends=True)[0],
        "journal-missing-exit": replace_once(journal, b",11.25,", b",,"),
        "market-changed-title": replace_once(market, b"paper kites", b"changed fictional wording"),
        "market-empty-channel": b'<rss version="2.0"><channel><title>Fictional</title><link>https://www.federalreserve.gov/feeds/feeds.htm</link><description>Fictional</description></channel></rss>',
        "invalid-xml": b"not xml: private-marker\n",
    })
    goldens = {"watchlist-default": _read(root / "evaluations/watchlist-expected.md"),
               "journal-default": _read(root / "examples/paper-journal-expected.md"),
               "market-default": _golden_block(_read(root / "experiments/market-brief/README.md"))}
    variants = _read(root / "evaluations/variant-expected.md")
    for _, _, _, golden in IDENTITIES.values():
        if golden is not None and golden not in goldens:
            goldens[golden] = _golden_block(variants, golden)
    if any(not raw or not raw.endswith(b"\n") or len(raw) > MAX_REPORT_BYTES for raw in goldens.values()):
        raise SetupError("setup_golden_invalid")
    if hashlib.sha256(goldens["watchlist-default"]).hexdigest() != WATCHLIST_GOLDEN_HASH:
        raise SetupError("setup_golden_hash")
    return cases, inputs, goldens


DEPENDENCY_SCRIPT = """import contextlib, json, os, sys, unittest
from pathlib import Path
root = Path(sys.argv[1])
sys.path[:0] = [str(root), str(root / 'tests')]
with open(os.devnull, "w", encoding="utf-8") as sink, contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
    from test_watchlist import WatchlistTests
    result = unittest.TestResult()
    unittest.TestSuite([WatchlistTests('test_budget_blocks_before_paid_calls')]).run(result)
print(json.dumps({'tests_run': result.testsRun, 'failures': len(result.failures),
                  'errors': len(result.errors), 'skips': len(result.skipped),
                  'success': result.wasSuccessful()}, sort_keys=True))
raise SystemExit(0 if result.wasSuccessful() else 1)
"""


def _command(name, root, kit_root, folder):
    command = [sys.executable, "-X", "utf8", "-I", "-B"]
    if name == "kit-budget-stop":
        return command + ["-c", DEPENDENCY_SCRIPT, str(kit_root)]
    _, experiment, _, _ = IDENTITIES[name]
    command += [str(root / "experiments" / experiment / "run.py"), "--output", str(folder / "report.md")]
    if experiment == "watchlist-investigator":
        command += ["--kit", str(kit_root)]
        if name != "watchlist-default":
            command += ["--fixture", str(folder / "input")]
        if name == "watchlist-changed-evidence":
            command += ["--symbols", "SPY,QQQ,SPXW"]
    elif name not in ("journal-default", "market-default"):
        command += ["--input", str(folder / "input")]
    if name == "market-changed-limited":
        command += ["--limit", "1"]
    return command


def _dependency_reasons(child):
    try:
        value = decode_record(child["stdout"])
    except RecordError:
        return ["dependency_result_invalid"]
    expected = {"tests_run": 1, "failures": 0, "errors": 0, "skips": 0, "success": True}
    if (child["exit_code"] != 0 or type(child["exit_code"]) is not int or type(value) is not dict
            or value.keys() != expected.keys()
            or any(type(value[key]) is not type(wanted) or value[key] != wanted for key, wanted in expected.items())):
        return ["dependency_result_invalid"]
    return []


def run_suite(*, root=ROOT, kit_root=None):
    """Internal entry after probe guards; return only fixed codes and synthetic evidence.

    This function is not an isolation boundary. It neither imports Kit into this
    process nor uses metadata to choose commands. The wrapper supplies committed,
    read-only source and the probe verifies its runtime restrictions first.
    """
    deadline = time.monotonic() + SUITE_SECONDS
    lab = inspect_checkout(root)
    kit = {"required_revision": KIT_REVISION, "observed_revision": None, "verification": "not_checked"}
    summary = {"schema_version": 1, "status": "setup_failed", "reasons": [], "lab": lab, "kit": kit,
               "python": sys.version.split()[0], "scope": "fixed offline workflows and one simulated Kit budget test",
               "cases": [{"id": name, "status": "not_run", "reasons": [],
                          "prepared_input_sha256": None, "expected_report_sha256": None} for name in IDENTITIES]}
    setup_complete = False
    try:
        if lab["state"] != "clean" or not isinstance(lab["revision"], str) or not re.fullmatch(r"[0-9a-f]{40}", lab["revision"]):
            raise SetupError("lab_unverified")
        root = Path(root).resolve(strict=True)
        cases, inputs, goldens = prepare_suite(root)
        if kit_root is not None:
            observed = inspect_checkout(kit_root)
            kit["observed_revision"] = observed["revision"]
            kit["verification"] = ("read_failed" if observed["revision"] is None
                                   else "revision_mismatch" if observed["revision"] != KIT_REVISION
                                   else "dirty" if observed["state"] == "dirty"
                                   else "verified" if observed["state"] == "clean" else "read_failed")
            if kit["verification"] == "verified":
                kit_root = Path(kit_root).resolve()
        with tempfile.TemporaryDirectory(prefix="lab-evaluation-") as directory:
            base = Path(directory).resolve()
            commands = {}
            # Materialize every private input before the first child, including on omitted-Kit runs.
            for row in summary["cases"]:
                name = row["id"]
                folder = base / name
                folder.mkdir(mode=0o700)
                scope, _, source, golden = IDENTITIES[name]
                if scope == "lab_workflow":
                    row["prepared_input_sha256"] = hashlib.sha256(inputs[source]).hexdigest()
                    row["expected_report_sha256"] = hashlib.sha256(goldens[golden]).hexdigest() if golden else None
                    if name not in ("watchlist-default", "journal-default", "market-default"):
                        with open(folder / "input", "xb", opener=lambda path, flags: os.open(path, flags, 0o600)) as target:
                            target.write(inputs[source])
                commands[name] = _command(name, root, kit_root, folder)
            setup_complete = True
            for row in summary["cases"]:
                name = row["id"]
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    row.update(status="not_run", reasons=["suite_timeout"])
                    continue
                scope, experiment, source, golden = IDENTITIES[name]
                if experiment == "watchlist-investigator" and kit["verification"] != "verified":
                    row.update(status="unverified", reasons=["kit_unverified"])
                    continue
                child = run_child(commands[name], base / name, remaining)
                if child["stop_reason"] != "exited":
                    reasons = ["child_" + child["stop_reason"]]
                elif scope == "kit_dependency":
                    reasons = _dependency_reasons(child)
                else:
                    try:
                        stderr = child["stderr"].decode("utf-8")
                    except UnicodeError:
                        reasons = ["child_stderr_invalid"]
                    else:
                        reasons = list(compare_workflow(cases[name], exit_code=child["exit_code"], stderr=stderr,
                            input_bytes=inputs[source], lab=lab, kit=kit if experiment == "watchlist-investigator" else None,
                            golden=goldens.get(golden), report_path=base / name / "report.md"))
                row.update(status="failed" if reasons else "passed", reasons=reasons)
        summary["status"] = "passed" if all(row["status"] == "passed" for row in summary["cases"]) else "failed"
    except (CaseError, SetupError, OSError, ValueError) as error:
        # No raw exceptions, source text or filesystem paths are part of the summary.
        reason = ("evaluation_io_failed" if setup_complete else str(error) if isinstance(error, SetupError)
                  else "setup_cases_invalid" if isinstance(error, CaseError) else "setup_io_failed")
        summary["status"] = "failed" if setup_complete else "setup_failed"
        summary["reasons"] = [reason]
        for row in summary["cases"]:
            if row["status"] == "not_run" and not row["reasons"]:
                row["reasons"] = [reason]
    return summary


def main():
    print("Run python3 -X utf8 -I -B scripts/run_isolated.py --evaluate --kit PATH "
          "(or --without-kit). Direct evaluation without the isolation probe is refused.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
