# Verify a Lab change

From the repository root:

```sh
python3 scripts/validate_experiments.py
python3 -m unittest discover -s tests -v
python3 -m compileall -q scripts tests templates/experiment experiments
python3 templates/experiment/run.py --output /tmp/lab-example.md
diff -u templates/experiment/expected.md /tmp/lab-example.md
```

The metadata checker must reject invalid manifests and return nonzero. Unit tests
exercise missing fields, malformed JSON, invalid statuses, escaping paths and
other boundary cases. They also show that command metadata stays inert. The
template tests check actual output, changed inputs and clear failures.

Kit-dependent tests require an available local checkout at the documented pin.
Without one, they visibly skip: **Kit runtime integration remains unverified**.
For the full local check, complete the
[Watchlist setup](../experiments/watchlist-investigator/README.md), then run:

```sh
SKYLIT_AGENT_KIT=../skylit-agent-kit-watchlist python3 -m unittest discover -s tests -v
```

In PowerShell, set `$env:SKYLIT_AGENT_KIT = '../skylit-agent-kit-watchlist'`
first, then run `py -3 -m unittest discover -s tests -v`. Adjust the path if you
chose a different new Kit directory. Require no Kit-related skips for runtime
integration evidence.

GitHub Actions runs the same checks on Python 3.11 and 3.14 using synthetic local
inputs and no service credentials. Setup downloads Python and pinned actions;
this workflow does not claim network isolation. CI does not obtain Kit or add a
cross-repository token, so its Kit-dependent tests remain skipped and unverified.

### Hosted Kit coverage prerequisite

Read-only settings inspection on 2026-10-01 found both repositories INTERNAL,
Lab's default workflow token read-only, no repository or inherited organization
Actions secrets/variables, no configured environments, and Kit's Actions sharing
access set to `none`. The current workflow has only `contents: read`.
[GitHub documents that `GITHUB_TOKEN` is limited to its workflow repository](https://docs.github.com/en/actions/concepts/security/github_token);
[checking out another nonpublic repository needs separate authorized access](https://github.com/actions/checkout#checkout-multiple-repos-private).
Increasing Lab's token permissions would not give that token access to Kit.

At Lab `81a65f9a7e88a4d9ce2b81c6c9c9aa7db18ef639`, each hosted Python job
discovered 178 tests: 144 executed and 34 skipped because the pinned Kit was
absent. The same revision passed all 178 locally on Python 3.11.14 and 3.14.5
with Kit `0f82039759ef4db9d5b3dbd90f52863f8074f2a6` and zero skips.
The 34 skipped cases are:

| Test module | Skipped cases |
|---|---:|
| `test_kit_consumer` | 10 |
| `test_record_files` | 1 |
| `test_setup_watchlist` | 1 |
| `test_watchlist_investigator` | 9 |
| `test_watchlist_live` | 6 |
| `test_watchlist_records` | 7 |

Closing hosted coverage requires owner-approved read access to Kit for a trusted
integration job, such as a GitHub App installation token or fine-grained token
limited to Kit's `Contents: read`. No such CI credential is configured here. Its
setup and trust boundary require separate approval; do not expose it to untrusted
PR code or use `pull_request_target` to run that code with secrets. A future
checkout must select the exact documented Kit commit, use
`persist-credentials: false`, verify the revision and cleanliness, and require
zero Kit-related skips. A substitute fixture, copied internal source or a public
visibility change does not close this coverage gap. No access setting or
credential was changed for this check.

Syntax compilation includes experiments but does not execute them. Metadata
validation never runs contributed commands. Repository tests themselves are
executable PR code.

The release owner should require both matrix jobs and appropriate code review
before merge. Branch protection, outside-fork behavior, host integrations and
live service behavior need their own recorded checks; this file does not certify
that those controls are already configured.

For a review record, include the revision, environment, exact commands, observed
results, AI slop findings/fixes and remaining limitations. A passing foundation
check does not establish trading performance or complete the community pilot.
