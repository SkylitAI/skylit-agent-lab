# Skylit Agent Lab

Build and share trading research experiments using your chosen agent. Lab holds
community experiments; [Agent Kit](https://github.com/SkylitAI/skylit-agent-kit)
holds maintained tools and starter workflows.

**Status: first synthetic template.** It demonstrates a runnable contribution
package, not a trading strategy. No agent host or live service is certified.
Repository access is required while the pilot is INTERNAL.

## Run and change the example

Requires Git and Python 3.11+. On Windows use `py -3` for Python commands.

```sh
git clone https://github.com/SkylitAI/skylit-agent-lab.git
cd skylit-agent-lab
python3 templates/experiment/run.py
```

Open the printed report path. It contains two fictional observations and labels
missing information. Change a note in `templates/experiment/fixture.json`, rerun,
and see the report change. No packages, account, API key, model or network are
needed for the example.

[Template guide](templates/experiment/README.md) · [Source rules](SECURITY.md) ·
[Ownership](docs/maintainers.md) · [Scope](docs/release-scope.md)

## Verify a change

```sh
python3 -m unittest discover -s tests -p test_template.py -v
python3 -m compileall -q tests templates/experiment
```

Manifest validation and the full contribution guide are the next foundation
increment. The manifest is currently descriptive metadata; do not treat it as a
certificate or automatically execute commands from a contributed manifest.

Code is MIT licensed. The template records synthetic fixture rights separately.
Software licensing does not include Skylit service access or third-party data
rights. Use [Academy](https://www.skylit.ai/learn/reading-heatseeker) for future
Skylit educational examples and [public API documentation](https://www.skylit.ai/docs/api-reference/getting-started)
for integration contracts.
