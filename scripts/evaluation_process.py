"""Bound a reviewed evaluator child; this is not a filesystem/network sandbox.

Callers construct argv/cwd internally and supply the remaining monotonic 90-second
suite budget. This helper does not interpret manifests, choose commands or print
captured data. The evaluator's container must supply filesystem/network isolation.
Descendants must remain in the child's POSIX process group.
"""

import math
import os
import selectors
import signal
import subprocess
import time


CHILD_SECONDS = 20
STREAM_BYTES = 65536
CLEANUP_SECONDS = 1


def run_child(argv, cwd, remaining_seconds):
    """Return raw bounded prefixes, a reaped exit code or None, and a fixed reason.

    ``exited`` includes nonzero exits. Limits produce ``timeout``, ``stdout_limit``
    or ``stderr_limit``; failures produce ``invalid_request``, ``launch_failed``,
    ``io_failed`` or ``cleanup_failed``. Windows returns ``unsupported_platform``.
    Cleanup kills the group, closes pipes and allows at most one further second
    to reap the direct child; it never fabricates an exit when reaping fails.
    Orphan reaping requires an external init/subreaper; this helper reaps only
    its direct child.
    """
    result = {"exit_code": None, "stdout": b"", "stderr": b"", "stop_reason": "invalid_request"}
    if (type(remaining_seconds) not in (int, float) or remaining_seconds < 0
            or type(remaining_seconds) is float and not math.isfinite(remaining_seconds)):
        return result
    if remaining_seconds == 0:
        result["stop_reason"] = "timeout"
        return result
    if os.name != "posix":
        result["stop_reason"] = "unsupported_platform"
        return result
    deadline = time.monotonic() + min(CHILD_SECONDS, remaining_seconds)
    try:
        child = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 env={"PATH": os.defpath, "LC_ALL": "C"},
                                 start_new_session=True, close_fds=True)
    except (OSError, ValueError, TypeError):
        result["stop_reason"] = "launch_failed"
        return result

    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    result["stop_reason"] = "exited"
    try:
        with selectors.DefaultSelector() as selector:
            for name, pipe in (("stdout", child.stdout), ("stderr", child.stderr)):
                os.set_blocking(pipe.fileno(), False)
                selector.register(pipe, selectors.EVENT_READ, name)
            while selector.get_map() or child.poll() is None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    result["stop_reason"] = "timeout"
                    break
                for key, _ in selector.select(min(remaining, 0.05)):
                    buffer = buffers[key.data]
                    available = STREAM_BYTES - len(buffer)
                    try:
                        chunk = os.read(key.fd, min(8192, available + 1))
                    except BlockingIOError:
                        continue
                    if not chunk:
                        selector.unregister(key.fileobj)
                        key.fileobj.close()
                    else:
                        buffer.extend(chunk[:available])
                        if len(chunk) > available:
                            result["stop_reason"] = key.data + "_limit"
                            break
                if result["stop_reason"] != "exited":
                    break
    except OSError:
        result["stop_reason"] = "io_failed"
    finally:
        # The leader may already have exited while descendants retain its pipes.
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError:
            result["stop_reason"] = "cleanup_failed"
        for pipe in (child.stdout, child.stderr):
            try:
                pipe.close()
            except OSError:
                result["stop_reason"] = "cleanup_failed"
        try:
            result["exit_code"] = child.wait(timeout=CLEANUP_SECONDS)
        except (OSError, subprocess.TimeoutExpired):
            result["stop_reason"] = "cleanup_failed"
    result.update({name: bytes(buffer) for name, buffer in buffers.items()})
    return result
