# Legal Services LSX-021-030 Interconnect Narrative

This narrative applies the PE-owned published-bus pattern to `Legal Services LSX-021-030` in the
`legal-services` domain. OpenClaw and localAIStack/Ollama remain PE-side translators
and resolvers. RE evaluates only ordinary vector state.

Focus: Legal Services LSX-021-030.

## Published Bus

```text
legal-services.lsx-021-030
published-bus-legal-services-lsx-021-030
```

Input lane: `[15728:15758]`

```text
[0] Legal Services Copyright Workflow Work Type Classification active output[0] bit
[1] Legal Services Copyright Workflow Work Type Classification active output[1] bit
[2] Legal Services Copyright Workflow Work Type Classification active output[2] bit
[3] Legal Services Copyright Workflow Authorship And Work Made For Hire active output[0] bit
[4] Legal Services Copyright Workflow Authorship And Work Made For Hire active output[1] bit
[5] Legal Services Copyright Workflow Authorship And Work Made For Hire active output[2] bit
[6] Legal Services Copyright Workflow Publication Status Review active output[0] bit
[7] Legal Services Copyright Workflow Publication Status Review active output[1] bit
[8] Legal Services Copyright Workflow Publication Status Review active output[2] bit
[9] Legal Services Copyright Workflow Deposit Material Preparation active output[0] bit
[10] Legal Services Copyright Workflow Deposit Material Preparation active output[1] bit
[11] Legal Services Copyright Workflow Deposit Material Preparation active output[2] bit
[12] Legal Services Copyright Workflow Software Source Code Deposit active output[0] bit
[13] Legal Services Copyright Workflow Software Source Code Deposit active output[1] bit
[14] Legal Services Copyright Workflow Software Source Code Deposit active output[2] bit
[15] Legal Services Copyright Workflow Group Registration Eligibility active output[0] bit
[16] Legal Services Copyright Workflow Group Registration Eligibility active output[1] bit
[17] Legal Services Copyright Workflow Group Registration Eligibility active output[2] bit
[18] Legal Services Copyright Workflow Preregistration Eligibility active output[0] bit
[19] Legal Services Copyright Workflow Preregistration Eligibility active output[1] bit
[20] Legal Services Copyright Workflow Preregistration Eligibility active output[2] bit
[21] Legal Services Copyright Workflow eCO Application Assembly active output[0] bit
[22] Legal Services Copyright Workflow eCO Application Assembly active output[1] bit
[23] Legal Services Copyright Workflow eCO Application Assembly active output[2] bit
[24] Legal Services Copyright Workflow Certificate And Record Docket active output[0] bit
[25] Legal Services Copyright Workflow Certificate And Record Docket active output[1] bit
[26] Legal Services Copyright Workflow Certificate And Record Docket active output[2] bit
[27] Legal Services Copyright Workflow Recordation And Transfer active output[0] bit
[28] Legal Services Copyright Workflow Recordation And Transfer active output[1] bit
[29] Legal Services Copyright Workflow Recordation And Transfer active output[2] bit
```

Output lane: `[15758:15762]`

```text
[0] domain family review bit
[1] domain family optimization bit
[2] domain family monitoring bit
[3] domain family stable bit
```

Source machines publish active output lanes into this family bus. Stable source
states remain represented by no active PE-composed bits.

## Example Workflow: Legal Services LSX-021-030 domain family review

PE composes:

```text
Legal Services LSX-021-030 Interconnect[15728:15758]
= [1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
```

RE emits:

```text
Legal Services LSX-021-030 Interconnect[15758:15762]
= [1, 0, 0, 0]
```

## Example Workflow: Legal Services LSX-021-030 domain family optimization

PE composes:

```text
Legal Services LSX-021-030 Interconnect[15728:15758]
= [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
```

RE emits:

```text
Legal Services LSX-021-030 Interconnect[15758:15762]
= [0, 1, 0, 0]
```

## Example Workflow: Legal Services LSX-021-030 domain family monitoring

PE composes:

```text
Legal Services LSX-021-030 Interconnect[15728:15758]
= [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]
```

RE emits:

```text
Legal Services LSX-021-030 Interconnect[15758:15762]
= [0, 0, 1, 0]
```

## Message Flow

```mermaid
sequenceDiagram
  participant Source as Domain Sources
  participant OC as OpenClaw Input Analysts
  participant PE as Perception Engine
  participant RE as Reality Engine
  participant BUS as Legal Services LSX-021-030 Interconnect
  participant LAI as localAIStack / Ollama
  participant Downstream as Lane Scoped Consumers

  Source->>OC: observations and source events
  OC-->>PE: accepted-no-wait native input completions
  PE->>RE: next vector snapshot includes source inputs
  RE-->>PE: source machine outputs
  PE->>PE: compose compact family bus input lane
  PE->>RE: write bus input [15728:15758]
  RE-->>PE: bus output [15758:15762]
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
