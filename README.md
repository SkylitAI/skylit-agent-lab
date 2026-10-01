# Skylit Agent Lab

Build and share trading research experiments using your chosen agent. Lab holds
community experiments; [Agent Kit](https://github.com/SkylitAI/skylit-agent-kit)
holds maintained tools and starter workflows. Useful Lab work can graduate into
Kit through review.

**Status: contributor foundation and an offline Watchlist Investigator.** The
examples use fictional observations and need no account, API key, model or
installed packages to run. Agent integrations are planned; this repository does
not yet certify any agent host or live service. Repository access is required
while the pilot is INTERNAL.

## Run the example

Requires Git and Python 3.11 or newer. On Windows, use `py -3` for Python commands.

```sh
git clone https://github.com/SkylitAI/skylit-agent-lab.git
cd skylit-agent-lab
python3 templates/experiment/run.py
```

Open `templates/experiment/reports/example.md`. It shows two fictional watchlist
notes and labels missing information. Change a note in
`templates/experiment/fixture.json`, rerun, and see the output change.

For a fictional GEX, VEX and flow report, try
[Watchlist Investigator](experiments/watchlist-investigator/README.md). Its guide
shows how to obtain a separate pinned Kit checkout, select symbols and save a
local report while keeping missing components visible.

## Contribute an experiment

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
