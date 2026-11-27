# threat-dynamics package status

Factory lifecycle: **CANDIDATES_BUILT_NOT_ADMITTED**. Package `0.1.0`. The 11
candidate machines are in this package's `machines/`. Nothing is under the
repository's `machines/domains/`, and no runtime file is changed.

The steps are ai-governance-regime's (its PACKAGE_STATUS.md, GOV-SD-02).

| # | Step | Produces | State |
|---|---|---|---|
| 1 | Intake | `admission-source-manifest.json` (by sha256), `REVIEW_QUEUE.md`, `tools/verify_package.py` | **done** 2026-11-25 |
| 2 | Scope | `scope-decisions.json` TD-SD-01..07 | **decided** 2026-11-25 (from GOV-SD-10, 11, 12, 16; amendments approved, TD-SD-07) |
| 3 | Sources | the specification pinned; producers staged per milestone | pinned; staging open (TD-R02) |
| 4 | Asset catalog | — | not applicable: the domain has no governed documents |
| 5 | Machine conversion | `machines/*.json`, `semantic-amendments.json` | **built** 2026-11-25 |
| 6 | Families and runbooks | `families/`, `runbooks/` | open |
| 7 | Agents | — | none: observe only (TD-SD-02) |
| 7a | Sources and simulations | `threat-sources.json` | **built** 2026-11-25 |
| 8 | Acceptance | `acceptance/` | live run recorded 2026-11-26 (`acceptance/live-run-2026-11-26.json`); extension-corpus regression 2026-11-27 passed 3-of-3 (CI run `20261127T000353Z`), followers agree after RealityEngine_CI#880; CES shard and TD-R08 open |
| 9 | Admission | `scripts/approve-domain.sh plan`, then `prepare` | open; before ai-governance-regime (TD-SD-06) |
| 10 | Deployment | `deployments/` | open |

## Step 5 and 7a record (2026-11-25)

- **Consumed:** SP 2400-102e2026 ipd §4.1–4.7 and §5.1.3; ai-governance-regime's
  `governance-sources.json` (the three signals it takes from this domain);
  SURFACE_SPEC.md Sources & Sensors; the PE's simulated-source sample in C++
  `reality.cpp` and Manager `PerceptionEngine.ts`.
- **Produced** by `tools/build_machines.py`:
  - 11 machines: THR01–07, one per NISTAML.061–.067; THR08, 09 and 10; and
    THR00;
  - 69 CESs (50 in the observers, 19 in THR00), 63 fixtures;
  - `threat-sources.json`: 33 signals, 3 published lanes, 45 simulations
    (20 adversarial, 15 near-miss, 10 nominal).
- **Layout:** band `[17440:17759]`:
  - inputs `[17440:17599]`, 16 cells per machine;
  - outputs `[17600:17679]`, 8 each;
  - roll-up input `[17680:17706]`;
  - roll-up output `[17707:17709]`.
- **Verified:** `python3 tools/verify_machines.py` passes:
  - schema-valid against `schemas/machine.schema.json`;
  - one pattern per CES; nothing cloneable;
  - no decision outputs, agents or latches;
  - regions clear of governance, the corpus, reserved ranges and the clone
    space;
  - names unique, `THR` free;
  - a reproducible build;
  - 63 fixtures replay;
  - 45 simulations replay through the ISRE their Sources compose, one
    simulated Source per input cell;
  - the published lanes match `governance-sources.json`;
  - every class has adversarial and near-miss simulations, and every
    confirming and gate CES is fired by one.
- **Not done:** producers (TD-R02).
- **Live run 2026-11-26:** 45 of 45 simulations agree 3-of-3; Rust and Go agree on all 45; output persistence found (TD-R08).
- **Approved 2026-11-25:** TD-SA-01..06 (TD-SD-07, TD-R03 closed).
