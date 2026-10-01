# Fictional observation example

This package demonstrates the contribution format. It writes a small report from
two made-up watchlist observations. It is not a trading strategy or factual
market analysis. No account, key, network or model is used.

From this directory, with Python 3.11+:

```sh
python3 run.py
```

The printed path is `reports/example.md`; compare it with `expected.md`.
Edit a note or symbol in `fixture.json` and rerun. A `null` note stays visible as
`Not provided`. Notes are treated as text, not Markdown or instructions. You can
also pass `--fixture PATH` and `--output PATH`. Relative custom paths are resolved
from your current directory. An existing output report is replaced; an output
that points to the input fixture is rejected so it cannot destroy that input.

To contribute, use the [repository copy command](../../README.md#contribute-an-experiment)
to create `experiments/<your-id>/` without generated reports or bytecode, update
the manifest ID and owner, and describe your own example. Reports are ignored by
Git. The manifest's command runs from the experiment directory. Its paths are relative to that same
directory, even when validation runs from the repository root.

## Sources and limits

`fixture.json` and `expected.md` were independently authored as synthetic data.
SkylitAI dedicates those two files to the public domain under
[CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/). Code is covered by
the repository's MIT license. New contributors must state the actual rights for
their own inputs; copying this manifest does not grant rights to third-party data.

No agent host has been certified for this template. `tested_hosts` is empty and
`kit` is null because this standalone demonstration does not depend on Agent Kit.
The metadata validator does not test the experiment or verify provenance.
