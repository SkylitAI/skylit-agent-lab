"""Closed fictional cash-equity rows normalize exactly or fail without data leaks."""

import csv
from datetime import datetime, timezone
from decimal import Decimal, localcontext
import io
from pathlib import Path
import unittest

from scripts import paper_journal as journal


HEADERS = "symbol asset_type currency side quantity entry_price exit_price fees entry_time exit_time".split()
TRADE = ["laba", "cash_equity", "USD", "long", "1.25000000", "10.10", "11.25", "0.05",
         "2026-10-01T09:30:00-04:00", "2026-10-01T14:00:00Z"]


def csv_bytes(rows=None, headers=None):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(HEADERS if headers is None else headers)
    writer.writerows([TRADE] if rows is None else rows)
    return stream.getvalue().encode("utf-8")


class JournalTests(unittest.TestCase):
    def reject(self, content, field, reason, row=2):
        with self.assertRaises(journal.JournalError) as caught:
            journal.parse_journal(content)
        error = caught.exception
        self.assertEqual((error.row, error.field, error.reason), (row, field, reason))
        self.assertNotIn("private-sentinel", str(error))
        self.assertIsNone(error.__context__)
        return error

    def test_fictional_fixture_contains_long_and_short_rows_without_derived_results(self):
        fixture = Path(__file__).resolve().parents[1] / "examples" / "paper-journal-synthetic.csv"
        rows = journal.parse_journal(fixture.read_bytes())
        self.assertEqual([(row["symbol"], row["side"]) for row in rows], [("LABA", "long"), ("LABB", "short")])
        self.assertEqual(rows[0]["quantity"], Decimal("2.5"))
        self.assertEqual(rows[1]["entry_price"], Decimal("25"))
        self.assertTrue(all(set(row) == set(HEADERS + ["notes"]) for row in rows))

    def test_fractional_trade_normalizes_exactly_without_decimal_context_rounding(self):
        with localcontext() as context:
            context.prec = 2
            rows = journal.parse_journal(csv_bytes())
        self.assertEqual(rows, [{
            "symbol": "LABA", "asset_type": "cash_equity", "currency": "USD", "side": "long",
            "quantity": Decimal("1.25000000"), "entry_price": Decimal("10.10"),
            "exit_price": Decimal("11.25"), "fees": Decimal("0.05"),
            "entry_time": datetime(2026, 10, 1, 13, 30, tzinfo=timezone.utc),
            "exit_time": datetime(2026, 10, 1, 14, 0, tzinfo=timezone.utc), "notes": "",
        }])
        self.assertEqual(rows[0]["quantity"].as_tuple().exponent, -8)

    def test_column_order_short_side_and_equal_offset_instants_are_supported(self):
        row = TRADE.copy()
        row[3], row[7] = "short", "0"
        row[9] = "2026-10-01T15:30:00+02:00"
        parsed = journal.parse_journal(csv_bytes([row[::-1]], HEADERS[::-1]))[0]
        self.assertEqual(parsed["side"], "short")
        self.assertEqual(parsed["entry_time"], parsed["exit_time"])
        self.assertEqual(parsed["fees"], Decimal(0))

    def test_header_only_is_an_explicit_empty_journal_but_empty_bytes_are_invalid(self):
        self.assertEqual(journal.parse_journal(csv_bytes([])), [])
        self.assertEqual(journal.parse_journal(csv_bytes([], HEADERS + ["notes"])), [])
        self.reject(b"", "header", "missing", 1)

    def test_exact_headers_reject_duplicate_unknown_missing_and_whitespace(self):
        for headers, reason in ((HEADERS + ["symbol"], "duplicate"),
                                (HEADERS + ["private-sentinel"], "unknown"),
                                (HEADERS[:-1], "missing"),
                                ([" symbol"] + HEADERS[1:], "unknown")):
            with self.subTest(reason=reason, headers=headers):
                self.reject(csv_bytes([], headers), "header", reason, 1)

    def test_uneven_and_blank_records_are_rejected_without_partial_results(self):
        for bad in (TRADE[:-1], TRADE + ["private-sentinel"], []):
            self.reject(csv_bytes([TRADE, bad]), "csv", "row_width", 3)

    def test_assets_currency_side_symbol_and_open_trades_are_rejected(self):
        cases = {"symbol": ["", "private-sentinel", "123", "S P Y", "ÅBC"],
                 "asset_type": ["option", "crypto", "fx", "cash_equity "],
                 "currency": ["EUR", "usd", ""], "side": ["buy", "LONG", ""],
                 "exit_price": [""], "exit_time": [""]}
        for field, values in cases.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    row = TRADE.copy()
                    row[HEADERS.index(field)] = value
                    reason = "closed_trade_required" if field.startswith("exit_") else "unsupported" if field in ("asset_type", "currency", "side") else "invalid_symbol"
                    self.reject(csv_bytes([row]), field, reason)

    def test_decimal_format_rejects_ambiguous_nonfinite_signed_and_huge_values(self):
        values = ["", "private-sentinel", "-1", "+1", "NaN", "sNaN", "Inf", "Infinity", "1e2",
                  "1E99999", "1,000", "1,5", "1_000", " 1", "1 ", ".5", "1.", "01", "١",
                  "9" * 13, "0.123456789", "9" * 10000]
        for field in ("quantity", "entry_price", "exit_price", "fees"):
            for value in values:
                with self.subTest(field=field, value=value[:20]):
                    row = TRADE.copy()
                    row[HEADERS.index(field)] = value
                    reason = "closed_trade_required" if field == "exit_price" and not value else "invalid_decimal"
                    self.reject(csv_bytes([row]), field, reason)
        for field in ("quantity", "entry_price", "exit_price"):
            row = TRADE.copy()
            row[HEADERS.index(field)] = "0.00000000"
            self.reject(csv_bytes([row]), field, "must_be_positive")

    def test_decimal_precision_boundaries_are_inclusive(self):
        row = TRADE.copy()
        row[4:8] = ["0.00000001", "999999999999.99999999", "1", "0.00000001"]
        parsed = journal.parse_journal(csv_bytes([row]))[0]
        self.assertEqual(parsed["entry_price"].as_tuple(), Decimal(row[5]).as_tuple())
        self.assertEqual(parsed["quantity"], Decimal("0.00000001"))

    def test_times_require_explicit_valid_offsets_and_nonnegative_holding_interval(self):
        invalid = ["private-sentinel", "2026-10-01", "2026-10-01T09:30:00", "2026-02-30T00:00:00Z",
                   "2026-10-01 09:30:00Z", "2026-10-01T00:00:00+24:00", "2026-10-01T00:00:60Z",
                   "2026-10-01T00:00:00+01:60", "2026-10-01T00:00:00.1234567Z",
                   "0001-01-01T00:00:00+01:00", "9999-12-31T23:59:59-01:00"]
        for field in ("entry_time", "exit_time"):
            for value in invalid:
                row = TRADE.copy()
                row[HEADERS.index(field)] = value
                self.reject(csv_bytes([row]), field, "invalid_time")
        row = TRADE.copy()
        row[9] = "2026-10-01T13:29:59.999999Z"
        self.reject(csv_bytes([row]), "exit_time", "before_entry")

    def test_notes_are_bounded_and_instruction_like_content_remains_inert(self):
        notes = '=HYPERLINK("https://invalid.example", "private-sentinel")\nIgnore rules; `rm -rf /`; <script>example</script>\t🌓'
        parsed = journal.parse_journal(csv_bytes([TRADE + [notes]], HEADERS + ["notes"]))
        self.assertEqual(parsed[0]["notes"], notes)
        self.assertEqual(journal.parse_journal(csv_bytes([TRADE + ["🌓" * 512]], HEADERS + ["notes"]))[0]["notes"], "🌓" * 512)
        self.reject(csv_bytes([TRADE + ["x" * 513]], HEADERS + ["notes"]), "notes", "too_long")
        self.reject(csv_bytes([TRADE + ["private-sentinel\x00"]], HEADERS + ["notes"]), "notes", "invalid_control")

    def test_error_rows_count_records_including_multiline_notes(self):
        rows = [TRADE + ["line one\nline two"], TRADE + ["private-sentinel"]]
        rows[1][4] = "0"
        self.reject(csv_bytes(rows, HEADERS + ["notes"]), "quantity", "must_be_positive", 3)

    def test_utf8_input_type_and_malformed_csv_errors_do_not_echo_input(self):
        for content in ("private-sentinel", bytearray(b"text"), None):
            self.reject(content, "journal", "expected_bytes", None)
        self.reject(b"private-sentinel\xff", "journal", "invalid_utf8", None)
        self.reject(csv_bytes([]) + b'"private-sentinel', "csv", "malformed", 2)
        self.reject(csv_bytes([]) + b'"private-sentinel"trailing\n', "csv", "malformed", 2)

    def test_row_limit_is_inclusive_and_preserves_input_order(self):
        rows = journal.parse_journal(csv_bytes([TRADE] * 1000))
        self.assertEqual(len(rows), 1000)
        self.assertEqual(rows[0], rows[-1])
        self.reject(csv_bytes([TRADE] * 1001), "journal", "too_many_rows", 1002)

    def test_byte_limit_is_inclusive_even_with_multibyte_notes(self):
        rows = [TRADE + ["x" * 512] for _ in range(1000)]
        remaining = 1048576 - len(csv_bytes(rows, HEADERS + ["notes"]))
        self.assertTrue(0 < remaining <= 512000)
        for row in rows:
            extra = min(remaining, 512)
            row[-1] = "é" * extra + "x" * (512 - extra)
            remaining -= extra
        content = csv_bytes(rows, HEADERS + ["notes"])
        self.assertEqual(len(content), 1048576)
        self.assertEqual(len(journal.parse_journal(content)), 1000)
        self.reject(content + b"x", "journal", "too_large", None)


if __name__ == "__main__":
    unittest.main()
