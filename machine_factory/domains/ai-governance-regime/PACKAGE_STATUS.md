# AI governance regime package status

Factory lifecycle: **INTAKE_NOT_ADMITTED**. Package `0.1.0-intake`. Nothing is
under `machines/domains/`, and no runtime file is changed.

This domain is the proof of workflow for new domain production
(GOV-SD-02). The table is the workflow. Each step records what it consumed,
what it produced and how it was verified, so a later domain can follow the
same path. Directories appear when their step produces content
(GOV-SD-03).

| # | Step | Produces (ifrs-accounting equivalent) | State |
|---|---|---|---|
| 1 | Intake: receive, preserve, index, review | `intake/`, `admission-source-manifest.json`, `REVIEW_QUEUE.md`, `tools/verify_package.py` | **done** 2026-11-20 |
| 2 | Scope: owner decisions on R02, R04, R06–R09 | `scope-decisions.json` entries | open |
| 3 | Sources: pin the baseline and each in-scope framework edition; extract controls | `source-requirements.json`, `source-reference-map.json` | open (R07, R08) |
| 4 | Asset catalog: governance document types, fields, owners, dependencies | `document-asset-catalog.json`, `document-dependencies.json`, `templates/` | partly received (SHACL shapes, SoA template) |
| 5 | Machine conversion: canonical candidate files | `machines/domains/ai-governance-regime/*.json`, `machine-import-manifest.json` | open (R01–R05) |
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
