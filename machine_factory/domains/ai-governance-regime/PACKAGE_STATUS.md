# AI governance regime package status

Factory lifecycle: **CANDIDATES_BUILT_NOT_ADMITTED**. Package `0.2.0`. The 18
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
| 2 | Scope: owner decisions on R02, R04, R06–R09 | `scope-decisions.json` entries | **decided** 2026-11-25 (GOV-SD-04/05, 09–16); R14, the amendments, still with the owner |
| 3 | Sources: pin the baseline and each in-scope framework edition; extract controls | `source-requirements.json`, `source-reference-map.json`, milestone scope | baseline pinned (GOV-SD-15); per-milestone framework scope and producer staging open (GOV-SD-14, 16) |
| 4 | Asset catalog: governance document types, fields, owners, dependencies | `document-asset-catalog.json`, `document-dependencies.json`, `templates/` | partly received (SHACL shapes, SoA template) |
| 5 | Machine conversion: canonical candidate files | `machines/*.json` here, `machine-import-manifest.json`, `semantic-amendments.json` | **built** 2026-11-21; copied to `machines/domains/` at admission |
| 6 | Families and runbooks: one accountable family per workflow | `families/`, `runbooks/` | open; seven workflows in `agentic-workflow-contract.json` |
| 7 | Agent candidates and the workflow contract | `agent-candidates/`, `agentic-workflow-contract.json`, `governance-sources.json` | **built** 2026-11-21: 16 neutral behaviors, W1–W7, 38 Sources |
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

## 0.2.0 record (connected rebuild)

- **Consumed:** CONNECTED_WORKFLOW.md, and owner decisions GOV-SD-07 (every
  workflow and Source in v1) and GOV-SD-08 (runtime-neutral agents).
- **Produced** by `tools/build_machines.py`:
  - 18 machines with 141 CESs: 79 of one event, 52 of two, 10 of three;
  - 145 fixtures;
  - 16 agent behaviors (`agent-candidates/ai-governance-regime/`);
  - `governance-sources.json`;
  - `agentic-workflow-contract.json`.

  It also adds `schemas/agent-behavior.schema.json` at the repository root,
  the runtime-neutral agent contract.
- **What changed from 0.1.0:**
  - templates reserve the lifecycle lanes in cells 2–7;
  - every agent step is a chain: requested, then completed or failed;
  - approvals need a dwell on a rendered diff;
  - watchdogs trip on a sustained breach and release only after their
    agent's triage;
  - templates no longer publish on the bus, and GOV00 folds fixtures only;
  - every template and five fixtures carry an `agentBinding` with a
    completion Source;
  - the band is `[16960:17429]`, with 10-element outputs, adding
    AGENT_REQUESTED and OVERDUE.
- **Verified:** `tools/verify_machines.py` passes:
  - schema-valid machines and behaviors;
  - one pattern per CES;
  - 11 templates cloneable;
  - lanes on every template, no template bus edges;
  - every agent trigger is a real CES, and every completion lane is inside
    its input;
  - regions clear;
  - a reproducible build;
  - 145 fixtures replay.

  In localOpenClawStack, `tests/run_runtime_tests.py` renders all 16
  behaviors for OpenClaw (valid OC agent specs) and for ACP (session-scoped
  frame servers).
- **Not done:** GOV-R11, R12, R19, R20 and R21; no engine run.

## Step 2 record (scope, 2026-11-25)

- **Consumed:** the owner's review of the received hardening workplan against
  NIST SP 2400-102e2026 (initial public draft), and a second received document,
  `organizational-wrapper-governance-machine.md`.
- **Decided:**
  - GOV-SD-09: the scope stays the 18 machines;
  - GOV-SD-10: threat classification and observation are a peer domain,
    threat-dynamics;
  - GOV-SD-11: observe vs decide; three Sources come from threat-dynamics;
  - GOV-SD-12: one shared extension corpus for both domains;
  - GOV-SD-13: approval quorum vs engine quorum (closes R06);
  - GOV-SD-14: framework alignment on the ifrs pattern, scoped per milestone
    (R07);
  - GOV-SD-15: the baseline is V0.18, NIST terminology revision (closes R08);
  - GOV-SD-16: inputs are simulated Sources through the ISRE until producers
    exist; producers are staged by milestone (R09).
- **Produced:**
  - the wrapper document intaken byte-for-byte as
    `intake/ORGANIZATIONAL-WRAPPER-MACHINE.md` (GOV-R22);
  - `producerDomain: threat-dynamics` on `gate_redteam_pass`,
    `mon_canary_drift_score` and `mon_xdomain_mu_agg` in
    `governance-sources.json` (GOV-R23);
  - GOV-SD-05's band corrected to `[16960:17429]`;
  - GOV-R03 closed, GOV-R11 decided, GOV-R14's count corrected to 22.
- **The received workplan against this scope.** RESOLUTION_WORKPLAN.md stays
  as received. Read it with this mapping:

  | Workplan says | In this package |
  |---|---|
  | 315 machines, M-GOV-01..315; 1,867 corpus machines | 18 machines, GOV00–GOV17 (GOV-SD-04, GOV-SD-09) |
  | band `[16960:17087]`, hardened cells 16987–16991 | per-machine regions in `[16960:17429]`; the cell numbers are `inputSemantics` labels (GOV-SD-05) |
  | M-GOV-15 / 16 / 17 | GOV15 break-glass, GOV16 cross-domain delegation cap, GOV17 quorum key revocation |
  | outputs at 17056–17059 | each machine's 10-element output; the domain verdicts are GOV00's output |
  | "C++, Scala, and Lisp voting runtimes" | the quorum contract's C++, LSP and Scala, 3-of-3 |
  | AgentDojo gate, canary probe, cross-domain μ aggregate | produced by threat-dynamics, consumed here (GOV-SD-11) |
  | 100% pass-set equality, `p99 <= 820 ns` | designed, not measured (GOV-R09) |
  | weeks 1–8 | no calendar; the order of the gaps is kept |

- **Verified:** `python3 tools/verify_package.py` and
  `python3 tools/verify_machines.py` pass (see the PR).
- **Also produced:** the baseline intaken byte-for-byte as
  `intake/BASELINE-V0.18-NIST.pdf`; the 19 November edition the received
  documents cite is recorded by sha256 only.
- **Not done:** the threat-dynamics package itself; the milestone scope and the
  simulated-Source definitions (step 3); R14 (owner); R10 and R22 wait for the
  next document revision.
