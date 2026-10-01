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
