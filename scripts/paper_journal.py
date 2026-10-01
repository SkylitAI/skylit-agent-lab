"""Parse bounded closed USD cash-equity paper trades; no I/O or calculations."""

import csv
from datetime import datetime, timezone
from decimal import Decimal
import io
import re


MAX_BYTES = 1048576
MAX_ROWS = 1000
MAX_NOTES = 512
HEADERS = "symbol asset_type currency side quantity entry_price exit_price fees entry_time exit_time".split()
DECIMAL = re.compile(r"(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,8})?")
TIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
                  r"(?:\.[0-9]{1,6})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])")


class JournalError(ValueError):
    """Safe logical CSV row, known field and fixed reason; never source values."""

    def __init__(self, row, field, reason):
        self.row, self.field, self.reason = row, field, reason
        location = "input" if row is None else f"row {row}"
        super().__init__(f"Journal {location}: {field}: {reason}.")


def _time(value, row, field):
    result = None
    if TIME.fullmatch(value):
        try:
            result = datetime.fromisoformat(value).astimezone(timezone.utc)
        except (ValueError, OverflowError):
            pass
    if result is None:
        raise JournalError(row, field, "invalid_time")
    return result


def _trade(values, row):
    symbol = values["symbol"]
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9.-]{0,11}", symbol):
        raise JournalError(row, "symbol", "invalid_symbol")
    values["symbol"] = symbol.upper()
    for field, allowed in (("asset_type", ("cash_equity",)), ("currency", ("USD",)), ("side", ("long", "short"))):
        if values[field] not in allowed:
            raise JournalError(row, field, "unsupported")
    for field in ("exit_price", "exit_time"):
        if not values[field]:
            raise JournalError(row, field, "closed_trade_required")
    for field in ("quantity", "entry_price", "exit_price", "fees"):
        if not DECIMAL.fullmatch(values[field]):
            raise JournalError(row, field, "invalid_decimal")
        values[field] = Decimal(values[field])
        if field != "fees" and values[field] == 0:
            raise JournalError(row, field, "must_be_positive")
    for field in ("entry_time", "exit_time"):
        values[field] = _time(values[field], row, field)
    if values["exit_time"] < values["entry_time"]:
        raise JournalError(row, "exit_time", "before_entry")
    notes = values.setdefault("notes", "")
    if len(notes) > MAX_NOTES:
        raise JournalError(row, "notes", "too_long")
    if any(not char.isprintable() and char not in "\t\r\n" for char in notes):
        raise JournalError(row, "notes", "invalid_control")
    return values


def parse_journal(content):
    """Return normalized dictionaries, or raise JournalError without partial rows.

    Header is logical row 1. Numbers remain Decimal; aware times become UTC
    datetime objects. Optional notes are unchanged text, defaulting to empty.
    """
    if type(content) is not bytes:
        raise JournalError(None, "journal", "expected_bytes")
    if len(content) > MAX_BYTES:
        raise JournalError(None, "journal", "too_large")
    decoded = None
    try:
        decoded = content.decode("utf-8")
    except UnicodeError:
        pass
    if decoded is None:
        raise JournalError(None, "journal", "invalid_utf8")
    reader = csv.reader(io.StringIO(decoded, newline=""), strict=True)
    row = 1
    try:
        headers = next(reader, [])
        if len(set(headers)) != len(headers):
            raise JournalError(row, "header", "duplicate")
        if set(headers) - set(HEADERS + ["notes"]):
            raise JournalError(row, "header", "unknown")
        if set(HEADERS) - set(headers):
            raise JournalError(row, "header", "missing")
        result = []
        row = 2
        for cells in reader:
            if row > MAX_ROWS + 1:
                raise JournalError(row, "journal", "too_many_rows")
            if len(cells) != len(headers):
                raise JournalError(row, "csv", "row_width")
            result.append(_trade(dict(zip(headers, cells)), row))
            row += 1
        return result
    except csv.Error:
        pass
    raise JournalError(row, "csv", "malformed")
