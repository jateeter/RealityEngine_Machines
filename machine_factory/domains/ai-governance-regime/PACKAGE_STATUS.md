# AI governance regime package status

Factory lifecycle: **CANDIDATES_BUILT_NOT_ADMITTED**. Package `0.1.0`. The 18
candidate machines are in this package's `machines/`. Nothing is under the
repository's `machines/domains/`, and no runtime file is changed.

This domain is the proof of workflow for new domain production
(GOV-SD-02). The table is the workflow. Each step records what it consumed,
what it produced and how it was verified, so a later domain can follow the
same path. Directories appear when their step produces content
(GOV-SD-03).

| # | Step | Produces (ifrs-accounting equivalent) | State |
|---|---|---|---|
| 1 | Intake: receive, preserve, index, review | `intake/`, `admission-source-manifest.json`, `REVIEW_QUEUE.md`, `tools/verify_package.py` | **done** 2026-11-20 |
| 2 | Scope: owner decisions on R02, R04, R06–R09 | `scope-decisions.json` entries | R02 and the layout decided (GOV-SD-04/05); R06–R09 open |
| 3 | Sources: pin the baseline and each in-scope framework edition; extract controls | `source-requirements.json`, `source-reference-map.json` | open (R07, R08) |
| 4 | Asset catalog: governance document types, fields, owners, dependencies | `document-asset-catalog.json`, `document-dependencies.json`, `templates/` | partly received (SHACL shapes, SoA template) |
| 5 | Machine conversion: canonical candidate files | `machines/*.json` here, `machine-import-manifest.json`, `semantic-amendments.json` | **built** 2026-11-21; copied to `machines/domains/` at admission |
| 6 | Families and runbooks: one accountable family per workflow | `families/`, `runbooks/` | open; seven families identified in `machine-import-manifest.json` |
| 7 | Agent candidates and the workflow contract | `agent-candidates/`, `agentic-workflow-contract.json` | open |
| 8 | Acceptance: synthetic cases, positive/negative/boundary | `acceptance/` | open |
| 9 | Admission: `scripts/approve-domain.sh plan`, then `prepare` | `domains/approvals/ai-governance-regime/...` | open |
| 10 | Deployment | `deployments/`, `DEPLOYMENT.md` | open |

## Step 1 record (intake)

- **Consumed:** 14 files the owner placed in
  `machine_factory/domains/AIGovernanceRegime/` on 2026-11-20.
- **Produced:** this layout, the source manifest (received name → path,
  sha256), the import manifest, the scope decisions, the review queue
  (GOV-R01–R10) and the verifier.
- **Changed:** names and locations only. The directory takes the canonical
  domain id, matching `ifrs-accounting`.
- **Verified:** `python3 tools/verify_package.py` passes: 14 received files
  unchanged, every JSON file parses, and the corpora are consistent (312 and
  315 unique ids, counts as stated, 315 ⊇ 312).
- **Not done:** no schema validation, no engine run, no semantic review of the
  governance content beyond the queue.

## Step 5 record (machine conversion)

- **Consumed:** SPECIFICATION.md §4.3 (M-GOV-01–14) and
  HARDENING_TRANSITION_RULES.md (M-GOV-15–17, hardened M-GOV-01 and -06), plus
  owner decisions GOV-SD-04, -05 and -06. The intake corpora were not used for
  behavior.
- **Produced:** `tools/build_machines.py`, which writes `machines/`:
  - 17 governance machines and the GOV00 verdict aggregator;
  - 143 CESs, each one regular expression; the expression is in
    `sequences[].metadata.regularExpression`;
  - 106 fixtures;
  - 11 cloneable templates and 7 fixtures (the aggregator included).

  `semantic-amendments.json` records the 12 resolutions of the
  specification.
- **Layout:** band `[16960:17439]`:
  - machine inputs `[16960:17231]`, 16 cells each;
  - machine outputs `[17232:17367]`, 8 each: halt, revoke, permit, incident,
    parked, approach, latch, rework;
  - aggregator input `[17368:17435]`;
  - domain verdicts `[17436:17439]`.
- **Verified:** `python3 tools/verify_machines.py` passes:
  - schema-valid against `schemas/machine.schema.json`, through Ajv, as
    `validate-schemas.mjs` validates;
  - `check-one-ces-one-pattern.py`: 0 violations;
  - `cloneable_machines.py`'s rule: every template cloneable, nothing else;
  - one initial and one terminal event per CES;
  - no region overlap, and clear of the corpus (ends at 16944) and the clone
    space (20480);
  - unique filenames, and the `GOV` prefix is free;
  - a reproducible build;
  - every fixture replays under SURFACE_SPEC's transition rule.
- **Not done:**
  - no engine has loaded these machines;
  - no 3-of-3 trajectory comparison (GOV-R12);
  - the multi-valued watchdogs need an extension corpus (GOV-R11);
  - the amendments need owner review (GOV-R14).
