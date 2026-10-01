# Current scope

Lab supplies a runnable synthetic template, metadata validation, behavioral tests
and an offline [Watchlist Investigator](../experiments/watchlist-investigator/README.md).
The experiment renders selected fictional symbols and gaps through a pinned local
Kit checkout and saves private local reports. It does not supply a trading agent,
live data adapter or evaluation engine.

| Target | Status |
|---|---|
| Python utilities | Python 3.11+; CI targets 3.11 and 3.14 on Linux |
| Watchlist Investigator | Offline synthetic input, selected symbols, source-time evidence, visible gaps and no-overwrite reports; no market-freshness guarantee or live mode |
| Claude Code and OpenClaw | Planned host probes; no certified integration |
| Muse | Provisional Muse Code CLI discovery recorded in the [host matrix](host-matrix.md); model access and Watchlist execution unverified |
| Custom agents | Can invoke documented commands; integration example planned |
| Live Skylit data | Reuse the maintained Kit; Lab integration and live verification pending |
| Public contribution | Repository remains INTERNAL; outside access and fork CI remain unverified |

Source-time comparisons use a declared fictional reference and demonstration
age threshold; they do not establish a synchronized market snapshot. The next
increment adds run records. Bounded live verification and host integrations remain
planned. Later work includes Market
Brief, Journal Reviewer, evaluation cases and independent reproductions.

Before public release, verify named review ownership, source and license
provenance, relevant live and host behavior, and an observed newcomer trial.
Public access changes and announcements are explicit release actions. Historical
evaluation and paper trading are later work. Live orders are outside this scope.

Specialized reviewer staffing and the exact Muse surface remain release and
integration requirements. The offline packages do not mark those requirements done.
