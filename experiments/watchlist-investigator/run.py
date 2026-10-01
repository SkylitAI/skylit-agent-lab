"""Save an explicitly fictional watchlist using a pinned local Agent Kit."""

import argparse
import codecs
import locale
from pathlib import Path
import subprocess
import sys


PACKAGE = Path(__file__).resolve().parent
sys.path.insert(0, str(PACKAGE.parents[1] / "scripts"))
from probe_kit_watchlist import build_result, load_fixture, load_kit, render_result
from watchlist_time import assess_times, parse_max_age, parse_reference, render_time_evidence


def main():
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
    try:
        kit = load_kit(args.kit)
        from skylit_agent_kit.watchlist_cli import save_private
    except (OSError, subprocess.CalledProcessError, ImportError):
        print("error: Cannot load --kit; provide a readable pinned Kit repository root and ensure Git is available.", file=sys.stderr)
        return 1
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    try:
        result = build_result(kit, load_fixture(args.fixture), args.symbols)
        assessment = assess_times(result, reference, max_age)
        report = render_result(kit, result, title="Watchlist Investigator")
        report += "\n" + render_time_evidence(assessment)
    except (ValueError, RecursionError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    output = args.output.absolute()
    message = f"Saved private synthetic report: {output}"
    try:
        message.encode(sys.stdout.encoding or "utf-8")
    except UnicodeError:
        print("error: Output path cannot be displayed by stdout; choose an ASCII path or rerun with UTF-8 stdout (python3 -X utf8 -I -B ...).", file=sys.stderr)
        return 1
    try:
        save_private(output, report)
    except FileExistsError:
        print("error: Output already exists; choose a new --output path.", file=sys.stderr)
        return 1
    except (OSError, ValueError):
        print("error: Cannot save report; check the --output directory and permissions.", file=sys.stderr)
        return 1
    print(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
