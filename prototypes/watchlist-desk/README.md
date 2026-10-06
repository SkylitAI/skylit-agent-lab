# Watchlist Desk Docker proof

Build a local viewer from two fictional Watchlist snapshots using the existing
pinned Kit parser. One structured result feeds both JSON and HTML. This is a
bounded architecture probe, not an installable agent, live integration or stable
evidence API. The existing experiments and manifest/run-record contracts are
unchanged. Python 3.11+ standard library only.

The before input is the repository's CC0 Watchlist fixture. The independently
authored after variation sets SPY gamma at strike 110 to -199, advances board
times by ten minutes, changes vanna expiration coverage and removes flow.
QQQ remains unavailable. Gamma 110 changes by -19; gamma 115 is unchanged;
vanna is not comparable. Missing observations never become zero. Code is MIT;
these synthetic variations are CC0-1.0. No private material or domain scoring is
used. Values are in the fixture's unspecified source scale, not asserted units.

## Run locally

Read the Watchlist Investigator guide for the required clean Kit checkout at
`0f82039759ef4db9d5b3dbd90f52863f8074f2a6`. From Lab:

```sh
python3 -X utf8 -I -B scripts/watchlist_desk.py --kit /path/to/pinned-kit --output reports/desk-first
```

Open `reports/desk-first/index.html`. Use a new directory on each run. Customize
with `--gamma-value -210` (delta -30) or `--symbols QQQ,SPXW` (explicit gaps).
Generated synthetic inputs, parsed evidence, comparison and artifact hashes are
saved together. `proof.json` is written last; it is a prototype completion marker,
not a Lab v1 run record, atomic transaction or authenticated network audit.
The Docker build also supplies `baseline.md` and its existing Lab run record.

## Docker build contract

The Dockerfile expects an explicitly staged context with `lab/` and `kit/`.
Stage only reviewed repository sources, no ignored files or credentials. Kit must
retain sanitized Git metadata at its exact pin for runtime verification. Do not
use a home directory as build context. See the recorded local trial for the actual
environment and commands. Image setup can download the pinned public Python base
and Git packages. All synthetic generation runs with Docker networking disabled.

The image generates the existing Watchlist report and sidecar, the prototype
viewer, and runs its focused tests during build. Test again with `--network none`,
read-only source, dropped capabilities and a temporary writable `/tmp`.
Serve the baked synthetic viewer on a loopback-published port using Docker's
standard bridge, no host mounts and a read-only container. The viewer network
permits outbound traffic; the static server does not initiate it. Execution tests
use `--network none` separately. This is a local demo
server, not deployment infrastructure. No image is pushed.

From the Lab root, using new staging/resource names:

```sh
python3 prototypes/watchlist-desk/prepare.py --kit /path/to/pinned-kit --output /tmp/skylit-desk-context
docker build -t skylit-desk:local /tmp/skylit-desk-context
docker run --rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges --pids-limit 64 --memory 256m --cpus 1 --tmpfs /tmp:rw,noexec,nosuid,nodev,size=128m,mode=1777 skylit-desk:local python -B -m unittest discover -s tests -p test_watchlist_desk.py -v
docker run -d --name skylit-desk-local --network bridge --read-only --cap-drop ALL --security-opt no-new-privileges --pids-limit 64 --memory 256m --cpus 1 -p 127.0.0.1:8765:8080 skylit-desk:local
```

Open `http://127.0.0.1:8765`. The preparer reads tracked working-tree files and an
explicit allowlist of prototype additions. It excludes ignored files and source
Git history, records exact Lab file hashes in `lab/source-snapshot.json`, and uses
the existing sanitized staging helper for the clean pinned Kit. Review tracked
sources before running. A failed staging operation leaves an incomplete directory;
choose a new output on retry. It neither changes nor commits your source checkout.

Stop and remove only these demo resources when finished:

```sh
docker rm -f skylit-desk-local
docker image rm skylit-desk:local
```

## Tests and boundaries

`tests/test_watchlist_desk.py` tests real Kit parsing when the pinned checkout is
available, changed input, gaps, expiry/time mismatches, duplicate strike identity,
HTML escaping and no-overwrite behavior. Missing Kit explicitly skips integration
coverage. Run all repository tests before promoting this prototype.

Only fixed synthetic fixtures are accepted by the CLI. Comparison functions are
internal consumers of Kit-parsed data, not general untrusted JSON ingestion APIs.
They compare gamma and vanna separately at matching strikes/expiry sets with later
source times. Flow is displayed only. Matching fields does not establish market
freshness, session alignment, units across providers or a trading conclusion.
The proof does not validate a model's interpretation or newcomer usability.
