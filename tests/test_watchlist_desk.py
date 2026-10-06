"""Observable behavior of the synthetic architecture prototype."""

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from scripts import watchlist_desk as desk

KIT = Path(os.environ.get("SKYLIT_AGENT_KIT", desk.ROOT.parent / "skylit-agent-kit-watchlist"))


def sample(value=-180, stamp="2026-10-01T13:55:00+00:00"):
    board = {"status": "available", "as_of": stamp, "expirations": ["2026-10-02"],
             "strikes": [{"strike": 110, "value": value, "nodeType": "king"}]}
    return {"scope": "synthetic-desk-prototype", "kit_revision": "same", "id": "test",
            "symbols": ["SPY"], "rows": {"SPY": {"gamma": board, "vanna": deepcopy(board)}}}


class DeskComparisonTests(unittest.TestCase):
    def setUp(self):
        self.before = sample()
        self.after = sample(-199, "2026-10-01T14:05:00+00:00")

    def test_value_change_and_unchanged(self):
        self.after["rows"]["SPY"]["vanna"]["strikes"][0]["value"] = -180
        rows = desk.compare(self.before, self.after)["changes"]
        self.assertEqual(rows[0]["delta"], "-19")
        self.assertEqual(rows[1]["status"], "unchanged")

    def test_expiration_mismatch_does_not_compute_delta(self):
        self.after["rows"]["SPY"]["gamma"]["expirations"] = ["2026-10-09"]
        row = desk.compare(self.before, self.after)["changes"][0]
        self.assertIsNone(row["delta"])
        self.assertEqual(row["reason"], "Expiration coverage differs")

    def test_missing_strike_is_not_zero(self):
        self.after["rows"]["SPY"]["gamma"]["strikes"][0]["strike"] = 115
        rows = desk.compare(self.before, self.after)["changes"]
        self.assertIsNone(rows[0]["after"])
        self.assertIsNone(rows[1]["before"])
        self.assertTrue(all(row["delta"] is None for row in rows[:2]))

    def test_duplicate_strike_refused(self):
        board = self.after["rows"]["SPY"]["gamma"]
        board["strikes"].append(deepcopy(board["strikes"][0]))
        self.assertEqual(desk.compare(self.before, self.after)["changes"][0]["reason"], "Duplicate strike identity")

    def test_equal_or_older_timestamp_refused(self):
        for stamp in ("2026-10-01T13:55:00+00:00", "2026-10-01T13:54:00+00:00"):
            self.after["rows"]["SPY"]["gamma"]["as_of"] = stamp
            self.assertIsNone(desk.compare(self.before, self.after)["changes"][0]["delta"])

    def test_unsupported_scope_and_parser_revision_refused(self):
        self.after["scope"] = "live"
        with self.assertRaises(ValueError):
            desk.compare(self.before, self.after)
        self.after["scope"] = self.before["scope"]
        self.after["kit_revision"] = "different"
        with self.assertRaises(ValueError):
            desk.compare(self.before, self.after)

    def test_html_escapes_source_status(self):
        self.after["rows"]["SPY"]["gamma"]["status"] = "<script>alert(1)</script>"
        page = desk.viewer(self.before, self.after, desk.compare(self.before, self.after)).decode()
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;", page)


@unittest.skipUnless(KIT.is_dir(), "Set SKYLIT_AGENT_KIT to the exact pinned checkout")
class DeskIntegrationTests(unittest.TestCase):
    def test_real_kit_artifacts_and_customization(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "first"
            comparison = desk.run(KIT, first)
            self.assertEqual(comparison["changes"][0]["delta"], "-19")
            self.assertEqual(comparison["changes"][2]["reason"], "Expiration coverage differs")
            self.assertTrue(all(r["delta"] is None for r in comparison["changes"] if r["symbol"] == "QQQ"))
            after = json.loads((first / "after.json").read_text())
            self.assertEqual(after["rows"]["SPY"]["flow"]["status"], "missing from synthetic fixture")
            proof = json.loads((first / "proof.json").read_text())
            for name, expected in proof["artifacts"].items():
                self.assertEqual(hashlib.sha256((first / name).read_bytes()).hexdigest(), expected)
            with self.assertRaises(FileExistsError):
                desk.run(KIT, first)
            changed = desk.run(KIT, root / "custom", gamma_value=-210)
            self.assertEqual(changed["changes"][0]["delta"], "-30")
            gaps = desk.run(KIT, root / "gaps", symbols="QQQ,SPXW")
            self.assertEqual({r["symbol"] for r in gaps["changes"]}, {"QQQ", "SPXW"})
            self.assertTrue(all(r["delta"] is None for r in gaps["changes"]))


if __name__ == "__main__":
    unittest.main()
