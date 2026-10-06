"""Synthetic Docker proof: one Kit parse feeds JSON, comparison and a static viewer."""

import argparse
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import html
import json
from pathlib import Path
import sys

if __package__:
    from . import probe_kit_watchlist as consumer
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import probe_kit_watchlist as consumer

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "experiments/watchlist-investigator/fixture.json"


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def digest(content):
    return hashlib.sha256(content).hexdigest()


def snapshot(kit, fixture, symbols, snapshot_id):
    """Prototype-only envelope; no live or caller-supplied data ingestion."""
    result = consumer.build_result(kit, fixture, symbols)
    return {"schema_version": 1, "scope": "synthetic-desk-prototype",
            "id": snapshot_id, "kit_revision": consumer.KIT_REVISION,
            "input_sha256": digest(encoded(fixture)),
            "symbols": result["symbols"], "rows": result["rows"]}


def compare(before, after):
    """Compare fixed strikes within the same synthetic metric and expiry coverage."""
    if any(s.get("scope") != "synthetic-desk-prototype" for s in (before, after)):
        raise ValueError("Only prototype synthetic snapshots are supported.")
    if before["kit_revision"] != after["kit_revision"]:
        raise ValueError("Snapshots require the same Kit parser revision.")
    changes = []
    for symbol in dict.fromkeys(before["symbols"] + after["symbols"]):
        for metric in ("gamma", "vanna"):
            old = before["rows"].get(symbol, {}).get(metric, {})
            new = after["rows"].get(symbol, {}).get(metric, {})
            reason = None
            if old.get("status") != "available" or new.get("status") != "available":
                reason = f"Before: {old.get('status', 'symbol not selected')}; after: {new.get('status', 'symbol not selected')}"
            elif sorted(old["expirations"]) != sorted(new["expirations"]):
                reason = "Expiration coverage differs"
            elif datetime.fromisoformat(new["as_of"]) <= datetime.fromisoformat(old["as_of"]):
                reason = "After source time must be later than before"
            old_nodes = {n["strike"]: n for n in old.get("strikes", [])}
            new_nodes = {n["strike"]: n for n in new.get("strikes", [])}
            if (len(old_nodes) != len(old.get("strikes", []))
                    or len(new_nodes) != len(new.get("strikes", []))):
                reason = "Duplicate strike identity"
            base = {"symbol": symbol, "metric": metric,
                    "before_time": old.get("as_of"), "after_time": new.get("as_of")}
            if reason:
                changes.append({**base, "strike": None, "before": None, "after": None,
                                "delta": None, "status": "not comparable", "reason": reason})
                continue
            for strike in sorted(old_nodes.keys() | new_nodes.keys()):
                left, right = old_nodes.get(strike), new_nodes.get(strike)
                delta = (str(Decimal(str(right["value"])) - Decimal(str(left["value"])))
                         if left and right else None)
                changes.append({**base, "strike": strike,
                                "before": left["value"] if left else None,
                                "after": right["value"] if right else None,
                                "delta": delta,
                                "status": ("not comparable" if delta is None else
                                           "unchanged" if Decimal(delta) == 0 else "changed"),
                                "reason": "Strike absent from one snapshot" if delta is None else None})
    return {"schema_version": 1, "scope": "synthetic-desk-prototype",
            "before": before["id"], "after": after["id"], "changes": changes}


def viewer(before, after, comparison):
    def cell(value):
        return html.escape("Unavailable" if value is None else str(value))

    changes = "".join(
        '<tr data-status="' + cell(row["status"]) + '">' + "".join(
            f'<td data-label="{key.title()}">{cell(row[key])}</td>' for key in
            ("symbol", "metric", "strike", "before", "after", "delta", "status", "reason")) + "</tr>"
        for row in comparison["changes"])
    observations = "".join(
        "<tr>" + "".join(f'<td data-label="{label}">{cell(value)}</td>' for label, value in zip(
            ("Snapshot", "Symbol", "Component", "Source status", "Source time", "Expirations"),
            (bundle["id"], symbol, metric, row["status"],
             row.get("as_of", row.get("generated_at")),
             ", ".join(row.get("expirations", [])) or None))) + "</tr>"
        for bundle in (before, after) for symbol in bundle["symbols"]
        for metric, row in bundle["rows"][symbol].items())
    return ('''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Watchlist Desk · synthetic prototype</title>
<style>
:root{color-scheme:light dark;font-family:system-ui,sans-serif;background:light-dark(#f5f6f8,#141820);color:light-dark(#202938,#e5eaf3)}
body{max-width:1120px;margin:auto;padding:36px 24px}header{margin-bottom:32px}h1{font-size:32px;letter-spacing:-1px;margin:10px 0}h2{font-size:20px;margin-top:32px}p{line-height:1.6;max-width:850px}.eyebrow{font-size:12px;letter-spacing:2px}a{color:light-dark(#2856ad,#9bc0ff)}
.tag{display:inline-block;padding:6px 10px;border-radius:6px;background:light-dark(#e2eafa,#273b59);font-size:13px}.table{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;padding:13px 10px;border-bottom:1px solid light-dark(#d6dce6,#354052)}th{font-size:12px;text-transform:uppercase;letter-spacing:.5px}tr[data-status="changed"]{background:light-dark(#e4f2ed,#17382f)}nav{display:flex;gap:18px;flex-wrap:wrap}label{display:block;margin:16px 0}footer{margin-top:30px;font-size:13px}code{overflow-wrap:anywhere}
@media(max-width:760px){thead{display:none}table,tbody{display:block}tbody tr{display:grid;grid-template-columns:1fr 1fr;margin-bottom:18px;border:1px solid light-dark(#d6dce6,#354052);border-radius:8px}tbody tr[hidden]{display:none}td{display:block;overflow-wrap:anywhere;min-width:0}td:before{content:attr(data-label);display:block;font-size:11px;text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px;opacity:.75}body{padding:24px 16px}}
</style><header><div class="eyebrow">SKYLIT / AGENT LAB</div>
<h1>What changed in my watchlist?</h1><span class="tag">Fictional data · offline Docker prototype</span>
<p>One Kit parser supplies the structured evidence and this viewer. The comparison uses matching strikes within each metric and expiration set. Values are copied from synthetic fixtures; delta is simple subtraction in the fixture's source scale.</p>
<nav><a href="before.json">Before evidence</a><a href="after.json">After evidence</a><a href="comparison.json">Comparison JSON</a><a href="proof.json">Run proof</a></nav></header>
<h2>Snapshot comparison</h2><label><input id="only" type="checkbox"> Show changes and gaps only</label>
<div class="table"><table id="changes"><thead><tr><th>Symbol</th><th>Metric</th><th>Strike</th><th>Before</th><th>After</th><th>Delta</th><th>Status</th><th>Reason</th></tr></thead><tbody>'''
        + changes + '''</tbody></table></div><h2>Source evidence</h2>
<p>The second fixture changes SPY gamma at strike 110, advances board times by ten minutes, changes vanna expiration coverage, and removes the flow response. QQQ remains missing. These deliberately exercise both changes and refusals.</p>
<div class="table"><table><thead><tr><th>Snapshot</th><th>Symbol</th><th>Component</th><th>Source status</th><th>Source time</th><th>Expirations</th></tr></thead><tbody>'''
        + observations + '''</tbody></table></div>
<footer>No live market data, model calls, trade recommendations or orders. Comparability here is limited to fictional fixtures; matching fields does not establish market synchronization. Flow observations are displayed but not numerically compared.</footer>
<script>document.getElementById('only').addEventListener('change',function(){document.querySelectorAll('#changes tbody tr').forEach(row=>{row.hidden=this.checked&&row.dataset.status==='unchanged';});});</script></html>''').encode()


def run(kit_path, output, symbols="SPY,QQQ", gamma_value=-199):
    kit = consumer.load_kit(kit_path)
    fixture = consumer.load_fixture(FIXTURE)
    changed = deepcopy(fixture)
    changed["gamma"]["data"]["symbols"][0]["strikes"][0]["value"] = gamma_value
    changed["gamma"]["data"]["symbols"][0]["asOf"] = "2026-10-01T14:05:00Z"
    changed["vanna"]["data"]["symbols"][0]["asOf"] = "2026-10-01T14:04:00Z"
    changed["vanna"]["data"]["symbols"][0]["expirations"] = ["2026-10-09"]
    changed["flow"] = {}
    before = snapshot(kit, fixture, symbols, "before")
    after = snapshot(kit, changed, symbols, "after")
    comparison = compare(before, after)
    payloads = {"before.json": encoded(before), "after.json": encoded(after),
                "comparison.json": encoded(comparison),
                "before-input.json": encoded(fixture), "after-input.json": encoded(changed),
                "index.html": viewer(before, after, comparison)}
    output.mkdir(parents=True, exist_ok=False)
    for name, content in payloads.items():
        (output / name).write_bytes(content)
    # Prototype proof is intentionally separate from Lab's strict v1 run records.
    proof = {"scope": "synthetic-desk-prototype", "outcome": "completed",
             "executed_at": datetime.now(timezone.utc).isoformat(),
             "python": sys.version.split()[0], "kit_revision": consumer.KIT_REVISION,
             "parameters": {"symbols": before["symbols"], "gamma_value": gamma_value},
             "artifacts": {name: digest(content) for name, content in payloads.items()},
             "network_requests": 0, "model_calls": 0,
             "limits": "Fixed synthetic inputs only; prototype, not a public evidence schema"}
    (output / "proof.json").write_bytes(encoded(proof))
    return comparison


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New directory; never overwritten")
    parser.add_argument("--symbols", default="SPY,QQQ")
    parser.add_argument("--gamma-value", type=int, default=-199, choices=range(-1000000, 1000001),
                        metavar="INTEGER", help="Synthetic after value (-1000000 through 1000000)")
    args = parser.parse_args()
    try:
        result = run(args.kit, args.output, args.symbols, args.gamma_value)
    except (OSError, ValueError):
        print("Prototype stopped. Check pinned Kit, symbols and a new output directory; partial output has no completed proof.", file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
