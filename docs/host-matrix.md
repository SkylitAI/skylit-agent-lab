# Watchlist host discovery matrix

The [offline Watchlist package](../experiments/watchlist-investigator/README.md)
can render a fictional report through a pinned local Kit checkout. Its Python
tests do not demonstrate an agent host invoking it. **Every host below remains
unverified for Watchlist.** No live mode exists in the package.

Discovery date: **2026-10-01**. Observed CLI versions came from macOS arm64;
there is no Windows certification. No host configuration or adapter ships
with this matrix, and the experiment's `tested_hosts` stays empty.

| Candidate | Version evidence | Candidate integration surface | Offline Watchlist | Live Watchlist | Auth/access |
|---|---|---|---|---|---|
| Claude Code | Maintainer CLI discovery: `2.1.145` | Repository skill plus reviewed command execution | Unverified | Unverified | Unverified |
| OpenClaw | Maintainer CLI discovery: `2026.6.33 (7af0cfc)` | Workspace skill plus reviewed command execution | Unverified | Unverified | Unverified |
| Muse Code (provisional target) | Independently repeated version/help: `1.4.2 (1.4.2-R4684.1)` | Headless `exec` and policy-gated workspace tools | Unverified | Unverified | Unverified |
| Custom agent | No framework selected; no version evidence | Invoke the documented Python command with an explicit local Kit path | Unverified | Unverified | Unverified |

## Documented interfaces and limits

[Claude Code's skills documentation](https://code.claude.com/docs/en/skills)
describes repository skills at `.claude/skills/<name>/SKILL.md`, direct
`/name` invocation and `disable-model-invocation: true` for user-only
invocation. `allowed-tools` grants tool permissions; it is not a restriction
that removes other available tools. A future probe must review actual runtime
permissions and verify the contract against the recorded CLI version.

[OpenClaw's skills documentation](https://docs.openclaw.ai/tools/skills)
describes `<workspace>/skills` and `<workspace>/.agents/skills` sources.
The configured agent workspace can remain the skill source during managed
worktree runs, so the current working directory alone does not establish
context isolation. Skill eligibility does not grant tool access, and a binary
found on the host must also be available inside a sandbox when one is used.

These current documentation pages describe candidate integration paths; their
contents are not version-specific execution evidence for the discovered
Claude Code and OpenClaw binaries.

[Muse Code discovery](evidence/muse-feasibility.md) records its verified binary
hash, four successful help/version commands, advertised input/output controls
and unknown authentication status. This is technical feasibility evidence,
not a completed Watchlist run. The target remains provisional if the intended
Muse was a personal agent instead of Meta's Muse Code.

A custom agent can use the package's existing command without a new framework.
No custom agent runtime, skill or wrapper has been selected or tested.

## Evidence needed for a verified row

Record the exact host version, OS, Kit revision, workspace and permission setup
without secrets, plus the command actually executed and its observed outcome.
The host must produce the fictional report with selected symbols and missing
data still shown as gaps, and expose command failures without claiming success.
Authentication or costs, if required by that host, must be stated separately
from the package's credential-free offline rendering. Keep output local and
private by default. No row is promoted by documentation or manifest validation
alone; see the [manifest's host evidence contract](manifest.md#host-evidence).
