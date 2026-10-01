# Closed paper-journal input

[`parse_journal(content)`](../scripts/paper_journal.py) validates an in-memory
UTF-8 CSV and returns closed, fictional USD cash-equity trades for later exact
arithmetic. It performs no file access, network calls, calculations, reporting or
order execution. This is parser preparation; no journal workflow is implemented.
There is no CLI or file loader. A future caller must bound file reads before
passing bytes, for example reading at most `MAX_BYTES + 1` from an already-open
regular file. The parser cannot undo an unbounded read by its caller.

Each row represents one fully closed paper trade with a single entry and exit.
Quantity is shares, prices are USD per share, and fees are the total explicitly
entered USD fees for that trade. `short` records direction only. The parser does
not model borrow costs, margin, availability, partial exits, corporate actions,
options, FX, crypto, open positions or portfolios. Instrument type and currency
are caller declarations; ticker syntax does not verify an actual security.

## CSV contract

Input must be exactly `bytes`, at most **1,048,576 bytes**, containing at most
**1,000 data records**. Both limits are inclusive. UTF-8 decoding is strict;
a byte-order mark is not stripped. CSV uses comma delimiters, double-quoted
fields with doubled embedded quotes, and Python's `csv.reader(strict=True)`.
LF, CRLF and CR record endings are accepted; quoted notes may contain newlines.
Blank records are rejected. One final record terminator is allowed.

The following headers are required, case-sensitive and may appear in any order.
The only optional header is `notes`. Duplicate, unknown or missing headers and
rows of a different width are rejected. No cells or headers are whitespace-trimmed.

| Field | Accepted input and returned value |
|---|---|
| `symbol` | ASCII letter followed by 0–11 ASCII letters, digits, dots or hyphens; returned uppercase. |
| `asset_type` | Exactly `cash_equity`; retained as text. |
| `currency` | Exactly `USD`; retained as text. |
| `side` | Exactly `long` or `short`; retained as text. |
| `quantity` | Strictly positive decimal shares. |
| `entry_price`, `exit_price` | Strictly positive decimal USD per share. |
| `fees` | Nonnegative decimal USD, including `0`. |
| `entry_time`, `exit_time` | Aware ISO timestamps under the rule below; returned as UTC `datetime` objects. Exit must be at or after entry. |
| `notes` | Optional, at most **512 Unicode characters** after CSV decoding; retained exactly. Printable characters plus tab, CR and LF are allowed. Omitted notes become `""`. |

All four numeric fields return `Decimal` objects constructed directly from text,
without float conversion, rounding, or dependence on the active Decimal precision.
Accepted grammar is `(0|[1-9][0-9]{0,11})(\.[0-9]{1,8})?`: at most 12 integer
digits and 8 fractional digits, hence at most 20 digits and 21 characters.
Examples: `0`, `2.5`, `0.00000001`, `999999999999.99999999`. Trailing fractional
zeros are preserved. Signs, exponents, NaN/infinity, grouping separators, decimal
commas, Unicode digits, leading integer zeros and surrounding whitespace are
rejected. Future arithmetic must choose adequate Decimal precision explicitly;
parsing alone does not guarantee that later multiplication or sums avoid rounding.

Timestamps use `YYYY-MM-DDTHH:MM:SS`, optionally 1–6 fractional-second digits,
followed by `Z` or an explicit `+HH:MM`/`-HH:MM` offset (hours 00–23, minutes
00–59). Calendar and clock values must be valid and representable in UTC; leap
seconds, naive times and date-only values are rejected. Offset-equivalent entry
and exit instants are allowed. Times are supplied paper-trade data, not observed
execution times or claims about a market session. An empty exit price or time
is rejected as `closed_trade_required`; no missing exit is inferred.

Returned rows are ordinary dictionaries with exactly the eleven fields above,
in input record order. Repeated trades are preserved, not deduplicated. A valid
header with no trades returns `[]`, meaning **no trade observations**; empty bytes
are invalid. No P&L, zero result, score or recommendation is fabricated.

Notes remain untrusted local text even after validation. Formula-like text, URLs,
Markdown and instructions are not evaluated, followed or used as prompts. A later
renderer/exporter must escape them for its destination; parsing does not make
notes safe to execute, publish or open as spreadsheet formulas.

## Errors and verification

`JournalError(ValueError)` exposes `row`, `field` and `reason`. Row is the logical
CSV record number: header 1, first trade 2; quoted multiline notes still count as
one record. Input type/byte/UTF-8 errors use `row=None`. Only fixed known fields
and reasons are included, never source values, notes or paths. No partial list
is returned when any record fails.

Reasons are `expected_bytes`, `too_large`, `invalid_utf8`, `duplicate`, `unknown`,
`missing`, `malformed`, `row_width`, `too_many_rows`, `invalid_symbol`, `unsupported`,
`closed_trade_required`, `invalid_decimal`, `must_be_positive`, `invalid_time`,
`before_entry`, `too_long` and `invalid_control`. Malformed CSV, including the
standard reader's field-size rejection, uses field `csv`; header errors use
`header`. Multiple faults stop at the first validation failure.

From the Lab root, run `python3 -B -m unittest discover -s tests -p test_paper_journal.py -v`.
These tests need no Kit checkout, credentials, model or network. The independently
authored [LABA/LABB fixture](../examples/paper-journal-synthetic.csv) contains two
made-up long/short trades. SkylitAI dedicates this synthetic fixture to CC0-1.0;
it contains no copied strategy, account export or private source material.
