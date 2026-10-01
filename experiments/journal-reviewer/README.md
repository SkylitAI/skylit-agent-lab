# Journal Reviewer

Save a local Markdown review of closed USD cash-equity paper trades. The default
uses two bundled fictional LABA/LABB trades. Custom input stays labeled as
supplied paper input; it is not verified as fictional or actual trading history.
No Kit, credentials, network, model, upload or order execution is involved.
The package is experimental, maintained by `@prodij`, with no certified agent host.

Keep the package inside the full Lab checkout. It reuses the existing
[CSV parser](../../docs/paper-journal-input.md) and
[calculation/report helper](../../docs/paper-journal-calculations.md).
With Python 3.11+, run from the Lab root:

```sh
python3 -X utf8 -I -B experiments/journal-reviewer/run.py
```

The command saves `experiments/journal-reviewer/reports/journal.md` and the adjacent
`journal.md.run.json`, then prints both absolute paths. The default directory is
ignored by Git. Both files are created exclusively with mode `0600` on POSIX.
Existing files, hard links and final-path symlinks are refused. Choose a new
output for every run:

```sh
python3 -X utf8 -I -B /path/to/skylit-agent-lab/experiments/journal-reviewer/run.py --output /path/to/new-journal-review.md
```

That absolute-script command works from any working directory. To review your
own **paper** CSV, explicitly supply `--input` and choose a private destination:

```sh
python3 -X utf8 -I -B /path/to/skylit-agent-lab/experiments/journal-reviewer/run.py --input /path/to/paper-trades.csv --output /path/to/new-paper-review.md
```

Explicit relative paths use the current working directory. Default paths use
this package's directory. Custom destinations may not be ignored by Git; keep
private inputs and reports out of commits. Parent-directory symlinks are not an
isolation boundary. Output is encoded explicitly as UTF-8 with LF newlines.
`-X utf8` also makes displaying non-ASCII destination paths predictable.
Every character in the absolute output path must be printable; control characters
are rejected before creating a file or parent directory. Ordinary Unicode paths work.
The report basename must be at most 255 characters, without colon or backslash,
to fit the run-record contract; filesystem filename limits also apply.

The bundled [`fixture.csv`](fixture.csv) is a byte-identical CC0-1.0 copy of the
shared [synthetic source](../../examples/paper-journal-synthetic.csv). The runner
checks its known byte hash before using the fictional label; an edited default
(including changed line endings) must be passed explicitly with `--input` or
restored to the bundled copy.
Every explicit `--input`, including the bundled path, is labeled **supplied
paper-trade input**. The parser verifies neither provenance declaration.

Input must be a regular readable file, at most **1 MiB** and **1,000 closed
trades**, following the linked CSV contract. The runner reads a single bounded
buffer, then parses, calculates and renders it before creating the report. A FIFO,
directory, malformed CSV, open trade or unsupported instrument is rejected.
No input/output alias is overwritten. A header-only journal reports no
observations and unavailable aggregate P&L.

The default [expected report](../../examples/paper-journal-expected.md) has exact
nets `2.7125` and `2.05`, total `4.7625`; USD-cent displays are `2.71`, `2.05` and
`4.76`. Totals are summed exactly before display rounding. Source values, UTC
times and entered fees stay visible. Supplied notes are escaped inert text with
a fixed review question; absent notes remain unavailable. No motives, borrow
costs, dividends, splits, slippage, tax or strategy scores are inferred.

To try a synthetic fee change from the Lab root, copy
`experiments/journal-reviewer/fixture.csv` to an unused local file such as
`paper-fees.csv`. In the copy, change LABA's `fees` from `0.10` to `1.10`, leaving
the other fields unchanged. Keep the copy uncommitted and choose a new output:

```sh
python3 -X utf8 -I -B experiments/journal-reviewer/run.py --input paper-fees.csv --output experiments/journal-reviewer/reports/fee-review.md
```

The exact total becomes `3.7625`, displayed as `3.76`. Because `--input` is explicit,
the report labels this as supplied paper input even though you copied the fixture.

Success exits **0** and prints both saved paths. Invalid CLI syntax exits **2**;
input, setup and output failures exit **1** with controlled stderr. Diagnostics
identify safe parser rows/fields or an actionable file problem without echoing
CSV values, notes, paths or raw exceptions. With a usable output path, invalid,
unreadable, oversized or changed bundled input saves a **stopped record only**;
this may create the output parent directory. Invalid CLI syntax, missing helpers
or output-path/stdout preflight failures stop before artifacts and have no record.

The private [Journal run-record profile](../../docs/run-record.md#journal-and-market-profiles)
records the exact consumed input hash, the exact persisted report-byte hash,
real UTC execution times, offline process usage and an observation of Lab's Git
state before creating artifacts. Dirty Lab state does not assert equivalence to
committed bytes, and this observation is not a snapshot. The record has `kit: null`
and `{}` parameters. Its source evidence is only the trade count, earliest entry
and latest exit in UTC; empty input has zero count and unavailable endpoints.
Source times are supplied data, separate from actual execution times. No input
paths, symbols, notes or financial values are stored in the sidecar. Even the
aggregate times and count are private: keep sidecars local. Recorded zero requests
and reservations describe this known offline Python process; billing and model
tokens remain unknown, and launching-host usage is outside its scope.

The sidecar is reserved first. An existing sidecar prevents report writing; an
existing report is preserved with a stopped `output_exists` record. The two writes
are **not atomic**. Write, flush, close or process failure can leave partial files;
no failure silently deletes artifacts. A failed record rewrite can leave JSON
marked completed even though the command failed. Check **exit status as well as
record contents** and choose a new output after resolving a failure. A failure to
print completion also exits 1 although both artifacts may already exist.
Evaluation cases and host verification remain pending.

From the Lab root, run the subprocess tests:

```sh
python3 -B -m unittest discover -s tests -p 'test_journal_*.py' -v
```

The tests use isolated Python, block sockets and credential prompts, compare the
complete golden output and exercise custom input, file limits, FIFO rejection,
aliases, permissions, exact hashes, private metadata and report/record write
failures. They need no Kit checkout or network.
