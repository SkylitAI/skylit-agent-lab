# Current scope

Lab supplies three experimental workflows that save private local Markdown
reports and validated run records, plus a runnable synthetic template, metadata
validation and behavioral tests. Watchlist Investigator renders fictional symbols
and gaps through a pinned local Kit checkout. Market Brief reports selected
Federal Reserve press releases. Journal Reviewer calculates and reviews closed
USD cash-equity paper trades. None is a trading agent or evaluation engine.

| Target | Status |
|---|---|
| Python utilities | Python 3.11+; CI targets 3.11 and 3.14 on Linux |
| [Watchlist Investigator](../experiments/watchlist-investigator/README.md) | Offline synthetic input, selected symbols, source-time evidence, visible gaps and private reports/run records; no live mode |
| [Market Brief](../experiments/market-brief/README.md) | Bundled synthetic or caller-supplied saved feed; explicit `--fetch` makes at most one unauthenticated request to the fixed Federal Reserve feed. Report and run-record integration includes completed and stopped outcomes; the README records a dated real fetch. |
| [Journal Reviewer](../experiments/journal-reviewer/README.md) | Offline bundled synthetic or supplied paper CSV, exact calculations, escaped notes and private reports/run records; completed and stopped outcomes implemented |
| Claude Code and OpenClaw | Planned host probes; no certified integration |
| Muse | Provisional Muse Code CLI discovery recorded in the [host matrix](host-matrix.md); model access and Watchlist execution unverified |
| Custom agents | Can invoke documented commands; integration example planned |
| Live Skylit data | Reuse the maintained Kit; authenticated Lab integration and live verification pending |
| Public contribution | Outside access and fork CI remain unverified; publication is a separate release action |

Watchlist's source-time comparisons use a declared fictional reference and
demonstration age threshold. Market preserves publication times separately from
actual observed retrieval; saved input has no observed retrieval event. Journal
times come from supplied paper trades. None establishes market freshness or a
synchronized snapshot.

The [run records](run-record.md) identify consumed input bytes, Git observations,
output hashes, execution/source times and completed or stopped outcomes. They
describe the Python workflow, not its launching model host. Ordinary input or
computation failures save stopped records when the output location is usable;
early preflight failures and process termination cannot guarantee a record.
Report and record writes are not atomic, so check command exit status as well as
artifact contents. A Market gap report can be complete while its outcome remains
stopped.

The full release gates remain pending: named review ownership, source and license
review, relevant live Skylit and host evidence, independent human reproductions,
and an observed newcomer trial. Evaluation cases and a paper-trading workflow
remain later work; reviewing supplied paper trades does not implement that
workflow. Live orders are outside this scope. Public access changes and
announcements are explicit release actions.

Specialized reviewer staffing and the exact Muse surface remain release and
integration requirements. Implemented seed workflows and a dated public-feed
fetch do not certify hosts, authenticated Skylit access or completion of these
release gates.
