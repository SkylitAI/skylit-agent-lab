"""Run records are inert, bounded, explicitly qualified synthetic evidence."""

import json
import unittest

from scripts import run_records as records


class DecodeTests(unittest.TestCase):
    def test_byte_limit_is_inclusive_and_content_is_inert(self):
        content = b'{"command":"do not execute"}'
        self.assertEqual(records.decode_record(content), {"command": "do not execute"})
        self.assertEqual(records.decode_record(b"{}" + b" " * (262144 - 2)), {})
        with self.assertRaises(records.RecordError):
            records.decode_record(b"{}" + b" " * (262144 - 1))

    def test_malformed_duplicate_nonfinite_and_deep_json_are_rejected_safely(self):
        for content in (b"not JSON", b"[]", b"\xff", b'{"x":1,"x":2}',
                        b'{"x":{"a":1,"a":2}}', b'{"x":NaN}', b'{"x":Infinity}',
                        b'{"x":1e999}', b'{"x":' + b"[" * 2000 + b"]" * 2000 + b"}"):
            with self.subTest(content=content[:20]):
                with self.assertRaises(records.RecordError) as error:
                    records.decode_record(content)
                self.assertNotIn(content[:20].decode("utf-8", errors="replace"), str(error.exception))


if __name__ == "__main__":
    unittest.main()
