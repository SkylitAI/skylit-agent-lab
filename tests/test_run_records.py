"""Run records are inert, bounded, explicitly qualified synthetic evidence."""

import json
import unittest

from scripts import run_records as records


def sample_record():
    """Invented identifiers/hashes/times; no observed execution is claimed."""
    reference = "2026-10-01T14:01:00+00:00"
    return {
        "schema_version": 1, "experiment_id": "watchlist-investigator", "mode": "offline_synthetic",
        "lab": {"revision": "a" * 40, "state": "dirty"},
        "kit": {"required_revision": "b" * 40, "observed_revision": "b" * 40, "verification": "verified"},
        "inputs": [{"role": "synthetic_fixture", "sha256": "c" * 64, "hash_state": "complete"}],
        "execution": {"started_at": "2026-10-01T15:00:01Z", "finished_at": "2026-10-01T15:00:00Z"},
        "parameters": {"symbols": ["TEST"], "reference_time": reference, "max_age_seconds": 900},
        "source_time": {
            "reference_time": reference, "max_age_seconds": 900, "symbols": ["TEST"],
            "rows": {"TEST": {field: {"timestamp": None, "age_seconds": None, "status": "unavailable",
                                      "reason": "timestamp missing or invalid; missing from synthetic fixture"}
                              for field in ("gamma.as_of", "vanna.as_of", "flow.generated_at", "flow.latest_trade")}},
            "spans": {"TEST": {"seconds": None, "valid_fields": 0}},
        },
        "usage": {"scope": "python_process", "basis": "known_offline_path", "requests_attempted": 0,
                  "credits_reserved": 0, "observed_billing": None,
                  "model": {"mode": "none", "provider": None, "tokens": None}},
        "outputs": [{"role": "report", "filename": "fictional-report.md", "sha256": "d" * 64, "state": "complete"}],
        "outcome": {"status": "completed", "reason": "completed"},
        "limits": {"fixture_bytes": 65536, "symbols": 100, "requests": 0, "credits": 0,
                   "model_calls": 0, "output_no_overwrite": True},
    }


class ContractTests(unittest.TestCase):
    def test_completed_record_allows_dirty_lab_gaps_and_backward_wall_clock(self):
        record = sample_record()
        self.assertEqual(records.parse_record(json.dumps(record).encode()), record)
        record["lab"] = {"revision": None, "state": "unknown"}
        self.assertEqual(records.validate_record(record), record)

    def test_stopped_record_preserves_unknowns_before_validation(self):
        record = sample_record()
        record.update(parameters=None, source_time=None, outcome={"status": "stopped", "reason": "invalid_parameters"})
        record["kit"].update(observed_revision=None, verification="not_checked")
        record["inputs"][0].update(sha256=None, hash_state="not_read")
        record["outputs"][0].update(filename=None, sha256=None, state="not_written")
        record["usage"].update(basis="unknown", requests_attempted=None, credits_reserved=None)
        record["execution"]["finished_at"] = None
        self.assertEqual(records.validate_record(record), record)

    def test_known_time_states_and_partial_output_remain_explicit(self):
        record = sample_record()
        fields = record["source_time"]["rows"]["TEST"]
        for field, status, age in zip(fields, ("within threshold", "stale", "future"), (60, 901, -1)):
            fields[field] = {"timestamp": "2026-10-01T14:00:00Z", "age_seconds": age, "status": status, "reason": None}
        record["source_time"]["spans"]["TEST"] = {"seconds": 902, "valid_fields": 3}
        self.assertEqual(records.validate_record(record), record)  # Shape validation does not recalculate ages.
        for bad_age in (True, float("nan"), float("inf")):
            fields["gamma.as_of"]["age_seconds"] = bad_age
            with self.assertRaises(records.RecordError):
                records.validate_record(record)
        fields["gamma.as_of"]["age_seconds"] = 60
        record["outcome"] = {"status": "stopped", "reason": "output_write_failed"}
        record["outputs"][0].update(state="partial", sha256=None)
        self.assertEqual(records.validate_record(record), record)
        record["outputs"][0]["sha256"] = "d" * 64
        with self.assertRaises(records.RecordError):
            records.validate_record(record)

    def test_invalid_types_hashes_times_states_and_completed_claims_are_rejected(self):
        cases = [
            (("schema_version",), True), (("schema_version",), 1.0), (("experiment_id",), "future-journal"),
            (("lab", "revision"), "A" * 40), (("lab", "revision"), None),
            (("kit", "observed_revision"), "c" * 40), (("kit", "verification"), "unknown"),
            (("inputs", 0, "sha256"), None), (("inputs", 0, "hash_state"), "unknown"),
            (("execution", "started_at"), "2026-10-01T14:00:00"),
            (("execution", "finished_at"), "2026-10-01T14:00:00+01:00"), (("execution", "finished_at"), None),
            (("parameters",), None), (("parameters", "max_age_seconds"), True),
            (("parameters", "symbols"), ["spy"]), (("parameters", "symbols"), ["TEST", "TEST"]),
            (("source_time",), None), (("source_time", "max_age_seconds"), 1),
            (("source_time", "rows", "TEST", "gamma.as_of", "reason"), "private exception text"),
            (("source_time", "rows", "TEST", "gamma.as_of", "status"), "fresh"),
            (("source_time", "spans", "TEST", "valid_fields"), False),
            (("usage", "requests_attempted"), False), (("usage", "credits_reserved"), 1),
            (("usage", "observed_billing"), 0), (("usage", "model", "tokens"), 0),
            (("outputs", 0, "sha256"), "x" * 64), (("outputs", 0, "state"), "partial"),
            (("outputs", 0, "filename"), "../report.md"), (("outputs", 0, "filename"), "C:report.md"),
            (("outputs", 0, "filename"), "/report.md"), (("outputs", 0, "filename"), "report\n.md"),
            (("outcome", "status"), "stopped"), (("outcome", "reason"), "private exception text"),
            (("limits", "output_no_overwrite"), 1), (("limits", "requests"), False),
        ]
        for path, value in cases:
            with self.subTest(path=path, value=value):
                record = sample_record()
                target = record
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                with self.assertRaises(records.RecordError):
                    records.validate_record(record)

    def test_unknown_keys_at_every_object_level_are_rejected(self):
        record = sample_record()
        objects = [record, record["lab"], record["kit"], record["inputs"][0], record["execution"],
                   record["parameters"], record["source_time"], record["source_time"]["rows"],
                   record["source_time"]["rows"]["TEST"], record["source_time"]["rows"]["TEST"]["gamma.as_of"],
                   record["source_time"]["spans"], record["source_time"]["spans"]["TEST"], record["usage"],
                   record["usage"]["model"], record["outputs"][0], record["outcome"], record["limits"]]
        for target in objects:
            target["unexpected"] = "do not disclose"
            with self.assertRaises(records.RecordError) as error:
                records.validate_record(record)
            self.assertNotIn("do not disclose", str(error.exception))
            del target["unexpected"]


class DecodeTests(unittest.TestCase):
    def test_byte_limit_is_inclusive_and_content_is_inert(self):
        content = b'{"command":"do not execute"}'
        self.assertEqual(records.decode_record(content), {"command": "do not execute"})
        self.assertEqual(records.decode_record(b"{}" + b" " * (262144 - 2)), {})
        with self.assertRaises(records.RecordError):
            records.decode_record(b"{}" + b" " * (262144 - 1))
        self.assertIsInstance(records.decode_record(b'{"x":' + b"[" * 31 + b"]" * 31 + b"}"), dict)
        with self.assertRaises(records.RecordError):
            records.decode_record(b'{"x":' + b"[" * 32 + b"]" * 32 + b"}")

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
