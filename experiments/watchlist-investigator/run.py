"""Save an explicitly fictional watchlist using a pinned local Agent Kit."""

import argparse
import codecs
import locale
from datetime import datetime, timezone
from pathlib import Path
import sys


PACKAGE = Path(__file__).resolve().parent
sys.path.insert(0, str(PACKAGE.parents[1] / "scripts"))
from git_provenance import inspect_checkout
from probe_kit_watchlist import (
    KIT_REVISION, FixtureError, KitError, build_result, load_fixture_with_hash,
    load_kit_with_metadata, render_result,
)
from record_files import PersistenceError, save_run
from watchlist_time import assess_times, parse_max_age, parse_reference, render_time_evidence


def main():
    started = datetime.now(timezone.utc).isoformat()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kit", required=True, help="Local Kit checkout at the manifest's exact revision")
    parser.add_argument("--symbols", default="SPY,QQQ", help="Comma-separated symbols; absent data stays missing")
    parser.add_argument("--fixture", type=Path, default=PACKAGE / "fixture.json", help="Synthetic JSON, at most 64 KiB")
    parser.add_argument("--output", type=Path, default=PACKAGE / "reports" / "watchlist.md", help="New local Markdown file; never overwritten")
    parser.add_argument("--reference-time", default="2026-10-01T14:01:00+00:00", help="Timezone-aware fictional ISO 8601 reference; never the wall clock")
    parser.add_argument("--max-age-seconds", default="900", help="Demonstration threshold, integer 0 through 86400")
    args = parser.parse_args()
    if codecs.lookup(locale.getpreferredencoding(False)).name != "utf-8":
        print("error: UTF-8 text mode is required; rerun with python3 -X utf8 -I -B ... before saving a report.", file=sys.stderr)
        return 1
    try:
        reference = parse_reference(args.reference_time)
        max_age = parse_max_age(args.max_age_seconds)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    output = args.output.absolute()
    if (not output.name or len(output.name) > 255 or not output.name.isprintable()
            or output.name in {".", ".."} or any(char in output.name for char in "/\\:")):
        print("error: Choose a printable --output filename of at most 255 characters without colon or backslash.", file=sys.stderr)
        return 1
    message = f"Saved private synthetic report: {output}"
    record_message = f"Saved private run record: {output}.run.json"
    try:
        (message + "\n" + record_message).encode(sys.stdout.encoding or "utf-8")
    except UnicodeError:
        print("error: Output path cannot be displayed by stdout; choose an ASCII path or rerun with UTF-8 stdout (python3 -X utf8 -I -B ...).", file=sys.stderr)
        return 1
    record = {
        "schema_version": 1, "experiment_id": "watchlist-investigator", "mode": "offline_synthetic",
        "lab": inspect_checkout(PACKAGE.parents[1]),
        "kit": {"required_revision": KIT_REVISION, "observed_revision": None, "verification": "not_checked"},
        "inputs": [{"role": "synthetic_fixture", "sha256": None, "hash_state": "not_read"}],
        "execution": {"started_at": started, "finished_at": None},
        "parameters": None, "source_time": None,
        "usage": {"scope": "python_process", "basis": "known_offline_path", "requests_attempted": 0,
                  "credits_reserved": 0, "observed_billing": None,
                  "model": {"mode": "none", "provider": None, "tokens": None}},
        "outputs": [{"role": "report", "filename": None, "sha256": None, "state": "not_written"}],
        "outcome": {"status": "stopped", "reason": "interrupted"},
        "limits": {"fixture_bytes": 65536, "symbols": 100, "requests": 0, "credits": 0,
                   "model_calls": 0, "output_no_overwrite": True},
    }
    report = save_private = None
    reason = "kit_unavailable"
    diagnostic = None
    try:
        kit, record["kit"] = load_kit_with_metadata(args.kit)
        from skylit_agent_kit.watchlist_cli import save_private
        reason = "invalid_parameters"
        symbols = kit.symbols_list(args.symbols)
        record["parameters"] = {"symbols": symbols, "reference_time": reference.isoformat(), "max_age_seconds": max_age}
        reason = "invalid_fixture"
        fixture, digest = load_fixture_with_hash(args.fixture)
        record["inputs"][0].update(sha256=digest, hash_state="complete")
        result = build_result(kit, fixture, symbols)
        record["source_time"] = assess_times(result, reference, max_age)
        report = render_result(kit, result, title="Watchlist Investigator")
        report += "\n" + render_time_evidence(record["source_time"])
    except KitError as error:
        record["kit"] = error.metadata
        reason, diagnostic = error.code, str(error)
    except FixtureError as error:
        record["inputs"][0].update(sha256=error.sha256, hash_state=error.hash_state)
        reason, diagnostic = error.code, str(error)
    except ImportError:
        record["kit"]["verification"] = "read_failed"
        diagnostic = "Cannot load --kit; provide a readable pinned Kit repository root and ensure Git is available."
    except (ValueError, RecursionError) as error:
        diagnostic = str(error) if isinstance(error, ValueError) else "Fixture exceeds the supported nesting limit."
    if diagnostic is not None:
        report = None
        record["outcome"] = {"status": "stopped", "reason": reason}
        print(f"error: {diagnostic}", file=sys.stderr)
    try:
        final = save_run(output, report, record, save_private)
    except PersistenceError as error:
        print(f"error: {error}", file=sys.stderr)
        if error.code in {"output_exists", "output_write_failed"}:
            print(record_message, file=sys.stderr)
        return 1
    if final["outcome"]["status"] != "completed":
        print(record_message, file=sys.stderr)
        return 1
    print(message)
    print(record_message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
