# Generic reference microgrids and authority

EI03 implementation: [issue #267](https://github.com/jateeter/RealityEngine_Machines/issues/267). The machine-readable source is [reference-microgrids.json](../../examples/reference-microgrids.json).

This is a reference-scope specification. It defines three generic scenarios, functional asset roles, topology connections, operating authority and standards applicability. It implements no simulator, controller, adapter or normative asset-template library and executes none of the 43 behavioral acceptance cases.

## Three scenarios cover the acceptance surface

| Scenario | Purpose | Operating modes and representative cases |
|---|---|---|
| REF01_CONNECTED | Connected community microgrid with PV, storage, critical/flexible loads, measurement/time, threat and carbon peers | Connected dispatch, degraded observability and recovery; data quality, security, carbon, model/RAG and source qualification |
| REF02_ISLAND_RESTORE | Islandable critical-service microgrid with grid-forming storage and independent modeled protection | Planned/unplanned island transitions, islanded operation, black start, resynchronization and recovery; AC02–AC05, AC18, AC25 and AC43 |
| REF03_FLEX_EV | Connected flexible load, EV/EVSE, demand-response and market-context cohort | Smart charging and priority/cancel semantics, aggregate feasibility, carbon-aware flexibility and protocol qualification; no real market settlement |

All 43 cases have at least one applicable scenario. Case-to-scenario membership is a scope map, not an execution result. Preliminary device and electrical models still need implementation before EI16/EI17 can run; EI18 must close complete simulated-required-hardware coverage afterward.

The connectivity graphs describe named upstream, transformer, PCC, local bus, generation, storage and load connections. They are not solved power-flow, protection or fast-transient models. Protection, metering, clocks and supervisory roles remain explicit even when their informational connections are not power-carrying edges.

## Generic parameters are assumptions, not standards claims

The scenarios use a chosen nominal 480 V line-to-line RMS, 60 Hz local reference. These values make a generic US-oriented scenario concrete; they are not asserted to be universal requirements or validated settings. The schema carries their units and `CHOSEN_GENERIC_REFERENCE_NOT_NORMATIVE_LIMIT` basis.

EI06 must supply reviewed reference envelopes for voltage/frequency/angle, switching, clock holdover, reserve, ramp, thermal, retry and completion tolerances before behavioral execution. EI05 must pin protocol editions, options and actual software peers. No customer-site record, physical procurement, utility permission or OEM certificate is required to define or accept these generic scenarios.

## Functional roles precede standards-class templates

The 19 functional asset roles cover electrical/hardware roles and actual software/peer roles. Electrical/hardware dependencies require simulated counterparts. Controllers, adapters, cryptography, models and admission software must execute genuinely; generic peer data does not authorize replacing real software assertions with invented receipts.

These role labels are not an authoritative IEC/CIM/SunSpec taxonomy. EI04 must enumerate each asset class defined by the associated applicable standards, preserve cross-standard distinctions, and map every such class to its required reusable template. No completeness of that future class inventory is claimed here.

## Authority remains explicit

Nine roles separate generic utility/operator/risk actors, independent modeled protection, actual dispatch/model/cyber software and authentic repository assurance/admission/release reviewers. No individual is falsely assigned.

Generic utility permission in an isolated scenario cannot override modeled synch-check or protection. Models may retrieve and propose; they cannot hold actuator credentials, write vectors directly, accept residual risk or approve their own actions. Execution checks remain EI10/EI11 deliverables.

Generic operating-role approvals support scenario tests. Real repository review, exact-source native quorum, official admission and release receipts require authentic identities and actual evidence; they cannot be replaced by generic human-role fixtures or TEST_ONLY workflow rehearsals.

## Standards applicability and exclusions

Every one of the 46 inventory entries has a disposition and rationale in the reference JSON. Shared design/security/AI/carbon guidance is tailored, not blanket law. Wire options, native peer choices and protocol profiles remain EI05 decisions. DNP3 is an explicit alternative, station/IED profiles are cohort-dependent, and DR/EV/market information applies to REF03. PMU services are excluded from this baseline pending an explicit reviewed extension. Physical equipment/AHJ certification and real market settlement are separate from corpus acceptance.

## Verify scope consistency

From the factory package:

```bash
python3 tools/verify_reference_scope.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tools -p 'test_reference_scope.py'
```

Checks cover unknown/duplicate roles, topology references, full case/standard coverage, protected authority boundaries, genuine-software versus simulated-hardware representation, parameter provenance and absence of fabricated execution. These checks do not evaluate the physics or run an acceptance case.
