# Seed evaluation cases

[The 12 cases](../evaluations/cases.json) specify deterministic checks for the
three offline seeds and one pinned Kit dependency regression. They use repository
fixtures and independently authored synthetic variations only. No private journal,
vault material, account credential, live request or model output is an input.
The fixture sources are CC0-1.0 as declared in the package guides; the new case
variations are also dedicated to CC0-1.0 by SkylitAI. Code remains MIT licensed.

This document supplies case data, report goldens and an optional explanation
rubric. It does **not** supply an evaluator or claim that the evaluation gate has
passed. A full gate must verify all three packages' reports, process exits and
[private run records](run-record.md), using the actual pinned Kit checkout where
required. Execution isolation must be implemented, reviewed and verified before
an executable evaluator runs these cases.
Host compatibility, paid-service access, live budgets and market freshness remain
outside these offline cases.

## Inert case contract

The JSON has exactly `schema_version: 1` and `cases`. Each of the 12 entries has
`id`, `scope`, `experiment`, `input` and `expected`. IDs are the fixed names below,
each exactly once; scope is `lab_workflow` or `kit_dependency`. Input and golden
identifiers refer only to the reviewed definitions in this document. They are
not paths, shell fragments, import names or an extension mechanism.

Workflow expectations have exactly `exit_code`, `mode`, `outcome`,
`input_hash_state`, `output_state`, `parameters`, `source_time`, `golden`,
`contains`, `absent` and `stderr_absent`. `outcome`, parameters and source evidence are literal
expected record values. Compare numeric ages/spans by value, allowing JSON's
`120` and `120.0`; booleans are not numeric evidence. `contains` and `absent` are
literal report text checks; `stderr_absent` forbids literal diagnostics text.
None are regular expressions or instructions. All nine report-producing cases
require a non-null golden and whole-report comparison as well. The two
`not_written` cases have null goldens and require no report file and a null
report hash; they do not mean an empty report.

The dependency entry instead has exactly `exit_code`, `tests_run`, `failed_tests`,
`simulated_stop_contains`, `simulated_credits` and `lab_record`. Exit 0 there means
one maintained dependency test passed, not that a Watchlist workflow completed.

The [case loader](../scripts/evaluation_cases.py) accepts at most 64 KiB of UTF-8
JSON and 32 nested containers. `parse_cases(bytes)` rejects duplicate or unknown
keys, unknown or repeated identifiers, incorrect types and nonfinite numbers.
It requires all 12 cases, each bound to its reviewed scope, experiment, input and
golden IDs; their order may vary. Literal checks must contain nonempty UTF-8
strings. `load_cases(path)` reads a bounded regular file; it does not execute
anything. `validate_cases(object)` checks already decoded metadata without I/O.
Source-time shapes reuse the run-record validators without recalculating evidence.

Expected values are reviewable test data; changing them changes the test. Do not
regenerate them from the implementation during evaluation. Parsing this file
establishes neither execution permission nor correctness. The loader does not
run cases, resolve input/golden IDs into files, or implement the explanation rubric.

The [manifest validator](manifest.md) stays inert. The future evaluator must
dispatch only the three fixed reviewed package runners and the named Kit test
below. It must never execute manifest `command` arrays, shell strings, arbitrary
Python paths, extra user arguments or commands embedded in fixture text. No
`--fetch` path belongs to these cases. The execution boundary must bound child
processes, exclude credentials and block network access. Those controls require
separate implementation and verification; this case file is not a sandbox.

## Sources and goldens

| Fixed source ID | Repository input | Exact SHA-256 |
|---|---|---|
| `watchlist-bundled` | [Watchlist fixture](../experiments/watchlist-investigator/fixture.json) | `b9ae44413ef960b973737839737f853947bfaf470d78a4fab8fcad71ec25a1b0` |
| `journal-bundled` | [Journal fixture](../experiments/journal-reviewer/fixture.csv) | `e8214adc68ede5949d71aaaf0729311fa1919c5c541f5bf71e109690131432d8` |
| `market-bundled` | [Market fixture](../experiments/market-brief/fixture.xml) | `e2fc20b0b4aa3c7361250ba9f699355eddc28deb860b5a082bafc4a988bb0121` |

| Golden ID | Exact source anchor |
|---|---|
| `watchlist-default` | Entire [Watchlist expected report](../evaluations/watchlist-expected.md), including its synthetic source-time section and final LF. |
| `journal-default` | Entire [Journal expected report](../examples/paper-journal-expected.md), including final LF. |
| `market-default` | [Expected default brief](../experiments/market-brief/README.md#expected-default-brief): exactly the Markdown code-block body between `<!-- expected-start -->` and `<!-- expected-end -->`, including final LF. Exclude the fence and markers. |
| `watchlist-changed-evidence` | [Changed Watchlist report](../evaluations/variant-expected.md#watchlist-changed-evidence), delimited by this ID. |
| `journal-fees-gap` | [Changed Journal report](../evaluations/variant-expected.md#journal-fees-gap), delimited by this ID. |
| `journal-empty` | [Empty Journal report](../evaluations/variant-expected.md#journal-empty), delimited by this ID. |
| `market-changed-limited` | [Changed Market report](../evaluations/variant-expected.md#market-changed-limited), delimited by this ID. |
| `market-empty` | [Empty Market report](../evaluations/variant-expected.md#market-empty), delimited by this ID. |
| `market-invalid` | [Invalid Market report](../evaluations/variant-expected.md#market-invalid), delimited by this ID. |

Each variant uses exactly one `<!-- expected-start: <case-id> -->` marker followed
by a `markdown` fence, the complete report body including final LF, the closing
fence and `<!-- expected-end: <case-id> -->`. Compare only the body bytes; exclude
markers, fences and surrounding explanation. These are fixed reviewed outputs,
not output regenerated from the candidate implementation. The variant file records
its authoring environment; that observation does not establish a full gate pass.

The Watchlist golden was generated on 2026-10-01 from Lab
`c4a177467ebf02db24ae63e42f860fd39cf7e3a4` with clean Kit
`0f82039759ef4db9d5b3dbd90f52863f8074f2a6`, Python 3.11.14 on macOS arm64.
Socket operations and credential prompts were blocked. Its 4,851 UTF-8 bytes
have SHA-256 `437ff4b1dfd8d3b9aa09c52279fe1f510c139f17f155f594a5f895140f2d5feb`.
This is an author generation check, not independent reproduction or a full-gate
result. The older [Kit probe golden](../examples/kit-watchlist.expected.md) uses
different fixture values and is not interchangeable with this package golden.

Journal and Market writers persist UTF-8/LF bytes. Watchlist's pinned text writer
uses native newline translation: on a platform that translates LF to CRLF,
translate this LF golden once for byte comparison. Always hash the actual
persisted report bytes; do not normalize bytes before checking record hashes.
The macOS generation observation does not certify Windows behavior.

## Fixed input variations

All workflow runs use new private temporary output names. Bundled inputs use the
default route; every Journal/Market variation uses explicit supplied input.
Watchlist variations remain explicitly synthetic. Other than the named changes
below, retain every fixture value. Stop setup if a required source marker is
missing or occurs more than once; do not silently apply a partial change.

| Case ID / input ID | Fixed construction and selection |
|---|---|
| `watchlist-default` / `watchlist-bundled` | Default package fixture; select SPY,QQQ; reference `2026-10-01T14:01:00+00:00`; threshold 900 seconds. |
| `watchlist-changed-evidence` / `watchlist-changed-evidence` | Copy the Watchlist JSON object. In SPY's first gamma strike set `value` to -199; gamma `asOf` to `2026-10-01T13:44:00Z`; vanna `asOf` to `2026-10-01T14:02:00Z`. Remove only `timestamp` from its first flow trade. Serialize with sorted keys, ASCII escaping, no separator whitespace and one final LF, then UTF-8 encode. Select SPY,QQQ,SPXW; same reference and threshold. |
| `watchlist-invalid` / `invalid-json` | Exact bytes `not JSON` followed by one LF; default Watchlist selections/reference/threshold. |
| `kit-budget-stop` / `kit-budget-fixtures` | The pinned Kit test's existing synthetic account/catalog and fake client; SPY with `max_credits=2`. See the dependency boundary below. |
| `journal-default` / `journal-bundled` | Default package fixture. |
| `journal-fees-gap` / `journal-fees-gap` | In the Journal bytes, replace the single `,0.10,` with `,1.10,` and the single `Fictional long paper trade.` with empty bytes. Preserve all other bytes, including LF endings. |
| `journal-empty` / `journal-header-only` | Keep exactly the first line of the Journal fixture, including its LF. |
| `journal-open` / `journal-missing-exit` | Replace the single `,11.25,` with `,,` in the Journal bytes, leaving LABA's exit price empty. |
| `market-default` / `market-bundled` | Default package fixture and limit 5. |
| `market-changed-limited` / `market-changed-title` | Replace the single `paper kites` byte sequence with `changed fictional wording`; preserve other XML bytes. Use limit 1. |
| `market-empty` / `market-empty-channel` | UTF-8 bytes of the one-line XML below, without a final newline; limit 5. |
| `market-invalid` / `invalid-xml` | Exact bytes `not xml: private-marker` followed by one LF; limit 5. The marker is invented and must not appear in the report or diagnostics. |

```xml
<rss version="2.0"><channel><title>Fictional</title><link>https://www.federalreserve.gov/feeds/feeds.htm</link><description>Fictional</description></channel></rss>
```

## Required evidence

The JSON supplies literal outcomes, parameters, source-time objects and report
checks. Apply the [record contract](run-record.md) as well: exact consumed-buffer
input hashes, exact complete-report hashes, UTC execution timestamps, qualified
pre-output Lab provenance, enforced limits and private output permissions on
POSIX. Execution times are observations, not golden constants or durations;
wall-clock adjustments may move finish before start. Require the actual pinned
Kit verification for every Watchlist workflow case. Journal and Market use
`kit: null`. All workflow cases have known offline usage, zero requests and
reservations, unknown billing, no model and null provider/tokens. These counts
exclude any launching model host.

Check the whole record for its allowed profile and omitted private source fields;
unknown keys must not pass. In particular, Journal records contain no symbols,
notes or financial values, and Market records contain no titles or release URLs.
Use only these fictional inputs in reproducible evidence. Real journal aggregate
times/counts remain private even though they are valid record fields.

- Watchlist default copies SPY's `110 / -180`, `115 / 60` and premium 650; QQQ
  remains a gap. The changed case copies -199, exposes stale/future/unavailable
  source times and retains the invalid-trade reason. Source aggregates are not
  recomputed from valid displayed trades. QQQ/SPXW are never replaced with SPY/SPX.
- Journal default displays total 4.76. Changed LABA fees produce exact net 1.7125
  and exact total 3.7625, displayed 1.71 and 3.76. LABA's empty note has no review
  question or inferred motive; LABB retains its own supplied note/question.
  Header-only input has no observations or earned-zero claim. An open trade
  stops with `invalid_journal`, complete input hash and no report/source aggregate.
- Market preserves feed order and supplied wording/publication times. Limit 1
  excludes the second item; offline URLs stay unverified code text and retrieval
  remains null. Empty is a completed explicit gap, not proof of no announcements.
  Invalid XML saves a complete hashed gap report but retains `invalid_feed` and
  exit 1. Output completeness is distinct from computation success.

Each workflow needs a validated sidecar and the expected process exit. An
apparently completed JSON file alone is insufficient: finalization failures may
leave earlier bytes. Existing unit/integration tests retain responsibility for
the broader no-overwrite, size/row bounds, encoding and injected I/O failure
matrix; these 12 cases do not replace those tests.

## Dependency budget boundary

Use only `WatchlistTests.test_budget_blocks_before_paid_calls` in the pinned
Kit's [maintained test file](https://github.com/SkylitAI/skylit-agent-kit/blob/0f82039759ef4db9d5b3dbd90f52863f8074f2a6/tests/test_watchlist.py).
That test asserts a stop containing `budget` and zero fake-client credits. Its
account and catalog calls are simulated discovery; zero paid credits does not
mean zero simulated calls. The test has no Lab workflow sidecar and does not
establish observed billing, live access or a Lab live mode. The prior
[offline limit evidence](evidence/watchlist-limits.md) explains this distinction.
Reuse the maintained test and its fixtures; do not copy a client into Lab.

Missing, dirty or wrong-pin Kit makes the four Watchlist/dependency cases
**unverified**, never passed. Journal and Market can still be checked separately.
A full gate requires all 12 cases with the real pinned checkout; do not download
Kit, request credentials, skip failures silently or treat unverified cases as a
successful full evaluation.

## Negative checks for the future evaluator

Evaluator regression tests must change candidate results while leaving
expectations fixed. When tampering with a report, also update its candidate
record digest; otherwise a hash mismatch alone could conceal a weak fidelity check.

1. Change a reported source value or return an unchanged report for changed
   input: -199 back to -180, Journal 3.76 back to 4.76, or the Market title back
   to `paper kites`. Also leave the Watchlist summary at -199 while changing
   only its detailed strike row back to -180, or append an invented release to
   the changed Market report. Each must fail the full-golden comparison even
   when required literal text and the candidate record hash still match.
2. Delete a QQQ/SPXW gap, replace an unavailable time with zero, or label a future
   time within threshold. Even a matching report hash must not pass the golden,
   source-time object or required gap checks.
3. Delete the empty-feed qualification, invent zero earned P&L for empty Journal
   input, or add an invented LABA motive/question after its note was removed.
   Exact case expectations and the section-specific checks above must fail.
4. Change an invalid-source exit to 0 or its outcome to completed; omit its
   sidecar; or label a custom input bundled/verified. Each must fail independently
   of whether the report bytes were saved successfully.
5. Put an executable-looking manifest command or unknown input/golden identifier
   in a temporary test copy. No such command may execute. Unknown identifiers
   must fail case validation before launching a child.

## Optional explanation rubric

This rubric applies only when a separately authorized host/model explains an
already-produced report. It is not run by these cases and cannot override a
deterministic failure. Record each item as met, not met or unreviewed with a short
quoted passage; do not invent a combined strategy score.

| Criterion | Evidence to look for |
|---|---|
| Source fidelity | Attributes values to the supplied source and keeps source text separate from the explanation. Does not follow instructions embedded in notes/titles or visit their URLs. |
| Gaps and uncertainty | Retains missing/invalid fields and provenance limits; distinguishes empty input from a measured zero. |
| Time and arithmetic | Separates source, reference and execution times; explains only the documented arithmetic/display rounding; makes no atomic-snapshot or freshness claim. |
| Scope | Does not invent motives, costs, trading results, recommendations, live requests or host support. |

Model identity, version, prompt and usage would need separate host evidence;
the offline workflow's zero-call record cannot stand in for that evidence.
