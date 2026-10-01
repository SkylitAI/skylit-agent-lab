"""Exclusive private report/sidecar persistence; the two files are not atomic."""

import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

if __package__:
    from .run_records import MAX_RECORD_BYTES, RecordError, validate_record
else:
    from run_records import MAX_RECORD_BYTES, RecordError, validate_record


class PersistenceError(ValueError):
    """A fixed failure code; no paths, report contents or raw I/O diagnostics."""

    def __init__(self, code):
        self.code = code
        super().__init__({
            "invalid_record": "Run record metadata is invalid; no files were written.",
            "invalid_report": "Report must be UTF-8 text; no files were written.",
            "record_exists": "Run record already exists; choose a new output path.",
            "record_unavailable": "Cannot reserve a private run record; report writing was not attempted.",
            "output_exists": "Report already exists and was preserved; a stopped run record was saved.",
            "output_write_failed": "Report writing failed; a partial report may exist. A stopped run record was saved.",
            "record_write_failed": "Run record finalization failed; a report and an incomplete record may exist.",
        }[code])


def _payload(record):
    validate_record(record)
    content = (json.dumps(record, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode("utf-8")
    if len(content) > MAX_RECORD_BYTES:
        raise RecordError("Run record exceeds its byte limit.")
    return content


def _write(descriptor, content):
    if os.write(descriptor, content) != len(content):
        raise OSError("Incomplete record write")
    os.fsync(descriptor)


def _finish(record):
    record["execution"]["finished_at"] = datetime.now(timezone.utc).isoformat()


def save_run(output, report, record, save_report):
    """Finalize a copied record; call the pinned Kit writer only after reservation.

    The caller supplies validated provenance and UTF-8/runtime preflight. This
    helper owns output metadata, finish time and persistence-failure outcomes.
    A None report preserves an already-stopped computation's outcome. A returned
    stopped record is not workflow success; report/persistence failures raise.
    """
    report_hash = None
    if report is not None:
        try:
            report_hash = hashlib.sha256(report.replace("\n", os.linesep).encode("utf-8")).hexdigest() if type(report) is str else None
        except UnicodeError:
            pass
        if report_hash is None:
            raise PersistenceError("invalid_report")
    invalid = False
    try:
        output = Path(output)
        sidecar = Path(str(output) + ".run.json")
        final = copy.deepcopy(record)
        final["outputs"] = [{"role": "report", "filename": output.name, "sha256": report_hash,
                             "state": "complete" if report is not None else "not_written"}]
        if report is not None:
            final["outcome"] = {"status": "completed", "reason": "completed"}
        elif final["outcome"]["status"] != "stopped":
            raise RecordError("A missing report requires a stopped outcome.")
        _finish(final)
        _payload(final)  # Reject caller contract bugs before creating either file.
    except (ValueError, TypeError, KeyError, RecursionError):
        invalid = True
    if invalid:
        raise PersistenceError("invalid_record")

    failure = None
    try:
        sidecar.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(sidecar, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                             | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0), 0o600)
    except FileExistsError:
        failure = "record_exists"
    except OSError:
        failure = "record_unavailable"
    if failure:
        raise PersistenceError(failure)

    try:
        if report is not None:
            try:
                save_report(output, report)
            except FileExistsError:
                failure = "output_exists"
                final["outputs"][0].update(state="not_written", sha256=None)
            except Exception:
                failure = "output_write_failed"
                final["outputs"][0].update(state="write_failed", sha256=None)
            if failure:
                final["outcome"] = {"status": "stopped", "reason": failure}
        try:
            _finish(final)
            _write(descriptor, _payload(final))
        except (OSError, ValueError, TypeError, KeyError, RecursionError):
            failure = "record_write_failed"
            final["outcome"] = {"status": "stopped", "reason": failure}
            try:
                # One bounded rewrite, through our descriptor only; never delete paths.
                _finish(final)
                content = _payload(final)
                os.lseek(descriptor, 0, os.SEEK_SET)
                os.ftruncate(descriptor, 0)
                _write(descriptor, content)
            except (OSError, ValueError, TypeError, KeyError, RecursionError):
                pass
    finally:
        try:
            os.close(descriptor)
        except OSError:
            failure = "record_write_failed"
    if failure:
        raise PersistenceError(failure)
    return final
