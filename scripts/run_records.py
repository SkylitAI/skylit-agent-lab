"""Bounded inert JSON and explicit Watchlist, Journal and Market record profiles."""

import json
import math
import re
from datetime import datetime


MAX_RECORD_BYTES = 262144
TIME_FIELDS = ("gamma.as_of", "vanna.as_of", "flow.generated_at", "flow.latest_trade")
STOP_REASONS = ("invalid_parameters input_unreadable input_too_large invalid_fixture kit_unavailable "
                "kit_mismatch kit_dirty encoding_unsupported output_path_unprintable output_exists "
                "output_write_failed record_write_failed interrupted").split()


class RecordError(ValueError):
    """Invalid record, with a safe diagnostic independent of submitted values."""


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise RecordError("Duplicate JSON key.")
        result[key] = value
    return result


def _finite(value):
    number = float(value)
    if not math.isfinite(number):
        raise RecordError("Nonfinite JSON number.")
    return number


def decode_record(content):
    """Decode at most 256 KiB of UTF-8 bytes; never execute or fetch content."""
    if type(content) is not bytes or len(content) > MAX_RECORD_BYTES:
        raise RecordError("Expected UTF-8 bytes within the 256 KiB record limit.")
    try:
        record = json.loads(content.decode("utf-8"), object_pairs_hook=_pairs,
                            parse_float=_finite, parse_constant=_finite)
    except RecordError:
        raise
    except (ValueError, RecursionError):
        raise RecordError("Record must contain valid UTF-8 JSON within the nesting limit.") from None
    if type(record) is not dict:
        raise RecordError("Record must be a JSON object.")
    pending = [(record, 1)]
    while pending:
        value, depth = pending.pop()
        if depth > 32:
            raise RecordError("Record exceeds the 32-level nesting limit.")
        children = value.values() if type(value) is dict else value
        pending.extend((child, depth + 1) for child in children if type(child) in (dict, list))
    return record


def _require(condition, field):
    if not condition:
        raise RecordError(f"Invalid run record field: {field}.")


def _keys(value, keys, field):
    _require(type(value) is dict and set(value) == set(keys.split() if type(keys) is str else keys), field)


def _integer(value, low, high):
    return type(value) is int and low <= value <= high


def _number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _hash(value, size):
    return type(value) is str and re.fullmatch(f"[0-9a-f]{{{size}}}", value) is not None


def _utc(value):
    _require(type(value) is str and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|\+00:00)", value), "UTC timestamp")
    try:
        datetime.fromisoformat(value)
    except ValueError:
        raise RecordError("Invalid run record field: UTC timestamp.") from None


def _assessment(value, parameters):
    _require(parameters is not None, "source_time requires parameters")
    _keys(value, "reference_time max_age_seconds symbols rows spans", "source_time")
    for key in ("reference_time", "max_age_seconds", "symbols"):
        _require(type(value[key]) is type(parameters[key]) and value[key] == parameters[key], "source_time parameters")
    symbols = parameters["symbols"]
    _keys(value["rows"], symbols, "source_time rows")
    _keys(value["spans"], symbols, "source_time spans")
    gap = (r"timestamp missing or invalid; (?:available|no strikes returned|no trades returned in requested window|"
           r"missing from heatmap response|invalid duplicate symbol in response|invalid or missing heatmap fields|"
           r"missing from synthetic fixture|partial: [1-9][0-9]{0,4} invalid (?:strikes|trades))")
    for symbol in symbols:
        _keys(value["rows"][symbol], TIME_FIELDS, "source_time fields")
        for item in value["rows"][symbol].values():
            _keys(item, "timestamp age_seconds status reason", "source_time field")
            _require(item["status"] in ("unavailable", "future", "stale", "within threshold"), "source_time status")
            if item["status"] == "unavailable":
                _require(item["timestamp"] is None and item["age_seconds"] is None
                         and type(item["reason"]) is str and re.fullmatch(gap, item["reason"]), "source_time gap")
            else:
                _utc(item["timestamp"])
                _require(_number(item["age_seconds"]) and item["reason"] is None, "source_time age")
        span = value["spans"][symbol]
        _keys(span, "seconds valid_fields", "source_time span")
        _require(_integer(span["valid_fields"], 0, 4), "source_time valid_fields")
        _require(span["seconds"] is None if span["valid_fields"] < 2
                 else _number(span["seconds"]) and span["seconds"] >= 0, "source_time span seconds")



def _journal_times(value):
    _keys(value, "basis trade_count first_entry_at last_exit_at", "journal source_time")
    _require(value["basis"] == "supplied_trade_times" and _integer(value["trade_count"], 0, 1000), "journal time basis/count")
    if value["trade_count"] == 0:
        _require(value["first_entry_at"] is None and value["last_exit_at"] is None, "empty journal times")
    else:
        _utc(value["first_entry_at"])
        _utc(value["last_exit_at"])
        _require(datetime.fromisoformat(value["first_entry_at"]) <= datetime.fromisoformat(value["last_exit_at"]), "journal time order")


def _feed_times(value, parameters, fetched, source):
    _keys(value, "status retrieved_at published_at", "feed source_time")
    status = value["status"]
    _require(status in ("available", "empty", "invalid", "unavailable"), "feed status")
    stamps = value["published_at"]
    _require(type(stamps) is list and len(stamps) <= parameters["limit"], "feed publication times")
    _require(bool(stamps) if status == "available" else not stamps, "feed status/times")
    for stamp in stamps:
        _utc(stamp)
    if status == "unavailable":
        _require(fetched and source["hash_state"] in ("read_failed", "too_large"), "incomplete fetch input")
    else:
        _require(source["hash_state"] == "complete", "parsed feed input")
    if fetched and status != "unavailable":
        _utc(value["retrieved_at"])
    else:
        _require(value["retrieved_at"] is None, "unobserved retrieval time")


def _seed_stop(record):
    reason = record["outcome"]["reason"]
    source, times = record["inputs"][0], record["source_time"]
    if reason in ("input_unreadable", "input_too_large", "invalid_parameters"):
        expected = {"input_unreadable": "read_failed", "input_too_large": "too_large", "invalid_parameters": "not_read"}[reason]
        _require(source["hash_state"] == expected and times is None, "stopped input evidence")
        if reason == "invalid_parameters":
            _require(record["parameters"] is None, "unvalidated parameters")
    elif reason == "fixture_changed":
        _require(record["mode"] == "offline_synthetic" and source["hash_state"] == "complete"
                 and record["parameters"] is not None and times is None
                 and record["outputs"][0]["state"] == "not_written", "changed fixture evidence")
    elif reason == "invalid_journal":
        _require(source["hash_state"] == "complete" and times is None and record["parameters"] is not None, "invalid journal evidence")
    elif reason in ("invalid_feed", "source_unavailable"):
        _require(times is not None and times["status"] == ("invalid" if reason == "invalid_feed" else "unavailable"), "stopped feed evidence")

def validate_record(record):
    """Validate v1 assertions, not their truth; perform no provenance or file I/O."""
    _keys(record, "schema_version experiment_id mode lab kit inputs execution parameters source_time usage outputs outcome limits", "root")
    _require(type(record["schema_version"]) is int and record["schema_version"] == 1, "schema_version")
    experiment, mode = record["experiment_id"], record["mode"]
    _require(experiment in ("watchlist-investigator", "journal-reviewer", "market-brief"), "experiment")
    watchlist = experiment == "watchlist-investigator"
    journal = experiment == "journal-reviewer"
    allowed_modes = ("offline_synthetic",) if watchlist else (("offline_synthetic", "offline_supplied") if journal
                                                           else ("offline_synthetic", "offline_supplied", "public_fetch"))
    _require(mode in allowed_modes, "experiment/mode")
    fetched = mode == "public_fetch"
    lab, kit = record["lab"], record["kit"]
    _keys(lab, "revision state", "lab")
    _require(lab["state"] in ("clean", "dirty", "unknown"), "lab state")
    _require(_hash(lab["revision"], 40) or lab["revision"] is None and lab["state"] == "unknown", "lab revision")
    if watchlist:
        _keys(kit, "required_revision observed_revision verification", "kit")
        _require(_hash(kit["required_revision"], 40), "required Kit revision")
        _require(kit["observed_revision"] is None or _hash(kit["observed_revision"], 40), "observed Kit revision")
        state = kit["verification"]
        _require(state in ("verified", "revision_mismatch", "dirty", "not_checked", "read_failed"), "Kit verification")
        if state in ("verified", "dirty", "revision_mismatch"):
            _require(kit["observed_revision"] is not None and
                     ((kit["observed_revision"] == kit["required_revision"]) == (state != "revision_mismatch")), "Kit verification/revision")
        if state == "not_checked":
            _require(kit["observed_revision"] is None, "unchecked Kit revision")
    else:
        _require(kit is None, "Kit is not used")
    _require(type(record["inputs"]) is list and len(record["inputs"]) == 1, "inputs")
    source = record["inputs"][0]
    _keys(source, "role sha256 hash_state", "input")
    role = "synthetic_fixture" if watchlist else "journal_csv" if journal else "fed_press_xml"
    _require(source["role"] == role and source["hash_state"] in ("complete", "too_large", "read_failed", "not_read"), "input state")
    _require(_hash(source["sha256"], 64) if source["hash_state"] == "complete" else source["sha256"] is None, "input hash")
    execution = record["execution"]
    _keys(execution, "started_at finished_at", "execution")
    _utc(execution["started_at"])
    if execution["finished_at"] is not None:
        _utc(execution["finished_at"])
    parameters = record["parameters"]
    if parameters is not None:
        if watchlist:
            _keys(parameters, "symbols reference_time max_age_seconds", "parameters")
            symbols = parameters["symbols"]
            _require(type(symbols) is list and 1 <= len(symbols) <= 100
                     and all(type(s) is str and re.fullmatch(r"[A-Z][A-Z0-9.-]{0,11}", s) for s in symbols)
                     and len(set(symbols)) == len(symbols), "symbols")
            _utc(parameters["reference_time"])
            _require(_integer(parameters["max_age_seconds"], 0, 86400), "max_age_seconds")
        elif journal:
            _keys(parameters, "", "journal parameters")
        else:
            _keys(parameters, "limit", "market parameters")
            _require(_integer(parameters["limit"], 1, 20), "market limit")
    if record["source_time"] is not None:
        if watchlist:
            _assessment(record["source_time"], parameters)
        else:
            _require(parameters is not None, "source_time requires parameters")
            if journal:
                _require(source["hash_state"] == "complete", "parsed journal input")
                _journal_times(record["source_time"])
            else:
                _feed_times(record["source_time"], parameters, fetched, source)
    usage = record["usage"]
    _keys(usage, "scope basis requests_attempted credits_reserved observed_billing model", "usage")
    known_basis = "known_public_fetch" if fetched else "known_offline_path"
    _require(usage["scope"] == "python_process" and usage["basis"] in (known_basis, "unknown"), "usage scope/basis")
    if usage["basis"] == "unknown":
        _require(usage["requests_attempted"] is None and usage["credits_reserved"] is None, "unknown usage counts")
    else:
        _require(_integer(usage["requests_attempted"], 0, 1 if fetched else 0)
                 and _integer(usage["credits_reserved"], 0, 0), "usage counts")
    if fetched and record["source_time"] is not None:
        _require(usage["basis"] == known_basis and usage["requests_attempted"] == 1, "fetch attempt evidence")
    _require(usage["observed_billing"] is None, "observed billing")
    _keys(usage["model"], "mode provider tokens", "model")
    _require(usage["model"] == {"mode": "none", "provider": None, "tokens": None}, "model usage")
    _require(type(record["outputs"]) is list and len(record["outputs"]) == 1, "outputs")
    output = record["outputs"][0]
    _keys(output, "role filename sha256 state", "output")
    _require(output["role"] == "report" and output["state"] in ("complete", "not_written", "write_failed", "partial"), "output state")
    name = output["filename"]
    _require(name is None and output["state"] == "not_written" or type(name) is str and 0 < len(name) <= 255
             and name not in (".", "..") and all(c.isprintable() and c not in "/\\:" for c in name), "output filename")
    _require(_hash(output["sha256"], 64) if output["state"] == "complete" else output["sha256"] is None, "output hash")
    outcome = record["outcome"]
    _keys(outcome, "status reason", "outcome")
    _require(outcome["status"] in ("completed", "stopped"), "outcome status")
    reasons = STOP_REASONS if watchlist else (
        "invalid_parameters input_unreadable input_too_large encoding_unsupported output_path_unprintable "
        "output_exists output_write_failed record_write_failed interrupted fixture_changed "
        + ("invalid_journal" if journal else "invalid_feed source_unavailable")
    ).split()
    _require(outcome["reason"] == "completed" if outcome["status"] == "completed" else outcome["reason"] in reasons, "outcome reason")
    if outcome["status"] == "completed":
        _require(parameters is not None and record["source_time"] is not None
                 and source["hash_state"] == output["state"] == "complete" and execution["finished_at"] is not None
                 and usage["basis"] == known_basis, "completed evidence")
        if watchlist:
            _require(state == "verified", "completed Kit evidence")
        elif not journal:
            _require(record["source_time"]["status"] in ("available", "empty"), "completed feed evidence")
    elif not watchlist:
        _seed_stop(record)
    limits = record["limits"]
    if watchlist:
        expected = {"fixture_bytes": 65536, "symbols": 100, "requests": 0, "credits": 0, "model_calls": 0, "output_no_overwrite": True}
    elif journal:
        expected = {"input_bytes": 1048576, "rows": 1000, "requests": 0, "credits": 0, "model_calls": 0, "output_no_overwrite": True}
    else:
        expected = {"input_bytes": 524288, "items": 100, "display_items": 20, "requests": 1 if fetched else 0, "credits": 0,
                    "model_calls": 0, "fetch_timeout_seconds": 10 if fetched else None, "output_no_overwrite": True}
    _keys(limits, expected, "limits")
    _require(all(type(limits[k]) is type(v) and limits[k] == v for k, v in expected.items()), "limits")
    return record


def parse_record(content):
    """Decode bounded UTF-8 bytes and validate one explicit experiment profile."""
    return validate_record(decode_record(content))
