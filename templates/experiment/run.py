"""Render fictional observations. No network, model or account access."""

import argparse
import json
from pathlib import Path
import re
import sys


def render(fixture):
    if not isinstance(fixture, dict) or set(fixture) != {"observations"}:
        raise ValueError("fixture must contain only an observations list")
    observations = fixture["observations"]
    if not isinstance(observations, list) or not observations:
        raise ValueError("observations must be a nonempty list")
    lines = ["# Fictional observation report", "",
             "Synthetic example only. No market data, API calls or model usage.", ""]
    for index, observation in enumerate(observations):
        if not isinstance(observation, dict) or set(observation) != {"symbol", "note"}:
            raise ValueError(f"observations[{index}] needs symbol and note")
        symbol, note = observation["symbol"], observation["note"]
        if not isinstance(symbol, str) or not re.fullmatch(r"[A-Z0-9.-]{1,16}", symbol):
            raise ValueError(f"observations[{index}].symbol must be 1–16 uppercase symbol characters")
        if note is not None and not isinstance(note, str):
            raise ValueError(f"observations[{index}].note must be text or null")
        text = " ".join(note.split()) if note else "Not provided"
        text = re.sub(r"([\\`*_{}\[\]()<>#!|])", r"\\\1", text)
        lines.append(f"- {symbol}: {text}")
    return "\n".join(lines) + "\n"


def main():
    folder = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=folder / "fixture.json")
    parser.add_argument("--output", type=Path, default=folder / "reports/example.md")
    args = parser.parse_args()
    try:
        with args.fixture.open("rb") as source:
            contents = source.read(65537)
        if len(contents) > 65536:
            raise ValueError("fixture exceeds 64 KiB")
        report = render(json.loads(contents.decode("utf-8")))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
