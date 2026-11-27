# Storage reconciliation with unknown opening carbon

The [journal storage evaluator](../tools/evaluate_journal_storage.mjs) derives
storage energy from source-checked, re-executed journal events and the
[journal import-carbon ledger](journal-carbon.md). It independently calculates
charge, discharge and conversion losses with exact rational arithmetic and
checks every applied storage energy state. Replays, denied requests and posture
events add neither energy nor carbon allocation. The original known-empty
[storage allocation fixture](storage-carbon.md) remains a separate calculation;
its zero opening inventory is never substituted for the simulator's 5 kWh seed.

## Energy balance and observation quality

The opening energy is derived from a fresh instance of the same pinned component
and run context. Applied receipts must reconcile with the fixed 900-second
interval, charge efficiency 0.9 and discharge efficiency 0.8. These are draft
generic parameters, not engineering-approved limits or physical measurements.

The scenario charges at 2 kW, idles, discharges at 2 kW, replays the original
charge, loses telemetry and holds another request. Exact balance is:

```text
5 opening + 0.5 charge input
  = 4.825 last applied storage + 0.5 delivered
    + 0.05 charging loss + 0.125 discharge loss
```

Historical energy is labelled `lastAppliedStoredKWh` with its observation time.
It is not a current telemetry fallback: after the injected loss,
`currentObservedStoredKWh` remains null and observation quality UNKNOWN.
Zero idle losses are an explicit limitation of this held-interval surrogate;
thermal, self-discharge, continuous-time and protective dynamics are not added.

## New charging attribution is not a known carbon inventory

The draft policy is
`DRAFT_FIXED_REF01_INCREMENTAL_GRID_CHARGE_WITH_UNKNOWN_OPENING_CARBON`.
The fixed REF01 scenario has 3 kW demand and 1 kW PV, leaving positive residual
load before charging. Under this project policy, additional charging energy is
allocated from incremental grid import with the same interval's synthetic
average factor. Charging input may not exceed that interval's import budget.
This is retrospective allocation, not proof of physical electron origin or a
general policy for other topologies, power sources or electrical modes.

In the scenario, 0.5 kWh charge input at 400 gCO2e/kWh receives 200 gCO2e.
The underlying PCC import ledger already contains 500 gCO2e for all imports.
The 200 gCO2e is a **subset of that 500**, not an additional emission. The
evaluator checks this budget and explicitly sets additional inventory emissions
false. It does not add allocated storage emissions to PCC emissions again.

Opening carbon remains `UNKNOWN_OPENING_INVENTORY`. Remaining carried mass,
delivered allocated mass and delivered intensity remain null at every step,
including idle and discharge without any recorded charge. Known new charging
attribution does not make total inventory carbon known. Callers cannot supply
zero or other overrides for opening energy/carbon. If the source import ledger
is ineligible because factors are missing, BAD or expired, energy reconciliation
still runs, but new charging attribution is null rather than a zero fallback.

## Reproduction and limits

From the repository root:

```bash
node machine_factory/domains/energyInfrastructure/tools/run_journal_storage_scenario.mjs
node --test machine_factory/domains/energyInfrastructure/tools/test_journal_storage.mjs
```

The scenario emits its complete input and result. The evaluator CLI accepts a
saved input JSON. Its 22 new tests cover exact energy/loss balances, subset
attribution, historical/current quality separation, unknown factors, idle,
charge-only and discharge-only paths, replay/hold exclusion, source tampering,
false opening-inventory overrides and false operating claims.

All factors are synthetic and unqualified. No new pool mixing/dispatch policy,
opening-carbon attestation, uncertainty bounds, additional provider rights or
facility-consumption intensity qualification is supplied. The existing
provisional FSGIM storage primary and OPC UA DI facet are retained. Journal
history remains unauthenticated and does not prove completeness or prevent
rollback; changes to sealed sources invalidate old journals without migration.

No actual engine, device, protocol peer, provider, gateway, Large Model or RAG
service is exercised. Native control remains DENY and operational authorization
false. All 43 integrated acceptance cases remain NOT_RUN; full simulated hardware
coverage, carbon qualification and domain admission remain pending. Required
hardware remains simulated and generic/template assets remain allowed throughout.

The [journal-backed revision archive](journal-revisions.md) now recomputes this reconciliation for each factor reporting revision and preserves earlier as-of reports. Recalculation does not resolve unknown opening/inventory/delivery carbon or authenticate reporting history.
