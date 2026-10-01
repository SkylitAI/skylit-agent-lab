"""Exercise the real pinned Kit from a credential-free, socket-blocked process."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts import probe_kit_watchlist as consumer


ROOT = Path(__file__).resolve().parents[1]
KIT = Path(os.environ.get("SKYLIT_AGENT_KIT", ROOT.parent / "skylit-agent-kit"))
PROBE = ROOT / "scripts" / "probe_kit_watchlist.py"
FIXTURE = ROOT / "examples" / "kit-watchlist.json"
GUARD = """
import getpass, runpy, sys
def deny(*args, **kwargs):
    raise AssertionError('Offline probe attempted network or credential input')
def audit(event, args):
    if event.startswith('socket.') or event == 'builtins.input':
        deny()
sys.addaudithook(audit)
getpass.getpass = deny
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name='__main__')
"""


class KitConsumerTests(unittest.TestCase):
    def run_probe(self, *args, kit=KIT):
        return subprocess.run(
            [sys.executable, "-I", "-B", "-c", GUARD, str(PROBE),
             "--kit", str(kit), *args],
            cwd=ROOT, env={"PATH": os.defpath}, stdin=subprocess.DEVNULL,
            capture_output=True, text=True, check=False,
        )

    def test_wrong_checkout_stops_before_rendering(self):
        result = self.run_probe(kit=ROOT)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("Kit revision must be 0f82039759ef4db9d5b3dbd90f52863f8074f2a6", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    @unittest.skipUnless(KIT.is_dir(), "Set SKYLIT_AGENT_KIT to the pinned local checkout")
    def test_real_kit_renders_synthetic_values_and_gaps_offline(self):
        result = self.run_probe()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertIn("Fictional", result.stdout)
        self.assertIn("source king: 100 / -250", result.stdout)
        self.assertIn("largest returned magnitude: 105 / 40", result.stdout)
        self.assertIn("missing from heatmap response", result.stdout)
        self.assertIn("missing from synthetic fixture", result.stdout)
        self.assertIn("0 requests attempted; 0 documented credits", result.stdout)
        self.assertEqual(result.stdout, (ROOT / "examples" / "kit-watchlist.expected.md").read_text())

    @unittest.skipUnless(KIT.is_dir(), "Set SKYLIT_AGENT_KIT to the pinned local checkout")
    def test_selected_symbols_are_normalized_deduplicated_and_not_substituted(self):
        result = self.run_probe("--symbols", "qqq,SPXW,qqq")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count("## QQQ\n"), 1)
        self.assertIn("## SPXW\n", result.stdout)
        self.assertNotIn("## SPX\n", result.stdout)
        self.assertNotIn("## SPY\n", result.stdout)
        self.assertLess(result.stdout.index("## QQQ\n"), result.stdout.index("## SPXW\n"))

    @unittest.skipUnless(KIT.is_dir(), "Set SKYLIT_AGENT_KIT to the pinned local checkout")
    def test_invalid_symbols_stop_without_partial_output(self):
        result = self.run_probe("--symbols", "SPY,https://example.com")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("Use comma-separated ticker symbols", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    @unittest.skipUnless(KIT.is_dir(), "Set SKYLIT_AGENT_KIT to the pinned local checkout")
    def test_changed_source_value_is_rendered_by_kit(self):
        fixture = json.loads(FIXTURE.read_text())
        fixture["gamma"]["data"]["symbols"][0]["strikes"][0]["value"] = -321
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "changed.json"
            path.write_text(json.dumps(fixture))
            result = self.run_probe("--fixture", str(path), "--symbols", "SPY")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("source king: 100 / -321", result.stdout)
        self.assertNotIn("-250", result.stdout)

    @unittest.skipUnless(KIT.is_dir(), "Set SKYLIT_AGENT_KIT to the pinned local checkout")
    def test_malformed_fixture_and_wrong_metric_fail_cleanly(self):
        wrong_metric = json.loads(FIXTURE.read_text())
        wrong_metric["gamma"]["meta"]["metric"] = "vanna"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            for contents in ("not json", "[]", json.dumps(wrong_metric)):
                with self.subTest(contents=contents[:40]):
                    path.write_text(contents)
                    result = self.run_probe("--fixture", str(path))
                    self.assertEqual(result.returncode, 1)
                    self.assertEqual(result.stdout, "")
                    self.assertIn("error:", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)

    @unittest.skipUnless(KIT.is_dir(), "Set SKYLIT_AGENT_KIT to the pinned local checkout")
    def test_dirty_checkout_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            checkout = Path(directory) / "kit"
            subprocess.run(
                ["git", "clone", "--local", "--no-hardlinks", "--quiet", str(KIT.resolve()), str(checkout)],
                check=True, capture_output=True, env={"PATH": os.defpath},
            )
            (checkout / "README.md").write_text("A local change.\n")
            result = self.run_probe(kit=checkout)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("Kit checkout must be clean", result.stderr)


class FixtureInputTests(unittest.TestCase):
    def test_fixture_read_has_an_inclusive_64_kib_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json"
            path.write_bytes(b"{}" + b" " * (65536 - 2))
            self.assertEqual(consumer.load_fixture(path), {})
            path.write_bytes(path.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "64 KiB"):
                consumer.load_fixture(path)

    def test_bad_files_have_actionable_fixture_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json"
            for contents in (b"not json", b"\xff", b"[" * 2000 + b"]" * 1999):
                with self.subTest(contents=contents[:20]):
                    path.write_bytes(contents)
                    with self.assertRaisesRegex(ValueError, "Fixture must contain valid UTF-8 JSON"):
                        consumer.load_fixture(path)
            with self.assertRaisesRegex(ValueError, "readable regular JSON file"):
                consumer.load_fixture(Path(directory))
            with self.assertRaisesRegex(ValueError, "readable regular JSON file"):
                consumer.load_fixture(Path(directory) / "missing.json")

    @unittest.skipUnless(KIT.is_dir(), "Set SKYLIT_AGENT_KIT to the pinned local checkout")
    def test_built_result_exposes_source_times_and_renders_without_fixture(self):
        kit = consumer.load_kit(KIT)
        fixture = json.loads(FIXTURE.read_text())
        result = consumer.build_result(kit, fixture, "spy,qqq,spy")
        self.assertEqual(result["symbols"], ["SPY", "QQQ"])
        spy = result["rows"]["SPY"]
        self.assertEqual(spy["gamma"]["as_of"], "2026-10-01T14:00:00+00:00")
        self.assertEqual(spy["vanna"]["as_of"], "2026-10-01T13:59:00+00:00")
        self.assertEqual(spy["flow"]["generated_at"], "2026-10-01T14:01:00+00:00")
        self.assertIsNone(spy["flow"]["latest_trade"])
        self.assertEqual(result["rows"]["QQQ"]["gamma"], {"status": "missing from heatmap response"})
        self.assertEqual(result["rows"]["QQQ"]["flow"], {"status": "missing from synthetic fixture"})
        original_result = json.loads(json.dumps(result))
        fixture.clear()
        self.assertEqual(
            consumer.render_result(kit, result),
            (ROOT / "examples" / "kit-watchlist.expected.md").read_text(),
        )
        self.assertEqual(result, original_result)

    @unittest.skipUnless(KIT.is_dir(), "Set SKYLIT_AGENT_KIT to the pinned local checkout")
    def test_reused_renderer_names_the_experiment_and_keeps_fictional_label(self):
        kit = consumer.load_kit(KIT)
        report = consumer.render_fixture(
            kit, json.loads(FIXTURE.read_text()), "SPY", title="Watchlist Investigator",
        )
        self.assertTrue(report.startswith("# Watchlist Investigator\n"))
        self.assertIn("**Fictional data only.**", report)
        self.assertNotIn("consumer probe", report)


if __name__ == "__main__":
    unittest.main()
