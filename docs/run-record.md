# Experiment run record v1

A run record describes one experiment Python process and its local report. It
does not measure the agent or LLM host that launched that process. A later host
record may link the exact record-file hash and record its own usage separately.
[Watchlist Investigator](../experiments/watchlist-investigator/README.md) writes
`<output>.run.json` beside its report. A successful command validates and saves
both artifacts; ordinary computation failures save a stopped record when the
sidecar is writable. Early CLI/preflight errors and process termination cannot
guarantee a record. Check the command's exit status as well as record contents.

The v1 envelope has explicit profiles for `watchlist-investigator`,
`journal-reviewer` and `market-brief`. Watchlist's existing profile is unchanged.
The Journal/Market additions below validate record shapes; this contract increment
alone does not establish their runner emission or persistence integration. No
model provider or authenticated trading-service profile is accepted.

All keys below are required; unknown keys are rejected at every object level.
`null` means unavailable, not zero or an empty collection. SHA values use lowercase
hex: 40 characters for Git revisions, 64 for exact-byte SHA-256 digests.

The following table describes the common envelope and existing **Watchlist**
profile. Journal/Market substitutions are specified below; fields from another
profile are rejected.

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

## Journal and Market profiles

Both new profiles require `kit: null`: neither experiment consumes Kit. They
retain the exact root keys, Lab observation, actual UTC execution timestamps,
private report output shape and bounded decoder. `parameters` and `source_time`
may be null before their validation/parsing stages. Completed records require
both, complete input/report hashes, a finish timestamp and known usage. The
validator checks assertions and correlations, not whether observations are true.

| Field | Journal Reviewer | Market Brief |
|---|---|---|
| `experiment_id` | `journal-reviewer` | `market-brief` |
| `mode` | `offline_synthetic` or `offline_supplied` | Either offline mode, or `public_fetch` |
| `inputs[0].role` | `journal_csv` | `fed_press_xml` |
| Validated `parameters` | Exactly `{}`; input paths are excluded | Exactly `{"limit": N}`, integer 1–20 |
| `source_time` | Aggregate supplied trade times below | Feed status, retrieval and selected publication times below |

Input entries still have exactly `role`, `sha256`, `hash_state`. `complete`
requires the exact whole consumed-buffer hash, including malformed complete CSV
or XML. `not_read`, `read_failed` and `too_large` require a null hash; an oversized
prefix never establishes a complete hash. `read_failed` includes an incomplete
or failed public fetch. Only the reviewed bundled synthetic route selects
`offline_synthetic`; custom local input is `offline_supplied`, not independently
verified provenance. Neither a matching shape nor the fixed feed identity
turns caller-supplied XML into an authenticated official response.

Journal `source_time` has exactly these keys:

```json
{"basis":"supplied_trade_times","trade_count":0,"first_entry_at":null,"last_exit_at":null}
```

`trade_count` is an integer 0–1000. For nonempty input, `first_entry_at` is the
minimum normalized entry time and `last_exit_at` the maximum normalized exit
time across parsed rows; both must be aware UTC, with first at or before last.
Zero trades requires both endpoints null. Empty input can complete without
inventing a trading result. The validator checks count/order/shape, not the
min/max computation. It accepts no symbols, per-trade times, notes or financial
values in this aggregate. **Even these aggregate times and count are private**:
keep them in the private local sidecar and omit them from shared/public
reproduction evidence. Source times remain supplied data, not execution times
or independently verified fills.

Market `source_time` has exactly `status`, `retrieved_at`, `published_at`.
Status is `available`, `empty`, `invalid` or `unavailable`. `published_at` is an
ordered list of normalized UTC publication times for the selected report items,
not titles or release URLs; its length cannot exceed `parameters.limit`.
`available` requires a nonempty list; the other statuses require `[]`.

The fixed Board feed URL is implicit in the Market experiment, not a configurable
record field. Offline records always have null `retrieved_at`. A fully received
public fetch, including an invalid XML body, requires an actual aware UTC
retrieval timestamp and a complete input hash. `unavailable` is a public-fetch
state only, requires null retrieval time and a `read_failed` or `too_large` input
with no hash. It cannot expose partial items. Parsing a saved file does not
create a new retrieval event. Source publication times do not establish freshness.

Usage retains `scope: python_process`, `observed_billing: null` and
`model: {"mode":"none","provider":null,"tokens":null}`. Offline profiles use
`known_offline_path` and integer zero requests/reservations. Only Market
`public_fetch` accepts `known_public_fetch`: actual attempts are integer 0–1 and
credit reservations zero. Before a request, zero is valid; once a feed result
exists, exactly one attempt and known usage are required, including invalid or
unavailable results. `unknown` usage retains null request/reservation counts.
No host usage or observed billing is inferred from these workflow values.

Limits have exact keys and constant values for each new profile:

```json
{"input_bytes":1048576,"rows":1000,"requests":0,"credits":0,"model_calls":0,"output_no_overwrite":true}
```

Market uses `input_bytes: 524288`, `items: 100`, `display_items: 20`,
`credits: 0`, `model_calls: 0`,
`output_no_overwrite: true`, plus `requests: 0, fetch_timeout_seconds: null` for
offline modes or `requests: 1, fetch_timeout_seconds: 10` for public fetching.
The fetch timeout describes the configured socket/between-read budget, not a
hard DNS/process deadline. The display limit does not change the 100-item feed cap.

New-profile stopped reasons share `invalid_parameters`, `input_unreadable`,
`input_too_large`, `encoding_unsupported`, `output_path_unprintable`,
`output_exists`, `output_write_failed`, `record_write_failed`, `interrupted`,
`fixture_changed`. Journal additionally accepts `invalid_journal`; Market accepts `invalid_feed`
and `source_unavailable`. Watchlist's Kit/fixture reasons are not accepted here.
`fixture_changed` is only for the bundled `offline_synthetic` route: the whole
input hash must be known, parameters validated, source_time null and report
`not_written`. It records a changed bundled-fixture hash, even when the bytes
would otherwise parse. It cannot be used for supplied/fetched input or a complete
report. The caller must compare against the known reviewed fixture digest; the
schema does not infer the expected digest or certify fictional provenance.
Input errors require the matching hash state and no source-time assessment;
`invalid_parameters` also requires null parameters. `invalid_journal` retains a
complete hash but no aggregate. Feed-error reasons require their matching feed
status. Raw exceptions, source error text and arbitrary reason variants are rejected.

Market completes only for `available` or `empty`; a valid empty feed is not an
invalid/unavailable feed. An invalid or unavailable feed may have a fully saved
gap report: `outputs.state: complete` and its exact hash coexist with
`outcome.status: stopped`. The command still exits nonzero. Output completeness
is separate from workflow success. These shapes permit byte-written reports,
but safe byte hashing and preserving gap outcomes require the separate
persistence extension before runner integration.

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
