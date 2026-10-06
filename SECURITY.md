# Source and execution boundaries

Use public Skylit Academy material for educational concepts, with lesson title and
link. Use official public API/MCP documentation for technical contracts. Other
inputs need public-reference or independently authored synthetic provenance and
appropriate usage rights.

Never copy, paraphrase, reconstruct or embed private Skylit formulas, weights,
thresholds, calibration, strategies, internal source code or private agent context.
This applies to code, prompts, tests, fixtures, images, reports, comments and Git
history. Renamed variables or fictional inputs do not make a private algorithm
publishable. Do not mount or index private vaults in distributable agent setups.

Do not commit keys, account identifiers, private journals or raw authenticated
responses. Ignore local reports. The separate opt-in live entry point uses documented access
and explicit budgets; its authenticated verification remains pending.

## What validation establishes

The manifest checker reads bounded JSON and checks metadata and package paths. It
does not execute the command field, fetch sources, verify owner identity or prove
that code is safe. It is not a sandbox. Files can change after validation; reviewers
must use the reviewed revision and an appropriate execution environment.

GitHub CI uses hosted runners, minimal token permissions and no production secrets.
It runs repository tests and the reviewed synthetic template. Treat PR changes to
tests and workflow files as executable code requiring review. Do not use
`pull_request_target` to check out and execute untrusted contributions.

## Report a possible disclosure

Do not include the suspected secret, private formula or affected private payload
in a public issue or PR. Use [GitHub private vulnerability reporting](https://github.com/SkylitAI/skylit-agent-lab/security/advisories/new)
and stop further distribution of the affected artifact. If unavailable, contact
the repository owner through an existing private channel. Coordinate credential rotation or history remediation
with the owner. Deleting the latest file alone does not remove Git history.
