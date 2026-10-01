"""Save a private review of closed USD cash-equity paper trades; no network or model."""

import argparse
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import stat
import sys


PACKAGE = Path(__file__).resolve().parent
BUNDLED_SHA256 = "e8214adc68ede5949d71aaaf0729311fa1919c5c541f5bf71e109690131432d8"


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "error: Invalid arguments; use --help. --input and --output each require a path.\n")


class InputError(ValueError):
    """A fixed input diagnostic safe to display without source data."""

    def __init__(self, code):
        self.code = code
        self.hash_state = "too_large" if code == "input_too_large" else "read_failed"
        super().__init__({
            "input_too_large": "Input exceeds 1 MiB; provide a smaller --input CSV.",
            "input_unreadable": "Provide a regular readable --input CSV; special files are unsupported.",
        }[code])


def _error(message):
    print(f"error: {message}", file=sys.stderr)
    return 1


def _read_input(path, limit):
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
    with os.fdopen(os.open(path, flags), "rb") as source:
        info = os.fstat(source.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise InputError("input_unreadable")
        if info.st_size > limit:
            raise InputError("input_too_large")
        content = source.read(limit + 1)
    if len(content) > limit:
        raise InputError("input_too_large")
    return content


def _save_private(output, content):
    # save_run already reserved the sidecar and created the parent. Preserve
    # FileExistsError so it can distinguish collisions from failed writes.
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                         | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0), 0o600)
    try:
        if os.write(descriptor, content) != len(content):
            raise OSError("Incomplete write")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def main():
    started = datetime.now(timezone.utc).isoformat()
    parser = Arguments(prog="journal-reviewer", description=__doc__)
    parser.add_argument("--input", type=Path, help="Caller-declared paper CSV; omitted uses the known fictional fixture")
    parser.add_argument("--output", type=Path, default=PACKAGE / "reports" / "journal.md",
                        help="New private Markdown file; default reports/journal.md in this package")
    args = parser.parse_args()
    sys.path.insert(0, str(PACKAGE.parents[1] / "scripts"))
    try:
        from paper_journal import JournalError, MAX_BYTES, MAX_ROWS, parse_journal
        from journal_report import calculate_journal, render_journal
        from git_provenance import inspect_checkout
        from record_files import PersistenceError, save_run
    except ImportError:
        return _error("Required helpers are missing; keep this package inside a complete Lab checkout.")
    try:
        output = args.output.absolute()
        if not str(output).isprintable():
            return _error("Output path must contain only printable characters; choose a new --output path.")
        if (not output.name or len(output.name) > 255 or output.name in {".", ".."}
                or any(char in output.name for char in "/\\:")):
            return _error("Choose an --output filename of at most 255 characters without colon or backslash.")
        message = f"Saved private paper-journal report: {output}"
        record_message = f"Saved private run record: {output}.run.json"
        (message + "\n" + record_message).encode(sys.stdout.encoding or "utf-8")
    except UnicodeError:
        return _error("Output path needs UTF-8 stdout; rerun with python3 -X utf8 -I -B or choose an ASCII path.")
    except (OSError, ValueError):
        return _error("Invalid output path; choose a new --output path in a writable directory.")
    record = {
        "schema_version": 1, "experiment_id": "journal-reviewer",
        "mode": "offline_synthetic" if args.input is None else "offline_supplied",
        "lab": inspect_checkout(PACKAGE.parents[1]), "kit": None,
        "inputs": [{"role": "journal_csv", "sha256": None, "hash_state": "not_read"}],
        "execution": {"started_at": started, "finished_at": None}, "parameters": {}, "source_time": None,
        "usage": {"scope": "python_process", "basis": "known_offline_path", "requests_attempted": 0,
                  "credits_reserved": 0, "observed_billing": None,
                  "model": {"mode": "none", "provider": None, "tokens": None}},
        "outputs": [{"role": "report", "filename": None, "sha256": None, "state": "not_written"}],
        "outcome": {"status": "stopped", "reason": "interrupted"},
        "limits": {"input_bytes": MAX_BYTES, "rows": MAX_ROWS, "requests": 0, "credits": 0,
                   "model_calls": 0, "output_no_overwrite": True},
    }
    report = diagnostic = None
    reason = "input_unreadable"
    try:
        content = _read_input(args.input if args.input is not None else PACKAGE / "fixture.csv", MAX_BYTES)
        digest = hashlib.sha256(content).hexdigest()
        record["inputs"][0].update(sha256=digest, hash_state="complete")
    except InputError as error:
        reason, diagnostic = error.code, str(error)
        record["inputs"][0]["hash_state"] = error.hash_state
    except (OSError, ValueError):
        record["inputs"][0]["hash_state"] = "read_failed"
        diagnostic = "Cannot read input; provide a regular readable --input CSV or restore the bundled fixture."
    if diagnostic is None and args.input is None and digest != BUNDLED_SHA256:
        reason = "fixture_changed"
        diagnostic = "Bundled fixture changed; use --input to declare supplied paper data or restore the known fixture."
    if diagnostic is None:
        try:
            rows = parse_journal(content)
        except JournalError as error:
            reason = "invalid_journal"
            diagnostic = f"{error} Check --input against the documented CSV contract."
        else:
            record["source_time"] = {"basis": "supplied_trade_times", "trade_count": len(rows),
                                     "first_entry_at": min(row["entry_time"] for row in rows).isoformat() if rows else None,
                                     "last_exit_at": max(row["exit_time"] for row in rows).isoformat() if rows else None}
            report = render_journal(calculate_journal(rows), synthetic_fixture=args.input is None).encode("utf-8")
            record["outcome"] = {"status": "completed", "reason": "completed"}
    if diagnostic is not None:
        record["outcome"] = {"status": "stopped", "reason": reason}
        _error(diagnostic)
    try:
        final = save_run(output, report, record, _save_private, preserve_outcome=True)
    except PersistenceError as error:
        return _error(str(error))
    if final["outcome"]["status"] != "completed":
        return _error("Stopped run record saved beside the requested output; choose a new --output path for the next run.")
    try:
        print(message + "\n" + record_message, flush=True)
    except (OSError, UnicodeError):
        try:
            sys.stdout.close()  # Prevent a second failed flush during interpreter shutdown.
        except (OSError, UnicodeError):
            pass
        return _error("Report was saved but its status could not be printed; check the output destination.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
