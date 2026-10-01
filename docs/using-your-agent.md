# Which agent do you use?

Run an example, adapt it with your existing agent, then contribute a small
experiment. You need repository access, Git and Python 3.11+. No Python packages,
Skylit key or model are needed for the offline examples. On Windows, replace
`python3` with `py -3`; native Windows execution remains unverified.

Lab currently provides deterministic Python workflows. Your coding agent can
help run, explain and edit them; the workflows themselves do not call a model or
act autonomously. Agent subscriptions and model-provider credentials are separate
from a Skylit key. Both repositories are INTERNAL, so a key does not grant GitHub
access. There is no released Lab installer or self-contained Watchlist bundle yet.

## Choose a path

| What you already use | How to use Lab today | Evidence and limits |
|---|---|---|
| Terminal / standalone Python | [Run the offline example](#run-the-offline-example), then copy an experiment | Local Python 3.11.14 / 3.14.5 on macOS arm64 verified; no model needed |
| Codex or Claude Code | [Open a repository session](#codex-or-claude-code), paste the prompt, review commands and changes | Lab execution through either host is unverified |
| OpenClaw or another skill-capable agent | [Use its existing workspace and command tools](#skill-capable-hosts) | Skill support alone does not provide Python or shell access; no Lab skill is shipped |
| A chat host with MCP only | [Use a terminal for Lab](#mcp-only-hosts); direct Skylit tools are a separate integration | An MCP connection does not install or execute Lab; host support is unverified |
| Meta Muse Code (provisional) | [Follow the discovery limits](#muse-code-provisional) and use the terminal route meanwhile | Only version/help discovery for 1.4.2; no model-driven Watchlist run verified |

All paths lead to the same [contribution walkthrough](#make-a-contribution).
See the [host matrix](host-matrix.md) for evidence required before claiming support.

## Run the offline example

Clone into a new directory. If you already have Lab, use its root rather than
overwriting or resetting that checkout. Review [AGENTS.md](../AGENTS.md) first.

```sh
git clone https://github.com/SkylitAI/skylit-agent-lab.git
cd skylit-agent-lab
python3 templates/experiment/run.py
```

Open `templates/experiment/reports/example.md`. It contains fictional observations
and a visible `Not provided` gap. Change one note in the template's `fixture.json`
and rerun to see the change. This template replaces its generated report on rerun;
it refuses an output path that would overwrite the input fixture.

For fictional GEX, VEX and flow, follow the
[Watchlist setup](../experiments/watchlist-investigator/README.md). It obtains
a **separate Kit checkout at the exact pin** and prints the private report path.
Keep that checkout clean. Subsequent Watchlist runs require a new output filename;
existing reports are preserved. Setup may access GitHub; rendering uses no network.

Once both clean checkouts are available, the [local setup helper](local-watchlist-setup.md)
creates a separate workspace and renders its first fictional report in one
command. It uses only local files and leaves the source checkouts unchanged.

## Codex or Claude Code

Open Lab as the working repository in your existing agent. Confirm it can read
the checkout and run Python in the chosen environment; a remote workspace may
need its own repository access and Python. Keep private vaults outside the session.
Use the prompt below, then follow [local key setup](#use-your-skylit-key-locally)
only when you choose live use. Contribute through [the same checks and PR path](#make-a-contribution).

```text
Work only in this Skylit Agent Lab checkout. Read AGENTS.md,
docs/using-your-agent.md and the selected example's README. Check Git and
Python 3.11+, run the standalone template offline, and show me its report.
Explain which observations are fictional and which inputs are missing.
If I choose Watchlist, follow its exact pinned-Kit setup and use a new output
filename. Preserve existing checkouts and reports. Do not request keys in chat,
read private vaults, make live calls or publish anything from this setup prompt.
When I ask to contribute, help copy the template, update its manifest and
synthetic example, run the relevant checks, and prepare a small reviewable diff.
Report commands actually run, failures, skipped tests and unverified host support.
```

Use your host's existing login. A Skylit key does not authenticate Codex or
Claude. Host features and account requirements are described in the official
[Codex quickstart](https://developers.openai.com/codex/quickstart) and
[Claude Code overview](https://code.claude.com/docs/en/overview), checked 2026-10-01.
These references establish available interfaces, not Lab certification.

## Skill-capable hosts

For OpenClaw or another agent, use a reviewed repository workspace with Python
and command execution available. Read the example before allowing it to run;
manifest command metadata is not execution permission. Paste the shared prompt
if your host supports that workflow. Otherwise use the terminal steps and ask
your agent to help edit the local example. Then use the same local-key and
contribution sections below.

[Agent Skills](https://agentskills.io/specification) packages instructions and
optional scripts; the host still determines executable tools and permissions.
Lab does not currently ship an installable skill or a `/watchlist` command.
Do not invent an install command or assume the current directory isolates a
host's wider workspace. [OpenClaw discovery](host-matrix.md#documented-interfaces-and-limits)
records that distinction. Keep any host-specific wrapper thin and document its
actual version, permissions and observed result before adding `tested_hosts`.

## MCP-only hosts

An [MCP connection](https://modelcontextprotocol.io/docs/learn/architecture)
exposes server capabilities; it does not give a chat host a local Python runtime.
If your host lacks reviewed command/file tools, run Lab in a terminal and share
only the synthetic result for explanation. Use Git or a coding agent to make
and check a contribution.

Optional direct Skylit MCP setup is documented in Kit's
[Codex](https://github.com/SkylitAI/skylit-agent-kit/blob/0f82039759ef4db9d5b3dbd90f52863f8074f2a6/agents/codex/README.md)
and [Claude](https://github.com/SkylitAI/skylit-agent-kit/blob/0f82039759ef4db9d5b3dbd90f52863f8074f2a6/agents/claude/README.md)
guides. That connection is separate from Lab, and its calls do not inherit Kit's
local runner budget caps. Follow the host's secure authorization UI; do not put
keys in a prompt or assume a successful connection certifies Watchlist.

## Muse Code (provisional)

Here “Muse” means **Meta Muse Code**, provisionally, not a personal assistant with
a similar name. The [discovery record](evidence/muse-feasibility.md) verified
version/help for `1.4.2 (1.4.2-R4684.1)` and describes its advertised workspace
tools. The [official overview](https://dev.meta.ai/docs/muse-code) documents the
CLI surface. No authenticated model run, Lab skill or Watchlist execution has
been verified. Use the terminal example and contribution path today; an existing
Muse session may help review files only within its actual available permissions.
Model entitlement and credentials are separate from Skylit access.

## Use your Skylit key locally

**Lab Watchlist has no live mode yet.** Its `run.py` accepts synthetic fixtures,
not API keys. For supported CLI syntax today, use the existing pinned Kit
checkout created by the Watchlist setup. Its REST live path has synthetic tests;
authenticated end-to-end verification remains pending.

From that **Kit root**, first inspect the free plan:

```sh
python3 -m skylit_agent_kit watchlist --dry-run
```

Create/manage your Skylit key in the [Developer page](https://app.skylit.ai/developer).
When you explicitly choose a live run, this command can consume service credits:

```sh
python3 -m skylit_agent_kit watchlist --live --max-credits 10 --max-requests 12 --max-seconds 120 --output reports/watchlist-first-live.md
```

Use your own interactive terminal: the runner asks for the key with typing hidden
when `SKYLIT_API_KEY` is absent. An already securely configured process environment
is also supported; the runner does not load `.env` files automatically. A host
without a hidden terminal prompt should direct you to your terminal rather than
collecting the key in chat. Never commit keys, private inputs or live reports.

The caps cover requests, documented credit reservations and elapsed checks, not a
hard process deadline or a lock on shared account spending. A smaller account
batch may stop the plan before paid calls. Read Kit's
[live guide](https://github.com/SkylitAI/skylit-agent-kit/blob/0f82039759ef4db9d5b3dbd90f52863f8074f2a6/docs/live-watchlist.md)
for limits. Use a new output name on later runs; preserve source attribution and
check data-sharing terms before sharing. This standalone mode needs no LLM key.

## Make a contribution

Use a clean checkout based on `main` and a new branch. Preserve unrelated work;
use a separate checkout if needed. Your agent can perform these steps with you.

```sh
git switch -c experiment/my-experiment
python3 -c "import shutil; shutil.copytree('templates/experiment', 'experiments/my-experiment', ignore=shutil.ignore_patterns('reports', '__pycache__', '*.pyc'))"
```

The copy refuses an existing destination and excludes generated reports. In
`experiments/my-experiment/experiment.json`, set `id` to `my-experiment`, replace
`owner` with your own `@GitHub-handle`, and describe your purpose, command, access,
costs and sources. Keep `tested_hosts` empty until you have actual host evidence.
Edit the copied synthetic fixture/code, README and expected output together.

```sh
python3 experiments/my-experiment/run.py
python3 scripts/validate_experiments.py
python3 -m unittest discover -s tests -v
python3 -m compileall -q scripts tests templates/experiment experiments
```

Inspect the report and diff. Add behavior tests for new logic. If your experiment
uses Kit, follow [the full local check](checks.md) with the exact pin and report
any skips. Foundation CI without Kit does not verify Kit consumption. A passing
manifest never proves source permission, host support or trading performance.

Follow [CONTRIBUTING.md](../CONTRIBUTING.md) to submit a focused PR with your exact
commands, results, source disclosures and limitations. Review generated commands
before executing them and keep output private by default. Outside contributors
need repository access until a public preview and fork workflow are verified.

## If setup stops

| Symptom | Next step |
|---|---|
| GitHub denies access | Request repository access; a Skylit key cannot fix GitHub permissions |
| Python is missing or too old | Check Python 3.11+ in the environment that actually runs commands; on Windows try `py -3 --version` |
| Kit revision/cleanliness refused | Use the documented separate pinned checkout; do not reset unrelated changes |
| Watchlist output already exists | Choose a new `--output` filename |
| No hidden key prompt in the host | Use your own interactive terminal for the Kit live command |
| Access, credit or request cap failure | Read the sanitized error and account limits; do not auto-increase caps or retry |
| Tests report skips | Supply the pinned Kit as described in checks.md before claiming full runtime verification |

The local helper does not obtain the repositories or install prerequisites.
Remaining download-key-run gaps are a distributable setup path, Lab's own bounded
live runner with run records, and authenticated service/host evidence. The examples
above do not claim those deliverables are complete.
