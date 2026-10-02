"""Synthetic boundary observations exercise fixed dispatch and real comparisons."""

import contextlib
import copy
import errno
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import evaluate
from evaluations import isolation_probe as probe
from scripts import run_isolated as wrapper
from test_run_records import sample_record, seed_record


ROOT = Path(__file__).resolve().parents[1]
LAB = {"revision": "a" * 40, "state": "clean"}
PIN = "0f82039759ef4db9d5b3dbd90f52863f8074f2a6"
KIT = {"required_revision": PIN, "observed_revision": PIN, "verification": "verified"}
DEPENDENCY = {"tests_run": 1, "failures": 0, "errors": 0, "skips": 0, "success": True}


class PreparationBase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / "lab"
        for name in ("evaluations/cases.json", "evaluations/watchlist-expected.md", "evaluations/variant-expected.md",
                     "examples/paper-journal-expected.md", "experiments/market-brief/README.md",
                     "experiments/watchlist-investigator/fixture.json", "experiments/journal-reviewer/fixture.csv",
                     "experiments/market-brief/fixture.xml"):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        self.kit = self.root.parent / "kit"

    def observation(self, path):
        return LAB if Path(path) == self.root else {"revision": PIN, "state": "clean"}

    def suite(self, **kwargs):
        with patch.object(evaluate, "inspect_checkout", side_effect=self.observation):
            return evaluate.run_suite(root=self.root, kit_root=self.kit, **kwargs)


class PreparationTests(PreparationBase):
    def test_all_inputs_and_nine_whole_goldens_are_prepared_without_children(self):
        with patch.object(evaluate, "run_child", side_effect=AssertionError("No setup children")):
            cases, inputs, goldens = evaluate.prepare_suite(self.root)
        self.assertEqual(len(cases), 12)
        self.assertEqual(len(inputs), 11)
        self.assertEqual(len(goldens), 9)
        changed = json.loads(inputs["watchlist-changed-evidence"])
        self.assertEqual(changed["gamma"]["data"]["symbols"][0]["strikes"][0]["value"], -199)
        self.assertNotIn("timestamp", changed["flow"]["SPY"]["data"]["trades"][0])
        self.assertEqual(inputs["watchlist-changed-evidence"],
                         (json.dumps(changed, sort_keys=True, separators=(",", ":")) + "\n").encode())
        self.assertEqual(inputs["journal-header-only"], inputs["journal-bundled"].splitlines(keepends=True)[0])
        self.assertEqual(inputs["invalid-json"], b"not JSON\n")
        self.assertEqual(inputs["invalid-xml"], b"not xml: private-marker\n")
        self.assertTrue(all(raw.endswith(b"\n") for raw in goldens.values()))
        self.assertNotIn(b"<!-- expected", goldens["market-default"])

    def assert_setup_stops(self):
        with patch.object(evaluate, "run_child") as child:
            summary = self.suite()
        child.assert_not_called()
        self.assertEqual(summary["status"], "setup_failed")
        self.assertEqual(len(summary["cases"]), 12)
        self.assertTrue(all(row["status"] == "not_run" for row in summary["cases"]))
        self.assertNotIn(str(self.root), json.dumps(summary))
        return summary

    def test_unknown_case_and_invalid_metadata_prevent_every_child(self):
        target = self.root / "evaluations/cases.json"
        original = target.read_bytes()
        for mutate in (lambda value: value["cases"][0].update(id="private-unknown-command"),
                       lambda value: value["cases"][0].update(command=["sh", "private-marker"]),
                       lambda value: value["cases"][0]["expected"].update(exit_code=True)):
            value = json.loads(original)
            mutate(value)
            target.write_text(json.dumps(value))
            summary = self.assert_setup_stops()
            self.assertNotIn("private-marker", json.dumps(summary))

    def test_fixture_hash_and_missing_last_golden_stop_before_partial_execution(self):
        fixture = self.root / "experiments/market-brief/fixture.xml"
        original = fixture.read_bytes()
        fixture.write_bytes(original + b" ")
        self.assert_setup_stops()
        fixture.write_bytes(original)
        target = self.root / "evaluations/variant-expected.md"
        target.write_bytes(target.read_bytes().replace(b"<!-- expected-end: market-invalid -->", b""))
        self.assert_setup_stops()

    def test_unique_markers_substitutions_and_bounded_sources_are_required(self):
        for raw in (b"absent", b"marker marker"):
            with self.assertRaises(evaluate.SetupError):
                evaluate.replace_once(raw, b"marker", b"changed")
        target = self.root / "experiments/market-brief/README.md"
        original = target.read_bytes()
        for raw in (original + original, b"x" * (1048576 + 1), b"\xff"):
            target.write_bytes(raw)
            self.assert_setup_stops()
        target.unlink()
        target.symlink_to(ROOT / "experiments/market-brief/README.md")
        self.assert_setup_stops()

    def test_dirty_or_unknown_lab_is_a_structured_setup_failure(self):
        for observation in ({"revision": "a" * 40, "state": "dirty"}, {"revision": None, "state": "unknown"}):
            with patch.object(evaluate, "inspect_checkout", return_value=observation), patch.object(evaluate, "run_child") as child:
                summary = evaluate.run_suite(root=self.root, kit_root=self.kit)
            child.assert_not_called()
            self.assertEqual(summary["status"], "setup_failed")
            self.assertEqual(summary["lab"], observation)


class ExecutionTests(PreparationBase):
    def setUp(self):
        super().setUp()
        self.prepared = evaluate.prepare_suite(self.root)
        self.calls = []
        self.mutate = None
        self.dependency = dict(DEPENDENCY)
        self.child_result = None

    def child(self, argv, cwd, remaining_seconds):
        folder = Path(cwd)
        name = folder.name
        self.assertEqual(folder, folder.resolve())
        self.assertEqual(folder.stat().st_mode & 0o777, 0o700)
        self.assertGreater(remaining_seconds, 0)
        self.assertLessEqual(remaining_seconds, 90)
        self.calls.append((name, list(argv)))
        if name == "kit-budget-stop":
            return self.child_result or {"exit_code": 0, "stdout": json.dumps(self.dependency).encode(),
                                         "stderr": b"", "stop_reason": "exited"}
        cases, inputs, goldens = self.prepared
        case = cases[name]
        expected = case["expected"]
        watchlist = case["experiment"] == "watchlist-investigator"
        record = sample_record() if watchlist else seed_record(case["experiment"], expected["mode"])
        record.update(lab=copy.deepcopy(LAB), kit=copy.deepcopy(KIT) if watchlist else None,
                      parameters=expected["parameters"], source_time=expected["source_time"], outcome=expected["outcome"])
        report = folder / "report.md"
        raw = goldens.get(expected["golden"])
        if self.mutate and name == "market-changed-limited":
            raw = self.mutate(raw)
        if raw is not None:
            report.write_bytes(raw)
            report.chmod(0o600)
        record["inputs"][0].update(hash_state="complete", sha256=hashlib.sha256(inputs[case["input"]]).hexdigest())
        record["outputs"][0].update(filename="report.md", state=expected["output_state"],
                                   sha256=hashlib.sha256(raw).hexdigest() if raw is not None else None)
        sidecar = Path(str(report) + ".run.json")
        sidecar.write_text(json.dumps(record))
        sidecar.chmod(0o600)
        for flag in ("--input", "--fixture"):
            if flag in argv:
                source = Path(argv[argv.index(flag) + 1])
                self.assertEqual(source.read_bytes(), inputs[case["input"]])
                self.assertEqual(source.stat().st_mode & 0o777, 0o600)
        return self.child_result or {"exit_code": expected["exit_code"], "stdout": b"private-output-path",
                                     "stderr": b"", "stop_reason": "exited"}

    def run_mocked(self):
        with patch.object(evaluate, "run_child", side_effect=self.child):
            return self.suite()

    def test_fixed_dispatch_all_twelve_and_default_routes(self):
        summary = self.run_mocked()
        self.assertEqual(summary["status"], "passed")
        self.assertEqual(len(self.calls), 12)
        self.assertTrue(all(row["status"] == "passed" for row in summary["cases"]))
        for name, command in self.calls:
            self.assertEqual(command[:5], [sys.executable, "-X", "utf8", "-I", "-B"])
            self.assertNotIn("--fetch", command)
            if name.endswith("-default"):
                self.assertNotIn("--input", command)
                self.assertNotIn("--fixture", command)
            if name == "watchlist-changed-evidence":
                self.assertEqual(command[command.index("--symbols") + 1], "SPY,QQQ,SPXW")
            if name == "market-changed-limited":
                self.assertEqual(command[command.index("--limit") + 1], "1")
            if name == "kit-budget-stop":
                self.assertEqual(command[5], "-c")
                self.assertIn("test_budget_blocks_before_paid_calls", command[6])
        serialized = json.dumps(summary)
        for private in (str(self.root), "private-output-path", "Fictional notice"):
            self.assertNotIn(private, serialized)
        self.assertEqual(summary["schema_version"], 1)
        for row in summary["cases"]:
            case = self.prepared[0][row["id"]]
            if case["scope"] == "lab_workflow":
                self.assertEqual(row["prepared_input_sha256"], hashlib.sha256(self.prepared[1][case["input"]]).hexdigest())
                raw = self.prepared[2].get(case["expected"]["golden"])
                self.assertEqual(row["expected_report_sha256"], hashlib.sha256(raw).hexdigest() if raw else None)
        self.assertEqual(summary["kit"], KIT)
        self.assertEqual(summary["lab"], LAB)
        self.assertEqual(summary["python"], sys.version.split()[0])

    def test_case_parameters_do_not_control_argv_or_manifest_commands(self):
        target = self.root / "evaluations/cases.json"
        data = json.loads(target.read_bytes())
        row = next(row for row in data["cases"] if row["id"] == "market-changed-limited")
        row["expected"]["parameters"]["limit"] = 2
        target.write_text(json.dumps(data))
        summary = self.run_mocked()
        command = next(command for name, command in self.calls if name == row["id"])
        self.assertEqual(command[command.index("--limit") + 1], "1")
        result = next(row for row in summary["cases"] if row["id"] == "market-changed-limited")
        self.assertIn("parameters_mismatch", result["reasons"])

    def test_rehashed_tampering_fails_real_comparator(self):
        for mutate in (lambda raw: raw.replace(b"changed fictional wording", b"paper kites"),
                       lambda raw: raw + b"\nInvented extra release.\n"):
            self.mutate = mutate
            summary = self.run_mocked()
            row = next(row for row in summary["cases"] if row["id"] == "market-changed-limited")
            self.assertEqual(row["status"], "failed")
            self.assertIn("golden_mismatch", row["reasons"])
            self.assertNotIn("report_hash_mismatch", row["reasons"])

    def test_missing_dirty_wrong_kit_runs_eight_and_never_imports_kit(self):
        for observed in ({"revision": None, "state": "unknown"}, {"revision": PIN, "state": "dirty"},
                         {"revision": "b" * 40, "state": "clean"}):
            self.calls.clear()
            with patch.object(evaluate, "inspect_checkout", side_effect=lambda path: LAB if Path(path) == self.root else observed), \
                 patch.object(evaluate, "run_child", side_effect=self.child):
                summary = evaluate.run_suite(root=self.root, kit_root=self.kit)
            self.assertEqual(len(self.calls), 8)
            self.assertEqual(sum(row["status"] == "unverified" for row in summary["cases"]), 4)
            self.assertEqual(sum(row["status"] == "passed" for row in summary["cases"]), 8)
            self.assertEqual(summary["status"], "failed")
        self.calls.clear()
        with patch.object(evaluate, "inspect_checkout", return_value=LAB) as inspect, \
             patch.object(evaluate, "run_child", side_effect=self.child):
            summary = evaluate.run_suite(root=self.root, kit_root=None)
        self.assertEqual(inspect.call_count, 1)
        self.assertEqual(len(self.calls), 8)
        self.assertEqual(summary["kit"]["verification"], "not_checked")

    def test_deadline_launches_no_remaining_children_and_never_hides_stop_reason(self):
        self.child_result = {"exit_code": 0, "stdout": b"", "stderr": b"private-error", "stop_reason": "timeout"}
        with patch.object(evaluate.time, "monotonic", side_effect=[0, 1, 91] + [92] * 12):
            summary = self.run_mocked()
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(summary["cases"][0]["reasons"], ["child_timeout"])
        self.assertTrue(all(row["status"] == "not_run" and row["reasons"] == ["suite_timeout"]
                            for row in summary["cases"][1:]))
        self.assertNotIn("private-error", json.dumps(summary))

    def test_dependency_requires_exact_counts_types_json_and_exit(self):
        for change in ({"tests_run": 0}, {"tests_run": True}, {"failures": 1}, {"errors": 1},
                       {"skips": 1}, {"success": 1}, {"success": False}, {"extra": "private-error"}):
            self.dependency = DEPENDENCY | change
            summary = self.run_mocked()
            row = next(row for row in summary["cases"] if row["id"] == "kit-budget-stop")
            self.assertEqual(row["status"], "failed")
        for raw in (b"not JSON", b'{"tests_run":1,"tests_run":1}', b"[]"):
            self.child_result = {"exit_code": 0, "stdout": raw, "stderr": b"", "stop_reason": "exited"}
            summary = self.run_mocked()
            row = next(row for row in summary["cases"] if row["id"] == "kit-budget-stop")
            self.assertEqual(row["status"], "failed")
        self.child_result = {"exit_code": 1, "stdout": json.dumps(DEPENDENCY).encode(), "stderr": b"", "stop_reason": "exited"}
        summary = self.run_mocked()
        self.assertEqual(next(row for row in summary["cases"] if row["id"] == "kit-budget-stop")["status"], "failed")


class EntryPointTests(unittest.TestCase):
    def test_direct_command_refuses_without_children(self):
        output = io.StringIO()
        with patch.object(evaluate, "run_child") as child, contextlib.redirect_stderr(output):
            self.assertNotEqual(evaluate.main(), 0)
        child.assert_not_called()
        self.assertIn("run_isolated.py --evaluate", output.getvalue())

    def test_isolated_direct_script_refuses_before_execution(self):
        child = subprocess.run([sys.executable, "-X", "utf8", "-I", "-B", str(ROOT / "scripts/evaluate.py")],
                               env={"PATH": os.defpath}, capture_output=True, timeout=10)
        self.assertEqual(child.returncode, 2)
        self.assertEqual(child.stdout, b"")
        self.assertIn(b"run_isolated.py --evaluate", child.stderr)
        self.assertNotIn(b"Traceback", child.stderr)

    def test_probe_checks_guards_before_evaluation_and_skips_duplicate_samples(self):
        for status, expected_exit in (("passed", 0), ("failed", 1)):
            summary = {"status": status}
            with patch.object(probe.os, "geteuid", return_value=65534), \
                 patch.object(probe.Path, "read_text", return_value="NoNewPrivs:\t1\nCapEff:\t0000000000000000\n"), \
                 patch.object(probe.socket, "socket") as socket, \
                 patch("builtins.open", side_effect=OSError(errno.EROFS, "synthetic")), \
                 patch.object(probe, "inspect_checkout", return_value=LAB), \
                 patch.dict(os.environ, {"PATH": os.defpath}, clear=True), \
                 patch.object(probe.subprocess, "run", side_effect=AssertionError("Duplicate sample")), \
                 patch.object(evaluate, "run_suite", return_value=summary) as suite, \
                 contextlib.redirect_stdout(io.StringIO()) as output:
                socket.return_value.__enter__.return_value.connect_ex.return_value = errno.ENETUNREACH
                self.assertEqual(probe.main(["--evaluate", "--without-kit"]), expected_exit)
            suite.assert_called_once_with(kit_root=None)
            self.assertEqual(json.loads(output.getvalue()), {"isolation": "passed", "evaluation": summary})
        with patch.object(probe.os, "geteuid", return_value=0), patch.object(evaluate, "run_suite") as suite:
            with self.assertRaises(ValueError):
                probe.main(["--evaluate"])
        suite.assert_not_called()

    def test_wrapper_cli_passes_evaluate_flag(self):
        with patch.object(sys, "argv", ["run_isolated.py", "--evaluate", "--without-kit"]), \
             patch.object(wrapper, "stage_checkout", return_value="a" * 40), \
             patch.object(wrapper, "docker_client", return_value="synthetic-client"), \
             patch.object(wrapper, "run_probe", return_value=0) as run, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(wrapper.main(), 0)
        self.assertEqual(run.call_args.args[1:], ("synthetic-client", True))
        self.assertEqual(run.call_args.kwargs, {"evaluate": True})

    def test_dependency_discards_output_to_a_sink_and_emits_only_actual_counts(self):
        # This authored stand-in tests the child script, not Kit or the full gate.
        with tempfile.TemporaryDirectory() as directory:
            tests = Path(directory) / "tests"
            tests.mkdir()
            (tests / "test_watchlist.py").write_text("""import os, stat, sys, unittest
class WatchlistTests(unittest.TestCase):
    def test_budget_blocks_before_paid_calls(self):
        for target in (sys.stdout, sys.stderr):
            self.assertTrue(stat.S_ISCHR(os.fstat(target.fileno()).st_mode))
            for _ in range(4):
                target.write('discarded synthetic output' * 65536)
""")
            child = subprocess.run([sys.executable, "-X", "utf8", "-I", "-B", "-c", evaluate.DEPENDENCY_SCRIPT, directory],
                                   env={"PATH": os.defpath}, capture_output=True, timeout=10)
        self.assertEqual(child.returncode, 0)
        self.assertEqual(child.stderr, b"")
        self.assertEqual(json.loads(child.stdout), DEPENDENCY)
        self.assertNotIn(b"discarded synthetic output", child.stdout)

    def test_normal_incomplete_evaluation_preserves_exit_without_infrastructure_diagnostic(self):
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory)
            calls = []
            def client(*args, **kwargs):
                calls.append(args)
                if args[0] == "build":
                    (stage / "image-id").write_text("sha256:" + "a" * 64)
                if args[0] == "run":
                    self.assertFalse(kwargs["check"])
                    return subprocess.CompletedProcess(args, 1)
                return subprocess.CompletedProcess(args, 0)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(wrapper.run_probe(stage, client, True, evaluate=True), 1)
            self.assertEqual(calls[-2][0], "rm")
            self.assertEqual(calls[-1][:2], ("image", "rm"))
        with patch.object(sys, "argv", ["run_isolated.py", "--evaluate", "--without-kit"]), \
             patch.object(wrapper, "stage_checkout", return_value="a" * 40), \
             patch.object(wrapper, "docker_client", return_value="synthetic-client"), \
             patch.object(wrapper, "run_probe", return_value=1), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(wrapper.main(), 1)
        self.assertNotIn("Isolation check failed", output.getvalue())
        self.assertNotIn("Docker availability", output.getvalue())

    def test_docker_start_failure_remains_distinct_and_cleans_up(self):
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory)
            calls = []
            def client(*args, **kwargs):
                calls.append(args)
                if args[0] == "build":
                    (stage / "image-id").write_text("sha256:" + "a" * 64)
                return subprocess.CompletedProcess(args, 125 if args[0] == "run" else 0)
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(subprocess.CalledProcessError):
                wrapper.run_probe(stage, client, True, evaluate=True)
            self.assertEqual(calls[-2][0], "rm")
            self.assertEqual(calls[-1][:2], ("image", "rm"))

    def test_wrapper_preserves_smoke_default_and_adds_evaluation_and_init(self):
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory)
            calls = []
            def client(*args, **kwargs):
                calls.append(args)
                if args[0] == "build":
                    (stage / "image-id").write_text("sha256:" + "a" * 64)
                return subprocess.CompletedProcess(args, 0)
            with contextlib.redirect_stdout(io.StringIO()):
                wrapper.run_probe(stage, client, True)
                wrapper.run_probe(stage, client, True, evaluate=True)
            runs = [command for command in calls if command[0] == "run"]
            self.assertNotIn("--evaluate", runs[0])
            self.assertEqual(runs[1][-2:], ("--without-kit", "--evaluate"))
            self.assertTrue(all("--init" in command for command in runs))


if __name__ == "__main__":
    unittest.main()
