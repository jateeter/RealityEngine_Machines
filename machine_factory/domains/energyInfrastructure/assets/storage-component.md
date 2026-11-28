# Offline storage simulated hardware component

EI18 now has a versioned executable component surrogate, recorded in the
[catalog](storage-component-catalog.json). This supplies partial battery energy,
fixed efficiency conversion and selected PCC meter power behavior for REF01.
The storage primary retains the existing provisional ASHRAE 201 FSGIM context
and OPC UA DI identity facet; it does not activate the projected Load or Generator
functions or assert normative model equivalence.

Run from the repository root:

```bash
node machine_factory/domains/energyInfrastructure/tools/simulate_storage_component.mjs
node --test machine_factory/domains/energyInfrastructure/tools/test_storage_simulator.mjs
```

Each new request holds a storage setpoint for 900 simulated seconds. Discharge is
positive, charge negative, in decimal kW at 10 W resolution. The independent
integer mWh state starts at 5 kWh. Discharge consumes energy at efficiency 0.8;
charging retains energy at efficiency 0.9. The generic, unapproved proposal screen
checks reserve, capacity, power, ramp, load and connected-grid limits before any
advance. Independent state and net import predictions must match its rational
results. Accepted steps advance clock and revision; denied steps advance neither.
This is a held-interval surrogate: time and loads do not evolve during holds.

The scenario discharges to 4.375 kWh, replays without advancing, idles, exports
at 1 kW while reaching 3.4375 kWh, rejects a reserve violation, then injects unknown
telemetry and holds another request. Charging has a separate golden-value test.
SunSpec 203 W/W_SF and TotWhImp/TotWhExp/TotWh_SF are encoded and decoded against the pinned public model.
Other register bytes are placeholders and must never be consumed as readings.
There are no Modbus frames, listener or network peer.
Meter import is positive; storage discharge is positive at its separate boundary.

Request IDs cache immutable receipts for one process lifetime, including rejected
requests. Identical replay returns the original receipt without changing current
state; conflicting intent is rejected. The cache permits 100 IDs without eviction.
Version 0.3.0 adds source-bound offline journal reconstruction (below). There is no authenticated durable delivery or concurrent distributed reservation.
Faults TELEMETRY_UNKNOWN, PROTECTION_BLOCKED and RISK_UNKNOWN latch for the
instance lifetime. Telemetry loss emits null energy and SunSpec unknown sentinels;
no numeric fallback is usable. Faults are injected labels, not actual threat detection
or protection dynamics. Reconstruction preserves faults; starting a fresh scenario is a reset, not authorized recovery.

Bootstrap CLEAR is an explicitly unreviewed synthetic assumption, not clearance
from the risk assessor. Native control remains DENY for every accepted simulator
step. Opening carbon inventory is unknown (`carriedCarbonGCO2e: null`); there is
no implied zero-carbon inventory or qualified intensity objective.

The 25 component tests are genuine executable software evidence, distinct from
the 43 integrated acceptance cases, which remain NOT_RUN. Full counterpart
coverage, protocol peers, protection and islanding physics, risk-qualified execution,
durable readback reconciliation, integrated simulation and domain admission remain
pending. No hardware fulfillment or admission receipt is issued here.

## Cumulative energy readback (version 0.2.0)

Import and export counters advance independently for each accepted held interval.
The fixed scale is -2 (0.01 Wh per raw unit); 900 seconds contributes 25 raw
units per watt. Opening counters 1,000,000 imported and 100,000 exported are
arbitrary synthetic nonzero seeds, not proof of historical import/export. They
avoid mistaking the SunSpec zero/not-accumulated sentinel for usable history.
Charging at 2 kW imports 1 kWh at the PCC while retaining 0.45 kWh in the battery;
these are different accounting boundaries. No direction is netted against another.

Before committing state, candidate counters are range-checked without wrap and
encoded/decoded, then passed through the existing interval evaluator. This now
allows the source-bound REF01 projection in addition to its original generic
projection; arbitrary paths and wrong PCC identities remain rejected. Receipts
include both the generated interval input and evaluated separate Wh/kWh deltas.
Identical replay returns the original interval receipt without adding counters
again. Rejected/held steps emit no interval. Telemetry loss emits missing counter
and scale sentinels, not usable zeros.

Epoch/source labels are deterministic scenario-local labels. Independent simulator
instances must not be spliced into one history. Version 0.3.0 accepts a scenario run label for counter epochs and reconstructs matching saved journals; globally unique persistent identity and operational restart reconciliation remain pending. Observations use simulated time and fixed 100 ms
receipt latency; no measured clock, transport delivery or continuous meter is
claimed. Unimplemented register bytes remain placeholders. Carbon inventory and
intensity remain unknown; no provider or opening-state carbon lineage is added.

## Source-bound execution journal (version 0.3.0)

The [journal tool](../tools/storage_execution_journal.mjs) records bounded STEP and
FAULT events with sequence numbers, previous-event hashes, inputs and generated
receipts. Each journal binds its synthetic run label and the complete sealed
package manifest hash. Package bytes are checked against all manifest entries
before construction/restoration. The currently executing journal implementation
is hashed separately. Source changes require a new journal; migration is not
silently inferred. The run label becomes the counter epoch; callers must not
reuse labels for unrelated histories. Labels are not authenticated identities.

Restoration re-executes every event from the fixed initial state and compares
each generated receipt, including interval readback, before returning a usable
instance. Stored numeric state is never loaded as authoritative state. Fault
latches, denied IDs and duplicate request receipts survive this reconstruction.
A matching repeated request returns its original receipt without accumulating
energy again; a conflicting request ID is still rejected. A restored instance
can continue its synthetic history. This proves deterministic offline replay,
not exactly-once device delivery.

From the repository root, save and reconstruct an explicit local evidence file:

```bash
node machine_factory/domains/energyInfrastructure/tools/storage_execution_journal.mjs > /tmp/energy-journal.json
node machine_factory/domains/energyInfrastructure/tools/storage_execution_journal.mjs --replay /tmp/energy-journal.json
node --test machine_factory/domains/energyInfrastructure/tools/test_storage_journal.mjs
```

Files must be regular files and at most 1 MiB. The reader enforces that limit
even if the file grows after opening. The API caps histories at 128 events, with
reserved byte capacity checked before simulation mutation. The underlying
component still caps distinct request IDs at 100. CLI export uses stdout; file
creation/storage is explicit. There is no background writer, fsync guarantee,
transactional outbox, lock, authenticated principal, signing key or trusted head
checkpoint. A valid shortened prefix can be reconstructed if its head is
recomputed: hashes detect inconsistency, not malicious rewriting, completeness
or rollback. The 27 journal tests include this limit as an expected result.

The fresh-process test writes an actual temporary journal and reconstructs it
in another Node process, then checks energy and meter counters. Tests reject
source drift, path escape, altered receipts (including rehashed false receipts),
sequence/order/head changes, false control claims, oversize input and unsupported
operations. All evidence remains simulation-only with control DENY, unknown
carbon inventory/intensity and zero integrated behavioral cases run. EI11, EI16,
EI18 and domain admission remain open.

## Assessed risk execution holds (version 0.4.0)

The component now accepts bounded source-bound inputs through
`applyRiskAssessment`, calls the existing conservative assessor, and carries
UNKNOWN/BLOCKED into subsequent proposal screening. This is stricter than the
initial unreviewed synthetic CLEAR bootstrap. There is no clearance path: empty,
NOT_AFFECTED, stale or unusable evidence never grants authority. Once BLOCKED,
subsequent assessments must acknowledge that prior posture and cannot downgrade
it. Injecting UNKNOWN also cannot weaken an assessed block.

Inputs must match the current simulated evaluation time, connected electrical
mode, topology and source projection, including its source hash. The assessor
still validates pinned STIX infrastructure/vulnerability/relationship bindings
and its draft policy. Inputs are capped at 16 findings, 80-character finding IDs
and 16 KiB, with an 8 KiB result cap before posture mutation. Wrong context,
source, prior state, scope or size throws before changing simulation state.

Version 0.4.0 starts the synthetic clock at 2026-11-25T00:00:00Z, aligned with the
already pinned synthetic threat objects. This replaces the earlier January
clock seed, which predates those objects. It is a versioned scenario parameter,
not current wall-clock or real threat-feed evidence. Existing journals remain
source-bound and are not silently migrated.

A finding bound to the REF01 microgrid controller holds discretionary storage
proposals in this single fixed scenario. This is a conservative project policy,
not a claim that every energy asset is vulnerable. Electrical protection,
critical-load declarations, meter readback and battery energy remain unchanged;
no automatic trip, load shedding, device command or remediation occurs. The
observed state exposes its effective risk posture. Denied steps still advance
neither clock nor counters and emit no interval. The held-interval time model
and synthetic CLEAR bootstrap remain limitations; this is not continuous plant
or autonomous threat monitoring.

Journals now support RISK_ASSESSMENT alongside STEP/FAULT events. Reconstruction
re-runs the assessor and compares its generated receipt, then restores the
posture and subsequent denied-request replay behavior. This shares the existing
source binding, size/event limits and lack of authenticated history completeness,
rollback protection or durable delivery.

Run the composed scenario and its 22 targeted tests from the repository root:

```bash
node machine_factory/domains/energyInfrastructure/tools/run_assessed_risk_scenario.mjs
node --test machine_factory/domains/energyInfrastructure/tools/test_assessed_risk_simulation.mjs
```

The scenario binds the existing synthetic finding to the simulator topology,
asserts AFFECTED, verifies BLOCKED, holds a proposal with no energy interval,
and reconstructs the same blocked state from its journal. No real CVE, threat
feed, authenticated risk acceptance, engineering approval, normative standards
conformance, integrated acceptance or admission is established. Native control
remains DENY, carbon inventory/intensity unknown, and all 43 integrated cases
remain NOT_RUN. All required hardware remains simulated; template/generic
assets remain allowed throughout.

A replay of an earlier accepted request returns its original historical receipt with `replayed: true`; the historical `applied: true` is not a fresh authorization. It advances no clock, energy or counters and does not weaken the current assessed posture. New requests remain held. A dedicated test verifies this behavior before and after journal reconstruction.

Version 0.5.0 adds [optional state snapshot preconditions](state-preconditions.md), exposes the synthetic run label in observations and records binding results in receipts. The two-field unbound component fixture path remains available; neither path grants operating authority.

Version 0.6.0 adds [explicit evaluation-clock advances](observation-age.md) and observation-age exclusion. The plant clock still advances only through accepted held intervals; separate evaluation-only events create no plant evolution or energy interval.
