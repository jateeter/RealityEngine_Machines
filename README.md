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
