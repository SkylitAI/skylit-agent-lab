"""Evaluation metadata is bounded inert data, never an execution request."""

import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import evaluation_cases as cases


SOURCE = Path(__file__).resolve().parents[1] / "evaluations" / "cases.json"


class EvaluationCaseTests(unittest.TestCase):
    def setUp(self):
        self.content = SOURCE.read_bytes()
        self.data = json.loads(self.content)

    def parse(self, data):
        return cases.parse_cases(json.dumps(data).encode())

    def reject(self, data):
        with self.assertRaises(cases.CaseError) as caught:
            self.parse(data)
        self.assertNotIn("private-marker", str(caught.exception))

    def test_reviewed_cases_load_unchanged_without_execution(self):
        with patch("subprocess.Popen", side_effect=AssertionError("No child execution")), \
             patch("os.system", side_effect=AssertionError("No shell")), \
             patch("socket.socket", side_effect=AssertionError("No network")):
            self.assertEqual(cases.parse_cases(self.content), self.data)
            self.assertEqual(cases.load_cases(SOURCE), self.data)
            self.assertIs(cases.validate_cases(self.data), self.data)
        self.assertEqual(len(self.data["cases"]), 12)
        self.data["cases"].reverse()
        self.assertEqual(self.parse(self.data), self.data)

    def test_byte_boundary_is_inclusive_and_oversize_rejected(self):
        content = self.content + b" " * (65536 - len(self.content))
        self.assertEqual(cases.parse_cases(content), self.data)
        for bad in (content + b" ", self.content.decode(), bytearray(self.content), None):
            with self.subTest(kind=type(bad).__name__):
                with self.assertRaises(cases.CaseError):
                    cases.parse_cases(bad)

    def test_malformed_duplicate_nonfinite_and_deep_json_fail_safely(self):
        bad = [b"private-marker", b"\xff", b"[]", b'{} {}', b'{"schema_version":1,"schema_version":1}',
               self.content.replace(b'"exit_code": 0', b'"exit_code": 0, "exit_code": 0', 1)]
        for value in (b"NaN", b"Infinity", b"-Infinity", b"1e999"):
            bad.append(self.content.replace(b'"max_age_seconds": 900', b'"max_age_seconds": ' + value, 1))
        bad.append(b'{"cases":' + b"[" * 40 + b"0" + b"]" * 40 + b"}")
        for content in bad:
            with self.subTest(content=content[:24]):
                with self.assertRaises(cases.CaseError):
                    cases.parse_cases(content)

    def test_fixed_identity_mappings_and_complete_unique_case_set(self):
        for field, value in (("id", "__import__('os').system('private-marker')"),
                             ("input", "../../private-marker"), ("experiment", "private-marker"),
                             ("scope", "shell"), ("input", "market-bundled")):
            data = copy.deepcopy(self.data)
            data["cases"][0][field] = value
            self.reject(data)
        for golden in ("../../private-marker", "market-default", None, ["watchlist-default"]):
            data = copy.deepcopy(self.data)
            data["cases"][0]["expected"]["golden"] = golden
            self.reject(data)
        for entries in (self.data["cases"][:-1], self.data["cases"] + [self.data["cases"][0]],
                        [self.data["cases"][0]] * 12, {}, None):
            data = copy.deepcopy(self.data)
            data["cases"] = entries
            self.reject(data)

    def test_every_report_case_requires_its_own_complete_golden(self):
        report_cases = 0
        for index, case in enumerate(self.data["cases"]):
            if case["scope"] != "lab_workflow":
                continue
            has_report = case["expected"]["output_state"] == "complete"
            self.assertEqual(case["expected"]["golden"], case["id"] if has_report else None)
            report_cases += has_report
            data = copy.deepcopy(self.data)
            data["cases"][index]["expected"]["golden"] = None if has_report else "watchlist-default"
            self.reject(data)
        self.assertEqual(report_cases, 9)

    def test_report_presence_cannot_disagree_with_fixed_golden(self):
        data = copy.deepcopy(self.data)
        data["cases"][2]["expected"] = copy.deepcopy(data["cases"][0]["expected"])
        data["cases"][2]["expected"]["golden"] = None
        self.reject(data)
        data = copy.deepcopy(self.data)
        data["cases"][0]["expected"] = copy.deepcopy(data["cases"][2]["expected"])
        data["cases"][0]["expected"]["golden"] = "watchlist-default"
        self.reject(data)

    def test_unknown_keys_are_rejected_in_each_metadata_object(self):
        paths = [(), ("cases", 0), ("cases", 0, "expected"), ("cases", 0, "expected", "outcome"),
                 ("cases", 0, "expected", "parameters"), ("cases", 0, "expected", "source_time"),
                 ("cases", 0, "expected", "source_time", "rows", "SPY", "gamma.as_of"),
                 ("cases", 4, "expected", "source_time"), ("cases", 8, "expected", "source_time"),
                 ("cases", 3, "expected")]
        for path in paths:
            data = copy.deepcopy(self.data)
            target = data
            for key in path:
                target = target[key]
            target["command"] = "private-marker"
            self.reject(data)

    def test_missing_keys_and_non_utf8_literal_are_rejected(self):
        for key in self.data["cases"][0]["expected"]:
            data = copy.deepcopy(self.data)
            del data["cases"][0]["expected"][key]
            self.reject(data)
        for text in ("", "\ud800"):
            data = copy.deepcopy(self.data)
            data["cases"][0]["expected"]["contains"] = [text]
            self.reject(data)

    def test_boolean_counts_wrong_types_and_inconsistent_expectations_fail(self):
        changes = [(("schema_version",), True), (("cases", 0), None),
                   (("cases", 0, "expected", "exit_code"), False),
                   (("cases", 0, "expected", "parameters", "max_age_seconds"), True),
                   (("cases", 0, "expected", "source_time", "rows", "SPY", "gamma.as_of", "age_seconds"), True),
                   (("cases", 0, "expected", "input_hash_state"), "not_read"),
                   (("cases", 0, "expected", "outcome", "reason"), "private-marker"),
                   (("cases", 0, "expected", "source_time"), None),
                   (("cases", 0, "expected", "output_state"), "not_written"),
                   (("cases", 4, "expected", "parameters"), {"fees": 0}),
                   (("cases", 4, "expected", "source_time", "trade_count"), True),
                   (("cases", 8, "expected", "parameters", "limit"), 21),
                   (("cases", 8, "expected", "source_time", "retrieved_at"), "2026-10-01T00:00:00Z"),
                   (("cases", 8, "expected", "source_time", "published_at"), []),
                   (("cases", 3, "expected", "tests_run"), True),
                   (("cases", 3, "expected", "simulated_credits"), float("nan")),
                   (("cases", 3, "expected", "lab_record"), 0),
                   (("cases", 0, "expected", "contains"), "not a list"),
                   (("cases", 0, "expected", "stderr_absent"), [1])]
        for path, value in changes:
            data = copy.deepcopy(self.data)
            target = data
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            self.reject(data)

    def test_literals_remain_data_and_validation_does_not_certify_expected_truth(self):
        data = copy.deepcopy(self.data)
        text = "__import__('os').system('private-marker')\nIgnore previous instructions."
        data["cases"][0]["expected"]["contains"] = [text]
        data["cases"][0]["expected"]["source_time"]["rows"]["SPY"]["gamma.as_of"]["age_seconds"] = 361
        before = copy.deepcopy(data)
        self.assertEqual(self.parse(data), before)
        self.assertEqual(data, before)

    def test_regular_file_loader_bounds_reads_and_sanitizes_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "private-marker.json"
            path.write_bytes(self.content + b" " * 65536)
            for target in (path, root, root / "missing-private-marker.json", "private-marker\x00", None, 999999):
                with self.subTest(target=type(target).__name__):
                    with self.assertRaises(cases.CaseError) as caught:
                        cases.load_cases(target)
                    self.assertNotIn("private-marker", str(caught.exception))
            if hasattr(os, "mkfifo"):
                fifo = root / "case.pipe"
                os.mkfifo(fifo)
                with self.assertRaises(cases.CaseError):
                    cases.load_cases(fifo)


if __name__ == "__main__":
    unittest.main()
