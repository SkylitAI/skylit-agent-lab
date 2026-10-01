"""Exact closed paper-trade arithmetic and Markdown from normalized journal rows."""

from decimal import Context, Decimal, ROUND_HALF_UP, localcontext
import string


# Parser bounds require at most 44 digits for 1,000 exact net values summed.
_CONTEXT = Context(prec=50, rounding=ROUND_HALF_UP, Emin=-999999, Emax=999999,
                   capitals=1, clamp=0, flags=[], traps=[])


def calculate_journal(rows):
    """Copy validated parse_journal rows, adding exact gross/net and total_net.

    This consumes the parser's bounded contract; it does not validate arbitrary
    dictionaries. Empty input means no observations and an unavailable total.
    """
    trades = []
    with localcontext(_CONTEXT):
        for row in rows:
            difference = (row["exit_price"] - row["entry_price"] if row["side"] == "long"
                          else row["entry_price"] - row["exit_price"])
            gross = difference * row["quantity"]
            trades.append(dict(row, gross=gross, net=gross - row["fees"]))
        total = sum((trade["net"] for trade in trades), Decimal(0)) if trades else None
    return {"trades": trades, "total_net": total}


def _money(value):
    with localcontext(_CONTEXT):
        rounded = value.quantize(Decimal("0.01"))
        return "0.00" if rounded == 0 else format(rounded, ".2f")


def _escaped_note(text):
    parts = []
    for char in text:
        if not char.isprintable():
            char = {"\t": r"\t", "\r": r"\r", "\n": r"\n"}.get(char, f"\\u{ord(char):04x}")
        parts.extend(f"&#{ord(item)};" if item in string.punctuation else item for item in char)
    return "".join(parts)


def render_journal(result, *, synthetic_fixture=False):
    """Render calculate_journal output; fixture provenance is a caller declaration."""
    if type(synthetic_fixture) is not bool:
        raise ValueError("synthetic_fixture must be a boolean.")
    source = "caller-declared fictional fixture" if synthetic_fixture else "supplied paper-trade input"
    trades = result["trades"]
    lines = ["# Paper-journal review", "", f"Source: {source}.",
             "Paper/synthetic status, instruments, fills, fees and times are not independently verified.",
             "Calculations describe the supplied rows; they do not establish actual trading results.",
             "", f"Trade count: {len(trades)}", ""]
    if not trades:
        return "\n".join(lines + ["No trade observations. Aggregate net P&L: unavailable.", ""])
    lines += [f"Total net (USD): {_money(result['total_net'])}", "",
              "Gross and net displays use USD cents with ROUND_HALF_UP; the total is summed exactly before rounding.",
              "Displayed trade amounts may not add to the displayed total. Source values retain their supplied precision.",
              "Fees are entered totals. No borrow costs, dividends, splits, slippage or tax are inferred.", ""]
    for number, trade in enumerate(trades, 1):
        lines += [f"## Trade {number}: {trade['symbol']} ({trade['side']})", "",
                  f"- Asset type: {trade['asset_type']}; currency: {trade['currency']}.",
                  f"- Quantity (shares): {format(trade['quantity'], 'f')}",
                  f"- Entry price (USD/share): {format(trade['entry_price'], 'f')}; time (UTC): {trade['entry_time'].isoformat()}",
                  f"- Exit price (USD/share): {format(trade['exit_price'], 'f')}; time (UTC): {trade['exit_time'].isoformat()}",
                  f"- Entered fees (USD): {format(trade['fees'], 'f')}",
                  f"- Gross (USD): {_money(trade['gross'])}",
                  f"- Net (USD): {_money(trade['net'])}", ""]
        if trade["notes"]:
            lines += [f"Supplied note (inert text): {_escaped_note(trade['notes'])}", "",
                      "Review question: What context would you add to this supplied note?", ""]
        else:
            lines += ["Supplied note: unavailable; no reason supplied.", ""]
    return "\n".join(lines)
