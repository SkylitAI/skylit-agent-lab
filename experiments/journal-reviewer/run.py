"""Save a private review of closed USD cash-equity paper trades; no network or model."""

import argparse
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


def _error(message):
    print(f"error: {message}", file=sys.stderr)
    return 1


def _read_input(path, limit):
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
    with os.fdopen(os.open(path, flags), "rb") as source:
        info = os.fstat(source.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise InputError("Provide a regular readable --input CSV; special files are unsupported.")
        if info.st_size > limit:
            raise InputError("Input exceeds 1 MiB; provide a smaller --input CSV.")
        content = source.read(limit + 1)
    if len(content) > limit:
        raise InputError("Input exceeds 1 MiB; provide a smaller --input CSV.")
    return content


def _save_private(output, content):
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
    except (OSError, ValueError):
        raise ValueError("Cannot create the output directory; check --output and permissions.") from None
    try:
        descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                             | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0), 0o600)
    except FileExistsError:
        raise ValueError("Output already exists; choose a new --output path.") from None
    except (OSError, ValueError):
        raise ValueError("Cannot create the report; check the output directory and permissions.") from None
    try:
        try:
            if os.write(descriptor, content) != len(content):
                raise OSError("Incomplete write")
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError:
        raise ValueError("Cannot finish writing; an incomplete report may remain. Check storage and choose a new --output path.") from None


def main():
    parser = Arguments(prog="journal-reviewer", description=__doc__)
    parser.add_argument("--input", type=Path, help="Caller-declared paper CSV; omitted uses the known fictional fixture")
    parser.add_argument("--output", type=Path, default=PACKAGE / "reports" / "journal.md",
                        help="New private Markdown file; default reports/journal.md in this package")
    args = parser.parse_args()
    sys.path.insert(0, str(PACKAGE.parents[1] / "scripts"))
    try:
        from paper_journal import JournalError, MAX_BYTES, parse_journal
        from journal_report import calculate_journal, render_journal
    except ImportError:
        return _error("Required helpers are missing; keep this package inside a complete Lab checkout.")
    try:
        content = _read_input(args.input if args.input is not None else PACKAGE / "fixture.csv", MAX_BYTES)
    except InputError as error:
        return _error(str(error))
    except (OSError, ValueError):
        return _error("Cannot read input; provide a regular readable --input CSV or restore the bundled fixture.")
    if args.input is None and hashlib.sha256(content).hexdigest() != BUNDLED_SHA256:
        return _error("Bundled fixture changed; use --input to declare supplied paper data or restore the known fixture.")
    try:
        rows = parse_journal(content)
    except JournalError as error:
        return _error(f"{error} Check --input against the documented CSV contract.")
    report = render_journal(calculate_journal(rows), synthetic_fixture=args.input is None).encode("utf-8")
    try:
        output = args.output.absolute()
        if not str(output).isprintable():
            return _error("Output path must contain only printable characters; choose a new --output path.")
        message = f"Saved private paper-journal report: {output}"
        message.encode(sys.stdout.encoding or "utf-8")
    except UnicodeError:
        return _error("Output path needs UTF-8 stdout; rerun with python3 -X utf8 -I -B or choose an ASCII path.")
    except (OSError, ValueError):
        return _error("Invalid output path; choose a new --output path in a writable directory.")
    try:
        _save_private(output, report)
    except ValueError as error:
        return _error(str(error))
    try:
        print(message, flush=True)
    except (OSError, UnicodeError):
        try:
            sys.stdout.close()  # Prevent a second failed flush during interpreter shutdown.
        except (OSError, UnicodeError):
            pass
        return _error("Report was saved but its status could not be printed; check the output destination.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
