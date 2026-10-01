"""Exercise the real pinned Kit from a credential-free, socket-blocked process."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

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
        with self.assertRaises(consumer.KitError) as caught:
            consumer.load_kit_with_metadata(ROOT)
        self.assertEqual(caught.exception.code, "kit_mismatch")
        self.assertEqual(caught.exception.metadata["verification"], "revision_mismatch")

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
            for contents, message in (
                ("not json", "Fixture must contain valid UTF-8 JSON within the nesting limit."),
                ("[]", "Fixture requires gamma, vanna and flow objects."),
                (json.dumps(wrong_metric), "Heatmap response has invalid shape or wrong metric."),
            ):
                with self.subTest(contents=contents[:40]):
                    path.write_text(contents)
                    result = self.run_probe("--fixture", str(path))
                    self.assertEqual(result.returncode, 1)
                    self.assertEqual(result.stdout, "")
                    self.assertIn("error:", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertEqual(result.stderr, f"error: {message}\n")

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
            with self.assertRaises(consumer.KitError) as caught:
                consumer.load_kit_with_metadata(checkout)
            self.assertEqual(caught.exception.code, "kit_dirty")
            self.assertEqual(caught.exception.metadata, {"required_revision": consumer.KIT_REVISION,
                             "observed_revision": consumer.KIT_REVISION, "verification": "dirty"})
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("Kit checkout must be clean", result.stderr)


class KitMetadataTests(unittest.TestCase):
    def test_unknown_status_or_missing_package_preserves_head_without_importing(self):
        with tempfile.TemporaryDirectory() as directory:
            for state in ("unknown", "clean"):
                with mock.patch.object(consumer, "inspect_checkout", return_value={"revision": consumer.KIT_REVISION, "state": state}), \
                        mock.patch.object(consumer.importlib, "import_module") as importer:
                    with self.assertRaises(consumer.KitError) as caught:
                        consumer.load_kit_with_metadata(directory)
                importer.assert_not_called()
                self.assertEqual(caught.exception.code, "kit_unavailable")
                self.assertEqual(caught.exception.metadata["observed_revision"], consumer.KIT_REVISION)
                self.assertEqual(caught.exception.metadata["verification"], "read_failed")

    def test_missing_kit_exposes_only_safe_failure_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(consumer.KitError) as caught:
                consumer.load_kit_with_metadata(Path(directory) / "missing")
        self.assertEqual(caught.exception.code, "kit_unavailable")
        self.assertEqual(caught.exception.metadata, {"required_revision": consumer.KIT_REVISION,
                         "observed_revision": None, "verification": "read_failed"})
        self.assertNotIn(directory, str(caught.exception))
        self.assertIsNone(caught.exception.__context__)

    @unittest.skipUnless(KIT.is_dir(), "Set SKYLIT_AGENT_KIT to the pinned local checkout")
    def test_pinned_kit_returns_verified_metadata_and_keeps_wrapper(self):
        kit, metadata = consumer.load_kit_with_metadata(KIT)
        self.assertIs(consumer.load_kit(KIT), kit)
        self.assertEqual(Path(kit.__file__).resolve(), KIT.resolve() / "skylit_agent_kit" / "watchlist.py")
        self.assertEqual(metadata, {"required_revision": consumer.KIT_REVISION,
                         "observed_revision": consumer.KIT_REVISION, "verification": "verified"})

    @unittest.skipUnless(KIT.is_dir(), "Set SKYLIT_AGENT_KIT to the pinned local checkout")
    def test_failed_or_foreign_import_is_never_verified(self):
        for fake in (ImportError("private import detail"), mock.Mock(__file__=str(ROOT / "foreign.py"))):
            patch = {"side_effect": fake} if isinstance(fake, Exception) else {"return_value": fake}
            with mock.patch.object(consumer.importlib, "import_module", **patch):
                with self.assertRaises(consumer.KitError) as caught:
                    consumer.load_kit_with_metadata(KIT)
            self.assertEqual(caught.exception.code, "kit_unavailable")
            self.assertEqual(caught.exception.metadata["observed_revision"], consumer.KIT_REVISION)
            self.assertEqual(caught.exception.metadata["verification"], "read_failed")
            self.assertNotIn("private import detail", str(caught.exception))
            self.assertIsNone(caught.exception.__context__)


class FixtureInputTests(unittest.TestCase):
    def test_hash_covers_exact_bytes_including_whitespace(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json"
            path.write_bytes(b"{}")
            parsed, digest = consumer.load_fixture_with_hash(path)
            self.assertEqual(parsed, {})
            self.assertEqual(digest, "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a")
            path.write_bytes(b"{} \r\n")
            changed, changed_digest = consumer.load_fixture_with_hash(path)
            self.assertEqual(changed, parsed)
            self.assertEqual(changed_digest, hashlib.sha256(b"{} \r\n").hexdigest())
            self.assertNotEqual(changed_digest, digest)
            self.assertEqual(consumer.load_fixture(path), changed)

    def test_hash_and_parser_share_the_consumed_buffer(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json"
            content = b'{"original": true}'
            path.write_bytes(content)
            original_loads = json.loads

            def replace_after_read(value):
                path.write_bytes(b'{"replacement": true}')
                return original_loads(value)

            with mock.patch.object(consumer.json, "loads", side_effect=replace_after_read):
                parsed, digest = consumer.load_fixture_with_hash(path)
            self.assertEqual(parsed, {"original": True})
            self.assertEqual(digest, hashlib.sha256(content).hexdigest())

    def test_complete_invalid_bytes_keep_hash_without_payload_in_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "private-name.json"
            for content in (b"", b"private malformed payload", b"\xff", b"[" * 2000 + b"]" * 1999):
                with self.subTest(content=content[:20]):
                    path.write_bytes(content)
                    with self.assertRaises(consumer.FixtureError) as caught:
                        consumer.load_fixture_with_hash(path)
                    error = caught.exception
                    self.assertIsInstance(error, ValueError)
                    self.assertEqual((error.code, error.hash_state), ("invalid_fixture", "complete"))
                    self.assertEqual(error.sha256, hashlib.sha256(content).hexdigest())
                    self.assertEqual(str(error), "Fixture must contain valid UTF-8 JSON within the nesting limit.")
                    self.assertIsNone(error.__context__)

    def test_incomplete_input_has_no_full_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json"
            path.write_bytes(b" " * 65537)
            for source, code, state in ((path, "input_too_large", "too_large"),
                                        (Path(directory), "input_unreadable", "read_failed"),
                                        (path.with_name("missing.json"), "input_unreadable", "read_failed")):
                with self.subTest(code=code, source=source.name):
                    with self.assertRaises(consumer.FixtureError) as caught:
                        consumer.load_fixture_with_hash(source)
                    self.assertEqual((caught.exception.code, caught.exception.hash_state), (code, state))
                    self.assertIsNone(caught.exception.sha256)
                    self.assertIsNone(caught.exception.__context__)
            with mock.patch.object(consumer.os, "open", side_effect=PermissionError("private path")):
                with self.assertRaises(consumer.FixtureError) as caught:
                    consumer.load_fixture_with_hash(path)
            self.assertEqual((caught.exception.code, caught.exception.hash_state, caught.exception.sha256),
                             ("input_unreadable", "read_failed", None))
            self.assertEqual(str(caught.exception), "Choose a readable regular JSON file for --fixture.")
            self.assertIsNone(caught.exception.__context__)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "Named pipes require POSIX")
    def test_fifo_is_rejected_even_after_a_stale_regular_file_check(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.pipe"
            os.mkfifo(path)
            code = """
from pathlib import Path
import runpy, sys
from unittest import mock
module = runpy.run_path(sys.argv[1])
with mock.patch.object(Path, 'is_file', return_value=True):
    try:
        module['load_fixture_with_hash'](sys.argv[2])
    except module['FixtureError'] as error:
        assert (error.code, error.hash_state, error.sha256) == ('input_unreadable', 'read_failed', None)
    else:
        raise AssertionError('A FIFO was accepted as a regular fixture')
"""
            result = subprocess.run([sys.executable, "-I", "-B", "-c", code, str(PROBE), str(path)],
                                    capture_output=True, text=True, timeout=5, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_fixture_read_has_an_inclusive_64_kib_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json"
            content = b"{}" + b" " * (65536 - 2)
            path.write_bytes(content)
            self.assertEqual(consumer.load_fixture_with_hash(path), ({}, hashlib.sha256(content).hexdigest()))
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
