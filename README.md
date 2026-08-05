# RealityEngine_Machines

A collection of machines that represent the skills known to the RealityEngine.

## Architecture Contracts

This repository also owns the machine-domain constraints used to admit new
domains and agent-capable machines:

- [RealityEngine and PerceptionEngine operations](docs/REALITY_PERCEPTION_OPERATIONS.md)
- [Architecture audit and agent workflow roadmap](docs/ARCHITECTURE_AUDIT.md)
- [Domain manifest](domains/domain-manifest.json)
- [Domain registry](domains/domain-registry.json)
- [Domain manifest schema](schemas/domain-manifest.schema.json)
- [Agent binding schema](schemas/agent-binding.schema.json)
- [Agent autonomy policy schema](schemas/autonomy-policy.schema.json)
- [Agent-ready machine class schema](schemas/agent-ready-machine-class.schema.json)
- [localAIStack write-back schema](schemas/localai-writeback.schema.json)
- [localAIStack completion write-back schema](schemas/localai-completion-writeback.schema.json)
- [RE to localAIStack dispatch envelope schema](schemas/ai-trigger-envelope.schema.json)
- [Machine class catalog](schemas/machine-class.schema.json)

Run the compatibility validator:

```bash
npm run validate
```

`domains/domain-manifest.json` is the authoritative domain inventory. Every
loadable machine must resolve to a manifest domain, and every
`currentMachineCount` must match the recursive `machines/**/*.json` count for
that domain; normal validation fails on manifest drift.

Inventory or refresh the semantic bus registry:

```bash
npm run semantic-buses:inventory
npm run semantic-buses:write
```

`semantic-buses:inventory` validates the semantic published buses and checks the
checked-in registry. Mechanical range and core aggregation buses are set aside
from the semantic bus contract.

Run the local architecture contract tests:

```bash
npm run test:contracts
```

Run the stricter new-domain gate:

```bash
STRICT_DOMAIN_CONTRACT=1 npm run validate
```

## Testing

This repo owns tests that are specific to the machine corpus and the
multi-instance deployment:

- `tests/smoke/` — services-up smoke checks (`npm run test:smoke`)
- `tests/integration/` — corpus integrity, RAG round-trip, PE sensor
  registration, multi-instance, OpenClaw health (`npm run test:integration`)
- `tests/contracts/` — Python agent-contract tests (`npm run test:contracts`)
- `tests/e2e/engine-switcher.spec.ts` — Machines-specific e2e (`npm run test:e2e`)

The shared, application-level Playwright e2e specs (`api`,
`full-integration`, `multi-step-output-workflow`,
`perceptual-space-interconnection`, `visualizer-ui`) are **owned canonically by
RealityEngine_CI** at `RealityEngine_CI/e2e/tests/`. They previously lived here
as duplicates under `tests/e2e/specs/` and had already begun to drift
(`api.spec.ts` asserted a stale `vectorDimension`). To keep a single source of
truth, do **not** re-add copies of those specs here — edit them in
RealityEngine_CI. The unified runner `RealityEngine_CI/scripts/run-all-tests.sh`
executes both repos' suites.

### Where each suite is verified

This repo has no workflows of its own by design: verification is owned by
RealityEngine_CI's universe orchestration, since every contract here is
cross-runtime and only means something against running engines.

| Suite | Needs a live stack | Verified by |
|---|---|---|
| `npm run validate` | no | CI `corpus-gates` job |
| `npm run test:contracts` | no | CI `corpus-gates` job |
| `tests/e2e/engine-switcher.spec.ts` | yes | CI `e2e-tests` job |
| `tests/integration/corpus-integrity`, `openclaw-health` | yes | CI `e2e-tests` job |
| `tests/integration/healthkit-ingest-contract`, `machine-json-listing`, `pe-source-lane-compliance` | yes, plus a registry | CI `multi-engine-tests` job |
| `tests/integration/multi-instance` | yes, plus a registry | CI `multi-engine-tests` job |
| `tests/integration/rag-round-trip`, `pe-sensor-registration` | yes, plus localAI | operator-run — hosted jobs start with `--no-local-ai` |

The three cross-runtime contract specs run in `multi-engine-tests` rather than
`e2e-tests` because that is the job that exports `RE_REGISTRY_URL`. They are
skip-safe, so that step also fails when *every* one of them skips — a green run
that enforced nothing is the failure mode being guarded against.

`machine-json-listing` compares `json/list` against `MACHINES_CORPUS_DIR` — the
corpus the universe actually booted — rather than this repo's full tree, so it
is correct under both `--machine-corpus=standard-deployment` and a full-corpus
universe.

### OWL reasoning

`npm run validate` ends with `reason-owl: SKIPPED (ROBOT not installed)`. That
is expected: ROBOT's default report profile currently yields ~3,400 ERROR-level
`missing_label` violations on this corpus — OBO publishing conventions, not
logical inconsistency — and `report` fails before `robot reason` runs at all.
Enabling it needs a tailored profile first; see #46.
