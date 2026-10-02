"""Compare fixed offline workflow artifacts without running their producer."""

import hashlib
import os
from pathlib import Path
import re
import stat

from scripts.run_records import MAX_RECORD_BYTES, RecordError, parse_record


MAX_REPORT_BYTES = 131072


class _ArtifactError(ValueError):
    """Fixed internal reason, never a submitted filename or I/O diagnostic."""


def _read_private(path, limit):
    try:
        if any(part.is_symlink() for part in (path, *path.parents)):
            raise _ArtifactError("not_regular")

        def opener(name, flags):
            return os.open(name, flags | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0))

        with open(path, "rb", opener=opener) as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode):
                raise _ArtifactError("not_regular")
            if os.name != "posix" or stat.S_IMODE(info.st_mode) != 0o600 or info.st_uid != os.geteuid():
                raise _ArtifactError("not_private")
            content = stream.read(limit + 1)
        if len(content) > limit:
            raise _ArtifactError("too_large")
        return content
    except _ArtifactError:
        raise
    except FileNotFoundError:
        raise _ArtifactError("missing") from None
    except IsADirectoryError:
        raise _ArtifactError("not_regular") from None
    except (OSError, ValueError):
        raise _ArtifactError("unreadable") from None


def _provenance(lab, kit, watchlist):
    def sha(value):
        return type(value) is str and re.fullmatch(r"[0-9a-f]{40}", value) is not None

    if (type(lab) is not dict or set(lab) != {"revision", "state"}
            or lab["state"] != "clean" or not sha(lab["revision"])):
        return False
    if not watchlist:
        return kit is None
    return (type(kit) is dict and set(kit) == {"required_revision", "observed_revision", "verification"}
            and kit["verification"] == "verified" and sha(kit["required_revision"])
            and kit["observed_revision"] == kit["required_revision"])


def compare_workflow(case, *, exit_code, stderr, input_bytes, lab, kit, golden, report_path):
    """Return fixed failure codes, or () when these workflow artifacts match.

    Caller responsibilities: pass a trusted validated workflow case, the prepared
    input buffer, observed child exit/stderr, pre-output clean Lab observation,
    independently verified pinned Kit metadata (Watchlist only), and the entire
    reviewed golden as exact bytes. No golden or newline normalization occurs.
    These comparisons do not discover or certify caller observations. Dependency
    cases, execution/isolation and full-gate acceptance belong to a later executor.
    Artifact checks require POSIX owner/mode evidence and are not a sandbox against
    concurrent path replacement. The only reads are the supplied report and its
    adjacent .run.json; no path or code is taken from case/record contents.
    """
    if case["scope"] != "lab_workflow":
        return ("unsupported_scope",)
    expected = case["expected"]
    if not _provenance(lab, kit, case["experiment"] == "watchlist-investigator"):
        return ("invalid_provenance",)
    if type(input_bytes) is not bytes or type(stderr) is not str:
        return ("invalid_observation",)
    has_report = expected["output_state"] == "complete"
    if has_report:
        try:
            if type(golden) is not bytes or len(golden) > MAX_REPORT_BYTES:
                return ("invalid_golden",)
            golden.decode("utf-8")
        except UnicodeError:
            return ("invalid_golden",)
    elif golden is not None:
        return ("invalid_golden",)
    try:
        output = Path(report_path)
        sidecar = Path(str(output) + ".run.json")
    except (TypeError, ValueError):
        return ("invalid_artifact_path",)
    failures = []
    if type(exit_code) is not int or exit_code != expected["exit_code"]:
        failures.append("exit_code_mismatch")
    if any(text in stderr for text in expected["stderr_absent"]):
        failures.append("stderr_forbidden")
    try:
        record = parse_record(_read_private(sidecar, MAX_RECORD_BYTES))
    except _ArtifactError as error:
        return tuple(failures + ["record_" + str(error)])
    except RecordError:
        return tuple(failures + ["record_invalid"])
    for field, wanted in (("experiment_id", case["experiment"]), ("mode", expected["mode"]),
                          ("outcome", expected["outcome"]), ("parameters", expected["parameters"]),
                          ("source_time", expected["source_time"]), ("lab", lab), ("kit", kit)):
        if record[field] != wanted:
            failures.append(field + "_mismatch")
    if record["execution"]["finished_at"] is None:
        failures.append("execution_unfinished")
    # parse_record enforces the remaining counts, model, billing and limit fields.
    if record["usage"]["basis"] != "known_offline_path":
        failures.append("usage_mismatch")
    source, saved = record["inputs"][0], record["outputs"][0]
    if source["hash_state"] != expected["input_hash_state"]:
        failures.append("input_state_mismatch")
    if source["sha256"] != hashlib.sha256(input_bytes).hexdigest():
        failures.append("input_hash_mismatch")
    if saved["state"] != expected["output_state"]:
        failures.append("output_state_mismatch")
    if saved["filename"] != output.name:
        failures.append("output_name_mismatch")
    if not has_report:
        try:
            output.lstat()
            failures.append("unexpected_report")
        except FileNotFoundError:
            pass
        except (OSError, ValueError):
            failures.append("report_unreadable")
        if saved["sha256"] is not None:
            failures.append("report_hash_mismatch")
        return tuple(failures)
    try:
        report = _read_private(output, MAX_REPORT_BYTES)
    except _ArtifactError as error:
        return tuple(failures + ["report_" + str(error)])
    if saved["sha256"] != hashlib.sha256(report).hexdigest():
        failures.append("report_hash_mismatch")
    if report != golden:
        failures.append("golden_mismatch")
    try:
        text = report.decode("utf-8")
    except UnicodeError:
        return tuple(failures + ["report_invalid_utf8"])
    if any(item not in text for item in expected["contains"]):
        failures.append("report_required_text_missing")
    if any(item in text for item in expected["absent"]):
        failures.append("report_forbidden_text")
    return tuple(failures)
