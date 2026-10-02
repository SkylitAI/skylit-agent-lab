# Newcomer pilot

Measure whether five people who did not build these workflows can obtain an
offline Watchlist report and change its input using the published instructions.
Record failed attempts as carefully as successes. This is a protocol prepared
for a future cohort; no participants, completed trials or human results are
claimed here.

## Prepare the cohort

An authorized repository maintainer names a pilot coordinator. That person
confirms five willing participants, at least three self-described novices,
and records their relevant terminal, coding-agent and Lab experience privately.
Use consented participant IDs in shared results. A fresh AI session or the
author operating on someone's behalf does not count as a participant.

Assign at least two people to Claude Code and at least two to OpenClaw. Record
the fifth person's chosen host before starting. Use the same reviewed Lab
revision and pinned Kit for the cohort; record the actual host version, model
when available, OS and permission configuration for each person. Host access and
model costs are separate from the offline Python workflow's zero API usage.

Before a scored trial, confirm:

- The candidate's required workflow, evaluation, host and promotion checks have
  passed. The [host matrix](host-matrix.md) currently records unverified hosts;
  this document does not make that evidence complete.
- Each person already has authorized access to both repositories. INTERNAL
  access is not an outside-public contribution test. Confirm access before the
  trial without changing visibility or granting access through this protocol.
- Git, Python 3.11+, the chosen host and any host login are ready. Record all
  installation, access and account-provisioning time separately, including help.
- The person consents to the observation and separately chooses whether the
  sanitized record may be shared. Do not record credentials, account identifiers,
  unrelated workspaces, private journals or full host transcripts by default.

The coordinator records the candidate and assignments before observing outcomes.
Do not replace unsuccessful people with successful ones to improve the count.
If access or a prerequisite fails, retain that record as a provisioning failure;
do not describe an unstarted task as a timed success.

## Run one observed session

Use the [agent guide](using-your-agent.md) and
[Watchlist instructions](../experiments/watchlist-investigator/README.md).
The participant operates the host and follows the documented setup. The observer
may read the instructions aloud but must not supply hidden fixes, type commands
for the person or repair the environment without recording the intervention.

Start the equipped-machine clock when the person pastes the documented starter
prompt or begins the first setup instruction. Measure elapsed time with a
monotonic timer. Include reading, agent mistakes, retries and error recovery;
do not pause the clock to remove inconvenient delays. Also record total elapsed
time including provisioning. A participant can stop at any time; preserve the
observed elapsed time and reason without converting it into a completed result.

1. **First result:** obtain the default fictional SPY/QQQ report and its private
   `.run.json` sidecar through the selected host. Observe exit 0, both files,
   matching input/report hashes, and visible fictional-data and missing-data
   qualifications. Ask the participant to identify one source value and one
   missing input. Record elapsed minutes from the start, including any help.
2. **Customization:** using the published `--symbols` example, request `QQQ,SPXW`
   into a new output filename. Verify that those symbols appear, SPXW remains a
   gap and no SPX substitution is invented. Check the sidecar's selected symbols,
   hashes and actual exit. Record elapsed minutes from the same start. A renamed
   output with unchanged input does not count as customization.
3. **Contribution navigation:** ask the participant to find the experiment
   template, the maintained Kit boundary, source rules and the review steps.
   Record what they found and any confusing or missing instruction. This is an
   observation, not evidence that they submitted an accepted contribution.

Do not request a Skylit key or make a live call in this trial. Record launching
host usage if observable; otherwise state that it was unavailable. The seed
sidecar measures the Python process and cannot establish the host's model cost.
Use the [host explanation rubric](host-contract.md#evidence-and-interpretation) to inspect
source and gap explanations rather than expecting identical model wording.

The timing target is at least **four of the same five people** completing both
an unassisted first result within **15 minutes** and successful customization
within **30 minutes**. At least three of the five must be self-described novices.
A completed task requiring an undocumented fix is assisted and does not count
as an unassisted pass. A timed-out, abandoned or incorrect result remains in the
denominator. Record exact times rather than rounding a late result into a pass.

## Reproduction and contribution follow-ups

After the timed tasks, assign a non-author human to reproduce each of Watchlist,
Journal Reviewer and Market Brief at the recorded source revision. A participant
may cover more than one seed; record each attempt separately. Use only bundled
fictional inputs. The author must not repair the setup during an attempt. Record
the command, actual exit, checked artifacts and discrepancies using the
[evaluation procedure](evaluation.md). A current-feed fetch is a separate
observation and is not a byte-identical reproduction of a saved fixture.

Invite a willing participant to choose one substantive bounded contribution:
a runnable improvement, a reproducible defect fix, a checked reproduction or a
measurable documentation improvement. Follow [CONTRIBUTING](../CONTRIBUTING.md).
Keep the PR/check/review links and reviewer time. An unsubmitted diff, an automatic
acknowledgement or cosmetic churn is not an accepted substantive contribution.
Record waiting for review separately from active contribution time.

## Close out without losing failures

Keep one [sanitized attempt record](evidence/pilot-record-template.md) per person,
plus separate reproduction and contribution observations. Report the full cohort
with novice/host coverage, provisioning and task times, outcomes and interventions.
Store identity-to-ID mappings and raw observations privately under the coordinator's
agreed retention policy; publish only information the person consented to share.

For each failure, record the exact symptom, affected task and reproducible input,
then assign one small repair with an owner and a test that demonstrates the fix.
Retain the original failure when adding a retest. If a first-time usability result
was biased by prior learning, use a fresh novice for that retest and report both
the original cohort and additional participants. Do not retroactively exclude a
failure or lower the thresholds.

The pilot is complete only when the timing/coverage targets, one non-author
reproduction per seed and one accepted substantive non-author PR are evidenced,
with no unresolved blocker to setup, truthful output, budget enforcement or
contribution. This pilot does not establish public fork access or the later
30-day community participation and response targets.
