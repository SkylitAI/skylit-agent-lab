"""Compare Kit-parsed source times against an explicitly fictional reference."""

from datetime import datetime, timezone


def _timestamp(value):
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.astimezone(timezone.utc) if parsed.tzinfo is not None else None
    except (TypeError, ValueError, OverflowError):
        return None


def parse_reference(value):
    parsed = _timestamp(value)
    if parsed is None:
        raise ValueError("Use --reference-time as a timezone-aware ISO 8601 timestamp.")
    return parsed


def parse_max_age(value):
    try:
        if value.isascii() and value.isdecimal() and 0 <= int(value) <= 86400:
            return int(value)
    except ValueError:
        pass
    raise ValueError("Use --max-age-seconds as an integer from 0 through 86400.")


def assess_times(result, reference, max_age_seconds):
    """Return JSON-compatible evidence from a parsed Kit result and validated options."""
    assessment = {"reference_time": reference.isoformat(), "max_age_seconds": max_age_seconds,
                  "symbols": list(result["symbols"]), "rows": {}, "spans": {}}
    for symbol in result["symbols"]:
        fields, times = {}, []
        for component, key in (("gamma", "as_of"), ("vanna", "as_of"),
                               ("flow", "generated_at"), ("flow", "latest_trade")):
            source = result["rows"][symbol][component]
            stamp = _timestamp(source.get(key))
            age = (reference - stamp).total_seconds() if stamp is not None else None
            status = ("unavailable" if age is None else "future" if age < 0
                      else "stale" if age > max_age_seconds else "within threshold")
            fields[f"{component}.{key}"] = {
                "timestamp": stamp.isoformat() if stamp is not None else None,
                "age_seconds": age, "status": status,
                "reason": f"timestamp missing or invalid; {source['status']}" if stamp is None else None,
            }
            if stamp is not None:
                times.append(stamp)
        assessment["rows"][symbol] = fields
        assessment["spans"][symbol] = {
            "seconds": (max(times) - min(times)).total_seconds() if len(times) >= 2 else None,
            "valid_fields": len(times),
        }
    return assessment


def _seconds(value):
    return str(value).removesuffix(".0") if value is not None else "unavailable"


def render_time_evidence(assessment):
    """Render the assessment without recalculating or reparsing source times."""
    lines = ["## Synthetic source-time evidence", "",
             f"Fictional reference time: {assessment['reference_time']}.",
             f"Demonstration maximum age: {assessment['max_age_seconds']} seconds.",
             "Age = reference minus source time. Negative age is future; age greater than the threshold is stale; otherwise within threshold.",
             "Missing or invalid times are unavailable and excluded from the span.",
             "Times describe different measurements; even a zero span does not establish an atomic snapshot, market freshness or session alignment.", "",
             "| Symbol | Source field | Time (UTC) | Age (seconds) | Evidence |",
             "|---|---|---|---:|---|"]
    for symbol in assessment["symbols"]:
        for field, value in assessment["rows"][symbol].items():
            lines.append(f"| {symbol} | {field} | {value['timestamp'] or 'unavailable'} | "
                         f"{_seconds(value['age_seconds'])} | {value['reason'] or value['status']} |")
    lines.append("")
    for symbol in assessment["symbols"]:
        span = assessment["spans"][symbol]
        count = span["valid_fields"]
        description = (f"{_seconds(span['seconds'])} seconds across {count} valid fields."
                       if span["seconds"] is not None else f"unavailable ({count} valid fields; need at least 2).")
        lines.append(f"- {symbol}: observed timestamp span {description}")
    return "\n".join(lines) + "\n"
