# Current scope

Lab supplies a runnable synthetic template, metadata validation, behavioral tests
and an offline [Watchlist Investigator](../experiments/watchlist-investigator/README.md).
The experiment renders selected fictional symbols and gaps through a pinned local
Kit checkout and saves private local reports. It does not supply a trading agent,
live data adapter or evaluation engine.

| Target | Status |
|---|---|
| Python utilities | Python 3.11+; CI targets 3.11 and 3.14 on Linux |
| Watchlist Investigator | Available offline with synthetic input, selected symbols, visible gaps and no-overwrite report saving; no freshness check or live mode |
| Claude Code and OpenClaw | Planned host probes; no certified integration |
| Muse | Exact product surface and public integration contract unresolved |
| Custom agents | Can invoke documented commands; integration example planned |
| Live Skylit data | Reuse the maintained Kit; Lab integration and live verification pending |
| Public contribution | Repository remains INTERNAL; outside access and fork CI remain unverified |

The next increments add explicit temporal evidence and run records. Bounded live
verification and host integrations remain planned. Later work includes Market
Brief, Journal Reviewer, evaluation cases and independent reproductions.

Before public release, verify named review ownership, source and license
provenance, relevant live and host behavior, and an observed newcomer trial.
Public access changes and announcements are explicit release actions. Historical
evaluation and paper trading are later work. Live orders are outside this scope.

Specialized reviewer staffing and the exact Muse surface remain release and
integration requirements. The offline packages do not mark those requirements done.
