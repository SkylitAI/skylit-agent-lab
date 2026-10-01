"""Manifest contract tests; all fixtures are temporary and command strings stay inert."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_experiments.py"
SPEC = importlib.util.spec_from_file_location("validate_experiments", SCRIPT)
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def manifest(identifier="example-experiment"):
    return {
        "schema_version": 1,
        "id": identifier,
        "purpose": "Demonstrate a synthetic local fixture.",
        "owner": "@prodij",
        "status": "experimental",
        "command": ["python3", "run.py"],
        "inputs": ["fixture.json"],
        "outputs": ["reports/example.md"],
        "access": "Local files only; no credentials.",
        "cost": "No paid services.",
        "tested_hosts": [],
        "sources": [{"kind": "synthetic", "reference": "fixture.json", "license": "CC0-1.0"}],
        "kit": None,
    }


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.template = self.root / "templates" / "experiment"
        self.template.mkdir(parents=True)
        (self.template / "fixture.json").write_text("{}", encoding="utf-8")
        self.path = self.template / "experiment.json"
        self.data = manifest()
        self.save()

    def save(self, data=None, path=None):
        (path or self.path).write_text(json.dumps(self.data if data is None else data), encoding="utf-8")

    def run_validator(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            code = VALIDATOR.main(["--root", str(self.root)])
        self.assertNotIn("Traceback", output.getvalue())
        return code, output.getvalue()

    def assert_invalid(self, expected):
        code, output = self.run_validator()
        self.assertEqual(code, 1, output)
        self.assertIn(expected, output)
        return output

    def add_experiment(self, name="simple-example"):
        directory = self.root / "experiments" / name
        directory.mkdir(parents=True)
        (directory / "fixture.json").write_text("{}", encoding="utf-8")
        self.save(manifest(name), directory / "experiment.json")
        return directory

    def test_template_only_and_multiple_experiments(self):
        code, output = self.run_validator()
        self.assertEqual(code, 0, output)
        self.assertIn("0 experiment", output)
        self.add_experiment()
        self.add_experiment("another-example")
        code, output = self.run_validator()
        self.assertEqual(code, 0, output)
        self.assertIn("2 experiment", output)
        self.assertIn("1 template", output)

    def test_default_root_is_script_project_not_working_directory(self):
        original = VALIDATOR.__file__
        VALIDATOR.__file__ = str(self.root / "scripts" / "validate_experiments.py")
        self.addCleanup(setattr, VALIDATOR, "__file__", original)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(VALIDATOR.main([]), 0)

    def test_valid_statuses_and_pinned_kit(self):
        self.data["kit"] = {"repository": "https://github.com/SkylitAI/skylit-agent-kit", "revision": "a" * 40}
        for status in ["experimental", "reproduced", "maintained", "graduated", "archived"]:
            with self.subTest(status=status):
                self.data["status"] = status
                self.save()
                code, output = self.run_validator()
                self.assertEqual(code, 0, output)

    def test_commands_are_arbitrary_inert_metadata(self):
        marker = self.root / "never-created"
        self.data["command"] = ["python3", "-c", f"open({str(marker)!r}, 'w').write('executed')", "$(touch ignored);\n&"]
        self.save()
        self.assertEqual(self.run_validator()[0], 0)
        self.assertFalse(marker.exists())

    def test_required_and_unknown_fields_report_together(self):
        del self.data["purpose"]
        self.data["unexpected"] = "no"
        self.save()
        output = self.assert_invalid("purpose")
        self.assertIn("unexpected", output)
        self.assertIn("experiment.json", output)

    def test_root_must_be_object(self):
        self.save([])
        self.assert_invalid("object")

    def test_scalar_and_collection_types(self):
        cases = {
            "schema_version": [True, 1.0, "1", 2, None],
            "id": ["Example", "-bad", "bad-", "two--parts", "two_parts", "", 5],
            "purpose": ["", " \n", 4],
            "owner": ["", "prodij", "@-bad", "@bad--name", "@bad-", "@" + "a" * 40, 5],
            "status": ["stable", "", [], 1],
            "command": [[], "python3 run.py", [""], [None], ["  "]],
            "inputs": [None, "fixture.json", [5]],
            "outputs": [[], "report.md", [False]],
            "access": [None, "  "],
            "cost": [False, ""],
            "tested_hosts": [None, {}],
            "sources": [[], None, {}],
            "kit": [False, []],
        }
        for field, values in cases.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    changed = manifest()
                    changed[field] = value
                    self.save(changed)
                    self.assert_invalid(field)

    def test_template_and_actual_ids_and_duplicates(self):
        self.data["id"] = "different-example"
        self.save()
        self.assert_invalid("id")
        self.save(manifest())
        first = self.add_experiment("first-example")
        second = self.add_experiment("second-example")
        self.save(manifest("first-example"), second / "experiment.json")
        output = self.assert_invalid("duplicate id")
        self.assertIn("second-example", output)
        self.assertTrue(first.is_dir())

    def test_template_id_does_not_participate_in_actual_duplicates(self):
        self.add_experiment("example-experiment")
        code, output = self.run_validator()
        self.assertEqual(code, 0, output)

    def test_path_syntax_rejected_in_every_path_field(self):
        bad_paths = ["", " ", "/tmp/input", "../input", "part/../input", ".", "./input", "part/./input", "C:input", "C:/input", "part\\input", "\\\\server\\input", "part\ninput", "part\x00input", "part\x7finput", "part//input", "input/"]
        for field in ["inputs", "outputs", "tested_hosts"]:
            for value in bad_paths:
                with self.subTest(field=field, value=value):
                    changed = manifest()
                    changed[field] = ([{"name": "Example Host", "version": "1", "evidence": value}] if field == "tested_hosts" else [value])
                    self.save(changed)
                    self.assert_invalid(field)

    def test_file_existence_and_overlapping_paths(self):
        cases = [
            ({"inputs": ["missing.json"]}, "inputs"),
            ({"inputs": ["fixture.json", "fixture.json"]}, "duplicate"),
            ({"outputs": ["report.md", "report.md"]}, "duplicate"),
            ({"outputs": ["fixture.json"]}, "inputs"),
            ({"inputs": ["folder"]}, "regular file"),
            ({"outputs": ["folder"]}, "regular file"),
            ({"outputs": ["fixture.json/child.md"]}, "directory"),
        ]
        (self.template / "folder").mkdir()
        for changes, expected in cases:
            with self.subTest(changes=changes):
                changed = manifest()
                changed.update(changes)
                self.save(changed)
                self.assert_invalid(expected)
        self.save({**manifest(), "inputs": []})
        self.assertEqual(self.run_validator()[0], 0)

    def test_nested_drive_and_stream_paths_rejected_before_filesystem_checks(self):
        for field in ["inputs", "outputs", "tested_hosts"]:
            for value in ["sub/D:outside.md", "sub/C:/outside.md", "report.md:stream"]:
                with self.subTest(field=field, value=value):
                    changed = manifest()
                    changed[field] = ([{"name": "Example Host", "version": "1", "evidence": value}] if field == "tested_hosts" else [value])
                    self.save(changed)
                    output = self.assert_invalid(field)
                    self.assertIn("colon", output)

    def test_symlinked_paths_including_internal_and_broken_links(self):
        (self.template / "local-link").symlink_to(self.template / "fixture.json")
        (self.template / "broken-link").symlink_to(self.root / "absent")
        (self.template / "outside").symlink_to(self.root, target_is_directory=True)
        for field in ["inputs", "outputs"]:
            for value in ["local-link", "broken-link", "outside/new.md"]:
                with self.subTest(field=field, value=value):
                    changed = manifest()
                    changed[field] = [value]
                    self.save(changed)
                    self.assert_invalid("symlink")
        self.data["tested_hosts"] = [{"name": "Host", "version": "1", "evidence": "local-link"}]
        self.save()
        self.assert_invalid("symlink")

    def test_tested_hosts_exact_fields_and_existing_evidence(self):
        valid = {"name": "Example Host", "version": "1.0", "evidence": "fixture.json"}
        self.data["tested_hosts"] = [valid]
        self.save()
        self.assertEqual(self.run_validator()[0], 0)
        for host in [None, {}, {**valid, "extra": 1}, {**valid, "name": " "}, {**valid, "version": 1}, {**valid, "evidence": "missing.txt"}]:
            with self.subTest(host=host):
                self.data["tested_hosts"] = [host]
                self.save()
                self.assert_invalid("tested_hosts[0]")

    def test_sources_exact_fields_and_values(self):
        valid = self.data["sources"][0]
        for kind in ["synthetic", "public", "academy"]:
            self.data["sources"] = [{**valid, "kind": kind}]
            self.save()
            self.assertEqual(self.run_validator()[0], 0)
        for source in [None, {}, {**valid, "extra": 1}, {**valid, "kind": "private"}, {**valid, "kind": []}, {**valid, "reference": " "}, {**valid, "license": 5}]:
            with self.subTest(source=source):
                self.data["sources"] = [source]
                self.save()
                self.assert_invalid("sources[0]")

    def test_kit_requires_exact_repository_and_full_lowercase_commit(self):
        valid = {"repository": "https://github.com/SkylitAI/skylit-agent-kit", "revision": "f" * 40}
        for kit in [{}, {**valid, "extra": 1}, {**valid, "repository": "https://example.com/kit"}, {**valid, "revision": "main"}, {**valid, "revision": "F" * 40}, {**valid, "revision": 5}]:
            with self.subTest(kit=kit):
                self.data["kit"] = kit
                self.save()
                self.assert_invalid("kit")

    def test_unparseable_duplicate_nonfinite_and_oversized_json(self):
        original = json.dumps(manifest())
        bad_documents = [
            (b"{", "JSON"),
            (b"\xff", "UTF-8"),
            ((original[:-1] + ', "id": "again"}').encode(), "duplicate key"),
            (original.replace('"CC0-1.0"', '"CC0-1.0", "license": "MIT"').encode(), "duplicate key"),
            (original.replace('"No paid services."', "NaN").encode(), "finite"),
            (original.replace('"No paid services."', "Infinity").encode(), "finite"),
            (original.replace('"No paid services."', "1e999").encode(), "finite"),
            (b"[" * 2000 + b"]" * 2000, "$"),
            (b" " * (65536 + 1), "65536"),
        ]
        for raw, expected in bad_documents:
            with self.subTest(expected=expected):
                self.path.write_bytes(raw)
                self.assert_invalid(expected)

    def test_size_limit_inclusive_and_diagnostics_are_printable(self):
        raw = json.dumps(manifest()).encode()
        self.path.write_bytes(raw + b" " * (65536 - len(raw)))
        self.assertEqual(self.run_validator()[0], 0)
        self.save({**manifest(), "\ud800": "invalid field"})
        output = self.assert_invalid("unknown field")
        output.encode("utf-8")

    def test_missing_template_missing_actual_manifest_and_all_errors(self):
        self.path.unlink()
        missing = self.root / "experiments" / "missing-manifest"
        missing.mkdir(parents=True)
        self.add_experiment("invalid-example")
        self.save({**manifest("invalid-example"), "purpose": ""}, self.root / "experiments" / "invalid-example" / "experiment.json")
        output = self.assert_invalid("templates")
        self.assertIn("missing-manifest", output)
        self.assertIn("purpose", output)

    def test_scanning_is_direct_and_ignores_files(self):
        directory = self.add_experiment()
        (directory / "nested-no-manifest").mkdir()
        (directory.parent / "README.md").write_text("Documentation", encoding="utf-8")
        code, output = self.run_validator()
        self.assertEqual(code, 0, output)
        self.assertIn("1 experiment", output)

    def test_symlinked_experiment_directory_and_manifest(self):
        directory = self.add_experiment()
        (directory.parent / "linked-example").symlink_to(directory, target_is_directory=True)
        self.assert_invalid("symlink")
        (directory.parent / "linked-example").unlink()
        (directory / "experiment.json").unlink()
        (directory / "experiment.json").symlink_to(self.path)
        self.assert_invalid("symlink")

    def test_symlinked_template_directory(self):
        saved = self.root / "saved-template"
        self.template.rename(saved)
        self.template.symlink_to(saved, target_is_directory=True)
        self.assert_invalid("symlink")

    def test_symlinked_experiments_container(self):
        outside = self.root / "elsewhere"
        outside.mkdir()
        (self.root / "experiments").symlink_to(outside, target_is_directory=True)
        self.assert_invalid("symlink")

    def test_manifests_must_be_regular_files(self):
        self.path.unlink()
        self.path.mkdir()
        self.assert_invalid("regular file")


if __name__ == "__main__":
    unittest.main()
