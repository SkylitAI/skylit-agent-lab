"""Load reviewed evaluation expectations as inert data; never dispatch a case."""

import os
import re
import stat

from scripts import run_records as records


MAX_CASE_BYTES = 65536
# Case IDs bind to reviewed scope, experiment, input and golden IDs, never paths.
IDENTITIES = {
    "watchlist-default": ("lab_workflow", "watchlist-investigator", "watchlist-bundled", "watchlist-default"),
    "watchlist-changed-evidence": ("lab_workflow", "watchlist-investigator", "watchlist-changed-evidence", None),
    "watchlist-invalid": ("lab_workflow", "watchlist-investigator", "invalid-json", None),
    "kit-budget-stop": ("kit_dependency", "watchlist-investigator", "kit-budget-fixtures", None),
    "journal-default": ("lab_workflow", "journal-reviewer", "journal-bundled", "journal-default"),
    "journal-fees-gap": ("lab_workflow", "journal-reviewer", "journal-fees-gap", None),
    "journal-empty": ("lab_workflow", "journal-reviewer", "journal-header-only", None),
    "journal-open": ("lab_workflow", "journal-reviewer", "journal-missing-exit", None),
    "market-default": ("lab_workflow", "market-brief", "market-bundled", "market-default"),
    "market-changed-limited": ("lab_workflow", "market-brief", "market-changed-title", None),
    "market-empty": ("lab_workflow", "market-brief", "market-empty-channel", None),
    "market-invalid": ("lab_workflow", "market-brief", "invalid-xml", None),
}


class CaseError(ValueError):
    """Invalid or unreadable case metadata, without submitted values or paths."""


def _require(condition):
    if not condition:
        raise CaseError("Invalid evaluation case metadata.")


def _literals(value):
    _require(type(value) is list and all(type(item) is str and item for item in value))
    try:
        for item in value:
            item.encode("utf-8")
    except UnicodeError:
        raise CaseError("Expected UTF-8 literal text.") from None


def _workflow(case, golden):
    expected = case["expected"]
    records._keys(expected, "exit_code mode outcome input_hash_state output_state parameters source_time "
                  "golden contains absent stderr_absent", "expectations")
    _require(expected["golden"] == golden)
    for key in ("contains", "absent", "stderr_absent"):
        _literals(expected[key])
    watchlist = case["experiment"] == "watchlist-investigator"
    journal = case["experiment"] == "journal-reviewer"
    synthetic = watchlist or case["input"] in ("journal-bundled", "market-bundled")
    _require(expected["mode"] == ("offline_synthetic" if synthetic else "offline_supplied"))
    _require(expected["input_hash_state"] == "complete")
    parameters = expected["parameters"]
    if watchlist:
        records._keys(parameters, "symbols reference_time max_age_seconds", "parameters")
        symbols = parameters["symbols"]
        _require(type(symbols) is list and 1 <= len(symbols) <= 100
                 and all(type(s) is str and re.fullmatch(r"[A-Z][A-Z0-9.-]{0,11}", s) for s in symbols)
                 and len(set(symbols)) == len(symbols))
        records._utc(parameters["reference_time"])
        _require(records._integer(parameters["max_age_seconds"], 0, 86400))
    elif journal:
        records._keys(parameters, "", "parameters")
    else:
        records._keys(parameters, "limit", "parameters")
        _require(records._integer(parameters["limit"], 1, 20))
    outcome = expected["outcome"]
    records._keys(outcome, "status reason", "outcome")
    _require(outcome["status"] in ("completed", "stopped"))
    completed = outcome["status"] == "completed"
    invalid = "invalid_fixture" if watchlist else "invalid_journal" if journal else "invalid_feed"
    _require(outcome["reason"] == ("completed" if completed else invalid))
    _require(records._integer(expected["exit_code"], 0, 1) and expected["exit_code"] == (0 if completed else 1))
    has_report = completed or not (watchlist or journal)
    _require(expected["output_state"] == ("complete" if has_report else "not_written"))
    times = expected["source_time"]
    if not has_report:
        _require(times is None)
    elif watchlist:
        records._assessment(times, parameters)
    elif journal:
        records._journal_times(times)
    else:
        records._feed_times(times, parameters, False, {"hash_state": expected["input_hash_state"]})
        _require(times["status"] in ("available", "empty") if completed else times["status"] == "invalid")


def validate_cases(value):
    """Validate decoded case shapes and identities, not the truth of expectations."""
    try:
        records._keys(value, "schema_version cases", "root")
        _require(records._integer(value["schema_version"], 1, 1))
        entries = value["cases"]
        _require(type(entries) is list and len(entries) == len(IDENTITIES))
        seen = set()
        for case in entries:
            records._keys(case, "id scope experiment input expected", "case")
            name = case["id"]
            _require(type(name) is str and name in IDENTITIES and name not in seen)
            seen.add(name)
            scope, experiment, source, golden = IDENTITIES[name]
            _require((case["scope"], case["experiment"], case["input"]) == (scope, experiment, source))
            if scope == "kit_dependency":
                budget = {"exit_code": 0, "tests_run": 1, "failed_tests": 0,
                          "simulated_stop_contains": "budget", "simulated_credits": 0, "lab_record": False}
                records._keys(case["expected"], budget, "dependency expectations")
                _require(all(type(case["expected"][key]) is type(item) and case["expected"][key] == item
                             for key, item in budget.items()))
            else:
                _workflow(case, golden)
    except records.RecordError:
        raise CaseError("Invalid evaluation case metadata.") from None
    return value


def parse_cases(content):
    """Decode at most 64 KiB of UTF-8 JSON with a 32-container nesting limit."""
    if type(content) is not bytes or len(content) > MAX_CASE_BYTES:
        raise CaseError("Expected UTF-8 bytes within the 64 KiB case limit.")
    try:
        value = records.decode_record(content)
    except records.RecordError:
        raise CaseError("Cases require valid JSON without duplicate keys, nonfinite numbers or excessive nesting.") from None
    return validate_cases(value)


def load_cases(path):
    """Read one bounded regular file, without interpreting its strings or paths."""
    if not isinstance(path, (str, os.PathLike)):
        raise CaseError("Expected an evaluation case file path.")
    try:
        def opener(name, flags):
            return os.open(name, flags | getattr(os, "O_NONBLOCK", 0))

        with open(path, "rb", opener=opener) as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                raise CaseError("Cases must be read from a regular file.")
            content = source.read(MAX_CASE_BYTES + 1)
    except (OSError, ValueError):
        raise CaseError("Cannot read evaluation cases from a bounded regular file.") from None
    return parse_cases(content)
