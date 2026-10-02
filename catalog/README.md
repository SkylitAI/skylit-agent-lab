# Experiment catalogue

Find an experiment by the question it helps inspect. Owner, access and cost are
manifest declarations. Historical checks identify their recorded source revision;
they do not establish current-head verification, human reproduction or native host support.

## What dated entries appear in this one press&#45;release feed&#63;

### [market&#45;brief](../experiments/market-brief/README.md)

Save a dated Federal Reserve press&#45;feed brief with explicit synthetic&#44; saved&#45;input or fetched provenance and visible source gaps&#46;

| Field | Recorded information |
|---|---|
| Maturity | Experimental |
| Owner (declared) | &#64;prodij |
| Access (declared) | Python 3&#46;11&#43; and the full Lab checkout&#46; Default and saved&#45;input modes are offline&#46; Explicit &#45;&#45;fetch uses one unauthenticated request to the fixed public Board feed&#59; no credentials&#44; Kit or model&#46; |
| Cost (declared) | Local compute by default&#46; Explicit fetching adds ordinary network access with no paid API&#44; model or trading calls&#46; |
| Offline verification | Historical offline pass recorded 2026-10-02 at [dc530976b58fcc86db104ac7a173fca975c3718a](https://github.com/SkylitAI/skylit-agent-lab/commit/dc530976b58fcc86db104ac7a173fca975c3718a); see the evidence below |
| Native agent hosts | Unverified |

## What do my closed paper&#45;trade rows and entered notes show&#63;

### [journal&#45;reviewer](../experiments/journal-reviewer/README.md)

Review closed USD cash&#45;equity paper trades with exact arithmetic and inert supplied notes&#46;

| Field | Recorded information |
|---|---|
| Maturity | Experimental |
| Owner (declared) | &#64;prodij |
| Access (declared) | Python 3&#46;11&#43; and the full Lab checkout&#46; Default input is a bundled fictional CSV&#59; explicit &#45;&#45;input supplies caller&#45;declared paper trades&#46; No Kit&#44; account&#44; credentials&#44; model&#44; upload or network access is required&#46; |
| Cost (declared) | No API or model calls&#59; local compute only&#46; |
| Offline verification | Historical offline pass recorded 2026-10-02 at [dc530976b58fcc86db104ac7a173fca975c3718a](https://github.com/SkylitAI/skylit-agent-lab/commit/dc530976b58fcc86db104ac7a173fca975c3718a); see the evidence below |
| Native agent hosts | Unverified |

## Where are the gaps in fictional watchlist observations&#63;

### [watchlist&#45;investigator](../experiments/watchlist-investigator/README.md)

Render selected fictional watchlist symbols through Agent Kit while preserving unavailable components as gaps&#46;

| Field | Recorded information |
|---|---|
| Maturity | Experimental |
| Owner (declared) | &#64;prodij |
| Access (declared) | Python 3&#46;11&#43; with UTF&#45;8 text mode &#40;&#45;X utf8&#41;&#44; Git&#44; the full Lab checkout and an explicitly supplied clean local Kit checkout at the pinned revision&#46; No account&#44; key&#44; model or runtime network&#46; Obtaining an INTERNAL Kit repository requires separate repository access&#46; |
| Cost (declared) | Zero API credits or model usage&#59; local compute only&#46; |
| Offline verification | Historical offline pass recorded 2026-10-02 at [dc530976b58fcc86db104ac7a173fca975c3718a](https://github.com/SkylitAI/skylit-agent-lab/commit/dc530976b58fcc86db104ac7a173fca975c3718a); see the evidence below |
| Native agent hosts | Unverified |

## Historical evidence and limits

The [reviewed record](evidence.json) states that **12 fixed offline cases passed** on 2026-10-02
using container Python 3.11.17 and Kit `0f82039759ef4db9d5b3dbd90f52863f8074f2a6`.
Source Lab revision: `dc530976b58fcc86db104ac7a173fca975c3718a`.
Basis: author and AI review; [implementation review](https://github.com/SkylitAI/skylit-agent-lab/pull/33) and [evaluation guide](../docs/evaluation.md).

This is a reviewed historical assertion, not a new evaluator run. File existence
checks establish link integrity, not the truth of a claim. No independent human
reproduction, maintenance commitment, graduation or native-host pass is recorded
by this v1 catalogue. Host evidence links remain unreviewed reports.

A future reviewed contract must define evidence for higher maturity or scoped
host results before those labels can be published. The generator rejects other
manifest maturity values. New experimental entries appear even without curated evidence.

## Regenerate

From the repository root:

```sh
python3 -X utf8 -I -B scripts/generate_catalog.py
python3 -X utf8 -I -B scripts/generate_catalog.py --check
```

Edit `catalog/evidence.json` and experiment manifests through review; do not edit
this generated page. Source references in manifests remain human citations, not
paths inferred by the generator. Commands and metadata are never executed.
