"""Dry runs never read keys; live-path tests use synthetic HTTP responses only."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
import math
import os
from pathlib import Path
import socket
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import watchlist_live as live

KIT = Path(os.environ.get("SKYLIT_AGENT_KIT", ROOT.parent / "skylit-agent-kit"))


class LiveEntryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.root_patch = patch.object(live, "ROOT", self.root)
        self.root_patch.start(); self.addCleanup(self.root_patch.stop)
        self.kit = SimpleNamespace(make_plan=Mock(return_value={"symbols": ["SPY"], "requests": 5, "credits": 3}),
                                   number=lambda v: type(v) in (int, float) and math.isfinite(v),
                                   execute_live=Mock(side_effect=AssertionError("Unexpected execution")))
        self.cli = SimpleNamespace(credential=Mock(side_effect=AssertionError("Unexpected credential read")))

    def run_main(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with patch.object(live, "load_client", return_value=(self.kit, self.cli)), redirect_stdout(out), redirect_stderr(err):
            code = live.main(["--kit", str(KIT), *map(str, args)])
        return code, out.getvalue(), err.getvalue()

    def test_default_and_explicit_dry_run_never_read_keys_execute_or_write(self):
        for args in ((), ("--dry-run",)):
            code, out, err = self.run_main(*args)
            self.assertEqual((code, err), (0, ""))
            self.assertIn("DRY RUN", out)
            self.assertFalse((self.root / "reports").exists())
        self.cli.credential.assert_not_called(); self.kit.execute_live.assert_not_called()

    def test_invalid_and_insufficient_caps_stop_before_credentials(self):
        for args in (("--max-credits", "2"), ("--max-requests", "4"),
                     ("--max-seconds", "nan"), ("--max-seconds", "0"), ("--max-seconds", "3601")):
            code, out, err = self.run_main("--live", *args)
            self.assertEqual(code, 1); self.assertIn("error:", err)
        self.cli.credential.assert_not_called(); self.kit.execute_live.assert_not_called()

    def test_bad_output_paths_never_read_credentials_or_overwrite(self):
        reports = self.root / "reports"; reports.mkdir()
        existing = reports / "keep.md"; existing.write_text("keep")
        link = reports / "link.md"; link.symlink_to(existing)
        for output in (existing, link, reports, self.root / "escape.md", existing / "nested.md"):
            code, out, err = self.run_main("--live", "--output", output)
            self.assertEqual(code, 1); self.assertIn("error:", err)
        self.assertEqual(existing.read_text(), "keep")
        self.cli.credential.assert_not_called()

    def test_non_utf8_stops_before_loading_kit(self):
        with patch.object(live.locale, "getpreferredencoding", return_value="ascii"):
            code, out, err = self.run_main("--live")
        self.assertEqual(code, 1); self.assertIn("UTF-8", err)
        self.cli.credential.assert_not_called()

    def test_cancellation_at_key_prompt_or_execution_returns_without_traceback(self):
        self.cli.credential.side_effect = KeyboardInterrupt
        code, out, err = self.run_main("--live")
        self.assertEqual(code, 130); self.assertIn("Cancelled", err)
        self.kit.execute_live.assert_not_called()
        self.cli.credential.side_effect = None
        self.cli.credential.return_value = "synthetic-unused-key"
        self.kit.execute_live.side_effect = KeyboardInterrupt
        code, out, err = self.run_main("--live")
        self.assertEqual(code, 130); self.assertNotIn("Traceback", err)
        self.assertFalse((self.root / "reports").exists())


@unittest.skipUnless(KIT.is_dir(), "Live-path integration unverified: set SKYLIT_AGENT_KIT to the pinned checkout")
class PinnedLiveTransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kit, cls.cli = live.load_client(KIT)

    def run_mocked(self, directory, responses, *, key="synthetic-key", clock=None):
        out, err = io.StringIO(), io.StringIO()
        with patch.object(live, "ROOT", Path(directory)), \
             patch.object(live, "load_client", return_value=(self.kit, self.cli)), \
             patch.dict(os.environ, {"SKYLIT_API_KEY": key}, clear=True), \
             patch.object(sys.stdin, "isatty", return_value=False), \
             patch.object(socket, "socket", side_effect=AssertionError("Network forbidden")), \
             patch.object(self.kit, "build_opener") as opener, redirect_stdout(out), redirect_stderr(err):
            opener.return_value.open.side_effect = [r if isinstance(r, Exception) else io.BytesIO(json.dumps(r).encode()) for r in responses]
            if clock is None:
                code = live.main(["--kit", str(KIT), "--live"])
            else:
                with patch.object(self.kit.time, "monotonic", side_effect=clock):
                    code = live.main(["--kit", str(KIT), "--live"])
            calls = opener.return_value.open.call_count
        report = Path(directory) / "reports/live-watchlist.md"
        return code, out.getvalue() + err.getvalue(), report.read_text() if report.exists() else "", calls

    def payloads(self, balance=100):
        fixture = json.loads((ROOT / "experiments/watchlist-investigator/fixture.json").read_text())
        fixture["gamma"]["meta"]["attribution"] = "</pre><script>synthetic-key</script>"
        account = {"data": {"status": "active", "apiEligible": True, "creditsBalance": balance,
                            "limits": {"symbolsPerHeatmapCall": 10, "requestsPerMinute": 120}}}
        catalog = {"data": {"symbols": [{"symbol": "SPY", "metrics": ["gamma", "vanna"]}]}}
        return [account, catalog, fixture["gamma"], fixture["vanna"], fixture["flow"]["SPY"]]

    def test_mocked_success_preserves_attribution_redaction_and_private_utf8_report(self):
        with tempfile.TemporaryDirectory() as directory:
            code, output, report, calls = self.run_mocked(directory, self.payloads())
            self.assertEqual((code, calls), (0, 5), output)
            self.assertIn("Data: [Skylit]", report)
            self.assertIn("&lt;script&gt;", report)
            self.assertNotIn("<script>", report)
            self.assertNotIn("synthetic-key", report + output)
            self.assertIn("5 requests attempted; 3 documented credits", report)
            if os.name != "nt":
                self.assertEqual((Path(directory) / "reports/live-watchlist.md").stat().st_mode & 0o777, 0o600)

    def test_surrogate_source_notice_preserves_completed_report(self):
        payloads = self.payloads()
        payloads[2]["meta"]["attribution"] = "\ud800"
        with tempfile.TemporaryDirectory() as directory:
            code, output, report, calls = self.run_mocked(directory, payloads)
        self.assertEqual((code, calls), (0, 5), output)
        self.assertIn("\\ud800", report)
        self.assertIn("Data: [Skylit]", report)

    def test_missing_key_never_opens_transport(self):
        with tempfile.TemporaryDirectory() as directory:
            code, output, report, calls = self.run_mocked(directory, [], key="")
        self.assertEqual((code, calls, report), (1, 0, ""))
        self.assertIn("hidden key prompt", output)

    def test_account_balance_stops_before_paid_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            code, output, report, calls = self.run_mocked(directory, self.payloads(balance=0))
        self.assertEqual((code, calls), (2, 2))
        self.assertIn("0 documented credits", report)

    def test_rate_limit_timeout_and_bad_json_stop_without_retries(self):
        for error in (HTTPError("https://api.skylit.ai", 429, "private synthetic-key", {}, None), TimeoutError("private synthetic-key")):
            with tempfile.TemporaryDirectory() as directory:
                code, output, report, calls = self.run_mocked(directory, [error])
            self.assertEqual((code, calls), (2, 1))
            self.assertNotIn("synthetic-key", report + output)
        with tempfile.TemporaryDirectory() as directory:
            code, output, report, calls = self.run_mocked(directory, [[]])
        self.assertEqual((code, calls), (2, 1)); self.assertIn("unexpected response shape", report)

    def test_elapsed_cap_stops_before_first_request(self):
        with tempfile.TemporaryDirectory() as directory:
            code, output, report, calls = self.run_mocked(directory, [], clock=[0, 31])
        self.assertEqual((code, calls), (2, 0)); self.assertIn("Elapsed-time budget", report)
