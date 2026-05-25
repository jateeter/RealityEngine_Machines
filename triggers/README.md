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

## Dispatcher responsibilities

The dispatcher (currently a template — wire it into visualizer-backend or a
local Python worker) observes machine output events from the RE WebSocket
stream (`perceptual-simulation-stepped`) and for each matched rule builds the
event payload:

```python
event = {
  "processState": {
    "id":     "RS-FLIPFLOP-TRIGGER",
    "name":   "RS Flipflop Trigger",
    "status": "warning",     # derived from ragStatusCode
  },
  "context": {
    "sourceMachine":  "RSFlipFlopTrigger",
    "sourceSequence": "rs-set-sequence",
    "outputVector":   [1, 0],
  },
}
```

Then calls the template:

```python
from examples.triggers.graphql_trigger_template import dispatch
dispatch(event)
```

`dispatch()` POSTs the mutation, raises `TriggerError` on failure, and returns
the echoed `processState`.

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
