"""Save a dated single-source press brief; offline fictional data is the default."""

import argparse
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import stat
import string
import sys

PACKAGE = Path(__file__).resolve().parent
sys.path.insert(0, str(PACKAGE.parents[1]))
from scripts import fed_press_feed as feed
from scripts.git_provenance import inspect_checkout
from scripts.record_files import PersistenceError, save_run

BUNDLED_SHA256 = "e2fc20b0b4aa3c7361250ba9f699355eddc28deb860b5a082bafc4a988bb0121"


class InputError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


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
            raise InputError("input_unreadable", "Choose a regular input file, not a symlink.")
        flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise InputError("input_unreadable", "Choose a regular input file; directories and pipes are not supported.")
            with os.fdopen(descriptor, "rb", closefd=False) as stream:
                raw = stream.read(feed.MAX_BYTES + 1)
        finally:
            os.close(descriptor)
    except InputError:
        raise
    except (OSError, ValueError):
        raise InputError("input_unreadable", "Choose a readable regular file for --input.") from None
    if len(raw) > feed.MAX_BYTES:
        raise InputError("input_too_large", "Input exceeds 512 KiB.")
    return raw


def _check_output(path):
    if path.exists() or path.is_symlink():
        raise FileExistsError("Output already exists; choose a new --output path.")
    for parent in path.parents:
        if parent.is_symlink():
            raise ValueError("Output path components must not be symlinks; use a canonical path.")
        if parent.exists() and not parent.is_dir():
            raise ValueError("Output parent must be a directory.")


def _save(path, report):
    path.parent.mkdir(parents=True, exist_ok=True)
    _check_output(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                         | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0), 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        if hasattr(os, "fchmod"):
            os.fchmod(stream.fileno(), 0o600)
        if stream.write(report) != len(report):
            raise OSError("Incomplete report write")


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
    started = datetime.now(timezone.utc).isoformat()
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--input", type=Path, help="Caller-supplied saved RSS, at most 512 KiB; retrieval is unknown")
    source.add_argument("--fetch", action="store_true", help="Explicitly request the fixed official feed once")
    parser.add_argument("--limit", type=_limit, default=5, help="First 1–20 releases in feed order (default 5)")
    parser.add_argument("--output", type=Path, default=PACKAGE / "reports" / "brief.md", help="New private Markdown file")
    args = parser.parse_args(argv)
    output = args.output.absolute()
    sidecar = Path(str(output) + ".run.json")
    message = f"Saved brief: {output}"
    record_message = f"Saved private run record: {sidecar}"
    if (not str(output).isprintable() or not output.name or output.name in {".", ".."}
            or any(char in output.name for char in "/\\:") or len(os.fsencode(sidecar.name)) > 255):
        print("error: Choose a printable --output filename without colon or backslash, leaving room for .run.json.", file=sys.stderr)
        return 2
    try:
        (message + "\n" + record_message).encode(sys.stdout.encoding or "utf-8")
    except UnicodeError:
        print("error: Output path cannot be displayed; choose an ASCII path or UTF-8 stdout.", file=sys.stderr)
        return 2
    try:
        _check_output(output)
        _check_output(sidecar)
    except FileExistsError:
        print("error: Output or run record already exists; choose a new --output path.", file=sys.stderr)
        return 1
    except (OSError, ValueError):
        print("error: Output parent must be a usable directory with no symlink components.", file=sys.stderr)
        return 1
    mode = "fetch" if args.fetch else "saved" if args.input is not None else "synthetic"
    record = {
        "schema_version": 1, "experiment_id": "market-brief",
        "mode": {"fetch": "public_fetch", "saved": "offline_supplied", "synthetic": "offline_synthetic"}[mode],
        "lab": inspect_checkout(PACKAGE.parents[1]), "kit": None,
        "inputs": [{"role": "fed_press_xml", "sha256": None, "hash_state": "not_read"}],
        "execution": {"started_at": started, "finished_at": None},
        "parameters": {"limit": args.limit}, "source_time": None,
        "usage": {"scope": "python_process", "basis": "known_public_fetch" if args.fetch else "known_offline_path",
                  "requests_attempted": 0, "credits_reserved": 0, "observed_billing": None,
                  "model": {"mode": "none", "provider": None, "tokens": None}},
        "outputs": [{"role": "report", "filename": None, "sha256": None, "state": "not_written"}],
        "outcome": {"status": "stopped", "reason": "interrupted"},
        "limits": {"input_bytes": feed.MAX_BYTES, "items": feed.MAX_ITEMS, "display_items": 20,
                   "requests": 1 if args.fetch else 0, "fetch_timeout_seconds": feed.SECONDS if args.fetch else None,
                   "credits": 0, "model_calls": 0, "output_no_overwrite": True},
    }
    report = None
    try:
        if args.fetch:
            result = feed.fetch_feed()
            record["usage"]["requests_attempted"] = result["requests_attempted"]
            record["inputs"][0].update(sha256=result["sha256"],
                                       hash_state="read_failed" if result["status"] == "unavailable" else "complete")
        else:
            raw = _load_input(args.input or PACKAGE / "fixture.xml")
            digest = hashlib.sha256(raw).hexdigest()
            record["inputs"][0].update(sha256=digest, hash_state="complete")
            if mode == "synthetic" and digest != BUNDLED_SHA256:
                raise InputError("fixture_changed", "Bundled fixture changed; use --input explicitly for caller-supplied bytes.")
            result = feed.parse_feed(raw)
        record["source_time"] = {"status": result["status"], "retrieved_at": result["retrieved_at"] if args.fetch else None,
                                 "published_at": [item["published_at"] for item in result["items"][:args.limit]]}
        reason = {"invalid": "invalid_feed", "unavailable": "source_unavailable"}.get(result["status"], "completed")
        record["outcome"] = {"status": "completed" if reason == "completed" else "stopped", "reason": reason}
        report = render_brief(result, mode, args.limit).encode("utf-8")
        if reason != "completed":
            print("error: Source invalid or unavailable; saving a gap brief and stopped run record.", file=sys.stderr)
    except InputError as error:
        if error.code != "fixture_changed":
            record["inputs"][0]["hash_state"] = "too_large" if error.code == "input_too_large" else "read_failed"
        record["outcome"] = {"status": "stopped", "reason": error.code}
        print(f"error: {error}", file=sys.stderr)
    try:
        final = save_run(output, report, record, _save, preserve_outcome=True)
    except PersistenceError as error:
        print(f"error: {error}", file=sys.stderr)
        if error.code in {"output_exists", "output_write_failed"}:
            print(record_message, file=sys.stderr)
        return 1
    if report is None:
        print(record_message, file=sys.stderr)
        return 1
    try:
        print(message, flush=True)
        print(record_message, flush=True)
    except (OSError, ValueError):
        # Prevent the interpreter's final flush from turning a handled pipe error into exit 120.
        try:
            with open(os.devnull, "wb") as sink:
                os.dup2(sink.fileno(), sys.stdout.fileno())
        except (OSError, ValueError):
            pass
        print(f"error: Brief was saved at {output}, with run record {sidecar}, but stdout failed; check both before rerunning.", file=sys.stderr)
        return 1
    return 0 if final["outcome"]["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
