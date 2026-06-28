# Transportation TFX-111-120 Interconnect Narrative

This narrative applies the PE-owned published-bus pattern to `Transportation TFX-111-120` in the
`transportation` domain. OpenClaw and localAIStack/Ollama remain PE-side translators
and resolvers. RE evaluates only ordinary vector state.

Focus: Transportation TFX-111-120.

## Published Bus

```text
transportation.tfx-111-120
published-bus-transportation-tfx-111-120
```

Input lane: `[16374:16404]`

```text
[0] Transportation Fleet Network Planning Stop Demand Forecast active output[0] bit
[1] Transportation Fleet Network Planning Stop Demand Forecast active output[1] bit
[2] Transportation Fleet Network Planning Stop Demand Forecast active output[2] bit
[3] Transportation Fleet Network Planning Route Runtime Calibration active output[0] bit
[4] Transportation Fleet Network Planning Route Runtime Calibration active output[1] bit
[5] Transportation Fleet Network Planning Route Runtime Calibration active output[2] bit
[6] Transportation Fleet Network Planning Stop Spacing Review active output[0] bit
[7] Transportation Fleet Network Planning Stop Spacing Review active output[1] bit
[8] Transportation Fleet Network Planning Stop Spacing Review active output[2] bit
[9] Transportation Fleet Network Planning Service Span Optimization active output[0] bit
[10] Transportation Fleet Network Planning Service Span Optimization active output[1] bit
[11] Transportation Fleet Network Planning Service Span Optimization active output[2] bit
[12] Transportation Fleet Network Planning Frequency Optimization active output[0] bit
[13] Transportation Fleet Network Planning Frequency Optimization active output[1] bit
[14] Transportation Fleet Network Planning Frequency Optimization active output[2] bit
[15] Transportation Fleet Network Planning Bus Priority Signal Monitor active output[0] bit
[16] Transportation Fleet Network Planning Bus Priority Signal Monitor active output[1] bit
[17] Transportation Fleet Network Planning Bus Priority Signal Monitor active output[2] bit
[18] Transportation Fleet Network Planning Bus Lane Reliability active output[0] bit
[19] Transportation Fleet Network Planning Bus Lane Reliability active output[1] bit
[20] Transportation Fleet Network Planning Bus Lane Reliability active output[2] bit
[21] Transportation Fleet Network Planning Construction Impact Planner active output[0] bit
[22] Transportation Fleet Network Planning Construction Impact Planner active output[1] bit
[23] Transportation Fleet Network Planning Construction Impact Planner active output[2] bit
[24] Transportation Fleet Network Planning Ridership Recovery Monitor active output[0] bit
[25] Transportation Fleet Network Planning Ridership Recovery Monitor active output[1] bit
[26] Transportation Fleet Network Planning Ridership Recovery Monitor active output[2] bit
[27] Transportation Fleet Network Planning Planning Executive Scenario active output[0] bit
[28] Transportation Fleet Network Planning Planning Executive Scenario active output[1] bit
[29] Transportation Fleet Network Planning Planning Executive Scenario active output[2] bit
```

Output lane: `[16404:16408]`

```text
[0] domain family review bit
[1] domain family optimization bit
[2] domain family monitoring bit
[3] domain family stable bit
```

Source machines publish active output lanes into this family bus. Stable source
states remain represented by no active PE-composed bits.

## Example Workflow: Transportation TFX-111-120 domain family review

PE composes:

```text
Transportation TFX-111-120 Interconnect[16374:16404]
= [1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
```

RE emits:

```text
Transportation TFX-111-120 Interconnect[16404:16408]
= [1, 0, 0, 0]
```

## Example Workflow: Transportation TFX-111-120 domain family optimization

PE composes:

```text
Transportation TFX-111-120 Interconnect[16374:16404]
= [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
```

RE emits:

```text
Transportation TFX-111-120 Interconnect[16404:16408]
= [0, 1, 0, 0]
```

## Example Workflow: Transportation TFX-111-120 domain family monitoring

PE composes:

```text
Transportation TFX-111-120 Interconnect[16374:16404]
= [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]
```

RE emits:

```text
Transportation TFX-111-120 Interconnect[16404:16408]
= [0, 0, 1, 0]
```

## Message Flow

```mermaid
sequenceDiagram
  participant Source as Domain Sources
  participant OC as OpenClaw Input Analysts
  participant PE as Perception Engine
  participant RE as Reality Engine
  participant BUS as Transportation TFX-111-120 Interconnect
  participant LAI as localAIStack / Ollama
  participant Downstream as Lane Scoped Consumers

  Source->>OC: observations and source events
  OC-->>PE: accepted-no-wait native input completions
  PE->>RE: next vector snapshot includes source inputs
  RE-->>PE: source machine outputs
  PE->>PE: compose compact family bus input lane
  PE->>RE: write bus input [16374:16404]
  RE-->>PE: bus output [16404:16408]
  PE-->>LAI: accepted-no-wait resolver dispatch
  LAI-->>PE: resolver completion as configured source mapping
  PE-->>Downstream: lane-scoped fan-out, no PE cycle wait
```

## Problems And Extensions

1. This pass records an explicit family-level published-bus contract for every
   source machine in this remaining-domain family.

2. RE visibility remains limited to compact vector lanes. PE owns source
   provenance, transformation, resolver dispatch, and completion ingestion.

3. Future growth can add domain super-buses that consume family bridge outputs
   rather than reading every source machine directly.

## Safety Boundary

The PE-visible workflow carries normalized status bits only. Raw regulated data
and provider-specific records stay upstream. Resolver completions return through
PE as configured source mappings.
