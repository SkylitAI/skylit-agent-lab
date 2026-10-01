# Muse Code feasibility discovery

This discovery identifies an interface that could let an agent run the
[offline Watchlist package](../../experiments/watchlist-investigator/README.md).
It does not demonstrate a host-driven Watchlist run.

As of **2026-10-01**, technical discovery is **ready_for_review**; host
certification and authenticated model access are **unverified**. Muse Code is
the provisional target proposed during planning. Confirm the product before
implementation if “Muse” meant a personal agent instead.

## Reproducible evidence

Discovery used macOS arm64, Lab revision
`934a45fe55ef9507db5a3fc07f916c4254dbf85e`, and the package's existing Kit pin
`0f82039759ef4db9d5b3dbd90f52863f8074f2a6`. No Kit or host configuration changed.

The maintainer retrieved the public [stable channel](https://api.meta.ai/muse-code/channels/muse-stable)
and [release manifest](https://lookaside.facebook.com/lookaside/muse/download/?channel=muse&version=1.4.2-R4684.1&file=manifest.json)
without authentication; both returned HTTP 200. The downloaded macOS arm64
binary was independently checked:

| Property | Observed value |
|---|---|
| Version output | `Muse Code 1.4.2 (1.4.2-R4684.1)` |
| Size | `328024832` bytes |
| SHA-256 | `e9987ef4267a648dc1931c2836a23f6f16f8b4417368b126a810bece2abd308d` |

These were the only binary invocations; all exited 0:

```sh
muse --version
muse --help
muse exec --help
muse auth --help
```

Here `muse` denotes the downloaded binary, not an installed command. Each
invocation used a minimal environment: `PATH=os.defpath`, temporary
`MUSE_AUTH_PATH`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `XDG_DATA_HOME` and
`TMPDIR` locations, with no `HOME` override. No credentials or global
configuration were supplied to these commands; internal filesystem accesses
were not traced. The temporary auth file was not created. No login, credential
submission, global installation or model execution was attempted.

## Available interface

The [official overview](https://dev.meta.ai/docs/muse-code) describes a CLI
agent that can edit files and run commands, with a headless `exec` mode.
The downloaded version's help exposes the following contract:

| Need | Help-level contract |
|---|---|
| Task input | `muse exec [OPTIONS] [PROMPT]`; `--prompt-file <PATH>` accepts a prompt file. |
| Workspace | `--workspace <PATH>` registers workspace tools; `--trust-workspace` loads workspace rules and skills for the run. |
| Execution bounds | `--max-model-steps <N>` and `--max-tool-output-bytes <N>` provide explicit limits. |
| Context and web controls | `--no-foreign-personal-context` excludes foreign personal rules/skills; `--disable-web-tools` disables web tools. |
| Tool controls | `--disable-shell` disables shell; `--disable-write` disables non-shell writes. Approvals and sandboxing default on. |
| Output | `--json` emits JSONL events; `--no-session-log` disables session event log persistence. |
| Credentials | `muse auth set [--provider <PROVIDER>] --api-key-stdin` reads a key from stdin; `exec` also exposes `--api-key-stdin`. Only help was invoked. |

These are advertised controls, not tested enforcement. Disabling web tools
alone does not establish network isolation, and disabling non-shell writes
does not constrain shell writes. A future probe needs an explicit workspace
and reviewed tool permissions before running the package command.

## Remaining uncertainty

Public download access does not establish model entitlement, login success,
API-key availability, pricing or permission to spend. Those remain unknown.
No failure behavior, tool execution, skill loading or report output has been
tested through Muse. There is no Windows or Linux certification from this
macOS discovery.

The next host increment should confirm the intended Muse product and available
authorized access, then test one bounded synthetic Watchlist run and record
its actual version, commands and outcome in the [host matrix](../host-matrix.md).
No adapter, host configuration or `tested_hosts` entry is justified yet.
