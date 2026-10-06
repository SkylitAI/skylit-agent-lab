# Local Docker trial — 2026-10-05 America/Los_Angeles

The synthetic architecture slice ran on this machine. This is an author/agent
engineering trial, not independent human reproduction or agent-host certification.

## Environment and source identity

- Host: macOS arm64; Docker client 29.6.0.
- Docker Desktop 4.79.0 (230596), Engine 29.5.3, Linux arm64.
- Container Python 3.11.17.
- Baseline Lab: `c5a276a43ad9e82d4338ff44d3adfed086ee9ad0`.
- Kit: `0f82039759ef4db9d5b3dbd90f52863f8074f2a6`, separate clean local copy.
- Prototype: uncommitted additions to that Lab baseline. Exact build input hashes
  are in `/work/lab/source-snapshot.json` inside the image. The source directory
  was staged explicitly; ignored files and host credentials were not copied.
- Final image: `sha256:d316d1880ed7ec59ec0593bbd96cb00d2318c94c7c79894cebd0991241869ba2`.

## Checks actually run

Before prototype edits:

```sh
python3 scripts/run_isolated.py --kit /tmp/skylit-desk-FXNgvA/kit --evaluate
```

Isolation passed; all 12 fixed cases passed, including real pinned Kit consumption
and its simulated budget case. Runtime networking was disabled. This result names
the committed baseline above, not the later prototype snapshot.

After adding the prototype:

```sh
SKYLIT_AGENT_KIT=/tmp/skylit-desk-FXNgvA/kit python3 -m unittest discover -s tests -v
python3 scripts/validate_experiments.py
python3 -m compileall -q scripts tests templates/experiment experiments prototypes/watchlist-desk
git diff --check
```

All 345 tests passed with no skips. One template and three existing experiment
manifests validated; the prototype is deliberately outside the experiment catalogue.
Compilation and whitespace checks passed. The later responsive HTML adjustment
was checked by the final Docker build's eight focused tests and browser inspection.

The commands in README built and served the image. The eight focused prototype
tests passed during both builds with networking disabled; they also passed in a
read-only runtime container with `--network none`, dropped capabilities,
no-new-privileges, 256 MiB memory, one CPU and 64 PIDs.

An additional final-image CLI run used:

```sh
docker run --rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges --pids-limit 64 --memory 256m --cpus 1 --tmpfs /tmp:rw,noexec,nosuid,nodev,size=128m,mode=1777 skylit-desk:local python -I -B scripts/watchlist_desk.py --kit /work/kit --output /tmp/custom --gamma-value -210
```

It exited 0 and changed SPY gamma strike 110 from -180 to -210, delta -30.
The default is -199, delta -19. Vanna expiration mismatch blocks comparison,
QQQ stays missing, and SPY's removed flow stays missing. Duplicate strikes,
missing strikes, old/equal source times, unsupported scope/parser revisions,
source-text escaping and output-directory reuse are covered by focused tests.

## Browser and failure observations

The first internal-network Docker viewer did not publish its requested localhost
port on this engine: inspect showed an empty port mapping and HTTP connection was
refused. That container and unused network were removed. The documented viewer
uses the standard bridge with only `127.0.0.1:8765` published. This viewer can have
outbound network access; it serves baked fictional artifacts and does not fetch
data. It is distinct from the network-disabled execution tests.

The corrected endpoint returned HTTP 200. The browser displayed the real generated
comparison and evidence. Checking “Show changes and gaps only” hid the unchanged
row while retaining gaps. Initial narrow-screen columns were hard to inspect;
the final build renders labeled stacked rows at narrow widths, visually checked
in the browser. No model or authenticated service was invoked by the prototype.

## What this establishes

The pinned parser can feed structured artifacts, a comparison and a local UI.
An existing coding agent can invoke the documented command and change synthetic
parameters. These results support building the first structured-output release.

The evidence envelope and proof are prototype-specific. There is no arbitrary
snapshot importer, live integration, standalone agent, model-evaluation loop,
production server, trading-performance evidence or newcomer usability result.
No universal compatibility, data synchronization or market-freshness claim follows.
The preparer is development staging code, not a hostile-repository sandbox.
