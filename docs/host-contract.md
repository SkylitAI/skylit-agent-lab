# Watchlist host acceptance contract

Judge Claude Code, OpenClaw, Muse Code (provisional target) and a custom agent by
the same tasks below. A host must actually invoke its tools and expose command
results; a model's claim, valid schema, CLI discovery or direct maintainer run is
not host evidence. **No host is certified by this document.** Native host setup
and the shared setup/live launcher are separate work. See the current
[discovery matrix](host-matrix.md) and [offline package](../experiments/watchlist-investigator/README.md).

The Lab runner is offline only. Cases H5–H7 use the **pinned Kit's public CLI**, a
different surface with no Lab run-record emission. There is no Lab `--live` flag.
Use only repository material, bundled synthetic fixtures and approved public
contracts. Do not attach private vaults or host memory to this acceptance session.
Prompt scope is not an OS sandbox: record the tools and filesystem/network
permissions actually available. Do not install global host settings for a case.

## Common cases

For each host/version/platform, record `pass`, `fail` or `not-run` for every case,
with evidence and a reason. Start at `not-run`; never inherit another host's result.

| Case | Required observation |
|---|---|
| H0 — fresh setup | Host creates new local Lab/Kit checkouts, explicitly selects the Kit pin below, verifies its clean state and records the Lab revision/state. No existing checkout is reset. |
| H1 — default offline | Actual exit 0; fictional SPY/QQQ report and validated sidecar; exact fixture/report hashes; both files mode `0600` on POSIX. Preserve gaps and the default source-time evidence. |
| H2 — selected gaps | `QQQ,SPXW` yields those symbols, missing source components and no SPX substitution; exit 0 and matching validated record/hashes. |
| H3 — malformed fixture | Nonzero exit, no report, stopped sidecar with `invalid_fixture` and the exact complete input hash. |
| H4 — missing Kit | Nonzero exit, no report, stopped sidecar with `kit_unavailable`; fixture `not_read` with null hash. |
| H5 — Kit dry-run | One SPY plan: 5 total requests and 3 documented credits estimated; zero actual requests, no credential read and no report. |
| H6 — denied live | Explicit Kit live invocation without a secure key and with noninteractive stdin stops nonzero before any socket attempt or paid request. It must not ask for a key in chat or claim completion. |
| H7 — authorized bounded live | Pending authorization/access. Actual one-SPY Kit run, at most 5 requests/3 documented credit reservations, configured 30 seconds, no retries or cap increases. Retain the observed exit, report hash, component gaps, request/reservation counts and billing evidence or unknown reason. |

“Supported” requires all required applicable cases to pass for the named version,
OS and scope. Pending live access or Muse/model access remains `not-run` with a
reason, not a pass or silently excluded case. H0–H6 can establish only an explicitly
limited offline/denial result while H7 is pending. On a non-POSIX platform, record
`0600` as inapplicable and verify equivalent private access controls before a
platform support claim. An attempted case with a violated expectation is `fail`.

## Reproducible commands

These are POSIX-shell commands, executed separately so the host retains each
command's actual exit code. Carry the resolved variables between tool calls.
Use Python 3.11+ with UTF-8 mode. Obtain authorized repository access separately;
the [package setup](../experiments/watchlist-investigator/README.md) documents the
remote clone when needed. For a network-free fresh local setup, start in the Lab
root and set `ACCEPT_KIT_SOURCE` to an already available clean pinned Kit checkout:

```sh
ACCEPT_LAB_SOURCE="$PWD"
ACCEPT_KIT_SOURCE=/absolute/path/to/pinned/skylit-agent-kit
umask 077
ACCEPT_ROOT=$(mktemp -d)
ACCEPT_LAB="$ACCEPT_ROOT/lab"
ACCEPT_KIT="$ACCEPT_ROOT/kit"
git clone --local --no-hardlinks "$ACCEPT_LAB_SOURCE" "$ACCEPT_LAB"
git clone --local --no-hardlinks "$ACCEPT_KIT_SOURCE" "$ACCEPT_KIT"
git -C "$ACCEPT_KIT" checkout --detach 0f82039759ef4db9d5b3dbd90f52863f8074f2a6
```

Stop if either clone or checkout fails. Verify H0 before running any Python:

```sh
test "$(git -C "$ACCEPT_KIT" rev-parse HEAD)" = 0f82039759ef4db9d5b3dbd90f52863f8074f2a6
test -z "$(git -C "$ACCEPT_KIT" status --porcelain)"
git -C "$ACCEPT_LAB" rev-parse HEAD
git -C "$ACCEPT_LAB" status --porcelain
```

H1 and H2 reuse the bundled fixture, with new output paths:

```sh
python3 -X utf8 -I -B "$ACCEPT_LAB/experiments/watchlist-investigator/run.py" --kit "$ACCEPT_KIT"
python3 -X utf8 -I -B "$ACCEPT_LAB/experiments/watchlist-investigator/run.py" --kit "$ACCEPT_KIT" --symbols QQQ,SPXW --output "$ACCEPT_LAB/reports/selected.md"
```

H3 deliberately passes bundled Markdown as malformed JSON; H4 uses an absent
checkout. **Both commands must fail** while saving their stopped records:

```sh
python3 -X utf8 -I -B "$ACCEPT_LAB/experiments/watchlist-investigator/run.py" --kit "$ACCEPT_KIT" --fixture "$ACCEPT_LAB/examples/kit-watchlist.expected.md" --output "$ACCEPT_LAB/reports/malformed.md"
python3 -X utf8 -I -B "$ACCEPT_LAB/experiments/watchlist-investigator/run.py" --kit "$ACCEPT_ROOT/missing-kit" --output "$ACCEPT_LAB/reports/missing-kit.md"
```

Validate H1–H4 locally in addition to recording those exits:

```sh
python3 -X utf8 -I -B - "$ACCEPT_LAB" <<'PY'
import hashlib, os, sys
from pathlib import Path
lab = Path(sys.argv[1])
sys.path.insert(0, str(lab / 'scripts'))
from run_records import parse_record
package = lab / 'experiments/watchlist-investigator'
for output, symbols, reason, source in (
    (package / 'reports/watchlist.md', ['SPY', 'QQQ'], 'completed', package / 'fixture.json'),
    (lab / 'reports/selected.md', ['QQQ', 'SPXW'], 'completed', package / 'fixture.json'),
    (lab / 'reports/malformed.md', None, 'invalid_fixture', lab / 'examples/kit-watchlist.expected.md'),
    (lab / 'reports/missing-kit.md', None, 'kit_unavailable', None),
):
    sidecar = Path(str(output) + '.run.json')
    record = parse_record(sidecar.read_bytes())
    assert record['outcome']['reason'] == reason
    if os.name == 'posix':
        assert sidecar.stat().st_mode & 0o777 == 0o600
    assert record['inputs'][0]['sha256'] == (hashlib.sha256(source.read_bytes()).hexdigest() if source else None)
    if reason == 'completed':
        assert record['parameters']['symbols'] == symbols
        assert record['outputs'][0]['sha256'] == hashlib.sha256(output.read_bytes()).hexdigest()
        assert 'Fictional data only' in output.read_text(encoding='utf-8')
        if os.name == 'posix':
            assert output.stat().st_mode & 0o777 == 0o600
    else:
        assert record['outcome']['status'] == 'stopped' and not output.exists()
    print(output.name, reason, hashlib.sha256(sidecar.read_bytes()).hexdigest())
PY
```

For H5, change into the verified Kit root; its public module command needs that
working directory (unlike Lab's isolated script command):

```sh
cd "$ACCEPT_KIT"
python3 -X utf8 -B -m skylit_agent_kit watchlist --dry-run --symbols SPY --max-requests 5 --max-credits 3 --max-seconds 30
```

H6 removes the key from the child environment without inspecting it, provides
noninteractive stdin, and blocks/counts socket attempts. It invokes the same Kit
CLI entry point and retains its expected exit 1. The audit hook is a targeted
check, not a general sandbox:

```sh
env -u SKYLIT_API_KEY python3 -X utf8 -I -B - "$ACCEPT_KIT" <<'PY'
import runpy, sys
sys.path.insert(0, sys.argv[1])
attempts = []
def audit(event, args):
    if event.startswith('socket.'):
        attempts.append(event)
        raise AssertionError('Denied-live case attempted network access')
sys.addaudithook(audit)
sys.argv = ['skylit_agent_kit', 'watchlist', '--live', '--symbols', 'SPY',
            '--max-requests', '5', '--max-credits', '3', '--max-seconds', '30']
try:
    runpy.run_module('skylit_agent_kit', run_name='__main__')
except SystemExit as result:
    print('Denied-live exit:', result.code, 'socket attempts:', len(attempts))
    assert result.code == 1 and not attempts
    raise
PY
```

**H7 is not authorized by this document.** Run only after the user authorizes this
account and budget, using an existing secure process environment or Kit's hidden
terminal prompt. Never supply a key as an argument or in chat. From the verified
Kit root, choose a new private output name:

```sh
python3 -X utf8 -B -m skylit_agent_kit watchlist --live --symbols SPY --max-requests 5 --max-credits 3 --max-seconds 30 --output reports/host-acceptance-live.md
```

The 30-second setting is a socket/between-I/O budget, not a hard DNS/process
cancellation guarantee. Account eligibility, catalog support and limits can stop
the run before paid calls. A stopped run is useful failure evidence, not a passed
live-success case. No `--save-raw`, retry, polling or automatic budget increase is
part of acceptance. Kit's own report is the artifact; do not manufacture a Lab
v1 offline record for live output.

## Evidence and interpretation

Keep one private local host acceptance record per run, with these fields (a
Markdown table is sufficient; no new schema is required):

- Actual UTC date, host name/version, OS/architecture, model/provider/version
  observed or null with reason; auth method/type only, never identity or secrets.
- Lab revision/state, Kit pin/state, repository-scoped configuration files and
  tools/approvals actually used; filesystem/network scope and known limitations.
- Per-case `pass`/`fail`/`not-run`, observed command exit, sanitized command/options,
  artifact-relative paths and exact-byte SHA-256 hashes, plus tool execution
  evidence references. Keep full private paths out of shared evidence.
- Python record path/hash for H1–H4. Separately record host model usage and costs
  from actual metering, or null with an unavailable reason. Python's zero requests
  and model `none` do not describe the launching host. Credit reservations are
  not observed billing; never replace unknown billing with zero.
- Reviewer/date, interpretation checks below, applicability decisions and limits.

Use mode `0600` for local evidence on POSIX, keep it in ignored `reports/`, and
upload nothing automatically. Exclude keys, account identifiers, prompts, raw
responses, private input content and private-vault material. Keep the actual exit
status even if a sidecar remains marked `completed` after a finalization failure;
file existence or schema validity alone cannot establish success.

The host must explain the saved results without new calls: distinguish copied
source values from Lab-derived ages; fictional source times from actual execution
times; missing data from zero; and timestamp span from an atomic snapshot or
market-freshness verdict. Preserve source labels and SPXW identity. The default
SPY ages are 360/420/300/330 seconds with span 120; QQQ is unavailable. No trade
recommendation follows from the report. Use the pinned Kit's
[reading guide](https://github.com/SkylitAI/skylit-agent-kit/blob/0f82039759ef4db9d5b3dbd90f52863f8074f2a6/docs/using-watchlist-data.md)
for interpretation boundaries, without reconstructing private scoring logic.

A direct maintainer dry-walk checks these commands only. It does not populate any
host pass row. Host-native setup, pending access, real live evidence and independent
review remain required before a support claim.
