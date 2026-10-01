"""Synthetic source-time evidence uses only parsed fields and an explicit clock."""

import json
import unittest

from scripts import watchlist_time as timing


class SourceTimeTests(unittest.TestCase):
    def assessment(self, times, reference="2026-10-01T14:01:00+00:00", threshold="900"):
        result = {"symbols": ["SPY"], "rows": {"SPY": {
            "gamma": {"as_of": times[0], "status": "available"},
            "vanna": {"as_of": times[1], "status": "missing from heatmap response"},
            "flow": {"generated_at": times[2], "latest_trade": times[3], "status": "partial: 1 invalid trades"},
        }}}
        return timing.assess_times(result, timing.parse_reference(reference), timing.parse_max_age(threshold))

    def report(self, times, **options):
        return timing.render_time_evidence(self.assessment(times, **options))

    def test_assessment_preserves_structured_evidence_for_later_consumers(self):
        assessment = self.assessment(["2026-10-01T14:00:00Z", None, None, None])
        self.assertEqual(json.loads(json.dumps(assessment, allow_nan=False)), assessment)
        self.assertEqual(assessment["rows"]["SPY"]["gamma.as_of"], {
            "timestamp": "2026-10-01T14:00:00+00:00", "age_seconds": 60,
            "status": "within threshold", "reason": None,
        })
        missing = assessment["rows"]["SPY"]["vanna.as_of"]
        self.assertIsNone(missing["age_seconds"])
        self.assertEqual(missing["status"], "unavailable")
        self.assertIn("missing from heatmap response", missing["reason"])

    def test_age_boundary_future_and_changed_reference(self):
        times = ["2026-10-01T13:46:00Z", "2026-10-01T13:45:59.999999Z",
                 "2026-10-01T14:01:01Z", "2026-10-01T14:01:00Z"]
        report = self.report(times)
        self.assertIn("| 900 | within threshold |", report)
        self.assertIn("| 900.000001 | stale |", report)
        self.assertIn("| -1 | future |", report)
        self.assertIn("| 0 | within threshold |", report)
        later = self.report(times, reference="2026-10-01T14:02:00Z")
        self.assertIn("| 960 | stale |", later)
        self.assertIn("| 59 | within threshold |", later)
        self.assertNotIn("| future |", later)
        self.assertIn("| 900 | stale |", self.report(times, threshold="0"))

    def test_offsets_are_equivalent_and_zero_span_is_not_an_atomic_snapshot(self):
        report = self.report(["2026-10-01T14:00:00Z", "2026-10-01T16:00:00+02:00",
                              "2026-10-01T07:00:00-07:00", "2026-10-01T14:00:00+00:00"])
        self.assertEqual(report.count("| 2026-10-01T14:00:00+00:00 | 60 | within threshold |"), 4)
        self.assertIn("SPY: observed timestamp span 0 seconds across 4 valid fields.", report)
        self.assertIn("even a zero span", report)
        self.assertIn("different measurements", report)

    def test_missing_invalid_and_naive_times_are_unavailable_with_component_reason(self):
        report = self.report([None, "invalid", "2026-10-01T14:00:00", []])
        self.assertEqual(report.count("| unavailable | unavailable |"), 4)
        self.assertIn("missing from heatmap response", report)
        self.assertIn("partial: 1 invalid trades", report)
        self.assertIn("span unavailable (0 valid fields; need at least 2)", report)
        self.assertIn("span unavailable (1 valid fields; need at least 2)",
                      self.report(["2026-10-01T14:00:00Z", None, None, None]))

    def test_span_excludes_unavailable_and_keeps_fields_distinct(self):
        report = self.report(["2026-10-01T13:59:00Z", None, "2026-10-01T14:02:00Z", None])
        for field in ("gamma.as_of", "vanna.as_of", "flow.generated_at", "flow.latest_trade"):
            self.assertIn(field, report)
        self.assertIn("observed timestamp span 180 seconds across 2 valid fields", report)

    def test_reference_and_threshold_reject_invalid_values(self):
        for value in ("", "bad", "2026-10-01", "2026-10-01T14:00:00", "0001-01-01T00:00:00+01:00"):
            with self.subTest(reference=value), self.assertRaisesRegex(ValueError, "--reference-time"):
                timing.parse_reference(value)
        for value in ("-1", "86401", "1.5", "nan", "inf", "1e3", "9" * 5000):
            with self.subTest(threshold=value[:20]), self.assertRaisesRegex(ValueError, "--max-age-seconds"):
                timing.parse_max_age(value)
        self.assertEqual(timing.parse_max_age("0"), 0)
        self.assertEqual(timing.parse_max_age("86400"), 86400)


if __name__ == "__main__":
    unittest.main()
