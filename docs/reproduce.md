# Reproduce the offline evaluation

Run the fixed 12-case evaluation against a recorded, clean Lab commit and the
required Kit pin. This procedure is not evidence that another person has reproduced
a result. A reproduction report must identify who ran it and the actual revisions,
environment, exit status and case results.

Use only the repository's fictional inputs. This gate does not contact live
services, call a model, read a private journal or certify an agent host. Its scope
and exact expectations are in the [evaluation contract](evaluation.md).

## Prepare the recorded sources

You need Git, Python 3.11 or later, and Docker Engine with Buildx through a local
Unix socket. The supported execution path uses a Linux container from macOS or
Linux; this guide does not certify Windows. Image setup may download the pinned
base image and system packages. The later evaluation runs with networking disabled.
No service credential is needed; both repositories are public.

Take the full, lowercase 40-character **Lab commit SHA from the result you intend
to reproduce**. Do not replace it with a moving branch name or derive your expected
value from whichever checkout happens to be present. In a POSIX shell, replace the
Lab placeholder below with that recorded SHA. Both clone targets must be unused;
choose different directory names throughout if either already exists.

```sh
REPRO_LAB_REVISION='replace-with-the-recorded-40-character-lab-sha'
REPRO_KIT_REVISION='0f82039759ef4db9d5b3dbd90f52863f8074f2a6'

git clone --no-checkout https://github.com/SkylitAI/skylit-agent-lab.git lab-reproduction &&
git -C lab-reproduction checkout --detach "$REPRO_LAB_REVISION"

git clone --no-checkout https://github.com/SkylitAI/skylit-agent-kit.git kit-reproduction &&
git -C kit-reproduction checkout --detach "$REPRO_KIT_REVISION"
```

Continue only when both checkouts succeeded. The `&&` guards prevent checkout
after a failed clone. These commands do not reset an existing checkout. An existing
clean checkout at the recorded commit can also be used by substituting its paths.
Do not edit fixtures or goldens to make a reproduction pass.

## Run and inspect the result

From the directory containing both new checkouts, in the same shell with the
revision variable set, choose an unused log filename **outside Lab**:

```sh
(
    cd lab-reproduction || exit
    REPRO_LOG='../reproduction.log'
    umask 077
    set -C
    python3 -X utf8 -I -B scripts/run_isolated.py --evaluate \
        --expected-lab "$REPRO_LAB_REVISION" --kit ../kit-reproduction \
        > "$REPRO_LOG" 2>&1
)
REPRO_EXIT=$?
printf 'Evaluation exit: %s\n' "$REPRO_EXIT"
```

The subshell creates an owner-only log on POSIX and refuses to overwrite an
existing log. It does not pipe away the wrapper's exit status. Keeping the log
outside Lab avoids making its source checkout dirty before staging.

`--expected-lab` is optional for ordinary evaluation, but use it for reproduction.
It accepts exactly 40 lowercase hexadecimal characters and requires `--evaluate`.
Invalid input exits 2 without echoing the submitted value. A revision mismatch
exits 1 and prints the validated expected and observed SHAs. The comparison uses
the actual staged Lab revision and occurs before Docker discovery, build or run.
The wrapper also rejects dirty source; the evaluator's existing fixture-hash
preflight rejects changed bundled input before launching cases. A matching SHA is
a source identity check, not a claim that the code or expectations are correct.

Success requires wrapper exit **0**, `isolation: passed`, evaluation status
`passed`, the expected clean Lab revision, verified Kit at the pin above, and all
**12 cases passed**. Record the container's reported Python version and local image
ID. A build/start failure is not a case result. Resolve the reported failure and
use a new log for any rerun; retain the unsuccessful observation as such.

Using `--without-kit` cannot reproduce a full pass: evaluation exits 1 with eight
independent cases passed and four Watchlist/dependency cases unverified. The
[narrower smoke check](evaluation.md#run-the-isolated-evaluation) has different
acceptance criteria. The simulated Kit budget test is dependency evidence, not a
live-account spending or billing observation.

## Compare stable evidence and explain gaps

At the same source revisions, the prepared synthetic input bytes and nine report
goldens are deterministic. Compare each workflow's `prepared_input_sha256` and
`expected_report_sha256` in the printed summary with the recorded result. These
fields identify prepared input and reviewed expectations, not observed output
digests. A passed case additionally means the comparator checked actual saved
report bytes, sidecar hashes and the expected process exit. The two no-report
cases require absent reports; the dependency case has no Lab report or sidecar.

Actual execution timestamps and resulting sidecar hashes can vary between runs;
they are not golden constants. Synthetic source/reference times remain fixed.
Docker image IDs can also vary because system package installation is not pinned
as a complete reproducible build. Record that environment rather than asserting
image-byte identity. A separately authorized live fetch can return changed bytes,
publication times and retrieval times; it is outside this offline gate and cannot
replace these fixtures or a failed case.

The evaluator discards its private temporary reports and records after comparison.
For any separately authorized model explanation of a synthetic report, apply the
[optional explanation rubric](evaluation.md#optional-explanation-rubric): attribute
values to the source, retain missing/invalid fields, separate source and execution
times, and avoid invented motives, scores or live claims. Mark each criterion met,
not met or unreviewed with a short supporting passage. Record model/version and
usage separately. A good explanation cannot override a deterministic failure;
this procedure itself performs no model review.

## Sanitized evidence template

Keep the raw log private. For review, copy only these fields and the evaluator's
fixed case IDs, statuses, reason codes and synthetic hashes. Omit absolute paths,
Docker endpoint/config details, environment values, credentials, raw errors,
report contents and private input. Do not label an automated author check as
independent human reproduction.

```text
Runner / role: <human reproducer or automated author check>
Observed at (UTC): <actual time>
Recorded expected Lab SHA: <40 lowercase hex>
Observed Lab SHA / state: <40 lowercase hex> / clean
Required / observed Kit SHA / verification: <pin> / <observed> / <state>
Host OS / architecture; Docker Engine and Buildx versions: <observed>
Container Python version / local image ID: <observed>
Wrapper exit / isolation status / evaluation status: <observed>
Cases: <all 12 fixed IDs with actual status and reason codes>
Workflow hashes: <prepared_input_sha256 and expected_report_sha256 per case>
Compared with recorded result: <matches and differences, or not compared>
Optional explanation rubric / model usage: <separate evidence, or unreviewed>
Limits: offline synthetic workflows and one simulated dependency budget test
Independent human reproduction: <supported evidence, or not established>
```
