"""Save a dated single-source press brief; offline fictional data is the default."""

import argparse
import hashlib
import os
from pathlib import Path
import stat
import string
import sys

PACKAGE = Path(__file__).resolve().parent
sys.path.insert(0, str(PACKAGE.parents[1]))
from scripts import fed_press_feed as feed

BUNDLED_SHA256 = "e2fc20b0b4aa3c7361250ba9f699355eddc28deb860b5a082bafc4a988bb0121"


def _limit(value):
    try:
        limit = int(value)
        if 1 <= limit <= 20:
            return limit
    except ValueError:
        pass
    raise argparse.ArgumentTypeError("--limit must be an integer from 1 through 20")


def _load_input(path):
    try:
        if path.is_symlink():
            raise ValueError("Choose a regular input file, not a symlink.")
        flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise ValueError("Choose a regular input file; directories and pipes are not supported.")
            with os.fdopen(descriptor, "rb", closefd=False) as stream:
                raw = stream.read(feed.MAX_BYTES + 1)
        finally:
            os.close(descriptor)
    except (OSError, UnicodeError):
        raise ValueError("Choose a readable regular file for --input.") from None
    if len(raw) > feed.MAX_BYTES:
        raise ValueError("Input exceeds 512 KiB.")
    return raw


def _check_output(path):
    if path.exists() or path.is_symlink():
        raise ValueError("Output already exists; choose a new --output path.")
    for parent in path.parents:
        if parent.is_symlink():
            raise ValueError("Output path components must not be symlinks; use a canonical path.")
        if parent.exists() and not parent.is_dir():
            raise ValueError("Output parent must be a directory.")


def _save(path, report):
    raw = report.encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    _check_output(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        if hasattr(os, "fchmod"):
            os.fchmod(stream.fileno(), 0o600)
        stream.write(raw)


def _text(value):
    return "".join((f"\\u{ord(char):04x}" if ord(char) <= 0xFFFF else f"\\U{ord(char):08x}")
                   if not char.isprintable() else f"&#{ord(char)};" if char in string.punctuation else char
                   for char in value)


def render_brief(record, mode, limit):
    provenance = {
        "synthetic": "Bundled fictional fixture: all release titles, dates and URLs below are invented.",
        "saved": "Caller-supplied saved feed: source authenticity and retrieval time are unverified.",
        "fetch": "Source: Federal Reserve Board press feed, explicitly fetched from its fixed URL.",
    }
    retrieval = (record["retrieved_at"] or "unavailable (fetch incomplete)") if mode == "fetch" else "unknown (offline input)"
    items = record["items"][:limit] if record["status"] == "available" else []
    lines = ["# Market Brief", "", provenance[mode], f"Actual retrieval (UTC): {retrieval}.", "",
             f"Source status: {record['status']}. Showing {len(items)} of {len(record['items'])} releases in feed order.",
             f"Requests attempted: {record['requests_attempted']}. Model calls: 0."]
    if record["status"] == "empty":
        lines.extend(["", "No releases were present in this feed; this does not establish an absence of announcements."])
    elif record["status"] != "available":
        lines.extend(["", "No usable releases. " + _text(record["error"] or "Source unavailable.")])
    for item in items:
        lines.extend(["", f"### Published (UTC): {item['published_at']}", _text(item["title"]), ""])
        if mode == "fetch":
            lines.append(f"[Board release]({item['url']})")
        else:
            label = "Fictional URL (not a citation)" if mode == "synthetic" else "Unverified input URL"
            lines.append(f"{label}: `{item['url']}`")
    digest = f"`{record['sha256']}`" if record["sha256"] is not None else "unavailable"
    lines.extend(["", f"Feed format reference: `{feed.SOURCE_URL}`.", f"Input SHA-256: {digest}.",
                  "This covers one press-release feed; it is not a complete market view or a freshness guarantee."])
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--input", type=Path, help="Caller-supplied saved RSS, at most 512 KiB; retrieval is unknown")
    source.add_argument("--fetch", action="store_true", help="Explicitly request the fixed official feed once")
    parser.add_argument("--limit", type=_limit, default=5, help="First 1–20 releases in feed order (default 5)")
    parser.add_argument("--output", type=Path, default=PACKAGE / "reports" / "brief.md", help="New private Markdown file")
    args = parser.parse_args(argv)
    output = args.output.absolute()
    message = f"Saved brief: {output}"
    if not str(output).isprintable() or len(output.name) > 255:
        print("error: Choose a printable --output path with a filename of at most 255 characters.", file=sys.stderr)
        return 2
    try:
        message.encode(sys.stdout.encoding or "utf-8")
    except UnicodeError:
        print("error: Output path cannot be displayed; choose an ASCII path or UTF-8 stdout.", file=sys.stderr)
        return 2
    try:
        _check_output(output)
        mode = "fetch" if args.fetch else "saved" if args.input is not None else "synthetic"
        if args.fetch:
            record = feed.fetch_feed()
        else:
            raw = _load_input(args.input or PACKAGE / "fixture.xml")
            if mode == "synthetic" and hashlib.sha256(raw).hexdigest() != BUNDLED_SHA256:
                raise ValueError("Bundled fixture changed; use --input explicitly for caller-supplied bytes.")
            record = feed.parse_feed(raw)
        report = render_brief(record, mode, args.limit)
        _save(output, report)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except (OSError, UnicodeError):
        print("error: Cannot save a new private UTF-8 brief; a partial report may remain at --output.", file=sys.stderr)
        return 1
    try:
        print(message, flush=True)
    except (OSError, ValueError):
        # Prevent the interpreter's final flush from turning a handled pipe error into exit 120.
        try:
            with open(os.devnull, "wb") as sink:
                os.dup2(sink.fileno(), sys.stdout.fileno())
        except (OSError, ValueError):
            pass
        print(f"error: Brief was saved at {output}, but stdout failed; check that file before rerunning.", file=sys.stderr)
        return 1
    if record["status"] not in {"available", "empty"}:
        print("error: Source invalid or unavailable; the saved brief records the gap.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
