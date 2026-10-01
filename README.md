# Skylit Agent Lab

Build and share trading research experiments using your chosen agent. Lab holds
community experiments; [Agent Kit](https://github.com/SkylitAI/skylit-agent-kit)
holds maintained tools and starter workflows. Useful Lab work can graduate into
Kit through review.

**Status: contributor foundation.** The example below uses fictional observations
and needs no account, API key, model or installed packages. Trading workflows and
agent integrations are planned; this repository does not yet certify any agent
host or live service. Repository access is required while the pilot is INTERNAL.

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

## Contribute an experiment

```sh
mkdir -p experiments
cp -R templates/experiment experiments/my-experiment
```

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
| Understand current scope and next work | [Release scope](docs/release-scope.md) |
| Find the maintainer | [Ownership](docs/maintainers.md) |
| Reproduce the checks | [Checks](docs/checks.md) |
| Handle sources or report a possible leak | [Security and sources](SECURITY.md) |

Code is MIT licensed. Synthetic fixture licensing is recorded with the template.
Software licensing does not include Skylit service access or third-party data
rights. [Skylit Academy](https://www.skylit.ai/learn/reading-heatseeker) is the
educational source for future Skylit examples; use
[public API documentation](https://www.skylit.ai/docs/api-reference/getting-started)
for integration contracts.
