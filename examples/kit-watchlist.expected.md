# Synthetic Kit consumer probe

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
| SPY | source king: 100 / -250 (available) | largest returned magnitude: 105 / 40 (available) | 0 trades; $0; no trades returned in requested window |
| QQQ | missing from heatmap response | missing from heatmap response | missing from synthetic fixture |

## SPY

### GEX · gamma

available
Board as of: 2026-10-01T14:00:00+00:00; latest spot: 101.
Returned expirations: 2026-10-02
Display: up to 3 largest returned strike magnitudes of 2 valid nodes; values copied from source.

| Strike | Source net exposure | Source node type |
|---:|---:|---|
| 100 | -250 | king |
| 105 | 75 | normal |
### VEX · vanna

available
Board as of: 2026-10-01T13:59:00+00:00; latest spot: 101.
Returned expirations: 2026-10-02
Display: up to 3 largest returned strike magnitudes of 1 valid nodes; values copied from source.

| Strike | Source net exposure | Source node type |
|---:|---:|---|
| 105 | 40 | normal |

### Recent options flow

no trades returned in requested window
Response generated: 2026-10-01T14:01:00+00:00; latest returned trade: unavailable.
Source trade count: 0; source sweep count: 0; source total premium USD: 0.
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

## How to use this

Check source times, trading session and expirations first; missing data is not zero.
No price chart or automatic freshness/alignment check is included. Separate observations from hypotheses.
Next steps: [reading hints and local extensions](https://github.com/SkylitAI/skylit-agent-kit/blob/main/docs/using-watchlist-data.md). Start with saved data; no new calls.

## Sources and usage

[Public heatmap contract](https://www.skylit.ai/docs/openapi.yaml) · [Public flow contract](https://www.skylit.ai/docs/flowseeker-openapi.yaml)


0 requests attempted; 0 documented credits reserved for attempts; no retries or model calls.
Reserved credits are a conservative estimate, not verified billing or a transactional cap on shared-account spending.
