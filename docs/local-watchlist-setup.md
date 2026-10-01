# Prepare a local Watchlist workspace

Create a separate workspace and its first fictional report in one command, using
Lab and Kit checkouts you already have. The setup copies committed Git files,
pins Kit, runs the existing offline Watchlist and writes a reusable launcher.
It does not download repositories, provision keys or run a model/live service.

## Prerequisites

- Python 3.11+ and Git available in the environment that runs the command.
- This full Lab Git checkout, with changes committed and no untracked files.
- A separate clean Kit Git checkout at
  `0f82039759ef4db9d5b3dbd90f52863f8074f2a6`. Use the existing
  [Watchlist setup instructions](../experiments/watchlist-investigator/README.md)
  to obtain it. Both repositories are INTERNAL and require GitHub access.
- A new destination outside both source checkouts, with an existing parent.
  Preserve work in a dirty checkout; use a separate clean checkout rather than
  resetting or discarding changes.

No Python packages, API key or model subscription are needed. Setup has local
disk/compute costs only. Native Windows execution remains unverified; in
PowerShell, replace `python3` with `py -3`.

## Create the workspace

From the Lab root, after obtaining the pinned Kit checkout:

```sh
python3 -X utf8 -I -B scripts/setup_watchlist.py --kit ../skylit-agent-kit-watchlist --destination ../watchlist-workspace
```

The command checks both sources before creating anything. It refuses an existing
destination, including an empty directory or symlink. It does not change either
source checkout, fetch remote objects or copy ignored local files such as `.env`
and generated reports. Only committed files and Git history are cloned; this is
a private local workspace, not a reviewed public distribution archive.

On success it prints the absolute workspace and report paths. The workspace has:

- `lab/` and `kit/`: independent local Git clones at recorded revisions.
- `reports/watchlist.md`: the initial fictional SPY/QQQ report with visible gaps.
- `run_watchlist.py`: a launcher for the existing offline runner.
- `setup.json`: setup revisions and the initial report path, not a workflow run record.

The workspace directory uses owner-only permissions on POSIX, and the existing
runner saves the report with owner-only permissions. The copies retain local Git
origins pointing to their source checkouts. They are detached; choose a branch
before editing the Lab copy. The originals remain unchanged.

## Run again or customize

From the new workspace:

```sh
python3 run_watchlist.py --symbols QQQ,SPXW --output reports/second.md
```

Open `reports/second.md`. Missing symbols remain gaps. The launcher forces UTF-8
for the runner and uses its bundled Kit checkout; it does not collect or pass
API keys. An existing report or output symlink is refused. Always choose a new
output filename. The default output stays inside the workspace; explicit relative
`--output` and `--fixture` paths are relative to your current directory.

Use the existing [runner options](../experiments/watchlist-investigator/README.md)
to select symbols, a synthetic fixture or a fictional reference time. Keep Kit
at its clean exact pin. A modified Lab copy can be used for local experimentation;
the launcher does not certify those edits. Follow the
[contribution walkthrough](using-your-agent.md#make-a-contribution) to prepare a
reviewable change through your existing agent or a terminal.

## If setup stops

Wrong pins, dirty sources, invalid paths and existing destinations fail before
creating a workspace. A later clone, rendering or write failure can leave a
private directory marked `.setup-incomplete`. Setup returns nonzero and refuses
to reuse it. Inspect that directory and choose a new destination after fixing the
reported cause. A successful setup removes the marker; do not remove it to imply
that a failed setup completed. Setup never deletes an existing directory for you.

This helper closes the manual local-copy-and-launch step only. Repository access,
Git, Python and obtaining the pinned Kit are still prerequisites. Lab Watchlist
still has no live mode, no installable agent skill and no autonomous model loop.
For explicitly chosen live use, the [agent guide](using-your-agent.md#use-your-skylit-key-locally)
describes the separate Kit command and its remaining verification limits. No host,
authenticated service or public download workflow is certified by this helper.
