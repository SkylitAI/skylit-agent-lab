# Watchlist Investigator

Select symbols and save a fictional GEX, VEX and flow report through Agent Kit.
The fixture contains made-up SPY observations and deliberately omits QQQ. No
account, key, network call or model is used. This is an experimental offline
package, maintained by `@prodij`; no agent host or live service is certified.

Keep this package inside the full Lab checkout: it reuses
`scripts/probe_kit_watchlist.py`. Use Python 3.11+, Git, and an already available
clean Kit checkout at **`0f82039759ef4db9d5b3dbd90f52863f8074f2a6`**. This tested
baseline is not the final release pin. Nothing is installed or downloaded by
the command. Obtaining Kit while it is INTERNAL requires repository access.

From the Lab root, with Kit alongside Lab:

```sh
python3 -I -B experiments/watchlist-investigator/run.py --kit ../skylit-agent-kit
```

From any working directory, substitute your actual absolute checkout paths:

```sh
python3 -I -B /path/to/skylit-agent-lab/experiments/watchlist-investigator/run.py --kit /path/to/skylit-agent-kit --symbols QQQ,SPXW
```

Both commands print the saved file's absolute path. The default is this package's
ignored `reports/watchlist.md`; it is created with owner-only permissions on
POSIX. Existing files and final-path symlinks are refused. Choose a new path for
another run, for example `--output /path/to/new-report.md`. Explicit relative
`--kit`, `--fixture` and `--output` paths use your current working directory;
default fixture/output paths always use this package's directory. Custom output
destinations may not be ignored by Git; keep local reports out of commits.

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
Zero requests and credits are used. There is no live mode, price chart, freshness
check, temporal comparison, trading signal or order execution in this package.

The fixture was independently authored using the pinned Kit's consumed fields;
SkylitAI dedicates it to CC0-1.0. Code is MIT licensed. No private source,
proprietary calculation or reconstructed score is included.

From the Lab root, run the package's behavior tests with a local Kit checkout:

```sh
SKYLIT_AGENT_KIT=../skylit-agent-kit python3 -m unittest discover -s tests -p test_watchlist_investigator.py -v
```

Tests use real Kit with socket operations and credential prompts blocked.
Checked 2026-10-01 on Darwin 25.6.0 arm64 with Python 3.11.14 and 3.14.5: all
47 Lab tests passed, including the seven package tests.
Without a local Kit checkout, five integration tests visibly skip; two setup
checks still run. That leaves runtime integration unverified. No CI credentials
or downloads are added. Explicit temporal evidence and run records are later
increments.
