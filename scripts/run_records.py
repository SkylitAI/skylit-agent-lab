"""Bounded inert JSON and the offline Watchlist run-record contract."""

import json
import math


MAX_RECORD_BYTES = 262144


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
