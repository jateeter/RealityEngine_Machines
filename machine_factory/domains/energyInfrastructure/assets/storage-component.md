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
This provides no durable, cross-restart or concurrent distributed reservation.
Faults TELEMETRY_UNKNOWN, PROTECTION_BLOCKED and RISK_UNKNOWN latch for the
instance lifetime. Telemetry loss emits null energy and SunSpec unknown sentinels;
no numeric fallback is usable. Faults are injected labels, not actual threat detection
or protection dynamics. Recovery requires constructing a fresh synthetic instance.

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
instances must not be spliced into one history; persistent identity and restart
reconciliation remain pending. Observations use simulated time and fixed 100 ms
receipt latency; no measured clock, transport delivery or continuous meter is
claimed. Unimplemented register bytes remain placeholders. Carbon inventory and
intensity remain unknown; no provider or opening-state carbon lineage is added.
