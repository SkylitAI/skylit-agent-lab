"""Render fictional watchlist responses through an explicitly pinned local Kit."""

import argparse
import importlib
import json
from pathlib import Path
import subprocess
import sys


KIT_REVISION = "0f82039759ef4db9d5b3dbd90f52863f8074f2a6"
FIXTURE = Path(__file__).resolve().parents[1] / "examples" / "kit-watchlist.json"


def load_fixture(path):
    """Read at most 64 KiB of synthetic JSON before Kit validates its fields."""
    path = Path(path)
    try:
        if not path.is_file():
            raise OSError("Not a regular file")
        with path.open("rb") as source:
            content = source.read(65537)
    except OSError:
        raise ValueError("Choose a readable regular JSON file for --fixture.") from None
    if len(content) > 65536:
        raise ValueError("Fixture exceeds the 64 KiB limit; use a smaller synthetic fixture.")
    try:
        return json.loads(content.decode("utf-8"))
    except (ValueError, RecursionError):
        raise ValueError("Fixture must contain valid UTF-8 JSON within the nesting limit.") from None


def load_kit(path):
    """Check the local revision before importing; never install or fetch anything."""
    root = Path(path).resolve()
    revision = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    if revision != KIT_REVISION:
        raise ValueError(f"Kit revision must be {KIT_REVISION}; found {revision}.")
    changes = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all"],
        check=True, capture_output=True, text=True,
    ).stdout
    if changes:
        raise ValueError("Kit checkout must be clean; review local changes before running.")
    if not (root / "skylit_agent_kit" / "watchlist.py").is_file():
        raise ValueError("--kit must name the Kit repository root.")
    sys.path.insert(0, str(root))
    return importlib.import_module("skylit_agent_kit.watchlist")


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
