"""Render fictional watchlist responses through an explicitly pinned local Kit."""

import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys


if __package__:
    from .git_provenance import inspect_checkout
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from git_provenance import inspect_checkout


KIT_REVISION = "0f82039759ef4db9d5b3dbd90f52863f8074f2a6"
FIXTURE = Path(__file__).resolve().parents[1] / "examples" / "kit-watchlist.json"


class FixtureError(ValueError):
    """A fixed safe failure code and provenance, without source paths or payloads."""

    def __init__(self, code, *, sha256=None):
        message, self.hash_state = {
            "input_unreadable": ("Choose a readable regular JSON file for --fixture.", "read_failed"),
            "input_too_large": ("Fixture exceeds the 64 KiB limit; use a smaller synthetic fixture.", "too_large"),
            "invalid_fixture": ("Fixture must contain valid UTF-8 JSON within the nesting limit.", "complete"),
        }[code]
        self.code = code
        self.sha256 = sha256
        super().__init__(message)


def load_fixture_with_hash(path):
    """Parse and hash one bounded buffer; never label an oversized prefix complete."""
    path = Path(path)
    content = None
    try:
        if not path.is_file():
            raise OSError("Not a regular file")
        # Recheck the opened descriptor; a FIFO replacement must not block open.
        with open(path, "rb", opener=lambda name, flags: os.open(name, flags | getattr(os, "O_NONBLOCK", 0))) as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                raise OSError("Not a regular file")
            content = source.read(65537)
    except OSError:
        # Raise outside the handler so private exception context is not retained.
        content = None
    if content is None:
        raise FixtureError("input_unreadable")
    if len(content) > 65536:
        raise FixtureError("input_too_large")
    digest = hashlib.sha256(content).hexdigest()
    try:
        return json.loads(content.decode("utf-8")), digest
    except (ValueError, RecursionError):
        pass
    raise FixtureError("invalid_fixture", sha256=digest)


def load_fixture(path):
    """Keep the original parsed-value-only interface for existing consumers."""
    return load_fixture_with_hash(path)[0]


class KitError(ValueError):
    """A fixed failure code and qualified revision evidence, without raw errors."""

    def __init__(self, code, observed_revision=None):
        message, verification = {
            "kit_unavailable": ("Cannot load --kit; provide a readable pinned Kit repository root and ensure Git is available.", "read_failed"),
            "kit_mismatch": (f"Kit revision must be {KIT_REVISION}; found {observed_revision}.", "revision_mismatch"),
            "kit_dirty": ("Kit checkout must be clean; review local changes before running.", "dirty"),
        }[code]
        self.code = code
        self.metadata = {"required_revision": KIT_REVISION, "observed_revision": observed_revision,
                         "verification": verification}
        super().__init__(message)


def load_kit_with_metadata(path):
    """Verify the requested checkout and imported module; never install or fetch."""
    checkout = inspect_checkout(path)
    revision = checkout["revision"]
    if revision is None:
        raise KitError("kit_unavailable")
    if revision != KIT_REVISION:
        raise KitError("kit_mismatch", revision)
    if checkout["state"] == "dirty":
        raise KitError("kit_dirty", revision)
    if checkout["state"] != "clean":
        raise KitError("kit_unavailable", revision)
    module = None
    try:
        root = Path(path).resolve()
        expected = root / "skylit_agent_kit" / "watchlist.py"
        if expected.is_file():
            sys.path.insert(0, str(root))
            module = importlib.import_module("skylit_agent_kit.watchlist")
            if Path(module.__file__).resolve() != expected:
                module = None
    except Exception:
        # Do not retain an import exception containing private paths or details.
        module = None
    if module is None:
        raise KitError("kit_unavailable", revision)
    return module, {"required_revision": KIT_REVISION, "observed_revision": revision, "verification": "verified"}


def load_kit(path):
    """Keep the existing module-only interface for the probe and experiment."""
    return load_kit_with_metadata(path)[0]


def build_result(kit, fixture, selected):
    """Parse local fixture envelopes once into the existing Kit report input."""
    if (not isinstance(fixture, dict)
            or any(not isinstance(fixture.get(key), dict) for key in ("gamma", "vanna", "flow"))
            or any(not isinstance(value, dict) for value in fixture["flow"].values())):
        raise ValueError("Fixture requires gamma, vanna and flow objects.")
    symbols = kit.symbols_list(selected)
    gamma = kit.parse_heatmap(fixture["gamma"], symbols, "gamma")
    vanna = kit.parse_heatmap(fixture["vanna"], symbols, "vanna")
    rows = {
        symbol: {
            "gamma": gamma[symbol], "vanna": vanna[symbol],
            "flow": (kit.parse_flow(fixture["flow"][symbol], symbol)
                     if symbol in fixture["flow"]
                     else kit.missing("missing from synthetic fixture")),
        }
        for symbol in symbols
    }
    return {
        "symbols": symbols, "rows": rows,
        "retrieved_at": "2026-10-01T14:01:00+00:00 (fictional fixture time)",
        "stop": "offline synthetic fixture rendered", "date": "2026-10-01",
        "flow_limit": 10, "sources": [], "requests": 0, "credits_reserved": 0,
    }


def render_result(kit, result, *, title="Synthetic Kit consumer probe"):
    """Render an already parsed Kit result with the fictional-data context."""
    report = kit.render_report(result)
    return (
        f"# {title}\n\n"
        "**Fictional data only.** Every value and timestamp below is made up.\n"
        "Kit's unchanged renderer uses REST terminology; no service was contacted.\n"
        f"Kit revision: `{KIT_REVISION}`. No credentials or model required.\n\n"
        + report
    )


def render_fixture(kit, fixture, selected, *, title="Synthetic Kit consumer probe"):
    """Keep the fixture-to-report interface for existing consumers."""
    return render_result(kit, build_result(kit, fixture, selected), title=title)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kit", required=True, help="Clean local Kit checkout at the pinned revision")
    parser.add_argument("--symbols", default="SPY,QQQ", help="Comma-separated synthetic selections")
    parser.add_argument("--fixture", type=Path, default=FIXTURE, help="Synthetic JSON envelopes")
    args = parser.parse_args()
    try:
        kit = load_kit(args.kit)
        fixture = load_fixture(args.fixture)
        report = render_fixture(kit, fixture, args.symbols)
    except (OSError, subprocess.CalledProcessError):
        print("error: Cannot read the local Kit checkout or fixture; check paths and Git availability.", file=sys.stderr)
        return 1
    except (ValueError, RecursionError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(report, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
