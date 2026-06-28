# Energy Resilient Community Microgrid Machine Formulation

Status: design note for future corpus expansion
Domain: energy
Primary pattern: PE-owned source aggregation, RE-visible CES vector state, OpenClaw/localAIStack/Ollama as asynchronous PE-side translators and resolvers

## Purpose

This note formulates the Energy-domain machines and CES contracts needed to operate a resilient community microgrid supporting critical civic infrastructure. The primary served users are schools, transportation services, AI data centers, communications, lighting, heating, and cooking. The local asset base is storage, generation, and transmission/distribution infrastructure. The operational target is stable islandable power with supply-chain-aware logistics and standard Smart Grid interconnection control.

The current corpus already contains the local asset layer: ENX001-ENX160 cover rooftop/carport/community/school/ground-mount solar, inverter banks, string combiners, wash crews, battery containers, BMS, thermal/fire safety, state-of-charge reserve, point of common coupling, feeder sectionalizers, community load flexibility, EV charging, backup panels, weather/irradiance, and preventive maintenance work orders. This design adds a service and operating layer above those assets.

## Design Principle

RE should see only normalized vector state and deterministic CES transitions. PE owns the practical interconnection work: protocol adapters, telemetry normalization, OpenClaw input projection, localAIStack/Ollama resolver dispatch, completion ingestion, and machine interconnection composition.

Normal behavior remains dispatch-without-wait. PE cycles must never block on an indeterminate OpenClaw, Ollama, DERMS, utility, or field-workflow completion.

## Existing Energy Foundation

The merged corpus has:

- 160 nested `machines/domains/energy/ENX*.json` source machines.
- 16 Energy interconnect bridge buses, one per ENX ten-machine family.
- 176 current Energy machines in the manifest after bridge addition.
- OpenClaw projection contracts for each ENX source machine.
- LocalAI/Ollama resolver contracts on the Energy bridge buses.

The existing ENX families are asset-operational. They should remain the source-of-truth machine layer for local device, DER, and maintenance signals.

## Proposed Service-Level Machine Families

The next Energy expansion should add a service-oriented layer. These machines consume existing Energy bridge outputs plus selected cross-domain service buses from schools, transportation, AI services/data-center, communications, built-space, and community services.

### 1. Community Critical Load Priority Controller

Purpose: classify and rank served loads across schools, transportation, AI data centers, communications, lighting, heating, and cooking.

Input CES dimensions:

```text
[0] school critical load demand active
[1] transportation charging or dispatch load active
[2] AI data center compute load active
[3] communications continuity load active
[4] public lighting safety load active
[5] heating demand active
[6] cooking/food resilience demand active
[7] medical/community shelter load active
[8] curtailment tolerance available
[9] human-safety override active
```

Output CES:

```text
[1,0,0,0] LOAD_SHED_BLOCKED_HUMAN_SAFETY
[0,1,0,0] PRIORITIZE_CRITICAL_SERVICES
[0,0,1,0] FLEXIBLE_LOAD_AVAILABLE
[0,0,0,1] LOAD_PRIORITY_STABLE
```

Primary consumers: dispatch controller, islanding coordinator, demand response planner, governance escalator.

### 2. Islanding Readiness Coordinator

Purpose: decide whether the microgrid can separate from or reconnect to the utility grid.

Input CES dimensions:

```text
[0] PCC instability or utility outage indicated
[1] feeder sectionalizer route available
[2] inverter grid-forming capability available
[3] storage reserve above island threshold
[4] black-start sequence available
[5] frequency/voltage stability acceptable
[6] protection settings synchronized
[7] resynchronization window available
```

Output CES:

```text
[1,0,0,0] ISLAND_NOW
[0,1,0,0] PREPARE_ISLANDING
[0,0,1,0] RECONNECT_READY
[0,0,0,1] GRID_CONNECTED_STABLE
```

Smart Grid interfaces: IEEE 1547, IEEE 2030.5, IEC 61850, DNP3, Modbus, SCADA/DERMS API.

### 3. Storage Reserve And Dispatch Optimizer

Purpose: coordinate battery state-of-charge, thermal constraints, fire safety, discharge rate, charge windows, and reserve requirements.

Input CES dimensions:

```text
[0] state-of-charge below reserve floor
[1] available discharge capacity sufficient
[2] battery thermal limit active
[3] BMS cell imbalance active
[4] fire safety loop impaired
[5] solar charge surplus available
[6] critical load forecast rising
[7] market/utility dispatch signal active
```

Output CES:

```text
[1,0,0,0] PROTECT_STORAGE_ASSET
[0,1,0,0] DISPATCH_STORAGE
[0,0,1,0] CHARGE_STORAGE
[0,0,0,1] RESERVE_STABLE
```

Primary consumers: islanding coordinator, load priority controller, DER dispatch agent, maintenance scheduler.

### 4. Distributed Generation Commitment Planner

Purpose: combine solar, inverter, weather, and backup generation into a committed generation plan.

Input CES dimensions:

```text
[0] rooftop solar available
[1] carport solar available
[2] school campus solar available
[3] community center solar available
[4] ground-mount solar available
[5] inverter bank healthy
[6] irradiance forecast favorable
[7] backup generation available
[8] generation maintenance restriction active
[9] power quality limit active
```

Output CES:

```text
[1,0,0,0] GENERATION_CONSTRAINED
[0,1,0,0] COMMIT_LOCAL_GENERATION
[0,0,1,0] USE_BACKUP_GENERATION
[0,0,0,1] GENERATION_STABLE
```

Primary consumers: storage optimizer, islanding coordinator, load priority controller.

### 5. Feeder And Transmission Path Manager

Purpose: reason over local transmission/distribution path availability and protection posture.

Input CES dimensions:

```text
[0] feeder sectionalizer available
[1] feeder power quality within band
[2] route capacity sufficient
[3] fault isolation active
[4] switching operation pending
[5] protection coordination valid
[6] communications to field device healthy
[7] alternate path available
```

Output CES:

```text
[1,0,0,0] ISOLATE_FAULT
[0,1,0,0] SWITCH_FEEDER_PATH
[0,0,1,0] ROUTE_CAPACITY_LIMITED
[0,0,0,1] PATH_STABLE
```

Smart Grid interfaces: IEC 61850 GOOSE/MMS, DNP3, Modbus TCP, utility SCADA, IEEE C37 protection event feeds.

### 6. Community Service Continuity Monitor

Purpose: convert energy state into user-facing service continuity posture.

Input CES dimensions:

```text
[0] schools below continuity threshold
[1] transportation below continuity threshold
[2] AI data center below continuity threshold
[3] communications below continuity threshold
[4] lighting below continuity threshold
[5] heating below continuity threshold
[6] cooking/food service below continuity threshold
[7] shelter/community service below continuity threshold
[8] service recovery action active
```

Output CES:

```text
[1,0,0,0] CRITICAL_SERVICE_INTERRUPTION
[0,1,0,0] SERVICE_DEGRADATION
[0,0,1,0] RECOVERY_IN_PROGRESS
[0,0,0,1] SERVICES_STABLE
```

Primary consumers: governance escalator, community notification, supply logistics, OpenClaw service resolution agent.

### 7. Energy Supply Chain Logistics Coordinator

Purpose: manage logistics required to keep generation, storage, transmission, and critical services operating.

Input CES dimensions:

```text
[0] spare inverter parts below threshold
[1] battery service parts below threshold
[2] generator fuel or alternate energy supply constrained
[3] field crew unavailable
[4] EV/mobile battery asset unavailable
[5] food/heating/cooking fuel support constrained
[6] communications repair part constrained
[7] mutual aid vendor capacity available
[8] procurement lead time exceeds resilience window
[9] work order backlog active
```

Output CES:

```text
[1,0,0,0] LOGISTICS_BLOCKING_RESILIENCE
[0,1,0,0] EXPEDITE_SUPPLY_CHAIN
[0,0,1,0] SCHEDULE_FIELD_CREW
[0,0,0,1] LOGISTICS_STABLE
```

Primary consumers: preventive maintenance work order machines, governance escalator, community service continuity monitor.

### 8. Smart Grid Protocol Adapter Health Monitor

Purpose: make protocol readiness a first-class PE source without leaking protocol implementation into RE.

Input CES dimensions:

```text
[0] IEEE 2030.5 DER control available
[1] IEEE 1547 telemetry/control available
[2] OpenADR signal available
[3] IEC 61850 substation/feeders available
[4] DNP3 SCADA available
[5] Modbus/OPC UA device bridge available
[6] OCPP EV charging control available
[7] MQTT event mirror available
[8] protocol auth/cert valid
[9] command acknowledgement latency acceptable
```

Output CES:

```text
[1,0,0,0] PROTOCOL_CONTROL_UNAVAILABLE
[0,1,0,0] DEGRADED_PROTOCOL_PATH
[0,0,1,0] FALLBACK_PROTOCOL_ACTIVE
[0,0,0,1] PROTOCOLS_STABLE
```

Primary consumers: islanding coordinator, feeder manager, DER dispatch planner, OpenClaw/Ollama resolver dispatch.

### 9. Microgrid Cyber Safety Gate

Purpose: gate energy actuation when command integrity, identity, or communications posture is unsafe.

Input CES dimensions:

```text
[0] protocol identity invalid
[1] command replay risk active
[2] DER command outside approved envelope
[3] SCADA/DERMS anomaly active
[4] operator approval missing
[5] rollback path unavailable
[6] firmware/config drift active
[7] emergency override active
```

Output CES:

```text
[1,0,0,0] BLOCK_ACTUATION
[0,1,0,0] REQUIRE_HUMAN_APPROVAL
[0,0,1,0] ALLOW_LIMITED_COMMANDS
[0,0,0,1] CYBER_SAFE
```

Machine class: safety-compliance-checker.

### 10. Resilient Community Microgrid Command Center

Purpose: aggregate the above service-layer machines into a single published domain bus for community microgrid operations.

Input CES dimensions:

```text
[0] critical load priority urgent/review bit
[1] islanding readiness urgent/review bit
[2] storage reserve urgent/review bit
[3] generation commitment urgent/review bit
[4] feeder path urgent/review bit
[5] service continuity urgent/review bit
[6] supply chain logistics urgent/review bit
[7] protocol adapter urgent/review bit
[8] cyber safety urgent/review bit
[9] cross-domain human-safety override bit
```

Output CES:

```text
[1,0,0,0] MICROGRID_EMERGENCY_RESPONSE
[0,1,0,0] MICROGRID_OPTIMIZATION_REQUIRED
[0,0,1,0] MICROGRID_MONITORING_REQUIRED
[0,0,0,1] MICROGRID_STABLE
```

This command center should be a published bus, not an agent-dispatcher. localAIStack/Ollama resolution should be attached as a `localAIResolver`, and completion should return through PE configured source mappings.

## Proposed Machine Class Mapping

```text
signal-monitor:
  Community Service Continuity Monitor
  Smart Grid Protocol Adapter Health Monitor

risk-forecaster:
  Distributed Generation Commitment Planner
  Storage Reserve And Dispatch Optimizer

optimizer:
  Community Critical Load Priority Controller
  Energy Supply Chain Logistics Coordinator

safety-compliance-checker:
  Microgrid Cyber Safety Gate
  Islanding Readiness Coordinator, if actuation gating is included

bridge:
  Resilient Community Microgrid Command Center
  Optional service-specific published buses

agent-dispatcher:
  Only for explicit localAI/Ollama action dispatch surfaces where direct agent binding is required.
```

## Smart Grid Interface Contract

The operational interface should be PE-owned and startup-configured. RE should see protocol readiness and command acknowledgement only as vector state.

Recommended protocol adapter source groups:

```text
ieee2030_5_der_control
ieee1547_interconnection_status
openadr_event_signal
iec61850_feeder_substation_state
dnp3_scada_point_state
modbus_opcua_device_state
ocpp_ev_charger_state
mqtt_grid_event_mirror
protocol_identity_cert_status
command_acknowledgement_latency
```

Required PE behavior:

- Register each protocol adapter as a source at startup.
- Normalize protocol telemetry into bounded vector lanes.
- Dispatch command intents asynchronously.
- Ingest acknowledgements and completions as PE sources.
- Preserve audit metadata outside the universal reality vector.
- Never wait in PE cycles for command completion, field confirmation, OpenClaw, Ollama, DERMS, SCADA, or utility response.

## OpenClaw And Ollama Roles

OpenClaw should perform ordinal and native-input mapping from operational narratives into machine input vectors. It should not own dispatch ordering or RE-visible truth.

Ollama/localAIStack should resolve ambiguous operational states, summarize cross-domain context, select handoff templates, and propose dispatch payloads. It should not bypass PE source mappings.

Canonical loop:

```text
External grid/field/user systems -> PE source adapters
PE source adapters -> OpenClaw native input projection
PE writes machine input source values
RE evaluates CES transitions
PE composes service/domain buses from RE outputs
PE dispatches resolver intent to localAIStack/Ollama accepted-no-wait
Ollama/localAIStack returns completion through PE source mapping
RE sees completion only as ordinary source/vector state on a later cycle
```

## Initial Test Workflows

### Workflow A: School Islanding And Shelter Continuity

1. Utility instability and communications risk arrive through protocol sources.
2. School load and shelter load assert critical priority.
3. Storage reserve is sufficient and feeder route is available.
4. Islanding Readiness Coordinator emits `PREPARE_ISLANDING`, then `ISLAND_NOW`.
5. Command Center emits `MICROGRID_EMERGENCY_RESPONSE`.
6. localAIStack/Ollama receives resolver dispatch and returns an accepted completion as PE source mapping.
7. Community Service Continuity Monitor transitions to `RECOVERY_IN_PROGRESS` or `SERVICES_STABLE`.

### Workflow B: AI Data Center Load Shedding With Communications Protection

1. AI data center load rises while storage reserve falls.
2. Communications continuity asserts human-safety priority.
3. Critical Load Priority Controller emits `PRIORITIZE_CRITICAL_SERVICES`.
4. Storage Optimizer emits `PROTECT_STORAGE_ASSET`.
5. Cyber Safety Gate blocks non-approved curtailment commands until policy approval is present.
6. Command Center emits `MICROGRID_OPTIMIZATION_REQUIRED`.

### Workflow C: Transportation Charging And Cooking Resilience Logistics

1. EV charging depot and community cooking/heating demands overlap.
2. Supply Chain Logistics Coordinator detects field crew and fuel/parts constraint.
3. Generation Planner commits local solar/backup generation.
4. Storage Optimizer schedules charge/discharge windows.
5. Command Center emits `MICROGRID_MONITORING_REQUIRED` or `MICROGRID_OPTIMIZATION_REQUIRED`.

### Workflow D: Smart Grid Protocol Degradation Fallback

1. IEEE 2030.5 control is unavailable but DNP3 and MQTT mirror remain healthy.
2. Protocol Adapter Health Monitor emits `FALLBACK_PROTOCOL_ACTIVE`.
3. Cyber Safety Gate emits `ALLOW_LIMITED_COMMANDS` only if identity and rollback are valid.
4. Islanding and feeder commands route through allowed fallback source mappings.

## Machine JSON Implementation Notes

- Allocate service-layer lanes above the current Energy bridge range. Current generated Energy bridge buses end at approximately `16510`; reserve a new band after that for community microgrid service-level machines.
- Preserve existing ENX001-ENX160 asset machines; do not rewrite their meanings.
- Add a small set of service machines first, then add a command-center published bus.
- Use `metadata.openClawProjection` for every new source/service machine with native input semantics.
- Use `metadata.publishedDomainBus.localAIResolver` on the command-center bus.
- Add `inputSequences` for all four output states of each new service machine.
- Add contract tests that exercise PE composition into the command-center bus and resolver completion write-back.

## Suggested First Coding Pass

1. Add 10 service-layer machine JSON files under `machines/domains/energy/` with a new ENX2xx code range.
2. Add `EnergyCommunityMicrogridCommandCenterInterconnect.json` as the published service-level bus.
3. Add a narrative doc parallel to the existing interconnect narratives.
4. Add a contract test for the command center and at least two workflow input sequences.
5. Update domain manifest count.
6. Run `npm run validate`, `npm run validate:strict`, and `npm run test:contracts`.
