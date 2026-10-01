# Offline run record v1

A run record describes one Watchlist Python process and its local report. It
does not measure the agent or LLM host that launched that process. A later host
record may link the exact record-file hash and record its own usage separately.
[Watchlist Investigator](../experiments/watchlist-investigator/README.md) writes
`<output>.run.json` beside its report. A successful command validates and saves
both artifacts; ordinary computation failures save a stopped record when the
sidecar is writable. Early CLI/preflight errors and process termination cannot
guarantee a record. Check the command's exit status as well as record contents.

The intended shared envelope is versioned, but v1 accepts only
`watchlist-investigator` in `offline_synthetic` mode. Market Brief, Journal,
providers and live modes need their own reviewed parameter contracts later.

All keys below are required; unknown keys are rejected at every object level.
`null` means unavailable, not zero or an empty collection. SHA values use lowercase
hex: 40 characters for Git revisions, 64 for exact-byte SHA-256 digests.

| Group | Exact fields and meaning |
|---|---|
| Root | `schema_version` (integer `1`), `experiment_id`, `mode`, and every group below. |
| `lab` | `revision` (SHA or null), `state` (`clean`, `dirty`, `unknown`). This is an observation before creating artifacts, not a file snapshot. A null revision requires unknown state. Dirty records do not claim equivalence to committed bytes. |
| `kit` | `required_revision` (SHA), `observed_revision` (SHA or null), `verification` (`verified`, `revision_mismatch`, `dirty`, `not_checked`, `read_failed`). Verified means the observed pin matches and the checkout passed its cleanliness check. |
| `inputs` | A one-element array containing an object with `role: synthetic_fixture`, `sha256` (digest or null), `hash_state` (`complete`, `too_large`, `read_failed`, `not_read`). Only complete has a digest; other states explain its absence. No input path is recorded. |
| `execution` | `started_at` and `finished_at`: actual aware UTC timestamps; finish may be null when unavailable. Wall-clock adjustment can make finish earlier; do not infer duration or change the workflow outcome from these values. |
| `parameters` | Null before validation; otherwise exactly `symbols` (1–100 unique normalized Kit tickers), `reference_time` (aware UTC fictional reference), `max_age_seconds` (integer 0–86400). |
| `source_time` | Null before parsing/assessment; otherwise the existing [source-time assessment](../scripts/watchlist_time.py), with its exact shape below. This is distinct from execution time. |
| `usage` | `scope: python_process`, `basis` (`known_offline_path`, `unknown`), `requests_attempted`, `credits_reserved`, `observed_billing`, `model`. Known offline paths use integer zero requests/reservations; unknown uses null. Billing is always null: reservation is not billing. |
| `usage.model` | Exactly `mode: none`, `provider: null`, `tokens: null`. No model/provider support is implied. |
| `outputs` | A one-element array containing an object with `role: report`, `filename` (record-relative basename or null before validation), `sha256` (digest or null), `state` (`complete`, `not_written`, `write_failed`, `partial`). Only complete has the full report hash. Other states explain the unknown hash; failed/partial writes never claim completeness. |
| `outcome` | `status` (`completed`, `stopped`) and a fixed safe `reason` code below. No exception text. |
| `limits` | Actual offline limits: `fixture_bytes: 65536`, `symbols: 100`, `requests: 0`, `credits: 0`, `model_calls: 0`, `output_no_overwrite: true`. These describe the workflow's enforced path, not OS isolation. |

`completed` requires reason `completed`, validated parameters and source-time
assessment, verified Kit, complete input/report hashes, a known finish time and
usage based on the known offline path.
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
`parse_record(content)` accepts bounded bytes and returns a validated inert record.
`decode_record(content)` only decodes bounded JSON; `validate_record(record)`
checks an already decoded object. Both validation entry points return the object
without modifying it. The bytes entry point enforces the size/nesting limits.
It never reads Git, other files, environment variables or network state, and
never executes record content. Invalid data raises `RecordError` with fixed
diagnostics that do not echo submitted content. The workflow hashes the same
bounded fixture buffer it parses and emits only allowlisted provenance. A
decoder or schema pass alone does not prove those observations or file writes;
the workflow tests exercise actual successful and stopped commands separately.

Run the contract tests without Kit: `python3 -m unittest discover -s tests -p test_run_records.py -v`.

## Private local persistence helper

`scripts/record_files.py` supplies `save_run(output, report, record, save_report)`.
The caller supplies the allowlisted provenance groups, performs CLI/UTF-8/stdout
preflight, and passes the pinned Kit's `save_private` writer. This helper does not
discover provenance or choose a writer. It deep-copies the record and owns its
output metadata, actual UTC finish time and persistence-failure outcome. Finish
is captured during finalization; it is not a duration or synthetic reference.

Before creating either file, it validates a prospective final record and encodes
the report as UTF-8 with the pinned writer's native newline translation. It
exclusively reserves `<output>.run.json` at mode `0600` before calling the report
writer. An existing record, including a symlink or hard link, prevents report
creation. After the report writer succeeds, the saved record may claim its full
byte hash. An existing report is preserved with a stopped `output_exists` record;
other write failures use `output_write_failed`, no report hash, and may leave a
partial report. No existing report is read, hashed as this run's output, or removed.

Pass `report=None` for an already-stopped computation. Its safe reason is retained,
and only a stopped sidecar is saved. Invalid input can therefore create a record
and its parent directory while creating no report. The returned finalized record
is not a success claim when its outcome is stopped. Report/persistence failures
raise `PersistenceError` with a fixed `code`; raw exception text is not recorded.

Record bytes are bounded, validated UTF-8, written through the retained descriptor
and flushed with `fsync`. A write, serialization or flush failure remains an error
even if a complete report exists. The helper makes one best-effort stopped rewrite
through the same descriptor; it never deletes paths or retries indefinitely.
These two files are **not atomic**. Failure, interruption or process termination
can leave an empty/partial record or a report without a usable record. A record
path's existence alone does not establish completion, and no crash-durability
guarantee is made for the pair. The caller must report the failure and possible
artifacts rather than claiming rollback or success.

If a stopped rewrite or descriptor close fails, an earlier complete JSON payload
can remain marked `completed` even though finalization raised an error. A valid
record alone is therefore insufficient evidence of command success: retain and
check the command's exit status as well. An unavailable parent directory is a
`record_unavailable` error; `record_exists` specifically identifies a collision
at the sidecar path.

Run-record filenames (`*.run.json`) are ignored by Lab's Git rules. Keep both
artifacts in ignored local reports directories; custom Markdown destinations may
not be ignored. Nothing is uploaded. Run persistence tests with
`python3 -m unittest discover -s tests -p test_record_files.py -v`; the real-Kit
writer test needs the documented pinned local checkout, while the filesystem
failure tests do not.
