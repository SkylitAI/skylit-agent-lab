"""Faithful synthetic artifacts; independent tampering never changes expectations."""

import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import evaluation_results as results
from scripts.evaluation_cases import load_cases
from scripts.run_records import parse_record
from test_run_records import sample_record, seed_record


ROOT = Path(__file__).resolve().parents[1]
CASES = {case["id"]: case for case in load_cases(ROOT / "evaluations/cases.json")["cases"]}
LAB = {"revision": "a" * 40, "state": "clean"}  # Invented pre-output observation.
KIT_PIN = "0f82039759ef4db9d5b3dbd90f52863f8074f2a6"
KIT = {"required_revision": KIT_PIN, "observed_revision": KIT_PIN, "verification": "verified"}


def inputs():
    watchlist = (ROOT / "experiments/watchlist-investigator/fixture.json").read_bytes()
    journal = (ROOT / "experiments/journal-reviewer/fixture.csv").read_bytes()
    market = (ROOT / "experiments/market-brief/fixture.xml").read_bytes()
    changed = json.loads(watchlist)
    changed["gamma"]["data"]["symbols"][0]["strikes"][0]["value"] = -199
    changed["gamma"]["data"]["symbols"][0]["asOf"] = "2026-10-01T13:44:00Z"
    changed["vanna"]["data"]["symbols"][0]["asOf"] = "2026-10-01T14:02:00Z"
    del changed["flow"]["SPY"]["data"]["trades"][0]["timestamp"]
    return {"watchlist-bundled": watchlist,
        "watchlist-changed-evidence": (json.dumps(changed, sort_keys=True, separators=(",", ":")) + "\n").encode(),
        "invalid-json": b"not JSON\n", "journal-bundled": journal,
        "journal-fees-gap": journal.replace(b",0.10,", b",1.10,").replace(b"Fictional long paper trade.", b""),
        "journal-header-only": journal.splitlines(keepends=True)[0],
        "journal-missing-exit": journal.replace(b",11.25,", b",,"), "market-bundled": market,
        "market-changed-title": market.replace(b"paper kites", b"changed fictional wording"),
        "market-empty-channel": b'<rss version="2.0"><channel><title>Fictional</title><link>https://www.federalreserve.gov/feeds/feeds.htm</link><description>Fictional</description></channel></rss>',
        "invalid-xml": b"not xml: private-marker\n"}


def golden(name):
    if name is None:
        return None
    files = {"watchlist-default": "evaluations/watchlist-expected.md",
             "journal-default": "examples/paper-journal-expected.md"}
    if name in files:
        return (ROOT / files[name]).read_bytes()
    if name == "market-default":
        body = (ROOT / "experiments/market-brief/README.md").read_bytes()
        start, end = b"<!-- expected-start -->\n```markdown\n", b"```\n<!-- expected-end -->"
    else:
        body = (ROOT / "evaluations/variant-expected.md").read_bytes()
        start = f"<!-- expected-start: {name} -->\n```markdown\n".encode()
        end = f"```\n<!-- expected-end: {name} -->".encode()
    assert body.count(start) == body.count(end) == 1
    return body.split(start)[1].split(end)[0]


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name).resolve()
        self.number = 0

    def prepare(self, name="market-default"):
        self.number += 1
        folder = self.folder / str(self.number)
        folder.mkdir(mode=0o700)
        self.output = folder / "report.md"
        self.sidecar = Path(str(self.output) + ".run.json")
        case = copy.deepcopy(CASES[name])
        expected = case["expected"]
        watchlist = case["experiment"] == "watchlist-investigator"
        record = sample_record() if watchlist else seed_record(case["experiment"], expected["mode"])
        record.update(lab=copy.deepcopy(LAB), kit=copy.deepcopy(KIT) if watchlist else None,
                      parameters=copy.deepcopy(expected["parameters"]), source_time=copy.deepcopy(expected["source_time"]),
                      outcome=copy.deepcopy(expected["outcome"]))
        raw = inputs()[case["input"]]
        record["inputs"][0].update(sha256=hashlib.sha256(raw).hexdigest(), hash_state="complete")
        report = golden(expected["golden"])
        record["outputs"][0].update(filename=self.output.name, state=expected["output_state"],
                                   sha256=hashlib.sha256(report).hexdigest() if report is not None else None)
        self.record = record
        self.options = {"exit_code": expected["exit_code"], "stderr": "", "input_bytes": raw,
                        "lab": copy.deepcopy(LAB), "kit": copy.deepcopy(KIT) if watchlist else None,
                        "golden": report, "report_path": self.output}
        self.case = case
        if report is not None:
            self.output.write_bytes(report)
            self.output.chmod(0o600)
        self.write_record()
        parse_record(self.sidecar.read_bytes())  # Baseline must be schema-valid before independent mutations.

    def write_record(self):
        self.sidecar.write_bytes((json.dumps(self.record) + "\n").encode())
        self.sidecar.chmod(0o600)

    def compare(self, **changes):
        return results.compare_workflow(self.case, **(self.options | changes))

    def tamper_report(self, raw):
        self.assertNotEqual(raw, self.options["golden"])
        self.output.write_bytes(raw)
        self.record["outputs"][0]["sha256"] = hashlib.sha256(raw).hexdigest()
        self.write_record()
        parse_record(self.sidecar.read_bytes())
        failures = self.compare()
        self.assertIn("golden_mismatch", failures)
        self.assertNotIn("report_hash_mismatch", failures)

    def test_all_eleven_workflow_artifacts_match_including_stopped_and_backward_clock(self):
        for name, case in CASES.items():
            if case["scope"] == "lab_workflow":
                with self.subTest(name=name):
                    self.prepare(name)
                    self.assertEqual(self.compare(), ())
                    self.assertLess(self.record["execution"]["finished_at"], self.record["execution"]["started_at"])

    def test_full_golden_rejects_rehashed_source_detail_gap_and_invented_content(self):
        mutations = [
            ("watchlist-changed-evidence", lambda raw: raw.replace(b"source king: 110 / -199", b"source king: 110 / -180")),
            ("watchlist-changed-evidence", lambda raw: raw.replace(b"| 110 | -199 | king |", b"| 110 | -180 | king |")),
            ("watchlist-changed-evidence", lambda raw: raw.replace(b"| QQQ | missing from heatmap response | missing from heatmap response | missing from synthetic fixture |\n", b"")),
            ("watchlist-changed-evidence", lambda raw: raw.replace(b"| -60 | future |", b"| -60 | within threshold |")),
            ("journal-fees-gap", lambda raw: raw.replace(b"Total net (USD): 3.76", b"Total net (USD): 4.76")),
            ("journal-fees-gap", lambda raw: raw + b"\nInvented LABA motive: impatience. Review question: why rush?\n"),
            ("journal-empty", lambda raw: raw + b"\nEarned P&L: 0.00\n"),
            ("market-changed-limited", lambda raw: raw.replace(b"changed fictional wording", b"paper kites")),
            ("market-changed-limited", lambda raw: raw + b"\n### Published (UTC): 2020-01-03T00:00:00+00:00\nInvented extra release\n"),
            ("market-empty", lambda raw: raw.replace(b"; this does not establish an absence of announcements", b"")),
        ]
        for name, mutation in mutations:
            with self.subTest(name=name):
                self.prepare(name)
                self.assertEqual(self.compare(), ())
                self.tamper_report(mutation(self.options["golden"]))

    def test_full_golden_is_required_even_if_all_literal_checks_still_match(self):
        for name in ("watchlist-changed-evidence", "journal-fees-gap", "market-changed-limited"):
            self.prepare(name)
            raw = self.options["golden"] + b"\nUnreviewed added text.\n"
            self.assertTrue(all(item in raw.decode() for item in self.case["expected"]["contains"]))
            self.assertTrue(all(item not in raw.decode() for item in self.case["expected"]["absent"]))
            self.tamper_report(raw)
        self.prepare()
        for bad in (None, self.options["golden"].decode(), b"\xff"):
            self.assertIn("invalid_golden", self.compare(golden=bad))

    def test_record_mismatches_are_detected_independently_of_report_hash(self):
        changes = [(("inputs", 0, "sha256"), "b" * 64, "input_hash_mismatch"),
                   (("lab", "revision"), "b" * 40, "lab_mismatch"),
                   (("lab", "state"), "dirty", "lab_mismatch"),
                   (("kit", "required_revision"), "b" * 40, "record_invalid"),
                   (("kit", "observed_revision"), None, "record_invalid"),
                   (("outputs", 0, "sha256"), "b" * 64, "report_hash_mismatch"),
                   (("outputs", 0, "filename"), "other.md", "output_name_mismatch"),
                   (("source_time", "rows", "SPY", "gamma.as_of", "age_seconds"), 361, "source_time_mismatch")]
        for path, value, reason in changes:
            self.prepare("watchlist-default")
            target = self.record
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            self.write_record()
            self.assertIn(reason, self.compare(), path)
        self.prepare("watchlist-default")
        self.record["kit"].update(required_revision="b" * 40, observed_revision="b" * 40)
        self.write_record()
        self.assertIn("kit_mismatch", self.compare())
        self.prepare("market-changed-limited")
        self.record["mode"] = "offline_synthetic"
        self.record["parameters"]["limit"] = 2
        self.write_record()
        self.assertIn("mode_mismatch", self.compare())
        self.assertIn("parameters_mismatch", self.compare())

    def test_exit_stderr_input_and_observation_mismatches_fail(self):
        self.prepare("market-invalid")
        self.assertIn("exit_code_mismatch", self.compare(exit_code=0))
        self.assertIn("exit_code_mismatch", self.compare(exit_code=True))
        self.assertIn("stderr_forbidden", self.compare(stderr="invented private-marker"))
        self.assertIn("input_hash_mismatch", self.compare(input_bytes=b"other prepared input"))
        for lab in (None, {"revision": None, "state": "unknown"}, {"revision": "a" * 40, "state": "dirty"},
                    {"revision": "not-a-sha", "state": "clean"}):
            self.assertIn("invalid_provenance", self.compare(lab=lab))
        self.prepare("watchlist-invalid")
        for kit in (None, KIT | {"verification": "not_checked", "observed_revision": None},
                    KIT | {"verification": "dirty"}, KIT | {"observed_revision": "b" * 40}):
            self.assertIn("invalid_provenance", self.compare(kit=kit))
        self.record["kit"].update(verification="not_checked", observed_revision=None)
        self.write_record()
        self.assertIn("kit_mismatch", self.compare())
        self.prepare()
        self.assertIn("invalid_provenance", self.compare(kit=KIT))

    def test_schema_valid_stopped_record_still_needs_known_usage_and_finish(self):
        self.prepare("market-invalid")
        self.record["usage"].update(basis="unknown", requests_attempted=None, credits_reserved=None)
        self.record["execution"]["finished_at"] = None
        self.write_record()
        parse_record(self.sidecar.read_bytes())
        self.assertIn("usage_mismatch", self.compare())
        self.assertIn("execution_unfinished", self.compare())

    def test_schema_valid_wrong_workflow_outcome_and_output_state_fail(self):
        self.prepare("market-invalid")
        self.record["outcome"]["reason"] = "output_write_failed"
        self.write_record()
        parse_record(self.sidecar.read_bytes())
        self.assertIn("outcome_mismatch", self.compare())
        self.prepare("market-default")
        self.case = copy.deepcopy(CASES["journal-default"])
        self.assertIn("experiment_id_mismatch", self.compare())
        self.prepare("watchlist-invalid")
        self.record["inputs"][0].update(hash_state="not_read", sha256=None)
        self.record["outputs"][0].update(state="complete", sha256="b" * 64)
        self.write_record()
        parse_record(self.sidecar.read_bytes())
        self.assertIn("input_state_mismatch", self.compare())
        self.assertIn("output_state_mismatch", self.compare())

    def test_comparison_never_starts_processes_or_network_requests(self):
        self.prepare()
        with patch("subprocess.Popen", side_effect=AssertionError("Unexpected child")), \
             patch("socket.socket", side_effect=AssertionError("Unexpected network")):
            self.assertEqual(self.compare(), ())

    def test_schema_is_reused_for_unknown_keys_bool_numbers_and_profile_limits(self):
        for mutate in (lambda r: r.update(private_payload="PRIVATE-CONTENT"),
                       lambda r: r["limits"].update(requests=1),
                       lambda r: r["source_time"]["spans"]["SPY"].update(seconds=True)):
            self.prepare("watchlist-default")
            mutate(self.record)
            self.write_record()
            self.assertEqual(self.compare(), ("record_invalid",))
        self.prepare("watchlist-default")
        self.record["source_time"]["spans"]["SPY"]["seconds"] = 120.0
        self.write_record()
        self.assertEqual(self.compare(), ())

    def test_not_written_requires_absence_not_empty_file_or_dangling_link(self):
        for name in ("watchlist-invalid", "journal-open"):
            self.prepare(name)
            self.assertEqual(self.compare(), ())
            self.output.write_bytes(b"")
            self.output.chmod(0o600)
            self.assertIn("unexpected_report", self.compare())
            self.output.unlink()
            self.output.symlink_to(self.folder / "absent")
            self.assertIn("unexpected_report", self.compare())

    def test_literals_are_inert_and_checked_in_addition_to_the_full_golden(self):
        self.prepare()
        self.case["expected"]["contains"] = ["__import__('os').system('PRIVATE-CONTENT')"]
        self.assertIn("report_required_text_missing", self.compare())
        self.case["expected"]["contains"] = []
        self.case["expected"]["absent"] = ["Fictional notice"]
        self.assertIn("report_forbidden_text", self.compare())

    def test_missing_malformed_and_oversized_artifacts_have_fixed_safe_reasons(self):
        for role in ("record", "report"):
            self.prepare()
            path = self.sidecar if role == "record" else self.output
            path.unlink()
            self.assertIn(role + "_missing", self.compare())
            path.write_bytes(b"x" * ((262144 if role == "record" else 131072) + 1))
            path.chmod(0o600)
            self.assertIn(role + "_too_large", self.compare())
        self.prepare()
        self.sidecar.write_bytes(b"PRIVATE-CONTENT\xff")
        self.assertEqual(self.compare(), ("record_invalid",))
        self.assertNotIn(str(self.folder), repr(self.compare()))

    @unittest.skipUnless(os.name == "posix", "POSIX owner/mode observations")
    def test_artifacts_require_private_permissions_and_current_owner(self):
        for role in ("record", "report"):
            self.prepare()
            path = self.sidecar if role == "record" else self.output
            path.chmod(0o644)
            self.assertIn(role + "_not_private", self.compare())
        self.prepare()
        with patch.object(results.os, "geteuid", return_value=os.geteuid() + 1):
            self.assertIn("record_not_private", self.compare())

    def test_symlinks_directories_and_fifos_are_not_read_as_artifacts(self):
        for role in ("record", "report"):
            for kind in ("symlink", "directory", "fifo"):
                if kind == "fifo" and not hasattr(os, "mkfifo"):
                    continue
                self.prepare()
                path = self.sidecar if role == "record" else self.output
                target = path.with_name("private-target")
                path.rename(target)
                if kind == "symlink":
                    path.symlink_to(target)
                elif kind == "directory":
                    path.mkdir(mode=0o700)
                else:
                    os.mkfifo(path, 0o600)
                self.assertIn(role + "_not_regular", self.compare())
        self.prepare()
        alias = self.folder / "alias"
        alias.symlink_to(self.output.parent, target_is_directory=True)
        self.assertIn("record_not_regular", self.compare(report_path=alias / self.output.name))

    def test_dependency_case_is_outside_this_comparator(self):
        self.prepare()
        self.case = CASES["kit-budget-stop"]
        self.assertEqual(self.compare(), ("unsupported_scope",))

    def test_exact_golden_bytes_are_not_newline_normalized(self):
        self.prepare("watchlist-default")
        self.tamper_report(self.options["golden"].replace(b"\n", b"\r\n"))


if __name__ == "__main__":
    unittest.main()
