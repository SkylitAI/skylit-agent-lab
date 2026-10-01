# Render a synthetic watchlist through pinned Kit

This T07 probe turns local fictional responses into a Markdown report using
Kit's existing Python functions. It proves the consumption path for a later
`experiments/watchlist-investigator` package. It is not that experiment yet.

Use Python 3.11+, Git, and an already available clean checkout of
`https://github.com/SkylitAI/skylit-agent-kit` at
**`0f82039759ef4db9d5b3dbd90f52863f8074f2a6`**. This is the tested starting
baseline, not a final release pin. Runtime imports are the standard library and
this Kit checkout; no installation, network, account, key or model is required.
Obtaining Kit while its repository is INTERNAL separately requires repository
access.

From the Lab root, with Kit in the sibling directory:

```sh
python3 -I -B scripts/probe_kit_watchlist.py --kit ../skylit-agent-kit
python3 -I -B scripts/probe_kit_watchlist.py --kit ../skylit-agent-kit --symbols qqq,SPXW,qqq
SKYLIT_AGENT_KIT=../skylit-agent-kit python3 -m unittest discover -s tests -p test_kit_consumer.py -v
```

For another local checkout, substitute its path in both `--kit` and
`SKYLIT_AGENT_KIT`. The probe checks HEAD and rejects visible tracked/untracked
changes before importing Kit. Git-ignored files are not an integrity check, and
these checks are not a sandbox. Run only a trusted checkout. `-I` excludes user
site packages and ambient Python import paths; `-B` avoids bytecode writes.

## Observed interface

| Input / call | Output or failure |
|---|---|
| `--kit PATH` | Required local repository root; wrong revision or visible changes exit 1 before rendering. Nothing is fetched or installed. |
| `--symbols TEXT` → `symbols_list(TEXT)` | Defaults to `SPY,QQQ`; Kit uppercases, deduplicates in order and validates tickers. `qqq,SPXW,qqq` becomes QQQ then SPXW, with no SPX substitution. |
| `--fixture PATH` | Defaults to [kit-watchlist.json](../examples/kit-watchlist.json). UTF-8 JSON with `gamma`, `vanna` and `flow` objects. This is the probe's synthetic envelope, not Kit's live raw-export format. |
| `parse_heatmap(envelope, symbols, metric)` | `gamma`/`vanna` each contain `data.symbols` and matching `meta.metric`; Kit preserves source nodes, times and expirations, and marks omitted symbols missing. |
| `parse_flow(envelope, symbol)` | `flow` maps tickers to envelopes containing `data.ticker`, `timeframe: "1d"`, `trades` and `meta`. An empty trade list remains empty; omitted source scores remain unavailable. |
| Missing flow envelope | Lab passes `missing("missing from synthetic fixture")`; no zero totals or trades are invented. |
| `render_report(result)` | Markdown string. Lab supplies selected symbols, parsed rows, fictional report time/date, stop reason, flow limit, empty source list, and zero request/credit counters. Kit owns all formatting and node selection. |

Success exits 0 and writes only stdout; failures exit 1 with `error:` on stderr
and no partial report. Argument-parser errors exit 2. Observed failures include
wrong revision, invalid symbols, malformed JSON/top-level input and a gamma
envelope labeled vanna (`Heatmap response has invalid shape or wrong metric.`).
Malformed fields within an otherwise valid Kit response can produce visible
gaps instead of rejecting the whole report. This is a synthetic interface probe,
not a comprehensive untrusted-file validator or stable external API guarantee.

The complete captured result is [kit-watchlist.expected.md](../examples/kit-watchlist.expected.md).
Its overview is:

| Symbol | Gamma | Vanna | Flow |
|---|---|---|---|
| SPY | source king: 100 / -250 | largest returned magnitude: 105 / 40 | 0 trades; $0; no trades returned |
| QQQ | missing from heatmap response | missing from heatmap response | missing from synthetic fixture |

Every value and timestamp is fictional. Kit's unchanged report says “Source
values from REST” and “Retrieval started”; the prominent synthetic prefix and
fixture-time label qualify those fields. No REST call occurred. The report ends
with `0 requests attempted; 0 documented credits reserved for attempts`.
It performs no freshness, session-alignment or chart-context verification.

## Reproduction evidence and limits

Recorded 2026-10-01 against the exact Kit SHA above: Python 3.14.5, Darwin 25.6.0
arm64. Initial tests failed before the probe/fixture existed (four failures,
two missing-fixture errors). After implementation, all six passed with no skips.
The subprocesses use isolated Python, an environment containing only a standard
`PATH`, closed stdin, blocked Python socket operations and blocked key prompts.
They render real Kit code and check changed input, selection, gaps and errors.
This is local offline Python evidence, not agent-host or live-service support.
All 36 Lab tests, manifest validation and compilation passed. A fresh default
probe output matched the captured Markdown exactly.

Basic Lab checks do not require Kit. The tests look for `SKYLIT_AGENT_KIT` or a
sibling checkout; if absent, five real-Kit tests visibly skip and the wrong-pin
test still runs. **A skipped run leaves Kit consumption unverified.** No CI token,
clone or download is added. Run the explicit command above with the pinned
checkout and require all six tests to execute when reviewing this contract.

The fixture was independently authored from the Kit parser's consumed fields;
its SPY values are invented and QQQ is deliberately absent. SkylitAI dedicates
`examples/kit-watchlist.json` to CC0-1.0. Code follows Lab's MIT license. The Kit
renderer and its documented source/watchlist/compatibility boundaries were read
at the pinned revision; no private source or new domain calculation was used.

Next: package a selected-symbol synthetic Watchlist Investigator around this
same Kit parser/renderer path, recording its full Kit pin in the experiment
manifest. Explicit time-gap evidence, richer flow cases, live access and host
verification need later work. Review and rerun this proof before changing Kit's
revision; no Kit files changed for T07.
