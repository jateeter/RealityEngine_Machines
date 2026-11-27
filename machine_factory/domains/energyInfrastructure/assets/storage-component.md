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
Only SunSpec 203 W/W_SF are encoded and decoded against the pinned public model.
Other register bytes are placeholders and must never be consumed as readings.
There are no cumulative energy counters, Modbus frames, listener or network peer.
Meter import is positive; storage discharge is positive at its separate boundary.

Request IDs cache immutable receipts for one process lifetime, including rejected
requests. Identical replay returns the original receipt without changing current
state; conflicting intent is rejected. The cache permits 100 IDs without eviction.
This provides no durable, cross-restart or concurrent distributed reservation.
Faults TELEMETRY_UNKNOWN, PROTECTION_BLOCKED and RISK_UNKNOWN latch for the
instance lifetime. Telemetry loss emits null energy and SunSpec unknown sentinels;
no numeric fallback is usable. Faults are injected labels, not actual threat detection
or protection dynamics. Recovery requires constructing a fresh synthetic instance.

Bootstrap CLEAR is an explicitly unreviewed synthetic assumption, not clearance
from the risk assessor. Native control remains DENY for every accepted simulator
step. Opening carbon inventory is unknown (`carriedCarbonGCO2e: null`); there is
no implied zero-carbon inventory or qualified intensity objective.

The 19 component tests are genuine executable software evidence, distinct from
the 43 integrated acceptance cases, which remain NOT_RUN. Full counterpart
coverage, protocol peers, protection and islanding physics, risk-qualified execution,
durable readback reconciliation, integrated simulation and domain admission remain
pending. No hardware fulfillment or admission receipt is issued here.
