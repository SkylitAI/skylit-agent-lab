# Current scope

Lab supplies a runnable synthetic template, metadata validation, behavioral tests
and an offline [Watchlist Investigator](../experiments/watchlist-investigator/README.md).
The experiment renders selected fictional symbols and gaps through a pinned local
Kit checkout and saves private local reports with validated run records. Lab also
has an experimental public-feed adapter and a closed paper-journal parser, ahead
of their report workflows. It does not supply a trading agent or evaluation engine.

| Target | Status |
|---|---|
| Python utilities | Python 3.11+; CI targets 3.11 and 3.14 on Linux |
| Watchlist Investigator | Offline synthetic input, selected symbols, source-time evidence, visible gaps and private reports/run records; no market-freshness guarantee or live mode |
| Market Brief | [Federal Reserve feed adapter](sources/federal-reserve.md) tested with synthetic cases and one real public fetch; report workflow and run-record integration pending |
| Journal Reviewer | [Closed paper-journal parser](paper-journal-input.md) tested; calculations, report workflow and run-record integration pending |
| Claude Code and OpenClaw | Planned host probes; no certified integration |
| Muse | Provisional Muse Code CLI discovery recorded in the [host matrix](host-matrix.md); model access and Watchlist execution unverified |
| Custom agents | Can invoke documented commands; integration example planned |
| Live Skylit data | Reuse the maintained Kit; Lab integration and live verification pending |
| Public contribution | Repository remains INTERNAL; outside access and fork CI remain unverified |

Source-time comparisons use a declared fictional reference and demonstration
age threshold; they do not establish a synchronized market snapshot. Local run
records identify consumed input bytes, revision observations, output hashes and
stopped outcomes; they measure the Python workflow, not its launching model host.
Bounded live verification and host integrations remain
planned. Later work includes Market
Brief, Journal Reviewer, evaluation cases and independent reproductions.

Before public release, verify named review ownership, source and license
provenance, relevant live and host behavior, and an observed newcomer trial.
Public access changes and announcements are explicit release actions. Historical
evaluation and paper trading are later work. Live orders are outside this scope.

Specialized reviewer staffing and the exact Muse surface remain release and
integration requirements. The offline packages do not mark those requirements done.
