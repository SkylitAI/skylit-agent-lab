# Expected variant reports

These fixed synthetic outputs cover six nondefault cases
in `cases.json`. Each fenced body includes the report's final LF. They are review
fixtures, not an executable evaluation gate or host-verification result.

Authoring: Lab `37275c6e07a883582798ef5f2010736c47999b18`, pinned Kit `0f82039759ef4db9d5b3dbd90f52863f8074f2a6`,
Python 3.11.14 on macOS arm64. Commands ran with a minimal environment,
blocked socket operations and blocked credential prompts. Inputs follow the fixed
variations in `docs/evaluation.md`; no live or private input was used.

## watchlist-changed-evidence

<!-- expected-start: watchlist-changed-evidence -->
```markdown
# Watchlist Investigator

**Fictional data only.** Every value and timestamp below is made up.
Kit's unchanged renderer uses REST terminology; no service was contacted.
Kit revision: `0f82039759ef4db9d5b3dbd90f52863f8074f2a6`. No credentials or model required.

# Skylit watchlist · GEX / VEX / recent flow

Retrieval started: 2026-10-01T14:01:00+00:00 (fictional fixture time)
Stopping reason: offline synthetic fixture rendered

Source values from REST (display rounded to six significant digits); no local proprietary calculations or trade recommendation.
GEX = requested gamma; VEX = requested vanna. Each board covers up to 92 strikes and the nearest 5 expirations, not the whole chain.
Flow window: 1d; date: 2026-10-01; at most 10 recent trades per symbol.
Separate requests are not an atomic snapshot. Compare the board and trade timestamps before use; no freshness guarantee.

| Symbol | GEX strike / source value | VEX strike / source value | Flow window |
|---|---|---|---|
| SPY | source king: 110 / -199 (available) | largest returned magnitude: 115 / 60 (available) | 1 trades; $650; partial: 1 invalid trades |
| QQQ | missing from heatmap response | missing from heatmap response | missing from synthetic fixture |
| SPXW | missing from heatmap response | missing from heatmap response | missing from synthetic fixture |

## SPY

### GEX · gamma

available
Board as of: 2026-10-01T13:44:00+00:00; latest spot: 109.
Returned expirations: 2026-10-02
Display: up to 3 largest returned strike magnitudes of 2 valid nodes; values copied from source.

| Strike | Source net exposure | Source node type |
|---:|---:|---|
| 110 | -199 | king |
| 115 | 45 | normal |
### VEX · vanna

available
Board as of: 2026-10-01T14:02:00+00:00; latest spot: 109.
Returned expirations: 2026-10-02
Display: up to 3 largest returned strike magnitudes of 1 valid nodes; values copied from source.

| Strike | Source net exposure | Source node type |
|---:|---:|---|
| 115 | 60 | normal |

### Recent options flow

partial: 1 invalid trades
Response generated: 2026-10-01T13:56:00+00:00; latest returned trade: unavailable.
Source trade count: 1; source sweep count: 0; source total premium USD: 650.
Source aggregate scores: VWF unavailable; SDF unavailable; FIR unavailable
Display: latest 0 of 0 valid returned trades (window counts are source totals).

| Trade time | Type | Strike | Expiration | Contracts | Premium USD | Flow Score | FlowBonus |
|---|---|---:|---|---:|---:|---:|---:|

## QQQ

### GEX · gamma

missing from heatmap response
### VEX · vanna

missing from heatmap response

### Recent options flow

missing from synthetic fixture

## SPXW

### GEX · gamma

missing from heatmap response
### VEX · vanna

missing from heatmap response

### Recent options flow

missing from synthetic fixture

## How to use this

Check source times, trading session and expirations first; missing data is not zero.
No price chart or automatic freshness/alignment check is included. Separate observations from hypotheses.
Next steps: [reading hints and local extensions](https://github.com/SkylitAI/skylit-agent-kit/blob/main/docs/using-watchlist-data.md). Start with saved data; no new calls.

## Sources and usage

[Public heatmap contract](https://www.skylit.ai/docs/openapi.yaml) · [Public flow contract](https://www.skylit.ai/docs/flowseeker-openapi.yaml)


0 requests attempted; 0 documented credits reserved for attempts; no retries or model calls.
Reserved credits are a conservative estimate, not verified billing or a transactional cap on shared-account spending.

## Synthetic source-time evidence

Fictional reference time: 2026-10-01T14:01:00+00:00.
Demonstration maximum age: 900 seconds.
Age = reference minus source time. Negative age is future; age greater than the threshold is stale; otherwise within threshold.
Missing or invalid times are unavailable and excluded from the span.
Times describe different measurements; even a zero span does not establish an atomic snapshot, market freshness or session alignment.

| Symbol | Source field | Time (UTC) | Age (seconds) | Evidence |
|---|---|---|---:|---|
| SPY | gamma.as_of | 2026-10-01T13:44:00+00:00 | 1020 | stale |
| SPY | vanna.as_of | 2026-10-01T14:02:00+00:00 | -60 | future |
| SPY | flow.generated_at | 2026-10-01T13:56:00+00:00 | 300 | within threshold |
| SPY | flow.latest_trade | unavailable | unavailable | timestamp missing or invalid; partial: 1 invalid trades |
| QQQ | gamma.as_of | unavailable | unavailable | timestamp missing or invalid; missing from heatmap response |
| QQQ | vanna.as_of | unavailable | unavailable | timestamp missing or invalid; missing from heatmap response |
| QQQ | flow.generated_at | unavailable | unavailable | timestamp missing or invalid; missing from synthetic fixture |
| QQQ | flow.latest_trade | unavailable | unavailable | timestamp missing or invalid; missing from synthetic fixture |
| SPXW | gamma.as_of | unavailable | unavailable | timestamp missing or invalid; missing from heatmap response |
| SPXW | vanna.as_of | unavailable | unavailable | timestamp missing or invalid; missing from heatmap response |
| SPXW | flow.generated_at | unavailable | unavailable | timestamp missing or invalid; missing from synthetic fixture |
| SPXW | flow.latest_trade | unavailable | unavailable | timestamp missing or invalid; missing from synthetic fixture |

- SPY: observed timestamp span 1080 seconds across 3 valid fields.
- QQQ: observed timestamp span unavailable (0 valid fields; need at least 2).
- SPXW: observed timestamp span unavailable (0 valid fields; need at least 2).
```
<!-- expected-end: watchlist-changed-evidence -->

## journal-fees-gap

<!-- expected-start: journal-fees-gap -->
```markdown
# Paper-journal review

Source: supplied paper-trade input.
Paper/synthetic status, instruments, fills, fees and times are not independently verified.
Calculations describe the supplied rows; they do not establish actual trading results.

Trade count: 2

Total net (USD): 3.76

Gross and net displays use USD cents with ROUND_HALF_UP; the total is summed exactly before rounding.
Displayed trade amounts may not add to the displayed total. Source values retain their supplied precision.
Fees are entered totals. No borrow costs, dividends, splits, slippage or tax are inferred.

## Trade 1: LABA (long)

- Asset type: cash_equity; currency: USD.
- Quantity (shares): 2.5
- Entry price (USD/share): 10.125; time (UTC): 2026-10-01T13:30:00+00:00
- Exit price (USD/share): 11.25; time (UTC): 2026-10-01T14:00:00+00:00
- Entered fees (USD): 1.10
- Gross (USD): 2.81
- Net (USD): 1.71

Supplied note: unavailable; no reason supplied.

## Trade 2: LABB (short)

- Asset type: cash_equity; currency: USD.
- Quantity (shares): 3
- Entry price (USD/share): 25; time (UTC): 2026-10-01T14:15:00+00:00
- Exit price (USD/share): 24.25; time (UTC): 2026-10-01T15:00:00+00:00
- Entered fees (USD): 0.20
- Gross (USD): 2.25
- Net (USD): 2.05

Supplied note (inert text): Fictional short paper trade&#46;

Review question: What context would you add to this supplied note?
```
<!-- expected-end: journal-fees-gap -->

## journal-empty

<!-- expected-start: journal-empty -->
```markdown
# Paper-journal review

Source: supplied paper-trade input.
Paper/synthetic status, instruments, fills, fees and times are not independently verified.
Calculations describe the supplied rows; they do not establish actual trading results.

Trade count: 0

No trade observations. Aggregate net P&L: unavailable.
```
<!-- expected-end: journal-empty -->

## market-changed-limited

<!-- expected-start: market-changed-limited -->
```markdown
# Market Brief

Caller-supplied saved feed: source authenticity and retrieval time are unverified.
Actual retrieval (UTC): unknown (offline input).

Source status: available. Showing 1 of 2 releases in feed order.
Requests attempted: 0. Model calls: 0.

### Published (UTC): 2020-01-01T12:00:00+00:00
Fictional notice&#58; changed fictional wording &#38; sample calendars

Unverified input URL: `https://www.federalreserve.gov/newsevents/pressreleases/fictional20200101a.htm`

Feed format reference: `https://www.federalreserve.gov/feeds/press_all.xml`.
Input SHA-256: `0f720295fb54fa5e1288ac99357670d0da004c06b4faf8c3efe372377aae85c1`.
This covers one press-release feed; it is not a complete market view or a freshness guarantee.
```
<!-- expected-end: market-changed-limited -->

## market-empty

<!-- expected-start: market-empty -->
```markdown
# Market Brief

Caller-supplied saved feed: source authenticity and retrieval time are unverified.
Actual retrieval (UTC): unknown (offline input).

Source status: empty. Showing 0 of 0 releases in feed order.
Requests attempted: 0. Model calls: 0.

No releases were present in this feed; this does not establish an absence of announcements.

Feed format reference: `https://www.federalreserve.gov/feeds/press_all.xml`.
Input SHA-256: `b70aaf06fb724875e11ee735e6a4321eef1a3315d2fd14b7eae9d6d7005aa30c`.
This covers one press-release feed; it is not a complete market view or a freshness guarantee.
```
<!-- expected-end: market-empty -->

## market-invalid

<!-- expected-start: market-invalid -->
```markdown
# Market Brief

Caller-supplied saved feed: source authenticity and retrieval time are unverified.
Actual retrieval (UTC): unknown (offline input).

Source status: invalid. Showing 0 of 0 releases in feed order.
Requests attempted: 0. Model calls: 0.

No usable releases. Invalid UTF&#45;8 RSS document&#46;

Feed format reference: `https://www.federalreserve.gov/feeds/press_all.xml`.
Input SHA-256: `1b428086af4cc21b040bf9d990329aa8d6505740b0bc8891a3ad78ef4bf2e154`.
This covers one press-release feed; it is not a complete market view or a freshness guarantee.
```
<!-- expected-end: market-invalid -->
