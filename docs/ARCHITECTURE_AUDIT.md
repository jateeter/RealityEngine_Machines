# Architecture Audit and Agent Workflow Roadmap

This repository is the source of truth for machine definitions, domain policy,
and localAIStack dispatch contracts.  New domains should be admitted only when
they satisfy the constraints below.

## 1. Corpus Validation

`npm run validate` now runs `scripts/audit-corpus.py`.

Default mode is compatibility-safe:

- hard schema errors fail;
- migration gaps are reported as warnings;
- existing machines can continue to seed and run.

Strict mode is for new domains and CI gates:

```bash
STRICT_DOMAIN_CONTRACT=1 npm run validate
```

Strict mode treats warnings as failures.  It should be required before adding a
new top-level domain or a large generated machine family.

The validator checks:

- parseable JSON;
- top-level `machine`;
- non-empty `name`, `description`, `metadata`, and `sequences`;
- `perceptualMapping.input` and `perceptualMapping.output`;
- `bitsPerElement` in `1, 2, 4, 8`;
- `metadata.governance`;
- `metadata.triggerConfig.rules`;
- trigger sequence IDs and RAG codes;
- `inputSemantics` shape and length;
- `sensorNormalization` shape;
- first-class `agentBinding` when present;
- `machineClass` against the standard class catalog.

## 2. Domain Manifest

`domains/domain-manifest.json` is the accepted domain inventory. It records the
domain display name, status, corpus count, source-data default, PE ingest
pattern, agent workflow, code prefixes, default autonomy level, required
machine classes, and default agent families.

`domains/domain-registry.json` carries the companion policy contract: autonomy
mode definitions, the standard machine-class catalog, accepted domain set, and
range-overlap policy. The validator checks that the manifest and registry name
the same domains.

Range ownership is explicit:

- `exclusive`: ordinary machine input/output ownership;
- `overlay`: shared range with declared alternate interpretation;
- `bridge`: producer output intentionally lands on another machine input;
- `deprecated`: retained for compatibility only.

New domains must add both a manifest entry and a registry entry before machine
JSON is added.

## 3. First-Class Agent Binding

Legacy fields remain supported as compatibility aliases:

- `dispatchableAgent`
- `agentActions`
- `aiTrigger`

Every dispatch-capable machine must use `metadata.agentBinding`, validated by
`schemas/agent-binding.schema.json`. The legacy fields may remain for older
loaders, but `dispatchableAgent` without `agentBinding` is now a validation
error.

Example:

```json
"agentBinding": {
  "agent": "care_coordinator_agent",
  "mode": "supervised-act",
  "trigger": "care-gap-risk",
  "allowedActions": [
    "Summarize current risk state.",
    "Draft a care coordination plan.",
    "Request human review before outreach."
  ],
  "writeBack": {
    "type": "pe-sensor",
    "sensorId": "localai.care_gap_prediction",
    "region": { "offset": 2100, "length": 4 },
    "semantics": ["risk", "confidence", "urgency", "review_required"],
    "ttlMs": 30000,
    "normalization": "already-normalized-0-1"
  },
  "riskControls": {
    "requiresHumanApproval": true,
    "requiresRunbook": true,
    "maxAutonomy": "supervised-act",
    "blockedWhenRag": ["RED"]
  }
}
```

## 4. RE/PE to localAIStack Dispatch

CES terminal events should use the canonical trigger envelope in
`triggers/ai_trigger_envelope.template.json`, validated by
`schemas/ai-trigger-envelope.schema.json`. The sample builder
`scripts/build-dispatch-envelope.py` derives the envelope from one machine file,
one trigger rule, and the current `metadata.agentBinding`.

Dispatch sequence:

1. RE emits a `mergeBatch` operation.
2. Dispatcher resolves `metadata.triggerConfig.rules`.
3. Governance is copied from the runtime decision.
4. Output semantics and provenance are attached.
5. `metadata.agentBinding` selects the localAIStack agent, autonomy mode,
   allowed action catalog, and write-back policy.
6. The envelope is sent to localAIStack GraphQL through the standardized
   `metadata.triggerConfig.dispatch` contract.

The AI side must not re-derive governance or vector semantics.

Every agent-bound machine now carries:

```json
"triggerConfig": {
  "endpoint": "http://localhost:4000/graphql",
  "template": "triggers/graphql_trigger_template.py",
  "dispatch": {
    "target": "localAIStack",
    "transport": "graphql",
    "mutation": "updateProcessState",
    "envelopeSchema": "schemas/ai-trigger-envelope.schema.json",
    "schemaRef": "localAIStack/services/api/routers/graphql_endpoint.py"
  }
}
```

## 5. localAIStack to PE Write-Back

AI predictions and recommendations should return through PE, not directly into
RE.  This preserves source identity, TTL, provenance, and replayability.

Supported write-back modes are defined in
`schemas/localai-writeback.schema.json`:

- `none`: AI observes only;
- `pe-sensor`: AI writes a named PE sensor source;
- `pe-domain-vector`: AI writes a domain vector block.

The preferred form is `pe-sensor`, because it matches existing PE source
semantics and can expire naturally.

Non-observe agents must now use `pe-sensor`. The write-back path is:

1. localAIStack produces a recommendation, prediction, or action result.
2. The adapter builds the completion payload described by
   `schemas/localai-completion-writeback.schema.json`.
3. PE receives it through `POST /api/integrations/completions`.
4. PE updates or creates the configured sensor source.
5. RE consumes the changed PE vector state on the next push cycle.

Every non-observe `metadata.agentBinding.writeBack` now carries:

```json
"writeBack": {
  "type": "pe-sensor",
  "provider": "localai",
  "sensorId": "localai.agx001.aquaculture.water.quality.agent.completion",
  "region": { "offset": 40, "length": 4 },
  "ttlMs": 300000,
  "normalization": "already-normalized-0-1",
  "ingest": {
    "endpoint": "/api/integrations/completions",
    "method": "POST",
    "triggerPush": false,
    "compactPush": true
  },
  "sourceMapping": {
    "id": "localai-agx001-completion",
    "sensorId": "localai.agx001.aquaculture.water.quality.agent.completion",
    "region": { "offset": 40, "length": 4 },
    "ttlMs": 300000
  }
}
```

## 6. Autonomy Staging

Every AI-capable machine declares one autonomy mode and a matching
`metadata.agentBinding.autonomyPolicy`, validated by
`schemas/autonomy-policy.schema.json`:

- `observe`: event capture only;
- `advise`: AI writes recommendations to PE;
- `supervised-act`: AI drafts or stages actions, human/governance confirms;
- `automated-act`: AI may execute an approved action with runbook and rollback.

Mode gates are enforced consistently:

- `observe`: no PE write-back; no staged or executed actions.
- `advise`: PE sensor write-back only; no staged or executed actions.
- `supervised-act`: PE sensor write-back plus staged actions; human approval
  and runbook are required; RED is blocked from direct action.
- `automated-act`: PE sensor write-back plus execution of approved operational
  actions; runbook and rollback are required; AMBER and RED are blocked.

Default stance:

- health, legal, community-services, and life-balance: `supervised-act`;
- operations domains default to `advise` unless a machine is clearly observe-only
  or clearly low-risk operational control/scheduling/optimization;
- observe-only machines use `observe`;
- low-risk infrastructure control/scheduling/optimization machines may use
  `automated-act` only with runbook, rollback, and RAG blocking.

Life-safety, legal, resident-impacting, crisis, security, compliance, or explicit
risk machines should not use `automated-act`.

Example policy:

```json
"autonomyPolicy": {
  "mode": "automated-act",
  "stage": 3,
  "writeBackType": "pe-sensor",
  "canWriteBack": true,
  "canStageActions": true,
  "canExecuteActions": true,
  "requiresHumanApproval": false,
  "requiresRunbook": true,
  "blockedWhenRag": ["AMBER", "RED"],
  "rollbackRequired": true
}
```

## 7. Agent-Ready Machine Classes

`domains/domain-registry.json` now includes an `agentReadyMachineClasses`
contract for every standard `metadata.machineClass`, validated by
`scripts/audit-corpus.py` and described by
`schemas/agent-ready-machine-class.schema.json`. A machine class is no longer
only a label; it declares its workflow stage, input/output contract, required
metadata, allowed autonomy modes, allowed write-back types, and downstream
class targets.

New domains should include these classes as a staged workflow:

1. `sensor-preaggregator` normalizes raw inputs.
2. `signal-monitor` detects current critical states.
3. `risk-forecaster` consumes predictive services from localAIStack.
4. `agent-dispatcher` routes CES outputs to agents.
5. `outcome-stabilizer` watches post-action recovery.
6. `governance-escalator` handles RED/AMBER routing.
7. `bridge` is used only when a producer output intentionally overlays another
   machine input range.

`agent-dispatcher` is the only class that requires `metadata.agentBinding`.
Machines that dispatch to localAIStack must therefore carry the first-class
agent binding, autonomy policy, trigger envelope dispatch contract, and PE
write-back policy. Non-dispatch classes can still participate in an agent-ready
workflow by producing governed CES state, forecast state, evidence state, or
post-action stabilization state for a downstream dispatcher.

This gives new domains a consistent path from live data to deterministic CES
state, to AI prediction, to governed action, and back into PE for replayable
state updates.

## 8. Contract Test Expansion

`npm run test:contracts` runs local, service-free architecture tests under
`tests/contracts`. These tests are the regression layer for the domain and
agent contracts, while the existing Playwright suites continue to cover live
service behavior.

The contract suite checks:

- `domains/domain-registry.json` has a complete agent-ready class catalog;
- every `agent-dispatcher` has first-class `metadata.agentBinding`;
- every agent binding carries the registry-equivalent autonomy policy,
  risk controls, and write-back type;
- observe agents have no write-back and non-observe agents use PE sensor
  write-back;
- dispatch-envelope and write-back payload builders preserve the machine
  contract;
- negative fixtures are rejected when `agentBinding` or autonomy policy drifts.

This makes agent readiness a testable deployment property instead of a
documentation-only convention.
