# Upstream triggers — machines → local AI

When a Reality Engine machine asserts an output, it can emit a **trigger**
that pushes contextualised information upstream into the local AI stack.  This
is the reverse direction of the regular perception flow: instead of the local
AI feeding sensors into the Reality Engine, a machine's output becomes new
context the local AI observes.

## Shape of the trigger

Every trigger is a GraphQL mutation against `localAIStack`'s `/graphql`
endpoint.  The schema lives in
`localAIStack/services/api/routers/graphql_endpoint.py`.

```graphql
mutation UpdateProcessState($input: UpdateProcessStateInput!) {
  updateProcessState(input: $input) {
    processState {
      id name status
      ragStatus { code description }
    }
  }
}
```

`ragStatusCode` is an enum — `GREEN`, `AMBER`, `RED`.  The Reality Engine
picks the code from the machine's current output (see `triggerConfig` below)
and the receiver attaches a human-readable description.

## Wiring a machine

Add a `triggerConfig` block to the machine's `metadata` in its JSON file.
Each entry maps a sequence's output vector to a RAG code:

```json
"triggerConfig": {
  "endpoint": "http://localhost:4000/graphql",
  "template": "examples/triggers/graphql_trigger_template.py",
  "rules": [
    {
      "sequenceId":    "rs-set-sequence",
      "outputMatches": [1, 0],
      "ragStatusCode": "AMBER",
      "processName":   "RS Flipflop Trigger"
    },
    {
      "sequenceId":    "rs-reset-sequence",
      "outputMatches": [0, 1],
      "ragStatusCode": "GREEN",
      "processName":   "RS Flipflop Trigger"
    }
  ]
}
```

See `examples/machines/RSFlipFlopTrigger.json` for a minimal working example.

AI-capable machines must add `metadata.agentBinding`; legacy
`dispatchableAgent`, `agentActions`, and `aiTrigger` may remain as
compatibility aliases, but `dispatchableAgent` without `agentBinding` fails
corpus validation. `agentBinding` is the first-class contract validated by
`schemas/agent-binding.schema.json`:

```json
"agentBinding": {
  "agent": "care_coordinator_agent",
  "mode": "supervised-act",
  "trigger": "care-gap-risk",
  "allowedActions": [
    "Summarize current risk state.",
    "Draft a care coordination plan."
  ],
  "writeBack": {
    "type": "pe-sensor",
    "sensorId": "localai.care_gap_prediction",
    "region": { "offset": 2100, "length": 4 },
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

### In-home wellness machines

Five health & wellness workflows ship with trigger configuration pre-wired.
Each sends `processName` + sequence metadata (including `ragStatusCode`,
`processStatus`, and a human-readable description) to the local AI on every
output assertion, so the AI can correlate signals across the cohort:

| Machine file | Workflow | Sequences (GREEN / AMBER / RED) |
|---|---|---|
| `MedicationAdherenceMonitor.json` | scheduled-dose compliance | on-time → delayed → missed |
| `FallDetection.json`              | motion-anomaly classification | nominal → near-fall → impact |
| `SleepQualityMonitor.json`        | nightly sleep pattern | restful → disturbed → poor |
| `HydrationMonitor.json`           | intake-proxy tracking | adequate → low → critical |
| `DailyActivityMonitor.json`       | movement vs 7-day baseline | active → sedentary → prolonged-inactivity |

All five are in the `healthservices` domain (metadata.category=`healthcare`,
metadata.domain=`wellness`) so they cluster in a single hull bubble in all
three visualizations.  Perceptual offsets 74–93 are reserved for them; the
block is contiguous so the whole group can be watched as a single region.

### Startup loading

Machines are loaded by `scala/src/main/scala/com/realityengine/api/Routes.scala`
via directory auto-discovery — every `*.json` in `examples/machines/` gets
loaded at engine startup with no allowlist to edit.  Adding a new machine JSON
and restarting Reality Engine (`./startUniverse.sh` or `./startUniverse.sh
--fresh` to rebuild without cache) is sufficient.

## Canonical RE to localAIStack Dispatch

The dispatcher observes terminal CES output events from RE/PE, resolves the
matching `metadata.triggerConfig.rules[]` entry, and emits the canonical
`ces.terminal.event` envelope defined by:

- `triggers/ai_trigger_envelope.template.json`
- `schemas/ai-trigger-envelope.schema.json`

Every agent-bound machine has this dispatch contract in
`metadata.triggerConfig`:

```json
"endpoint": "http://localhost:4000/graphql",
"template": "triggers/graphql_trigger_template.py",
"dispatch": {
  "target": "localAIStack",
  "transport": "graphql",
  "mutation": "updateProcessState",
  "envelopeSchema": "schemas/ai-trigger-envelope.schema.json",
  "schemaRef": "localAIStack/services/api/routers/graphql_endpoint.py"
}
```

The GraphQL template accepts both the canonical envelope and the older
`processState/context` shape. Runtime dispatch should use the canonical
envelope:

```python
from triggers.graphql_trigger_template import dispatch

dispatch(envelope)
```

`dispatch()` POSTs the mutation, raises `TriggerError` on failure, and returns
the echoed `processState`.

To inspect the canonical envelope shape for a machine:

```bash
npm run dispatch-envelope:example
```

## localAIStack to PE Write-Back

Agent completions return through PE, not directly into RE. Non-observe
`metadata.agentBinding.writeBack` blocks use `type: "pe-sensor"` and target the
provider-neutral PE completion endpoint:

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
  }
}
```

The completion payload shape is captured in
`schemas/localai-completion-writeback.schema.json`.

To inspect a PE completion-ingest payload for a machine:

```bash
npm run writeback-payload:example
```

## Agent Autonomy

`metadata.agentBinding.mode` uses the four-mode autonomy policy:

| Mode | Write-back | Stage actions | Execute actions | Required gates |
|---|---:|---:|---:|---|
| `observe` | no | no | no | none |
| `advise` | PE sensor | no | no | none |
| `supervised-act` | PE sensor | yes | no | human approval, runbook, RED block |
| `automated-act` | PE sensor | yes | yes | runbook, rollback, AMBER/RED block |

Each binding carries `autonomyPolicy` plus matching `riskControls`; corpus
validation fails when the mode, policy, write-back type, or RAG blocks drift.

## Manual test

1. Start `localAIStack` (GraphQL endpoint comes up at `http://localhost:4000/graphql`).
2. Load `RSFlipFlopTrigger` in the Reality Engine (via Tobias → Sequences).
3. Push a SET input (`[1, 0]`) at the machine's input offset.
4. Trigger the dispatcher (or simulate it from a shell):

   ```bash
   python examples/triggers/graphql_trigger_template.py
   ```

5. Inspect the events ring buffer:

   ```bash
   curl -s http://localhost:4000/graphql/events | jq
   ```

   You should see an entry whose `rag_status_code` matches the machine's
   configured code for that sequence.
