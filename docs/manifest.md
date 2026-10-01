# Experiment manifest v1

Each experiment lives directly under `experiments/<id>/` and contains an
`experiment.json` file. The required copy template is
`templates/experiment/experiment.json`; its ID is always `example-experiment`.
The template is validated independently and does not reserve that ID for actual
experiments. A repository with no actual experiments is valid.

Run the validator with Python 3.11 or later:

```sh
python3 scripts/validate_experiments.py
python3 scripts/validate_experiments.py --root /path/to/skylit-agent-lab
```

The default root is the project containing the validator script, regardless of
the working directory. Success prints template and experiment counts and exits
with status 0. Validation failures print file/field diagnostics and exit with
status 1. Problems are collected across manifests when those files can be read;
a JSON parsing failure is reported before field validation can proceed.

The validator scans only direct child directories of `experiments/`. Every such
directory must have a manifest, including hidden directories. Files such as
`experiments/README.md` are ignored. Nested directories are not independently
discovered as experiments. Symlinked experiment entries, manifests, and template
or experiment container directories are rejected.

## Required fields

Every listed root field is required. Unknown root fields and unknown fields in
the structured objects below are rejected.

| Field | Contract |
| --- | --- |
| `schema_version` | The integer `1`. Booleans, strings, and `1.0` are invalid. |
| `id` | A lowercase slug: lowercase letters/digits separated by single hyphens. For actual experiments, it must equal the containing directory name and be unique among actual experiments. |
| `purpose` | A nonblank explanation of the experiment's purpose. |
| `owner` | An `@`-prefixed GitHub handle. The handle has 1–39 ASCII letters, digits, or hyphens, with no leading, trailing, or consecutive hyphens. The copy template uses `@prodij`; set the owner when adopting a copy. |
| `status` | One of `experimental`, `reproduced`, `maintained`, `graduated`, or `archived`. |
| `command` | A nonempty array of nonblank strings describing a command and its arguments. These strings are inert metadata and are never executed, imported, interpolated, or passed to a shell by validation. |
| `inputs` | An array of experiment-relative paths to existing regular files. May be empty. |
| `outputs` | A nonempty array of experiment-relative output file paths. They and their parent directories may be absent. If present, an output must be a regular file and its parents must be directories. |
| `access` | A nonblank human explanation of required access, credentials, network use, or their absence. |
| `cost` | A nonblank human explanation of expected costs or their absence. |
| `tested_hosts` | An array of host evidence objects, described below. May be empty. |
| `sources` | A nonempty array of provenance objects, described below. |
| `kit` | `null` when unused; otherwise the pinned kit object described below. |

All manifest files must be UTF-8 JSON objects, at most 65,536 bytes (64 KiB),
with no duplicate keys at any object level. JSON constants such as `NaN` and
`Infinity`, as well as numbers that overflow to infinity, are rejected.

### Host evidence

Each `tested_hosts` entry has exactly these fields:

```json
{
  "name": "Example host",
  "version": "1.0",
  "evidence": "evidence/example-host.md"
}
```

`name` and `version` are nonblank strings. `evidence` must identify an existing
regular file within the experiment directory. Use `[]` until an actual host
test has been recorded. File existence does not establish that its contents
demonstrate compatibility.

### Source provenance

Each `sources` entry has exactly these fields:

```json
{
  "kind": "synthetic",
  "reference": "fixture.json",
  "license": "CC0-1.0"
}
```

`kind` is `synthetic`, `public`, or `academy`. `reference` and `license` must be
nonblank strings. A reference can be a human-readable citation, URL, or local
file reference; the validator does not fetch it or interpret it as a file path.
Neither a source category nor a license string grants permission to use material.
Record the actual provenance and applicable rights rather than copying example
values onto unrelated material.

### Optional kit use

The `kit` field is required even when the kit is unused, in which case it is
`null`. When used, the object must contain exactly:

```json
{
  "repository": "https://github.com/SkylitAI/skylit-agent-kit",
  "revision": "0123456789abcdef0123456789abcdef01234567"
}
```

The repository value must match exactly. The revision must be a full, lowercase
40-hex commit SHA. The SHA above only illustrates the format; substitute a real
commit before use. The validator does not contact GitHub, verify that a revision
exists, install dependencies, or read the kit repository.

## Path rules

`inputs`, `outputs`, and host `evidence` paths are relative to the directory
containing their manifest. Use forward slashes, such as `fixtures/sample.json`.
Absolute paths, colons anywhere in a path, backslashes, control characters,
empty components, and `.` or `..` components are invalid. Rejecting colons also
blocks nested Windows drive components (`sub/D:outside.md`, `sub/C:/outside.md`)
and NTFS alternate data streams (`report.md:stream`). Consequently `./sample.json`,
`sample//data.json`, and trailing slashes are invalid too.

No path component may be a symlink, including links that point inside the
experiment or have a missing target. Inputs and host evidence must already be
regular files; directories and special files are invalid. Duplicate entries
within `inputs` or `outputs` are rejected, as is an exact path appearing in both
lists. Comparison uses the supplied relative path strings; hard links and
filesystem-specific aliases are not an isolation mechanism.

## What passing means

Passing establishes the manifest's structure and the checked local file state.
It does not certify the owner's identity, source rights, host support, security,
command behavior, cost estimates, output quality, or the claimed maturity level.
Commands and evidence require human review and separate execution or inspection.
Validation is a local preflight check, not a sandbox: it cannot prevent files
from changing after a check. Keep experiments reproducible and use appropriate
execution isolation when running code.
