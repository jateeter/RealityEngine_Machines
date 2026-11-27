# Draft connected-storage proposal screen

The [generic profile](generic-storage-screen-profile.json), [synthetic proposal](storage-proposal-screen.json) and [screen](../tools/screen_storage_proposal.mjs) implement a bounded EI06/EI10/EI14 prerequisite: deterministic rejection of proposals that violate selected algebraic limits, regardless of a claimed carbon benefit. They use the source-hash-bound REF01 connected FSGIM projection and selected STORAGE_AC primary, retaining existing OPC UA DI source type facets and inactive functions. No normative control property, approved engineering envelope or actual device state is asserted.

## Scope and authority

Only REF01 GRID_CONNECTED with closed PCC, declared available grid, healthy protection and clear risk disposition is supported. State, profile, topology and target identities must match the proposal; timestamps, receipt order, freshness and expiry are checked. BAD/UNKNOWN/stale state, blocked/unknown protection or risk, unsupported grid mode and revision mismatches cannot produce numeric screening results or a simulation-eligible result. GOOD state cannot omit required quantities. These are synthetic declarations, not authenticated sensor, protection or dynamic threat-feed evidence.

The role label MODEL_PLANNER is descriptive only. It grants no principal identity, delegation, approval or write authority. Proposal operatingApproval must be null; extra override fields and fabricated engineering approval are rejected. `eligibleForFurtherSimulation` means **only** that the selected draft algebraic checks passed. Even then, operational authorization remains false, executionPathAvailable false and control DENY. No adapter or command-execution API exists here. CarbonObjectiveQualified remains false, and a claimed carbon-reduction percentage is never used to relax limits or establish an emissions result.

## Generic profile assumptions and exact equations

The profile explicitly says NOT_ENGINEERING_APPROVED. Its 10 kWh capacity, 3 kWh reserve, 4 kW charge/discharge limits, 3 kW step-change limit, 6/2 kW import/export bounds, 2 kW minimum critical demand, 0.9/0.8 charge/discharge efficiencies, 0.25 h maximum interval and 2 s freshness are arbitrary reproducible generic assumptions. They are not ASHRAE/IEEE limits, approved operating parameters or OEM characteristics. Profile bytes are SHA-256 bound; model proposals cannot override limits through proposal fields.

Power and energy are decimal strings in kW and kWh, with hours for the held interval. Proposal storage power is **AC discharge positive, charge negative**; this is a project control-proposal convention, distinct from the net-import-positive measurement convention. Actual adapter sign mappings remain pending. Exact rational arithmetic evaluates:

- Discharge: next stored energy = initial energy − (AC discharge power × hours / discharge efficiency).
- Charge: next stored energy = initial energy + (absolute AC charge power × hours × charge efficiency).
- Net PCC import = requested critical service + other demand − PV generation − storage discharge power.
- Start/end energy must stay within reserve/capacity; storage magnitude and change from previous storage power must stay within profile limits; net import/export must stay within the declared active-power bounds.
- All declared critical demand must be served, and the state must meet the selected generic critical-demand minimum. No discretionary critical-load shedding is offered.

The default independent example has 5 kWh initially, a 2 kW discharge for 0.25 h at efficiency 0.8, and next energy 4.375 kWh. With 2 kW critical demand, 1 kW other demand and 1 kW PV, net import is zero. A -2 kW charge instead gives 5.45 kWh and 4 kW net import. These are arithmetic predictions on declared inputs, not simulated or measured physical responses.

The step-change limit is not a time-based ramp-rate model. Active-power boundary bounds are not full feeder thermal/apparent-power or multi-phase constraints. The screen assumes constant power and declared available PV/demand within one interval; it does not solve power flow, voltage/frequency, reserve recovery, faults or transients. Its state starts at a declared 5 kWh and is **not** the separate storage-carbon fixture's known-empty opening inventory. Those fixtures cannot be combined into a claimed integrated scenario without reconciling energy/carbon state lineage.

## Reproduction and remaining acceptance

```bash
python3 tools/build_proposal_screen.py --write
python3 tools/build_proposal_screen.py
node tools/screen_storage_proposal.mjs assets/storage-proposal-screen.json
node --test tools/test_proposal_screen.mjs
```

PASS from the command means the input passed structural checks; inspect `eligibleForFurtherSimulation` and denial reasons. Structural/provenance/quantity errors throw before success. Algebraic violations return explicit reasons and predicted quantities for review; invalid/stale/interlocked context returns null calculations. No file/device state is changed.

Tests cover independent charging/discharging oracles, exact inclusive limits, reserve/capacity, critical service, boundary/step/power/interval limits, stale/unknown state, protection/risk blocks, expiry, revision/target binding, units, tampering and fabricated authority. This does not execute AC12–AC15 or AC34: authenticated principals/delegation/state, independently reviewed envelopes, native command gateway, concurrency reservations/fencing, TOCTOU rechecks, idempotency, durable denial/action receipts, actual solvers/adapters and simulated device behavior remain pending. No network/runtime link is created. All 43 behavioral cases stay NOT_RUN and corpus admission NOT_PERFORMED. Generic/template assets remain permitted; all required hardware remains simulated.
