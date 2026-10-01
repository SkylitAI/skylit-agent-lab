# Verify a foundation change

From the repository root:

```sh
python3 scripts/validate_experiments.py
python3 -m unittest discover -s tests -v
python3 -m compileall -q scripts tests templates/experiment
python3 templates/experiment/run.py --output /tmp/lab-example.md
diff -u templates/experiment/expected.md /tmp/lab-example.md
```

The metadata checker must reject invalid manifests and return nonzero. Unit tests
exercise missing fields, malformed JSON, invalid statuses, escaping paths and
other boundary cases. They also show that command metadata stays inert. The
template tests check actual output, changed inputs and clear failures.

GitHub Actions runs the same checks on Python 3.11 and 3.14 using synthetic local
inputs and no service credentials. Setup downloads Python and pinned actions;
this workflow does not claim network isolation. Metadata validation never runs
contributed commands. Repository tests themselves are executable PR code.

The release owner should require both matrix jobs and appropriate code review
before merge. Branch protection, outside-fork behavior, host integrations and
live service behavior need their own recorded checks; this file does not certify
that those controls are already configured.

For a review record, include the revision, environment, exact commands, observed
results, AI slop findings/fixes and remaining limitations. A passing foundation
check does not establish trading performance or complete the community pilot.
