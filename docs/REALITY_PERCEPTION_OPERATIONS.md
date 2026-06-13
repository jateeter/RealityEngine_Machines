# RealityEngine And PerceptionEngine Operations

This repository is the authoritative machine corpus for the RealityEngine
system. The runtime repositories execute the corpus. The CI repository deploys
the runtimes. The Manager repository observes and controls them.

## System Model

The integrated system has two engine roles:

- Reality Engine (RE): owns machines, evaluates CriticalEventSequences, updates
  perceptual space, emits transition results, merge batches, event-bus writes,
  governance decisions, and metrics.
- Perception Engine (PE): owns external sources, normalizes sensor/provider
  data into vectors, assembles the vector presented to RE, records source
  provenance, handles provider dispatch, and accepts provider write-back.

The engines communicate over HTTP. PE sends assembled vectors to RE through
`POST /api/perceive` or runtime-equivalent push flow. RE responds with the
result of machine processing. PE may retain the returned perceptual state as
the next persistent vector base.

## Machine Corpus Contract

Each machine JSON document declares:

- machine identity and description;
- one or more CriticalEventSequences;
- input and output perceptual mappings;
- metadata for governance, tags, agent binding, dispatch, and domain policy;
- optional input semantics and normalization hints.

The corpus is validated by:

```bash
bash scripts/validate-corpus.sh
```

Compatibility mode allows historical warnings. Strict mode is for new domains:

```bash
STRICT_DOMAIN_CONTRACT=1 bash scripts/validate-corpus.sh
```

## Perceptual Space

Perceptual space is a dense vector address space shared by all machines and PE
sources. `VECTOR_DIMENSION` is a compatibility floor, not a permanent logical
limit. Runtime implementations should grow or validate against the maximum
`offset + length` required by loaded machines and source mappings.

A machine reads from `perceptualMapping.input`:

```json
{ "offset": 4320, "length": 4 }
```

When one of its CriticalEventSequences fires, the machine writes asserted output
through `perceptualMapping.output`. Downstream machines can read that output by
declaring overlapping input regions or by using explicit compose/event-bus
metadata.

## Reality Engine Operation

RE startup:

1. Bind to the runtime-specific port from `REALITY_ENGINE_PORT`.
2. Load machine JSON from `MACHINES_DIR`, normally
   `../RealityEngine_Machines/machines`.
3. Validate JSON shape and runtime-loadable machine semantics.
4. Compute required perceptual-space dimension from machine mappings.
5. Expose health, config, runtime, machine, sequence, simulation, and metrics
   endpoints described by `SURFACE_SPEC.md`.

RE processing:

1. Receive a vector through `/api/perceive` or a simulation step.
2. Write the vector into perceptual space.
3. For each machine, extract its input region.
4. Evaluate CriticalEventSequences.
5. Apply output arbitration.
6. Merge asserted outputs in deterministic order.
7. Apply event-bus writes and latched bits.
8. Return transition results, active regions, merge batch, updated perceptual
   space, and metrics-relevant telemetry.

RE must not call external AI, HealthKit, MQTT, or ACP systems directly. Those
are PE/provider responsibilities.

## Perception Engine Operation

PE startup:

1. Bind to the runtime-specific port from `PERCEPTION_ENGINE_PORT`.
2. Resolve RE through `REALITY_ENGINE_URL` or `REALITY_ENGINE_PORT`.
3. Load source mappings from `INTEGRATIONS_CONFIG` when present.
4. Configure provider integrations such as HealthKit, CareKit, localAI, OpenAI,
   Ollama, MQTT, and ACP/OpenClaw.
5. Expose source, sensor, push, integration, dispatch, and event endpoints
   described by `SURFACE_SPEC.md`.

PE source flow:

1. Accept source data from sensors, providers, bridges, or test sources.
2. Normalize values into the mapped region.
3. Store last value, TTL, source identity, and provenance.
4. Assemble active source regions plus persistent perceptual base into a vector.
5. Push the vector to RE.
6. Record the RE response and update persistent state when the runtime contract
   requires it.

PE owns provider write-back. AI or bridge completions return to PE through
source mappings instead of writing directly into RE.

## HealthKit Bridge Operation

The native iOS bridge owns Apple HealthKit permissions, entitlements, anchored
reads, and on-device privacy handling. PE receives normalized read-only payloads
through:

```text
POST /api/integrations/healthkit/ingest
```

The current conformance families are:

| HealthKit identifier | PE sensor |
| --- | --- |
| `HKCorrelationTypeIdentifierBloodPressure` | `healthkit.blood-pressure` |
| `HKWorkoutTypeIdentifierWorkout` | `healthkit.exercise` |
| `HKCategoryTypeIdentifierSleepAnalysis` | `healthkit.sleep` |

The focused e2e must prove bridge token handling, source mapping resolution,
BP/exercise/sleep ingest, vector assembly, and downstream RE transitions.

## Dispatch And Write-Back

Machine metadata can declare dispatch rules and agent bindings. Runtime
dispatch should follow this rule:

1. RE detects a terminal machine transition and emits governance metadata in
   the merge batch.
2. PE dispatches to the configured provider without changing RE semantics.
3. Provider completion returns to PE.
4. PE writes completion values through a configured source mapping.
5. A later RE step consumes the provider completion as ordinary perceptual
   input.

This keeps provider timing, retries, provenance, and TTL in PE while preserving
RE as deterministic machine execution.

## Deployment Ports

The native runtime pairs are:

| Runtime | PE | RE |
| --- | ---: | ---: |
| Scala | `5000` | `5001` |
| CPP | `5300` | `5301` |
| LSP | `5600` | `5601` |

`3299/3300` are deprecated compatibility ports. They must not be documented as
canonical defaults.

## Operational Gates

Before a full-system deployment is accepted:

- runtime surface specs match;
- all runtimes build;
- the corpus validator reports zero hard errors;
- HealthKit BP/exercise/sleep conformance passes on all runtimes;
- Manager can read `RE_REGISTRY_URL` and switch active engines;
- multi-engine conformance runs with at least two live registered engines;
- CI deployment scripts fail visibly when a startup script or runtime is
  missing.
