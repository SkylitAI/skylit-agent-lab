# Watchlist Investigator

Select symbols and save a fictional GEX, VEX and flow report through Agent Kit.
The fixture contains made-up SPY observations and deliberately omits QQQ. No
account, key, network call or model is used. This is an experimental offline
package, maintained by `@prodij`; no agent host or live service is certified.

Keep this package inside the full Lab checkout: it reuses
`scripts/probe_kit_watchlist.py`. Use Python 3.11+, Git, and a clean Kit checkout
at **`0f82039759ef4db9d5b3dbd90f52863f8074f2a6`**. This tested baseline is not
the final release pin. Obtaining Kit while it is INTERNAL requires repository
access; rendering after setup needs no network or service credentials.

From the Lab root, obtain Kit in a **new directory** and run the experiment:

```sh
git clone --no-checkout https://github.com/SkylitAI/skylit-agent-kit.git ../skylit-agent-kit-watchlist &&
git -C ../skylit-agent-kit-watchlist checkout --detach 0f82039759ef4db9d5b3dbd90f52863f8074f2a6 &&
python3 -X utf8 -I -B experiments/watchlist-investigator/run.py --kit ../skylit-agent-kit-watchlist
```

Use a POSIX shell or PowerShell 7 for this chained command. On Windows, replace
`python3` with `py -3`. If `../skylit-agent-kit-watchlist` already exists, choose
a different new directory and replace that path in all three lines. The `&&`
operators ensure checkout runs only after cloning succeeds, and rendering runs
only after checkout succeeds. Do not reset or repurpose an existing checkout.

For another run from any working directory, substitute your actual absolute
checkout paths and choose a new output filename:

```sh
python3 -X utf8 -I -B /path/to/skylit-agent-lab/experiments/watchlist-investigator/run.py --kit /path/to/skylit-agent-kit-watchlist --symbols QQQ,SPXW --output /path/to/new-watchlist-report.md
```

Both commands print the saved file's absolute path. The default is this package's
ignored `reports/watchlist.md`; it is created with owner-only permissions on
POSIX. Existing files and final-path symlinks are refused. Choose a new path for
another run, for example `--output /path/to/new-report.md`. Explicit relative
`--kit`, `--fixture` and `--output` paths use your current working directory;
default fixture/output paths always use this package's directory. Custom output
destinations may not be ignored by Git; keep local reports out of commits.

Keep `-X utf8` in the command: the pinned Kit writer uses Python's default text
encoding. The runner rejects a non-UTF-8 default before creating any output or
parent directory. If stdout cannot display the output path, it also stops before
writing; use UTF-8 stdout or choose an ASCII output path.

The default report contains:

| Symbol | Gamma | Vanna | Flow |
|---|---|---|---|
| SPY | source king: 110 / -180 | largest returned magnitude: 115 / 60 | 1 trade; $650; source scores unavailable |
| QQQ | missing from heatmap response | missing from heatmap response | missing from synthetic fixture |

Change `--symbols` or a value in `fixture.json`, then use a new output filename.
Kit normalizes and deduplicates symbols; missing SPXW is never replaced by SPX.
Use `--fixture PATH` for another **synthetic** UTF-8 JSON fixture of at most
64 KiB. The `gamma`, `vanna` and ticker-keyed `flow` envelopes follow the
[consumer interface](../../docs/kit-consumer.md). Kit parses and renders them;
Lab supplies the synthetic context. Validation/rendering finish before the
output is opened, so invalid inputs cannot create or truncate a report.

Success exits 0. Missing CLI arguments exit 2; source, Kit and output failures
exit 1 with an actionable `error:` on stderr. A wrong Kit revision or dirty
checkout is rejected; review local changes and supply the exact pin. Missing/malformed
component fields may become explicit gaps according to Kit's parser.

Every number and timestamp is fictional, including the fixed report date/time.
The unchanged Kit renderer's REST/retrieval wording refers to fixture data here.
Zero requests and credits are used. There is no live mode, price chart, trading
signal or order execution in this package. Time comparisons below apply only to
the declared fictional reference and source fields.

The fixture was independently authored using the pinned Kit's consumed fields;
SkylitAI dedicates it to CC0-1.0. Code is MIT licensed. No private source,
proprietary calculation or reconstructed score is included.

The report adds a **synthetic source-time evidence** section after Kit's unchanged
values and component statuses. It compares `gamma.as_of`, `vanna.as_of`,
`flow.generated_at` and `flow.latest_trade` separately against the declared
fictional `--reference-time` (default `2026-10-01T14:01:00+00:00`). It never uses
the wall clock or the renderer's descriptive retrieval-time string as evidence.
Change the reference and demonstration threshold explicitly, using a new output:

```sh
python3 -X utf8 -I -B /path/to/skylit-agent-lab/experiments/watchlist-investigator/run.py --kit /path/to/skylit-agent-kit-watchlist --reference-time 2026-10-01T14:10:00+00:00 --max-age-seconds 300 --output /path/to/time-evidence.md
```

The reference must be timezone-aware ISO 8601. `--max-age-seconds` accepts a
nonnegative decimal integer from **0 through 86400**, default **900**; this is an
adjustable demonstration limit, not market or trading guidance. Age is reference
minus source time in seconds: negative is **future**, greater than the threshold
is **stale**, and zero through equality is **within threshold**. Offset-aware
times are normalized to UTC. Missing/invalid times are **unavailable**, with Kit's
component reason retained; they never become zero or another source's time.

For each symbol, the observed timestamp span is maximum minus minimum across
available fields, requiring at least two valid times. Boards, response generation
and latest trades describe different measurements. Even a zero span establishes
neither an atomic snapshot nor market freshness or session alignment. The default
SPY ages are 360, 420, 300 and 330 seconds respectively, with a 120-second span;
QQQ's times and span are unavailable. Parsed rows are shared by both renderers;
the structured assessment can be reused without scraping Markdown.

From the Lab root, run the package's behavior tests with a local Kit checkout:

```sh
SKYLIT_AGENT_KIT=../skylit-agent-kit-watchlist python3 -X utf8 -m unittest discover -s tests -p 'test_watchlist*.py' -v
```

For PowerShell, set `$env:SKYLIT_AGENT_KIT = '../skylit-agent-kit-watchlist'`
first, then run `py -3 -X utf8 -m unittest discover -s tests -p 'test_watchlist*.py' -v`.

Tests use real Kit with socket operations and credential prompts blocked.
Encoding regressions force `LC_ALL=C` and explicit `-X utf8=0` / `-X utf8`, checking
refusal before output creation, exact UTF-8 bytes, permissions and no overwrite.
Checked 2026-10-01 on Darwin 25.6.0 arm64 with Python 3.11.14 and 3.14.5:
all 60 Lab tests passed, including the twelve package tests and six source-time tests.
Without a local Kit checkout, nine package integration tests visibly skip; three setup
checks still run. That leaves runtime integration unverified. CI receives no Kit
credentials and does not download Kit. Source-time arithmetic tests run without Kit;
host verification and run records remain later increments.
