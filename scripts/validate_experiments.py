"""Validate the v1 manifest contract using only the standard library; never execute it."""

import argparse
import json
import math
from pathlib import Path
import re


MAX_BYTES = 65536
FIELDS = {
    "schema_version", "id", "purpose", "owner", "status", "command", "inputs",
    "outputs", "access", "cost", "tested_hosts", "sources", "kit",
}
STATUSES = {"experimental", "reproduced", "maintained", "graduated", "archived"}
KIT_REPOSITORY = "https://github.com/SkylitAI/skylit-agent-kit"
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
HANDLE = re.compile(r"@[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key {key!r}")
        result[key] = value
    return result


def finite_number(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("JSON numbers must be finite")
    return result


def validate_manifest(path, expected_id, problems):
    def error(field, message):
        problems.append(f"{path}: {field}: {message}")

    def exact_object(value, keys, field):
        if not isinstance(value, dict):
            error(field, "expected an object")
            return False
        for key in sorted(keys - value.keys()):
            error(f"{field}.{key}", "required field is missing")
        for key in sorted(value.keys() - keys):
            error(f"{field}[{key!r}]", "unknown field")
        return True

    def nonblank(value, field):
        if not isinstance(value, str) or not value.strip():
            error(field, "expected a nonblank string")
            return False
        return True

    def array(value, field, nonempty=False):
        if not isinstance(value, list) or (nonempty and not value):
            error(field, "expected a nonempty list" if nonempty else "expected a list")
            return []
        return value

    def local_file(value, field, required=True):
        if not nonblank(value, field):
            return None
        parts = value.split("/")
        if ("\\" in value or ":" in value
                or any(part in {"", ".", ".."} for part in parts)
                or re.search(r"[\x00-\x1f\x7f-\x9f]", value)):
            error(field, "use an experiment-relative path without absolute paths, colons, backslashes, empty/dot components or control characters")
            return None
        current = path.parent
        try:
            value.encode("utf-8")
            for index, part in enumerate(parts):
                current = current / part
                if current.is_symlink():
                    error(field, f"symlink paths are forbidden: {value!r}")
                    return None
                if index < len(parts) - 1 and current.exists() and not current.is_dir():
                    error(field, f"parent component is not a directory: {value!r}")
                    return None
            if (required or current.exists()) and not current.is_file():
                error(field, f"expected an existing regular file: {value!r}")
        except (OSError, UnicodeError) as exc:
            error(field, f"cannot inspect path: {exc}")
        return value

    try:
        if path.is_symlink():
            error("$", "symlink manifests are forbidden")
            return None
        if not path.is_file():
            error("$", "missing manifest or not a regular file")
            return None
        with path.open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            error("$", f"manifest exceeds {MAX_BYTES} bytes")
            return None
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object,
                          parse_constant=finite_number, parse_float=finite_number)
    except UnicodeError as exc:
        error("$", f"manifest must be UTF-8: {exc}")
        return None
    except (OSError, ValueError, RecursionError) as exc:
        error("$", f"cannot read valid JSON: {exc}")
        return None
    if not exact_object(data, FIELDS, "$"):
        return None
    if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        error("schema_version", "expected integer 1 (not a boolean)")
    identifier = data.get("id")
    if not isinstance(identifier, str) or not SLUG.fullmatch(identifier):
        error("id", "expected a lowercase slug, such as example-experiment")
    if identifier != expected_id:
        error("id", f"must equal {expected_id!r}")
    for field in ("purpose", "access", "cost"):
        nonblank(data.get(field), field)
    owner = data.get("owner")
    if (not isinstance(owner, str) or not HANDLE.fullmatch(owner)
            or not 1 <= len(owner) - 1 <= 39):
        error("owner", "expected an @-prefixed GitHub handle of 1–39 characters")
    status = data.get("status")
    if not isinstance(status, str) or status not in STATUSES:
        error("status", f"expected one of {', '.join(sorted(STATUSES))}")
    for index, argument in enumerate(array(data.get("command"), "command", True)):
        nonblank(argument, f"command[{index}]")
    paths = {}
    for field in ("inputs", "outputs"):
        paths[field] = set()
        for index, value in enumerate(array(data.get(field), field, field == "outputs")):
            checked = local_file(value, f"{field}[{index}]", field == "inputs")
            if checked is not None:
                if checked in paths[field]:
                    error(f"{field}[{index}]", f"duplicate path {checked!r}")
                paths[field].add(checked)
    for overlap in sorted(paths["inputs"] & paths["outputs"]):
        error("outputs", f"path also appears in inputs: {overlap!r}")
    for index, host in enumerate(array(data.get("tested_hosts"), "tested_hosts")):
        field = f"tested_hosts[{index}]"
        if exact_object(host, {"name", "version", "evidence"}, field):
            nonblank(host.get("name"), f"{field}.name")
            nonblank(host.get("version"), f"{field}.version")
            local_file(host.get("evidence"), f"{field}.evidence")
    for index, source in enumerate(array(data.get("sources"), "sources", True)):
        field = f"sources[{index}]"
        if exact_object(source, {"kind", "reference", "license"}, field):
            kind = source.get("kind")
            if not isinstance(kind, str) or kind not in {"synthetic", "public", "academy"}:
                error(f"{field}.kind", "expected synthetic, public, or academy")
            nonblank(source.get("reference"), f"{field}.reference")
            nonblank(source.get("license"), f"{field}.license")
    kit = data.get("kit")
    if kit is not None and exact_object(kit, {"repository", "revision"}, "kit"):
        if kit.get("repository") != KIT_REPOSITORY:
            error("kit.repository", f"must equal {KIT_REPOSITORY}")
        revision = kit.get("revision")
        if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
            error("kit.revision", "expected a full lowercase 40-hex commit SHA")
    return identifier if isinstance(identifier, str) else None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1],
                        help="repository root (defaults to the script's project)")
    root = parser.parse_args(argv).root.absolute()
    problems = []

    def directory(path):
        if path.is_symlink():
            problems.append(f"{path}: symlink directories are forbidden")
        elif not path.is_dir():
            problems.append(f"{path}: expected an existing directory")
        else:
            return True
        return False

    count = 0
    try:
        if directory(root):
            template = root / "templates" / "experiment"
            if directory(template.parent) and directory(template):
                validate_manifest(template / "experiment.json", "example-experiment", problems)
            experiments = root / "experiments"
            ids = {}
            if (experiments.exists() or experiments.is_symlink()) and directory(experiments):
                for entry in sorted(experiments.iterdir()):
                    if entry.is_symlink():
                        problems.append(f"{entry}: symlink experiment entries are forbidden")
                    elif entry.is_dir():
                        count += 1
                        path = entry / "experiment.json"
                        identifier = validate_manifest(path, entry.name, problems)
                        if identifier is not None:
                            if identifier in ids:
                                problems.append(f"{path}: id: duplicate id {identifier!r}; also in {ids[identifier]}")
                            ids[identifier] = path
    except OSError as exc:
        problems.append(f"{root}: cannot inspect repository: {exc}")
    if problems:
        print("Manifest validation failed:")
        for problem in problems:
            print(f"- {problem}")
        return 1
    print(f"Validated 1 template and {count} experiment(s). Commands were not executed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
