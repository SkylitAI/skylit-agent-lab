"""Bounded inert JSON and the offline Watchlist run-record contract."""

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


def validate_record(record):
    """Validate v1 assertions, not their truth; perform no provenance or file I/O."""
    _keys(record, "schema_version experiment_id mode lab kit inputs execution parameters source_time usage outputs outcome limits", "root")
    _require(type(record["schema_version"]) is int and record["schema_version"] == 1, "schema_version")
    _require(record["experiment_id"] == "watchlist-investigator" and record["mode"] == "offline_synthetic", "experiment/mode")
    lab, kit = record["lab"], record["kit"]
    _keys(lab, "revision state", "lab")
    _require(lab["state"] in ("clean", "dirty", "unknown"), "lab state")
    _require(_hash(lab["revision"], 40) or lab["revision"] is None and lab["state"] == "unknown", "lab revision")
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
    _require(type(record["inputs"]) is list and len(record["inputs"]) == 1, "inputs")
    source = record["inputs"][0]
    _keys(source, "role sha256 hash_state", "input")
    _require(source["role"] == "synthetic_fixture" and source["hash_state"] in ("complete", "too_large", "read_failed", "not_read"), "input state")
    _require(_hash(source["sha256"], 64) if source["hash_state"] == "complete" else source["sha256"] is None, "input hash")
    execution = record["execution"]
    _keys(execution, "started_at finished_at", "execution")
    _utc(execution["started_at"])
    if execution["finished_at"] is not None:
        _utc(execution["finished_at"])
    parameters = record["parameters"]
    if parameters is not None:
        _keys(parameters, "symbols reference_time max_age_seconds", "parameters")
        symbols = parameters["symbols"]
        _require(type(symbols) is list and 1 <= len(symbols) <= 100
                 and all(type(s) is str and re.fullmatch(r"[A-Z][A-Z0-9.-]{0,11}", s) for s in symbols)
                 and len(set(symbols)) == len(symbols), "symbols")
        _utc(parameters["reference_time"])
        _require(_integer(parameters["max_age_seconds"], 0, 86400), "max_age_seconds")
    if record["source_time"] is not None:
        _assessment(record["source_time"], parameters)
    usage = record["usage"]
    _keys(usage, "scope basis requests_attempted credits_reserved observed_billing model", "usage")
    _require(usage["scope"] == "python_process" and usage["basis"] in ("known_offline_path", "unknown"), "usage scope/basis")
    for key in ("requests_attempted", "credits_reserved"):
        _require(_integer(usage[key], 0, 0) if usage["basis"] == "known_offline_path" else usage[key] is None, "usage counts")
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
    _require(outcome["reason"] == "completed" if outcome["status"] == "completed" else outcome["reason"] in STOP_REASONS, "outcome reason")
    if outcome["status"] == "completed":
        _require(parameters is not None and record["source_time"] is not None and state == "verified"
                 and source["hash_state"] == output["state"] == "complete" and execution["finished_at"] is not None
                 and usage["basis"] == "known_offline_path", "completed evidence")
    limits = record["limits"]
    expected = {"fixture_bytes": 65536, "symbols": 100, "requests": 0, "credits": 0, "model_calls": 0, "output_no_overwrite": True}
    _keys(limits, expected, "limits")
    _require(all(type(limits[k]) is type(v) and limits[k] == v for k, v in expected.items()), "limits")
    return record


def parse_record(content):
    """Decode bounded UTF-8 bytes and validate the full offline record contract."""
    return validate_record(decode_record(content))
