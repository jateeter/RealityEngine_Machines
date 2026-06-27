# Patient Safety Transport Interconnect Narrative

This narrative describes the fall-detection and transportation-access example as
implemented by the machine corpus and OpenClaw machine-behavior pattern.

The governing rule for AI-augmented machine behavior is:

```text
OpenClaw agent transforms observations into that machine's native CES input vector.
PE accepts and places the vector as source state.
RE evaluates the CES deterministically.
PE composes downstream interconnect buses from deterministic machine outputs.
```

This keeps machine-specific semantic projection inside the OpenClaw agent
template behavior. PE manages source mappings, provenance, freshness, and bus
composition. RE remains unaware of bridge internals and only evaluates vector
regions.

## Corpus Participants

- `FallSensorMotionPreaggregator.json`
  - input: `[4300:4301]`
  - output: `[3813:3814]`
  - role: converts active accelerometer sample count into the motion-progression
    ordinal consumed by `FallDetection`.

- `FallDetection.json`
  - input: `[3813:3815]`
  - output: `[1941:1943]`
  - role: evaluates the fall critical-event sequence and emits fall tier plus
    confidence.

- `HomeTransportationBarrierMonitor.json`
  - input: `[1983:1987]`
  - output: `[2015:2019]`
  - role: evaluates whether transportation barriers block medical care access.

- `HomeSocialIsolationMonitor.json`
  - input: `[2011:2019]`
  - output: `[2035:2039]`
  - role: evaluates access-barrier-driven social isolation context.

- `PatientSafetyTransportInterconnect.json`
  - input: `[4310:4320]`
  - output: `[3827:3831]`
  - role: publishes the `health-personal` patient-safety transport bus for
    downstream care coordination, transportation, community-service, and
    life-balance consumers.

## OpenClaw Native Input Projection

OpenClaw agents in this workflow are input analysts. They do not decide the
machine outcome. They project observations into each target machine's native
input vector, write that vector back through PE source mapping, and allow RE to
evaluate the machine's CES.

For `FallDetection`, the OpenClaw agent writes native ordinal values:

```text
motion-progression-ordinal:
  0 = none
  1 = brief
  2 = sustained
  3 = severe

stillness-progression-ordinal:
  0 = moving
  1 = brief-still
  2 = sustained-still
  3 = very-sustained-still
```

For a confirmed fall case, the OpenClaw fall-detection input analyst writes:

```text
sourceMapping: acp-fall-detection-input-assessment
region: [3813:3815]
value: [3, 3]
```

RE then evaluates `FallDetection` and, if the deterministic sequence confirms
the condition, emits:

```text
FallDetection[1941:1943] = [4, 3]
```

That output means RED fall tier with high confidence.

For `HomeTransportationBarrierMonitor`, the OpenClaw input analyst writes the
machine-native 4D access vector:

```text
HomeTransportationBarrierMonitor[1983:1987]
= [
  appointment_attendance_norm,
  transit_access_norm,
  missed_critical_care_norm,
  proximity_norm
]
```

If RE detects critical access failure, the machine emits:

```text
HomeTransportationBarrierMonitor[2015:2019] = [1, 0, 0, 0]
```

For `HomeSocialIsolationMonitor`, OpenClaw may write the native 8D input vector
when observations are externally derived. If upstream medication and
transportation machines already provide deterministic outputs, PE may compose
the native input lane directly from those outputs. Either path must still
present a machine-native input vector to RE:

```text
HomeSocialIsolationMonitor[2011:2019]
```

The example uses the stable social-context output:

```text
HomeSocialIsolationMonitor[2035:2039] = [0, 0, 0, 1]
```

## Test Sequence Workflow

The authored test sequence in `PatientSafetyTransportInterconnect.json` models a
confirmed fall with transportation failure.

The deterministic upstream outputs are:

```text
FallDetection[1941:1943] = [4, 3]
HomeTransportationBarrierMonitor[2015:2019] = [1, 0, 0, 0]
HomeSocialIsolationMonitor[2035:2039] = [0, 0, 0, 1]
```

PE composes those outputs into the published bus input lane:

```text
PatientSafetyTransportInterconnect[4310:4320]
= [1, 0, 1, 1, 0, 0, 0, 0, 0, 1]
```

The ten positions mean:

```text
[0] fall red tier bit
[1] fall amber-high tier bit
[2] fall high-confidence bit
[3] transport critical access failure bit
[4] transport appointment barrier bit
[5] transport transit dependent risk bit
[6] transport adequate bit
[7] social severe isolation bit
[8] social isolation risk bit
[9] socially connected bit
```

RE evaluates `PatientSafetyTransportInterconnect` as an ordinary bridge
machine. The expected output is:

```text
PatientSafetyTransportInterconnect[3827:3831] = [1, 0, 0, 0]
```

That output publishes:

```text
URGENT_COORDINATED_RESPONSE
```

The `[3827:3831]` care-coordination lane fans out to downstream machines such
as:

- `HSPH132_care-coordination-resource-router.json`
- `HSPH135_care-coordination-referral-optimizer.json`
- `HSPH138_care-coordination-governance-escalator.json`
- `CSX053_homelessness-outreach-unsheltered-health-referral.json`
- `LBL046_stress-resilience-and-psychotherapy-therapy-homework-completion.json`

## Asynchronous Agent Boundary

OpenClaw dispatch is accepted without PE waiting for an indeterminate agent run.
The completion returns later as PE source state:

```text
OpenClaw accepted-no-wait dispatch
-> OpenClaw agent performs native input projection
-> completion lands through /api/integrations/completions
-> PE source mapping updates the target input region
-> RE evaluates the next available vector snapshot
```

This is the scaling pattern for future interconnection growth:

- OpenClaw performs machine-native observation-to-input projection.
- PE never owns machine-specific semantic coercion rules.
- PE owns source mapping, TTL, provenance, and bus composition.
- RE remains deterministic and bridge-agnostic.
- Published buses are expressed as corpus machines with explicit input
  composition and output fan-out regions.

## Privacy Boundary

The universal reality vector carries normalized state only. Raw observations,
clinical notes, device payloads, or other PHI-bearing source records remain in
the upstream source ledger or system of record. The published bus carries only
the compact state needed for deterministic CES evaluation and downstream
machine interconnection.
