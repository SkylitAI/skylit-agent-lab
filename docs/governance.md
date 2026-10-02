# Ownership and promotion

Contributors can propose experiments, fix reproducible defects, improve a user
task or independently reproduce a saved example. Lab holds experiments; Kit
holds reviewed shared tools. A useful experiment may remain in Lab indefinitely.
Popularity, a demo or a profitable-looking result does not establish correctness
or qualify it for promotion.

## Who decides and who maintains

The [repository owner](maintainers.md) routes proposals and release decisions.
An experiment's manifest names its **declared owner**. That handle preserves
attribution and provides a contact; it does not establish an accepted maintenance
role or a response-time commitment.

A contributor becomes an experiment maintainer when an authorized repository
maintainer reviews their work and records the person's explicit acceptance and
scope: package, modes/platforms, dependency updates, security/source review and
handoff. Link that decision in the experiment's evidence. Repository-wide
permissions require a separate owner decision; contributions do not automatically
grant write or release access.

Reviewers inspect behavior, relevant failures, calculation/source fidelity,
privacy and rights, access/cost claims, dependency pins and compatibility evidence.
Use the [AI slop check](../CONTRIBUTING.md#before-review) on code and prose. Report
exact commands, failed/skipped checks and unresolved limits. A schema pass or
file's existence does not prove its contents are true. Distinguish human
observations, automated tests and AI review.

The operating target after public launch is a substantive first reply within
three working days for at least 90% of incoming non-spam human issues and PRs,
with weekly triage. An acknowledgement alone does not count. A response owner,
timezone and holiday calendar must be named before operating this target;
bootstrap ownership alone is not an established response service. Record missed
targets and unanswered items rather than excluding them.

## What each maturity label means

Record decisions with the [evidence template](evidence/status-review-template.md).
Use the highest level whose requirements are present and reviewed. These labels
describe stewardship and reproducibility, not investment performance.

| Label | Required evidence |
|---|---|
| `experimental` | Runnable documented example, scope, declared owner, source/license/access/cost disclosures, and reviewed relevant behavior tests. |
| `reproduced` | Experimental requirements plus a non-author **human** independently following the pinned setup and recording date, environment, commands/exits, input/output checks, limitations and reviewer. An AI or author run alone does not qualify. |
| `maintained` | Reproduction evidence plus a named human's explicit acceptance of scoped maintenance and relevant dependency, security, source and compatibility responsibilities. |
| `graduated` | Maintained requirements plus an accepted Kit implementation, versioned Kit release, relevant checks/docs, contributor attribution and a Lab consumer migrated to that released pin. A proposed PR or copied helper is insufficient. |
| `archived` | Dated reviewed decision, reason, last known evidence and maintained replacement if one exists. Preserve history without implying current support. |

Maturity and host support are separate. A reproduced Python workflow is not a
verified Claude Code or OpenClaw integration. [Host acceptance](host-contract.md)
requires actual host execution and version/OS/auth/tool/usage evidence. Partial
offline/denial results stay scoped when live access is untested. Do not advertise
a host as supported just because `tested_hosts` points to a file. Retain failed
and not-run cases alongside passes.

The manifest validator only checks permitted status words. The first catalogue
supports experimental entries and historical offline checks; it rejects higher
declared maturity until a reviewed extension consumes the corresponding decision
evidence. Changing a manifest alone cannot promote an entry. Retain the exact
tested revision/date; an older result does not certify the current branch or a
changed dependency.

## If an owner is missing

Record maintenance as unassigned when no person has accepted it or an accepted
maintainer steps down. Keep historical attribution rather than inventing a
handle to satisfy the manifest. The repository owner routes the issue; a
volunteer explicitly accepts the scope before reviewed reassignment. A CODEOWNERS
match is a review route, not that acceptance.

Pause promotion and current maintenance/support claims while ownership is
unassigned. An authorized repository maintainer records a downgrade or archive
decision and updates the guide, evidence and catalogue together. Keep old results
as dated history. If the generator cannot represent that decision, extend it in
the same reviewed change; do not bypass its checks or silently drop the experiment.
There is no automatic deletion or assumed abandonment deadline.

## Move one capability into Kit

1. Describe a concrete repeated user need and the smallest shared capability
   that addresses it. Check Kit first; do not duplicate an existing maintained
   interface. An experiment's whole agent stack need not move.
2. Link reproduction and maintenance evidence, sources/licenses, behavior and
   failure tests, access/cost boundaries and relevant host results. State which
   interfaces and modes the candidate actually supports.
3. Agree the destination and owner with the Kit maintainer. Submit a bounded Kit
   PR preserving attribution and adding relevant tests/docs. Keep Kit independent
   of unreleased Lab code.
4. Obtain the normal Kit review, required checks and a versioned release. Record
   its exact commit and release link. A merge alone is not release evidence.
5. Update Lab to consume the released pin and remove its competing maintained
   implementation in the reviewed migration. Reproduce the original example,
   compare source values/gaps and recheck affected host cases. Record migration
   guidance and attribution links before marking it graduated.

Use the experiment-review issue form to propose a status change or graduation.
Submitting it requests review; it does not approve a release, assign a maintainer
or authorize credentials, live calls or publication.

## Applying the rubric now

**Watchlist Investigator remains experimental.** Its documented fixture path,
declared owner, pinned Kit, sources, negative tests and fixed offline evaluator
provide engineering evidence. The [evaluation guide](evaluation.md) describes
the checks. There is no accepted non-author human reproduction, scoped maintenance
acceptance, completed native-host contract or Kit graduation record. None can be
inferred from automated passes or the manifest's owner handle.

**Incomplete example, not a real submission:** a proposed adapter has an author
screenshot and a manifest claiming `graduated`, but lacks source rights, a
repeatable input, failure tests, human reproduction, accepted maintenance,
Kit PR/release and a Lab migration. It cannot graduate. Request source and
runnable evidence first; the screenshot and claimed status do not replace it.
This illustration implies no accepted contribution or maintainer.
