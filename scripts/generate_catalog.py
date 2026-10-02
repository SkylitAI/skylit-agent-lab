"""Generate a catalogue of declared scope and reviewed historical observations."""

import argparse
from datetime import date
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
if not __package__:
    sys.path.insert(0, str(ROOT))
from scripts import validate_experiments as manifests

REPOSITORY = "https://github.com/SkylitAI/skylit-agent-lab"
MAX_CATALOG_BYTES = 1048576


class CatalogError(ValueError):
    """Invalid catalogue data or local references; no metadata is executed."""


def _require(condition, message):
    if not condition:
        raise CatalogError(message)


def _keys(value, names, field):
    _require(type(value) is dict and set(value) == set(names.split()), f"{field}: expected exactly {names}.")


def _string(value, field):
    _require(type(value) is str and value.strip() and len(value) <= 4096, f"{field}: expected nonblank text, at most 4096 characters.")
    try:
        value.encode("utf-8")
    except UnicodeError:
        raise CatalogError(f"{field}: expected UTF-8 text.") from None


def _local(root, value, *, required=True):
    _string(value, "local reference")
    parts = value.split("/")
    _require(not any(part in ("", ".", "..") for part in parts)
             and ":" not in value and "\\" not in value and value.isprintable(),
             "local reference: use a repository-relative path without dots, colons, backslashes or controls.")
    path = root
    for index, part in enumerate(parts):
        path /= part
        _require(not path.is_symlink(), f"local reference {value!r}: symlinks are forbidden.")
        if index < len(parts) - 1:
            _require(path.is_dir(), f"local reference {value!r}: missing directory.")
    _require(not (required or path.exists()) or path.is_file(), f"local reference {value!r}: expected a regular file.")
    return path


def _read(path, limit):
    def opener(name, flags):
        return os.open(name, flags | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0))
    with open(path, "rb", opener=opener) as source:
        _require(stat.S_ISREG(os.fstat(source.fileno()).st_mode), "Expected a regular input file.")
        raw = source.read(limit + 1)
    _require(len(raw) <= limit, f"Input exceeds the {limit}-byte limit.")
    return raw


def _json(path):
    try:
        return json.loads(_read(path, manifests.MAX_BYTES).decode("utf-8"),
                          object_pairs_hook=manifests.unique_object,
                          parse_constant=manifests.finite_number, parse_float=manifests.finite_number)
    except (UnicodeError, ValueError, RecursionError):
        raise CatalogError("Expected bounded UTF-8 JSON without duplicate keys or nonfinite numbers.") from None


def _evidence(root, ids):
    value = _json(_local(root, "catalog/evidence.json"))
    _keys(value, "schema_version questions offline_evaluation", "catalogue evidence")
    _require(type(value["schema_version"]) is int and value["schema_version"] == 1, "schema_version: expected integer 1.")
    questions = value["questions"]
    _require(type(questions) is dict and not questions.keys() - ids, "questions: referenced experiment IDs must exist.")
    for question in questions.values():
        _string(question, "question")
    observed = value["offline_evaluation"]
    if observed is not None:
        _keys(observed, "date lab_revision kit_revision python passed_cases experiments review_basis guide pull_request", "offline_evaluation")
        try:
            _require(type(observed["date"]) is str and date.fromisoformat(observed["date"]).isoformat() == observed["date"],
                     "offline_evaluation.date: expected YYYY-MM-DD.")
        except ValueError:
            raise CatalogError("offline_evaluation.date: expected a valid YYYY-MM-DD date.") from None
        for key in ("lab_revision", "kit_revision"):
            _require(type(observed[key]) is str and re.fullmatch(r"[0-9a-f]{40}", observed[key]), f"{key}: expected a full lowercase Git SHA.")
        _require(type(observed["python"]) is str and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", observed["python"]), "python: expected a recorded x.y.z version.")
        _require(type(observed["passed_cases"]) is int and 1 <= observed["passed_cases"] <= 1000, "passed_cases: expected a positive integer, at most 1000.")
        covered = observed["experiments"]
        _require(type(covered) is list and covered and all(type(item) is str for item in covered)
                 and len(covered) == len(set(covered)) and set(covered) <= ids,
                 "offline_evaluation.experiments: expected unique existing experiment IDs.")
        _require(observed["review_basis"] == "author_and_ai", "review_basis: v1 accepts only author_and_ai; human reproduction needs a reviewed extension.")
        _local(root, observed["guide"])
        _require(type(observed["pull_request"]) is str and re.fullmatch(re.escape(REPOSITORY) + r"/pull/[1-9][0-9]*", observed["pull_request"]),
                 "pull_request: expected an HTTPS pull request in this Lab repository.")
    return questions, observed


def _text(value):
    # Entities keep printable wording while preventing Markdown/HTML structure.
    result = []
    for char in value:
        if not char.isprintable():
            result.append("&#92;" + (f"u{ord(char):04X}" if ord(char) <= 65535 else f"U{ord(char):08X}"))
        elif char.isalnum() or char == " ":
            result.append(char)
        else:
            result.append(f"&#{ord(char)};")
    return "".join(result)


def _link(label, relative):
    return f"[{_text(label)}](../{quote(relative, safe='/')})"


def build_catalog(root):
    """Render declarations and a reviewed observation; never recertify their truth."""
    root = Path(root).absolute()
    _require(manifests.main(["--root", str(root)]) == 0, "Manifest validation failed; fix the diagnostics above.")
    entries = {}
    for folder in sorted((root / "experiments").iterdir()):
        if folder.is_dir():
            entry = _json(_local(root, f"experiments/{folder.name}/experiment.json"))
            _require(entry["status"] == "experimental", f"{folder.name}: maturity {entry['status']!r} needs a reviewed governance extension; catalogue v1 accepts experimental only.")
            _local(root, f"experiments/{folder.name}/README.md")
            entries[folder.name] = entry
    questions, observed = _evidence(root, entries.keys())
    groups = {}
    for identifier in entries:
        groups.setdefault(questions.get(identifier), []).append(identifier)
    lines = ["# Experiment catalogue", "",
        "Find an experiment by the question it helps inspect. Owner, access and cost are",
        "manifest declarations. Historical checks identify their recorded source revision;",
        "they do not establish current-head verification, human reproduction or native host support.", ""]
    for question in sorted(groups, key=lambda value: (value is None, value or "")):
        lines += ["## " + (_text(question) if question is not None else "Other experiments"), ""]
        for identifier in sorted(groups[question]):
            entry = entries[identifier]
            lines += ["### " + _link(identifier, f"experiments/{identifier}/README.md"), "", _text(entry["purpose"]), "",
                      "| Field | Recorded information |", "|---|---|", "| Maturity | Experimental |"]
            for key in ("owner", "access", "cost"):
                lines.append(f"| {key.title()} (declared) | {_text(entry[key])} |")
            verification = "Verification not recorded"
            if observed and identifier in observed["experiments"]:
                revision = observed["lab_revision"]
                verification = f"Historical offline pass recorded {observed['date']} at [{revision}]({REPOSITORY}/commit/{revision}); see the evidence below"
            lines += [f"| Offline verification | {verification} |", "| Native agent hosts | Unverified |", ""]
            for host in sorted(entry["tested_hosts"], key=lambda item: (item["name"], item["version"], item["evidence"])):
                local = f"experiments/{identifier}/{host['evidence']}"
                _local(root, local)
                lines += ["Host evidence (reported, unreviewed): " + _link(host["name"] + " " + host["version"], local) + ".", ""]
    lines += ["## Historical evidence and limits", ""]
    if observed:
        lines += [f"The [reviewed record](evidence.json) states that **{observed['passed_cases']} fixed offline cases passed** on {observed['date']}",
                  f"using container Python {observed['python']} and Kit `{observed['kit_revision']}`.",
                  f"Source Lab revision: `{observed['lab_revision']}`.",
                  f"Basis: author and AI review; [implementation review]({observed['pull_request']}) and "
                  + _link("evaluation guide", observed["guide"]) + ".", ""]
    else:
        lines += ["No offline evaluation observation is recorded.", ""]
    lines += ["This is a reviewed historical assertion, not a new evaluator run. File existence",
              "checks establish link integrity, not the truth of a claim. No independent human",
              "reproduction, maintenance commitment, graduation or native-host pass is recorded",
              "by this v1 catalogue. Host evidence links remain unreviewed reports.", "",
              "A future reviewed contract must define evidence for higher maturity or scoped",
              "host results before those labels can be published. The generator rejects other",
              "manifest maturity values. New experimental entries appear even without curated evidence.", "",
              "## Regenerate", "", "From the repository root:", "", "```sh",
              "python3 -X utf8 -I -B scripts/generate_catalog.py",
              "python3 -X utf8 -I -B scripts/generate_catalog.py --check", "```", "",
              "Edit `catalog/evidence.json` and experiment manifests through review; do not edit",
              "this generated page. Source references in manifests remain human citations, not",
              "paths inferred by the generator. Commands and metadata are never executed.", ""]
    text = "\n".join(lines)
    _require(len(text.encode("utf-8")) <= MAX_CATALOG_BYTES, "Generated catalogue exceeds 1 MiB.")
    return text


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--check", action="store_true", help="Fail if the committed generated catalogue is missing or stale")
    args = parser.parse_args(argv)
    temporary = None
    try:
        raw = build_catalog(args.root).encode("utf-8")
        output = _local(args.root, "catalog/README.md", required=args.check)
        if args.check:
            _require(_read(output, MAX_CATALOG_BYTES) == raw, "Catalogue is stale; run scripts/generate_catalog.py and review the change.")
        else:
            with tempfile.NamedTemporaryFile(dir=output.parent, prefix=".catalog-", delete=False) as target:
                temporary = Path(target.name)
                target.write(raw)
            os.replace(temporary, output)
        print("Catalogue is current." if args.check else "Generated catalog/README.md; review declarations and evidence before publishing.")
        return 0
    except (CatalogError, OSError, UnicodeError) as error:
        print(f"Catalogue failed: {error}", file=sys.stderr)
        return 1
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
