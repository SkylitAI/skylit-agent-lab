# Watchlist limit verification

The pinned Kit stops a Watchlist plan when credentials, account access or the
available request/credit budget cannot cover it. The checked global HTTP failures,
transport errors and invalid JSON stop the run without retries. HTTP 404 and
some malformed component fields are recorded while remaining calls continue.
These are **offline tests**
using synthetic accounts and mocked transport, not service-access certification.

Checked on 2026-10-01 with Kit commit
`0f82039759ef4db9d5b3dbd90f52863f8074f2a6`, Darwin 25.6.0 arm64, Python 3.11.14
and 3.14.5. All **32 existing Watchlist and CLI tests passed on both versions**.
No real credential, network request or paid service was used.

From a clean Kit checkout at that revision, repeat the maintained checks:

```sh
python3 -m unittest discover -s tests -p 'test_watchlist*.py' -v
```

Use `python3.11` and `python3.14` to reproduce the two interpreter runs. Test
definitions are in the pinned
[Watchlist tests](https://github.com/SkylitAI/skylit-agent-kit/blob/0f82039759ef4db9d5b3dbd90f52863f8074f2a6/tests/test_watchlist.py)
and
[CLI tests](https://github.com/SkylitAI/skylit-agent-kit/blob/0f82039759ef4db9d5b3dbd90f52863f8074f2a6/tests/test_watchlist_cli.py).
Reading or cloning the current INTERNAL repository requires access.

| Boundary | Maintained verification |
|---|---|
| Offline preview | `test_dry_run_never_reads_credentials_or_connects` forbids credential lookup and live execution. |
| Missing/invalid credentials | `test_transport_rejects_invalid_credentials_shapes_and_large_bodies` asserts no transport is constructed; `test_noninteractive_missing_secret_stops_without_echo` refuses an unavailable hidden prompt. |
| Insufficient credits | `test_budget_blocks_before_paid_calls` and `test_account_balance_blocks_before_paid_calls` keep paid credits at zero. Discovery may already have occurred. |
| Account/rate allowance | Invalid account limits stop after one discovery request; complete-plan checks and exhausted response headers prevent further requests. |
| HTTP failure | `test_all_global_failure_statuses_stop_remaining_requests` covers 401, 402, 403, 429, 500, 503, 504 and an unclassified failure; the transport test asserts one attempted 429 request with no retry. |
| Timeout/deadline | `test_timeout_and_deadline_errors_are_sanitized` hides raw errors and rejects an expired deadline before sending. |
| Malformed response | Transport shape/size checks reject invalid or oversized JSON; component tests reject or label invalid source fields. |
| Local limits outside the workflow | `test_transport_limits_hold_even_without_workflow` refuses a request at a zero request cap. |

An additional check reused the same fixture builders and real `execute_live`
function with a mocked HTTP opener for the smallest SPY plan: gamma, vanna and
flow, plus account and symbol discovery. It used caps of 5 requests, 3 documented
credits and 30 seconds, reducing the relevant cap in the two local-budget cases.
The results below passed on both interpreters. Counts are transport attempts,
including failed requests, and conservative documented credit reservations.

| Synthetic case | Requests attempted | Credits reserved | Observed result |
|---|---:|---:|---|
| Missing credential | 0 | — | No transport constructed. |
| All responses valid | 5 | 3 | Completed. |
| Local credit cap of 2 | 2 | 0 | Stopped before paid calls. |
| Local request cap of 4 | 2 | 0 | Stopped before paid calls. |
| Account balance of 2 | 2 | 0 | Stopped before paid calls. |
| Account HTTP 401 | 1 | 0 | Stopped at discovery. |
| First paid request returns HTTP 429 | 3 | 1 | Stopped; no retry. |
| First paid request times out | 3 | 1 | Stopped; no retry. |
| First paid response is invalid JSON | 3 | 1 | Stopped; no retry. |

The supplemental checks asserted agreement between transport call counts and
the returned counters, stopped/completed outcomes, and absence of the synthetic
key and raw error marker in returned data. They were disposable verification
probes; the maintained regression coverage remains the Kit suite above.

Credit reservation is **not observed billing**. A failed paid attempt retains
its reservation because billing cannot be inferred from its failure. A missing
credential creates no client, so no client reservation counter exists.
None of these results proves current service entitlement, source freshness,
agent-host compatibility or a live run. The Lab package remains offline; its
zero-call path is separate from this verification of Kit's live boundary.
