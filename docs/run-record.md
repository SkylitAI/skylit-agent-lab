# Offline run record v1

A run record describes one Watchlist Python process and its local report. It
does not measure the agent or LLM host that launched that process. A later host
record may link the exact record-file hash and record its own usage separately.
This increment defines the contract and bounded JSON decoder; strict record
validation follows separately. No workflow currently produces these records.

The intended shared envelope is versioned, but v1 accepts only
`watchlist-investigator` in `offline_synthetic` mode. Market Brief, Journal,
providers and live modes need their own reviewed parameter contracts later.

All keys below are required; unknown keys are rejected at every object level.
`null` means unavailable, not zero or an empty collection. SHA values use lowercase
hex: 40 characters for Git revisions, 64 for exact-byte SHA-256 digests.

| Group | Exact fields and meaning |
|---|---|
| Root | `schema_version` (integer `1`), `experiment_id`, `mode`, and every group below. |
| `lab` | `revision` (SHA or null), `state` (`clean`, `dirty`, `unknown`). A null revision requires unknown state. Dirty records do not claim equivalence to committed bytes. |
| `kit` | `required_revision` (SHA), `observed_revision` (SHA or null), `verification` (`verified`, `revision_mismatch`, `dirty`, `not_checked`, `read_failed`). Verified means the observed pin matches and the checkout passed its cleanliness check. |
| `inputs` | One object: `role: synthetic_fixture`, `sha256` (digest or null), `hash_state` (`complete`, `too_large`, `read_failed`, `not_read`). Only complete has a digest; other states explain its absence. No input path is recorded. |
| `execution` | `started_at` and `finished_at`: actual aware UTC timestamps; finish may be null when unavailable. Wall-clock adjustment can make finish earlier; do not infer duration or change the workflow outcome from these values. |
| `parameters` | Null before validation; otherwise exactly `symbols` (1–100 unique normalized Kit tickers), `reference_time` (aware UTC fictional reference), `max_age_seconds` (integer 0–86400). |
| `source_time` | Null before parsing/assessment; otherwise the existing [source-time assessment](../scripts/watchlist_time.py), with its exact shape below. This is distinct from execution time. |
| `usage` | `scope: python_process`, `basis` (`known_offline_path`, `unknown`), `requests_attempted`, `credits_reserved`, `observed_billing`, `model`. Known offline paths use integer zero requests/reservations; unknown uses null. Billing is always null: reservation is not billing. |
| `usage.model` | Exactly `mode: none`, `provider: null`, `tokens: null`. No model/provider support is implied. |
| `outputs` | One object: `role: report`, `filename` (record-relative basename or null before validation), `sha256` (digest or null), `state` (`complete`, `not_written`, `write_failed`, `partial`). Only complete has the full report hash. Other states explain the unknown hash; failed/partial writes never claim completeness. |
| `outcome` | `status` (`completed`, `stopped`) and a fixed safe `reason` code below. No exception text. |
| `limits` | Actual offline limits: `fixture_bytes: 65536`, `symbols: 100`, `requests: 0`, `credits: 0`, `model_calls: 0`, `output_no_overwrite: true`. These describe the workflow's enforced path, not OS isolation. |

`completed` requires reason `completed`, validated parameters and source-time
assessment, verified Kit, complete input/report hashes, and a known finish time.
It does not require a clean Lab checkout. A report filename contains no directory
separator, colon or control character and cannot be `.` or `..`. The record
does not hash itself; no absolute paths, environment values, raw payloads, CLI
arguments, prompts, account identifiers or arbitrary error strings belong here.

Stopped reason codes are `invalid_parameters`, `input_unreadable`,
`input_too_large`, `invalid_fixture`, `kit_unavailable`, `kit_mismatch`,
`kit_dirty`, `encoding_unsupported`, `output_path_unprintable`, `output_exists`,
`output_write_failed`, `record_write_failed` and `interrupted`. Unknown hashes
are explained by the fixed input hash/output persistence states, never free text.

The source assessment has exactly `reference_time`, `max_age_seconds`, `symbols`,
`rows` and `spans`, matching validated parameters. Every selected symbol has four
row keys: `gamma.as_of`, `vanna.as_of`, `flow.generated_at`, `flow.latest_trade`.
Each field has `timestamp`, `age_seconds`, `status`, `reason`; status is `future`,
`stale`, `within threshold` or `unavailable`. Unavailable fields have null time/age
and a known Kit component reason prefixed by `timestamp missing or invalid; `.
Other fields have a UTC timestamp, finite numeric age and null reason. Each span
has `seconds` (finite nonnegative number or null) and `valid_fields` (integer
0–4); fewer than two fields means null span. Validation checks shape and states,
not the truth of observations or correctness of T09's arithmetic.

JSON must be UTF-8, at most **262144 bytes**, without duplicate keys, nonfinite
numbers, more than 32 container levels or booleans masquerading as numeric counts.
`decode_record(content)` accepts bounded bytes and returns an inert JSON object.
It never reads Git, other files, environment variables or network state, and
never executes record content. Invalid data raises `RecordError` with fixed
diagnostics that do not echo submitted content. Workflow integration, hashing
the actual consumed input buffer and exclusive private output persistence are
separate increments; a decoder or schema pass proves none of those behaviors.
