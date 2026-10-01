# Paper-journal calculations and review text

[`scripts/journal_report.py`](../scripts/journal_report.py) calculates supplied
closed paper-trade rows and renders a deterministic Markdown review. It uses
ordinary price-difference arithmetic and supplied notes. It performs no model
calls, network access, file access, order execution or strategy evaluation.
There is no journal CLI, package manifest or run-record integration yet.

## Input and exact results

Call `calculate_journal(rows)` with the unchanged output of
[`parse_journal(bytes)`](paper-journal-input.md). The parser's closed USD
cash-equity contract is the boundary: at most 1,000 rows, positive quantity and
prices, and nonnegative entered fees. The helper does not revalidate arbitrary
dictionaries or support other instruments. Each row is a single closed paper
trade, not a position to combine with other rows.

The returned dictionary has exactly `trades` and `total_net`. Each trade is a
new dictionary containing every normalized source field plus these `Decimal`
values:

| Value | Formula |
|---|---|
| Long gross USD | `(exit_price - entry_price) * quantity` |
| Short gross USD | `(entry_price - exit_price) * quantity` |
| Net USD | `gross - fees` |
| Total net USD | Sum of exact per-trade net values. |

Fees are the entered total USD fees for each trade. The helper does not infer
borrow costs, margin, dividends, splits, slippage, taxes or additional fees.
Repeated rows remain separate observations in input order. Source rows are not
modified; no float conversions, intermediate rounding or motive inference occurs.

All arithmetic runs in a separate explicit Decimal context with precision 50,
`ROUND_HALF_UP`, exponent bounds -999999 through 999999, and cleared traps/flags.
This ignores and preserves the caller's precision, rounding, exponent bounds,
traps and flags. Parser values have at most 12 integer and 8 fractional digits:
gross has at most 16 fractional digits, each absolute net is below `10^25`, and
the absolute sum of 1,000 nets is below `10^28`. At most 44 decimal digits are
therefore needed; precision 50 preserves every supported calculation exactly.
These guarantees apply to parser-normalized rows within its bounds.

Empty input returns `{"trades": [], "total_net": None}`. It means no trade
observations; it is not evidence of zero earnings or a measured performance.
No win rate, annualization, Sharpe ratio, strategy score or recommendation is added.

## Markdown and supplied notes

`render_journal(result, synthetic_fixture=False)` consumes that result and
returns Markdown ending in a newline. It reports trade count, source fields,
UTC entry/exit times, entered fees, gross/net and total net. Source quantities,
prices and fees retain their supplied decimal precision. Gross, net and total
displays round to USD cents with **ROUND_HALF_UP**: halfway values round away
from zero. Displayed negative zero becomes `0.00`; exact values remain unchanged.

The total is summed exactly **before** rounding. Two exact nets of `0.005`
display as `0.01` each, while their exact total `0.010` displays as `0.01`.
Displayed rows consequently need not add to the displayed total. Empty input
instead displays `Aggregate net P&L: unavailable` and no trade review questions.

The default source label is **supplied paper-trade input**. Paper/synthetic
status, instruments, fills, fees and times are caller declarations, not verified
facts or actual trading results. Only pass the Boolean `synthetic_fixture=True`
when the caller declares the input fictional; this changes the label to
**caller-declared fictional fixture**, without certifying that declaration.
The helper does not infer provenance from symbols, notes or arithmetic.

Empty notes display `unavailable; no reason supplied`. A supplied nonempty note
is rendered as inert text, followed by the fixed question, “What context would
you add to this supplied note?” It does not claim why the trade was made or
evaluate the note's content. ASCII punctuation is emitted as numeric character
references, preventing supplied Markdown/HTML/link syntax. Tabs, CR and LF become
visible `\t`, `\r`, `\n`; other nonprintable characters are escaped too. Notes
are never executed, fetched, interpreted as prompts, or used in calculations.
The underlying source note stays unchanged in the calculation result. This is
a Markdown display contract, not a safe spreadsheet-export format.

## Reproduction

The independently fictional [LABA/LABB fixture](../examples/paper-journal-synthetic.csv)
has exact nets **2.7125** and **2.05**, totaling **4.7625**. The reviewed
[expected Markdown](../examples/paper-journal-expected.md) displays **2.71**,
**2.05** and total **4.76** using the fictional-fixture label. The fixture's CC0
source declaration remains in the [input contract](paper-journal-input.md).

From the Lab root, run:

```sh
python3 -B -m unittest discover -s tests -p test_journal_report.py -v
```

The tests consume the local synthetic fixture, compare the exact output, and
check losing trades, fees, rounding, maximum supported bounds, hostile caller
Decimal contexts, empty journals and untrusted notes. No Kit or credentials are
needed. Passing these helpers does not establish an integrated journal workflow.
