# Logical observation age without invented plant evolution

Storage component 0.6.0 separates explicit evaluation-clock advance from its
existing held-interval plant clock. `advanceEvaluationClock(deltaMs)` increases
the logical evaluator offset and state revision, without advancing the plant
timestamp, battery energy or cumulative import/export counters. It records no
meter interval. This permits observation-age tests during a pause without
claiming a continuous physical plant or inventing unobserved energy.

## Timeliness and exclusion

Observations expose `observedAt`, `receivedAt`, `evaluationAt`, `stateAgeMs`,
`stateFresh` and `dataExclusionReasons`. The original synthetic timing starts
receipt at observation +100 ms and evaluation at observation +1,000 ms.
Additional evaluation offset is applied to proposal evaluation/publication
times, risk-context binding and any subsequent accepted meter-interval
evaluation. It is not added to source observation or receipt times.

The current unapproved generic profile has a 2,000 ms state-age limit. The
boundary is inclusive; 2,000 ms remains timely, and 2,001 ms is stale. Expiry
excludes numeric state with null energy and synthetic missing-point sentinel
blocks; it does not assert that a real device became unimplemented. Historical
GOOD receipt blocks remain unchanged. `STALE_STATE` distinguishes age exclusion
from injected `TELEMETRY_UNKNOWN`. Timeliness and source quality are separate:
`stateFresh: true` does not make failed telemetry usable or grant authority.

A snapshot taken before a clock advance no longer matches. A newly captured
snapshot of stale state can match its precondition, but proposal screening still
returns STALE_STATE, null calculations and no interval. Neither requesting a
fresh hash nor reconstructing the journal makes old data fresh. No observation
refresh/recovery operation is introduced.

## Journal and retrospective accounting

The journal records EVALUATION_CLOCK_ADVANCE with an integer delta and replays
it during reconstruction. Deltas must be positive integers; the cumulative
additional evaluation offset is capped at one hour. There is no backward/reset
operation. Existing journal byte/event limits also apply before mutation.

Clock events are not STEP intervals. Existing retrospective carbon/storage
tools continue to account only previously accepted historical intervals and
exclude clock/held/replay events. Their last applied energy remains explicitly
historical; current expired telemetry stays null. A valid earlier zero-import
interval still has undefined intensity, not a zero-carbon assertion.

From the repository root:

```bash
node machine_factory/domains/energyInfrastructure/tools/run_observation_age_scenario.mjs
node --test machine_factory/domains/energyInfrastructure/tools/test_observation_age.mjs
```

The scenario applies a discharge, adds 1,001 ms to evaluation time, holds a
request despite a matching snapshot, and reconstructs the same expired state.
Its 20 new tests cover exact boundaries, unchanged plant timestamps/readback
within the freshness window, stale exclusion, snapshot/risk clock binding,
invalid/backward/excessive advances, replay/reconstruction, event limits and
historical carbon/storage integration.

## Fidelity and acceptance limits

This is an explicitly driven logical clock, not wall-clock monitoring, trusted
time synchronization, anti-PTP/GNSS attack protection or a live lease. While the
evaluation clock advances, the model supplies no autonomous plant evolution,
load energy, self-discharge, thermal behavior, protection trip or physical
completion. Accepted held intervals still generate their next synthetic
observation; the evaluation offset persists. The timing values and resource
bound are draft project assumptions, not reviewed interoperability deadlines.

Current unbound component-fixture requests remain supported; neither bound nor
unbound requests can bypass stale/risk/protection screening. Source/package
hashes and journal reconstruction remain unauthenticated consistency evidence,
not complete-history, rollback or durable-delivery guarantees. Old source-bound
journals are not silently migrated to this new component version.

No actual engine, device, protocol peer, time service, provider, gateway, Large
Model or RAG service is exercised. FSGIM/OPC DI context remains provisional and
carbon qualification unresolved. Control stays DENY and all 43 integrated
acceptance cases remain NOT_RUN, including complete sensing/time/replay and time
compromise cases. Required hardware remains simulated; generic/template assets
remain permitted. Full hardware coverage and admission stay open.
