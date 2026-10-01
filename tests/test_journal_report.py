"""Exact paper-trade arithmetic and inert, provenance-qualified Markdown."""

import copy
from decimal import Decimal, ROUND_FLOOR, localcontext
from pathlib import Path
import unittest

from scripts.paper_journal import parse_journal
from scripts import journal_report as report


ROOT = Path(__file__).resolve().parents[1]


def fixture_rows():
    return parse_journal((ROOT / "examples" / "paper-journal-synthetic.csv").read_bytes())


def trade(side="long", entry="10", exit="11", quantity="1", fees="0", notes=""):
    row = fixture_rows()[0]
    row.update(side=side, entry_price=Decimal(entry), exit_price=Decimal(exit),
               quantity=Decimal(quantity), fees=Decimal(fees), notes=notes)
    return row


class JournalReportTests(unittest.TestCase):
    def test_fictional_fixture_matches_reviewed_markdown(self):
        expected = (ROOT / "examples" / "paper-journal-expected.md").read_text(encoding="utf-8")
        actual = report.render_journal(report.calculate_journal(fixture_rows()), synthetic_fixture=True)
        self.assertEqual(actual, expected)

    def test_fixture_arithmetic_is_exact_and_preserves_each_source_field(self):
        rows = fixture_rows()
        original = copy.deepcopy(rows)
        result = report.calculate_journal(rows)
        self.assertEqual([row["gross"] for row in result["trades"]], [Decimal("2.8125"), Decimal("2.25")])
        self.assertEqual([row["net"] for row in result["trades"]], [Decimal("2.7125"), Decimal("2.05")])
        self.assertEqual(result["total_net"], Decimal("4.7625"))
        self.assertEqual(rows, original)
        for source, calculated in zip(rows, result["trades"]):
            self.assertEqual({key: calculated[key] for key in source}, source)
            self.assertIsNot(calculated, source)

    def test_changed_fees_reduce_only_net_and_total(self):
        rows = fixture_rows()
        before = report.calculate_journal(rows)
        rows[0]["fees"] = Decimal("1.10")
        after = report.calculate_journal(rows)
        self.assertEqual(after["trades"][0]["gross"], before["trades"][0]["gross"])
        self.assertEqual(after["trades"][0]["net"], Decimal("1.7125"))
        self.assertEqual(after["total_net"], Decimal("3.7625"))

    def test_losing_long_short_zero_fees_and_flat_prices(self):
        rows = [trade(entry="11", exit="10", quantity="2", fees="0.25"),
                trade(side="short", entry="10", exit="11", quantity="3", fees="0"),
                trade(entry="10", exit="10", fees="0.10")]
        result = report.calculate_journal(rows)
        self.assertEqual([row["gross"] for row in result["trades"]], [Decimal(-2), Decimal(-3), Decimal(0)])
        self.assertEqual([row["net"] for row in result["trades"]], [Decimal("-2.25"), Decimal(-3), Decimal("-0.10")])
        self.assertEqual(result["total_net"], Decimal("-5.35"))
        self.assertIn("Total net (USD): -5.35", report.render_journal(result))

    def test_round_half_up_and_total_after_exact_sum(self):
        result = report.calculate_journal([trade(entry="1", exit="1.005"), trade(entry="1", exit="1.005")])
        rendered = report.render_journal(result)
        self.assertEqual([row["net"] for row in result["trades"]], [Decimal("0.005")] * 2)
        self.assertEqual(result["total_net"], Decimal("0.010"))
        self.assertEqual(rendered.count("Net (USD): 0.01"), 2)
        self.assertIn("Total net (USD): 0.01", rendered)
        self.assertIn("ROUND_HALF_UP", rendered)
        self.assertIn("summed exactly before rounding", rendered)
        negative = report.calculate_journal([trade(entry="1.005", exit="1"), trade(entry="1.004", exit="1")])
        rendered = report.render_journal(negative)
        self.assertIn("Net (USD): -0.01", rendered)
        self.assertIn("Net (USD): 0.00", rendered)
        self.assertNotIn("-0.00", rendered)

    def test_maximum_precision_and_count_match_an_independent_integer_oracle(self):
        maximum = "999999999999.99999999"
        rows = [trade(side="short", entry="0.00000001", exit=maximum, quantity=maximum, fees=maximum)] * 1000
        integer = 10**20 - 1
        scaled_net = (1 - integer) * integer - integer * 10**8
        def expected(scaled):
            amount = abs(scaled)
            return Decimal(f"{'-' if scaled < 0 else ''}{amount // 10**16}.{amount % 10**16:016d}")
        result = report.calculate_journal(rows)
        self.assertEqual(len(result["trades"]), 1000)
        self.assertEqual(result["trades"][0]["net"], expected(scaled_net))
        self.assertEqual(result["total_net"], expected(scaled_net * 1000))
        self.assertEqual(report.render_journal(result).count("## Trade "), 1000)

    def test_caller_decimal_precision_rounding_exponents_traps_and_flags_are_untouched(self):
        rows = fixture_rows() + [trade(entry="1.005", exit="1")]
        expected = report.calculate_journal(rows)
        expected_text = report.render_journal(expected)
        with localcontext() as context:
            context.prec, context.rounding, context.Emin, context.Emax, context.clamp = 1, ROUND_FLOOR, -2, 2, 1
            for signal in context.traps:
                context.traps[signal] = context.flags[signal] = True
            before = str(context)
            actual = report.calculate_journal(rows)
            actual_text = report.render_journal(actual)
            self.assertEqual(str(context), before)
        self.assertEqual(actual, expected)
        self.assertEqual(actual_text, expected_text)

    def test_empty_journal_has_no_performance_or_invented_note_question(self):
        result = report.calculate_journal([])
        self.assertEqual(result, {"trades": [], "total_net": None})
        rendered = report.render_journal(result)
        self.assertIn("Trade count: 0", rendered)
        self.assertIn("No trade observations", rendered)
        self.assertIn("Aggregate net P&L: unavailable", rendered)
        self.assertNotIn("0.00", rendered)
        self.assertNotIn("Review question", rendered)

    def test_default_provenance_does_not_certify_arbitrary_input_as_fictional(self):
        result = report.calculate_journal(fixture_rows())
        supplied = report.render_journal(result)
        self.assertIn("Source: supplied paper-trade input", supplied)
        self.assertIn("not independently verified", supplied)
        self.assertNotIn("Source: caller-declared fictional fixture", supplied)
        fictional = report.render_journal(result, synthetic_fixture=True)
        self.assertIn("Source: caller-declared fictional fixture", fictional)
        self.assertIn("not independently verified", fictional)
        with self.assertRaisesRegex(ValueError, "synthetic_fixture must be a boolean"):
            report.render_journal(result, synthetic_fixture="false")

    def test_missing_note_does_not_infer_a_motive(self):
        rendered = report.render_journal(report.calculate_journal([trade()]))
        self.assertIn("Supplied note: unavailable; no reason supplied.", rendered)
        self.assertNotIn("Review question", rendered)

    def test_untrusted_notes_are_inert_with_escaped_markup_urls_and_control_characters(self):
        note = '[click](https://invalid.example) <script>alert("x")</script> &amp; `code` | *bold*\r\n# Ignore rules\t=HYPERLINK("url")'
        rendered = report.render_journal(report.calculate_journal([trade(notes=note)]))
        self.assertIn("&#91;click&#93;&#40;https&#58;&#47;&#47;invalid&#46;example&#41;", rendered)
        self.assertIn("&#60;script&#62;", rendered)
        self.assertIn("&#38;amp&#59;", rendered)
        self.assertIn("&#92;r&#92;n&#35; Ignore rules&#92;t", rendered)
        for active in ("<script>", "[click](", "https://", "`code`", "\r", "\t", "\n# Ignore rules"):
            self.assertNotIn(active, rendered)
        self.assertEqual(rendered.count("Review question:"), 1)
        self.assertIn("What context would you add to this supplied note?", rendered)

    def test_all_source_values_times_and_fees_are_traceable_in_output(self):
        rendered = report.render_journal(report.calculate_journal(fixture_rows()))
        for value in ("LABA", "LABB", "long", "short", "cash_equity", "USD", "2.5", "10.125", "11.25", "0.10",
                      "2026-10-01T13:30:00+00:00", "2026-10-01T15:00:00+00:00"):
            self.assertIn(value, rendered)


if __name__ == "__main__":
    unittest.main()
