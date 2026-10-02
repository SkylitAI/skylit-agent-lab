# Contribute to Agent Lab

Start with a small experiment, a reproducible bug, an improved explanation or an
independent reproduction. Use issues for proposals and focused PRs for changes.
Repository access is currently limited by its INTERNAL visibility; the outside
fork workflow will be tested when a public preview opens.

Using an existing coding agent? Follow [Which agent do you use?](docs/using-your-agent.md)
for the shared prompt, offline setup and contribution walkthrough. A terminal
works too; no model is required to contribute a deterministic example.

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
python3 -m compileall -q scripts tests templates/experiment experiments
```

For Kit-dependent experiments, follow [the full local check](docs/checks.md)
with the pinned Kit checkout. Record skipped tests explicitly; a foundation CI
pass without Kit does not verify those integrations.

CI validates manifests and runs the explicitly reviewed tests/template. A new
experiment's command is not automatically executed. Reviewers inspect code and
dependencies before choosing to run it in a suitable isolated environment.
Never give untrusted PR code production secrets, private vault access or a
self-hosted runner with privileged credentials.

## Submitting from a local workspace

The setup helper's workspace contains a `lab/` Git checkout. Enter it with
`cd lab` before running contribution commands. Its `origin` points to the local
source checkout, so pushing to `origin` does not submit a GitHub contribution.

Inspect `git remote -v`. If you have repository write access and no existing
remote named `github`, add the repository as a separate remote:

```sh
git remote add github https://github.com/SkylitAI/skylit-agent-lab.git
git push -u github HEAD
```

Review the staged diff and commit only your intended source changes before
pushing. Open a draft PR for that branch through GitHub. If `github` already
exists, verify its destination instead of replacing it. Contributors without
write access need an authorized fork or maintainer-assisted route; INTERNAL
visibility currently limits outside access. Do not push generated reports or keys.

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
| reproduced | A non-author human independently reproduced the pinned example and recorded the result |
| maintained | Reproduction evidence and a named human's explicit acceptance of scoped maintenance |
| graduated | Maintained requirements, accepted Kit change/versioned release, attribution and a verified Lab migration |
| archived | Reason for archiving and any maintained replacement |

The validator checks allowed status values, not the truth of those claims. Start
new submissions as `experimental`. A useful experiment may stay in Lab; promotion
requires demand, repeatable setup, relevant tests, documented permissions/costs and
an owner. Lab consumes the released Kit implementation after graduation. Kit must
not depend on unreleased Lab code.

Follow [ownership and promotion](docs/governance.md) for reviewed status changes,
missing-owner handling and evidence required to move a capability into Kit.
