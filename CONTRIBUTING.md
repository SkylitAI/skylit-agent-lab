# Contribute to Agent Lab

Start with a small experiment, a reproducible bug, an improved explanation or an
independent reproduction. Use issues for proposals and focused PRs for changes.
Repository access is currently limited by its INTERNAL visibility; the outside
fork workflow will be tested when a public preview opens.

## Prepare a contribution

1. Read the [README](README.md), [manifest contract](docs/manifest.md) and
   [source rules](SECURITY.md).
2. Branch from `main` (fork first when outside contribution is available).
3. Copy `templates/experiment` into `experiments/<your-id>` and change its ID and
   owner. Supply a real offline command, fixture, expected result and README.
4. Declare actual access, costs, sources and dependencies. Pin a full Kit commit
   if used; use `null` when it is not used. Do not label an untested host supported.
5. Run the checks and inspect the generated report. Add behavior tests for new
   logic and failure cases that matter. Exclude local reports and private inputs.
6. Open a PR describing the user outcome, exact verification and remaining limits.
   The owner reviews code, sources and claims before inclusion.

```sh
python3 scripts/validate_experiments.py
python3 -m unittest discover -s tests -v
python3 -m compileall -q scripts tests templates/experiment
```

CI validates manifests and runs the explicitly reviewed tests/template. A new
experiment's command is not automatically executed. Reviewers inspect code and
dependencies before choosing to run it in a suitable isolated environment.
Never give untrusted PR code production secrets, private vault access or a
self-hosted runner with privileged credentials.

## Before review

Run this AI slop check on the actual change, whether written by a person or AI:

- The opening explains a concrete user task and the output it produces.
- Every documented command works at the submitted revision; no placeholder result
  is described as a completed capability.
- Tests check observable results and relevant failure behavior, not just function
  calls or assertions copied from implementation details.
- New abstractions have a current need; avoid an agent runtime or plugin framework
  for a small script. Remove dead code and repetitive explanations.
- Synthetic data, observations, assumptions and unavailable information are
  distinguishable. Do not turn missing data into invented facts or trade advice.
- Compatibility, live verification, costs and performance claims have evidence.
  A schema pass is not a certification, and a backtest is not a promised return.
- Sources, licensing, ownership and dependencies are explicit. No private formulas,
  credentials, internal agent context or account reports appear in files/history.
- Record findings and corrections in the PR. Fix broken commands and misleading
  claims before asking for review; do not call them future polish.

## Status and promotion

| Status | Required review evidence |
|---|---|
| experimental | Runnable instructions, scope, owner and source disclosures |
| reproduced | A non-author reproduced the pinned example and recorded the result |
| maintained | A named maintainer accepts updates and compatibility review |
| graduated | An accepted Kit change and versioned release, linked with attribution |
| archived | Reason for archiving and any maintained replacement |

The validator checks allowed status values, not the truth of those claims. Start
new submissions as `experimental`. A useful experiment may stay in Lab; promotion
requires demand, repeatable setup, relevant tests, documented permissions/costs and
an owner. Lab consumes the released Kit implementation after graduation. Kit must
not depend on unreleased Lab code.
