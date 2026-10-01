# Offline checks in Docker

Run the fixed isolation probe and synthetic examples from a clean, committed Lab
checkout with Python 3.11+, Git and a local Docker Engine with Buildx on macOS
or Linux (Unix socket):

```sh
python3 scripts/run_isolated.py --kit /path/to/clean-pinned-kit
```

Kit must be at the revision required by Watchlist. The wrapper only uses local
checkouts; obtain dependencies separately. It rejects uncommitted or untracked
source changes so a passing run names the code it actually tested.

The wrapper discovers only the active local Docker socket and installed Buildx
executable from client metadata. Build, run and cleanup then use an empty
temporary Docker configuration and a minimal client environment. Registry auth,
configured proxies and other client settings are not copied. The build uses the
public base image without registry credentials.

The wrapper stages fresh local Git clones and removes remotes, hooks and reflogs.
Ignored reports, environment files and the original Git configuration do not
enter the image. Tracked files and commit history do: review the source before
building. No personal directories, host environment variables, credentials or
Docker socket are mounted or passed to the evaluation container. No image is
pushed. This is for reviewed Lab code, not a service for running arbitrary PRs on
a personal computer.

The build pulls a digest-pinned official Python image and installs Git before
evaluation. Debian packages are not pinned byte-for-byte; the probe reports the
actual Python/Git versions and the wrapper prints the resulting local image ID.
Evaluation uses `docker run --network none`, a read-only root, a non-root user,
no effective capabilities and no-new-privileges. Temporary output lives in a
128 MiB tmpfs. The container has no host mounts, is limited to one CPU, 256 MiB
memory and 64 processes, and is removed after the run. The wrapper attempts to
remove its resulting image; Docker may retain build-cache layers. Use the
normal Docker cache-management tools when those local copies are no longer needed.

The probe requires an outbound TCP connection to fail with `ENETUNREACH`, verifies
that source is read-only, reads the declared synthetic fixture bytes, runs the
template and seed commands, and checks their records/hashes/private permissions.
Only the template output is compared with a full golden here; source-value and
failure-case evaluation belongs to the separate evaluator. No command from an
experiment manifest is executed.

While Kit is INTERNAL, secret-free hosted CI cannot obtain it. CI explicitly runs:

```sh
python3 scripts/run_isolated.py --without-kit
```

This checks isolation, the template, Journal and Market. It reports Watchlist as
**unverified**, never as passed. Full evaluation/release acceptance still needs
the real pinned Kit. Neither invocation verifies model hosts, live sources,
human usability or a security boundary beyond the tested Docker configuration.

The build can use the network; the later probe cannot. No model or service key
is needed. See [Docker's run reference](https://docs.docker.com/engine/containers/run/)
for the isolation options and [run records](run-record.md) for evidence limits.
