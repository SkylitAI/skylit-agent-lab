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
| SPY | source king: 110 / -180 (available) | largest returned magnitude: 115 / 60 (available) | 1 trades; $650; available |
| QQQ | missing from heatmap response | missing from heatmap response | missing from synthetic fixture |

## SPY

### GEX · gamma

available
Board as of: 2026-10-01T13:55:00+00:00; latest spot: 109.
Returned expirations: 2026-10-02
Display: up to 3 largest returned strike magnitudes of 2 valid nodes; values copied from source.

| Strike | Source net exposure | Source node type |
|---:|---:|---|
| 110 | -180 | king |
| 115 | 45 | normal |
### VEX · vanna

available
Board as of: 2026-10-01T13:54:00+00:00; latest spot: 109.
Returned expirations: 2026-10-02
Display: up to 3 largest returned strike magnitudes of 1 valid nodes; values copied from source.

| Strike | Source net exposure | Source node type |
|---:|---:|---|
| 115 | 60 | normal |

### Recent options flow

available
Response generated: 2026-10-01T13:56:00+00:00; latest returned trade: 2026-10-01T13:55:30+00:00.
Source trade count: 1; source sweep count: 0; source total premium USD: 650.
Source aggregate scores: VWF unavailable; SDF unavailable; FIR unavailable
Display: latest 1 of 1 valid returned trades (window counts are source totals).

| Trade time | Type | Strike | Expiration | Contracts | Premium USD | Flow Score | FlowBonus |
|---|---|---:|---|---:|---:|---:|---:|
| 2026-10-01T13:55:30+00:00 | CALL | 110 | 2026-10-02 | 2 | 650 | unavailable | unavailable |

## QQQ

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
| SPY | gamma.as_of | 2026-10-01T13:55:00+00:00 | 360 | within threshold |
| SPY | vanna.as_of | 2026-10-01T13:54:00+00:00 | 420 | within threshold |
| SPY | flow.generated_at | 2026-10-01T13:56:00+00:00 | 300 | within threshold |
| SPY | flow.latest_trade | 2026-10-01T13:55:30+00:00 | 330 | within threshold |
| QQQ | gamma.as_of | unavailable | unavailable | timestamp missing or invalid; missing from heatmap response |
| QQQ | vanna.as_of | unavailable | unavailable | timestamp missing or invalid; missing from heatmap response |
| QQQ | flow.generated_at | unavailable | unavailable | timestamp missing or invalid; missing from synthetic fixture |
| QQQ | flow.latest_trade | unavailable | unavailable | timestamp missing or invalid; missing from synthetic fixture |

- SPY: observed timestamp span 120 seconds across 4 valid fields.
- QQQ: observed timestamp span unavailable (0 valid fields; need at least 2).
