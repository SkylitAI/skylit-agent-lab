# Skylit Agent Lab

Build and share trading research experiments using your chosen agent. Lab holds
community experiments; [Agent Kit](https://github.com/SkylitAI/skylit-agent-kit)
holds maintained tools and starter workflows. Useful Lab work can graduate into
Kit through review.

**Status: three runnable research seeds: Watchlist Investigator, Journal Reviewer
and Market Brief.** Their defaults use fictional inputs and need no account,
API key, model or installed Python packages. Only Watchlist requires a pinned
Agent Kit checkout. Agent integrations are planned; this repository does
not yet certify any agent host or live service. Repository access is required
while the pilot is INTERNAL.

## Which agent do you use?

Use the agent you already have, or run Python directly. Start with
[the agent guide](docs/using-your-agent.md): it covers **Codex, Claude Code,
OpenClaw and other skill-capable hosts, MCP-only hosts, standalone Python, and
provisional Muse Code**. It includes a copyable prompt and one contribution path.
The Python examples are tested locally; host-driven runs remain unverified.

A Skylit API key is separate from your agent's subscription or model-provider
credentials. The default examples are **offline deterministic workflows**. A separate
[opt-in live entry point](docs/using-your-agent.md#use-your-skylit-key-locally)
uses the pinned Kit client; authenticated verification remains pending.
An API key alone does not grant access to these INTERNAL repositories.

## Choose an offline workflow

| What you want to inspect | Workflow | Inputs and limits |
|---|---|---|
| GEX, VEX and flow observations with visible gaps | [Watchlist Investigator](experiments/watchlist-investigator/README.md) | Fictional defaults; requires the exact pinned Kit checkout |
| Closed paper-trade rows and entered notes | [Journal Reviewer](experiments/journal-reviewer/README.md) | Fictional defaults or explicit closed USD cash-equity paper CSV; no inferred strategy or tax analysis |
| Dated entries from one press-release feed | [Market Brief](experiments/market-brief/README.md) | Fictional defaults or saved RSS; selects 1–20 entries, not broad market analysis |

Requires Git and Python 3.11 or newer. On Windows, use `py -3` for Python commands.

```sh
git clone https://github.com/SkylitAI/skylit-agent-lab.git
cd skylit-agent-lab
```

From the Lab root, run either of these without Kit, keys or a model:

```sh
python3 -X utf8 -I -B experiments/journal-reviewer/run.py
python3 -X utf8 -I -B experiments/market-brief/run.py
```

Each prints a private Markdown report and `.run.json` sidecar path. Records stay
local and describe the Python process; they are not adoption telemetry or a
measurement of your launching agent. Writes are not atomic: check exit status
and both files. Choose a new `--output` path on later runs; existing files are
preserved. Market's explicit `--fetch` option attempts one bounded unauthenticated
Federal Reserve RSS request; it is never the default. See its guide before fetching.

For a fictional GEX, VEX and flow report, try
[Watchlist Investigator](experiments/watchlist-investigator/README.md). Its guide
shows how to obtain a separate pinned Kit checkout, select symbols and save a
local report while keeping missing components visible.

Already have clean Lab and pinned Kit checkouts? [Prepare a local Watchlist
workspace](docs/local-watchlist-setup.md) with one command. It copies committed
files into a new directory and runs the fictional demo; no key or network is used.

## Contribute an experiment

For the smallest editable scaffold, run `python3 templates/experiment/run.py`
and open `templates/experiment/reports/example.md`. Then copy the template:

```sh
python3 -c "import shutil; shutil.copytree('templates/experiment', 'experiments/my-experiment', ignore=shutil.ignore_patterns('reports', '__pycache__', '*.pyc'))"
```

Run this from the repository root (replace `python3` with `py -3` in Windows
PowerShell). It excludes generated reports and
bytecode. Choose a new directory name if `my-experiment` already exists; the copy
does not overwrite an existing experiment.

Set the copied `experiment.json` ID to `my-experiment`, use your GitHub handle as
owner, and describe your purpose, commands, inputs, costs and sources. Replace
the example code and fixture with your experiment, then update its README and
expected output. Keep private reports and credentials out of Git.

```sh
python3 scripts/validate_experiments.py
python3 -m unittest discover -s tests -v
```

Read [the contribution guide](CONTRIBUTING.md) before opening a PR. The validator
checks metadata and file paths; it never runs an experiment's declared command.
It does not certify its safety, sources, performance or agent compatibility.

## Find your next step

| Task | Guide |
|---|---|
| Understand the package fields | [Manifest contract](docs/manifest.md) |
| Run or adapt the template | [Template guide](templates/experiment/README.md) |
| Test local watchlist rendering through a pinned Kit checkout | [Kit consumer probe](docs/kit-consumer.md) |
| Understand current scope and next work | [Release scope](docs/release-scope.md) |
| Find the maintainer | [Ownership](docs/maintainers.md) |
| Reproduce the checks | [Checks](docs/checks.md) |
| Handle sources or report a possible leak | [Security and sources](SECURITY.md) |

Code is MIT licensed. Synthetic fixture licensing is recorded in each package's README.
Software licensing does not include Skylit service access or third-party data
rights. [Skylit Academy](https://www.skylit.ai/learn/reading-heatseeker) is the
educational source for future Skylit examples; use
[public API documentation](https://www.skylit.ai/docs/api-reference/getting-started)
for integration contracts.
