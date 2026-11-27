# Retrospective carbon accounting from a reconstructed simulation journal

The [carbon evaluator](../tools/evaluate_carbon_ledger.mjs) now accepts
`SYNTHETIC_JOURNAL_IMPORT_CARBON_LEDGER` alongside the original fixture ledger.
It reconstructs the complete source-bound journal before selecting energy
intervals. Only STEP events that were applied and were not replays are counted.
Faults, risk assessments, rejected requests and historical replay receipts do
not create additional energy. Empty histories cannot manufacture zero energy.

Factor entries must match every selected event hash exactly and in order.
Callers supply no energy quantities, meter intervals or computed emissions.
The evaluator derives these from reconstructed receipts, re-decodes the meter
intervals and enforces the existing source/projection/PCC binding, endpoint
continuity, quantity, basis, quality and factor publication rules. The original
generic fixture input contract and its calculation results remain unchanged.

## Historical observation and report time

Journal intervals retain their original observation, receipt and acquisition
evaluation times and freshness policies. Each interval must have been eligible
at acquisition and evaluated no later than the carbon report. The report does
not rewrite historical timestamps or enlarge a freshness horizon to make data
look current. Factor publication/expiry is evaluated at report time. The
original fixture ledger still requires its single shared evaluation clock.

Currently unknown telemetry does not turn previously reconstructed GOOD
historical observations into current readings or erase their historical energy.
Only the accepted historical intervals are accounted; no energy is imputed
during denied steps. The simulator's held-interval clock limitation still applies.

## Exact synthetic example

The [scenario](../tools/run_journal_carbon_scenario.mjs) includes an accepted
request, its duplicate replay, another import interval, an export interval,
telemetry loss and a held request. Its three applied intervals have:

| Interval | Imported kWh | Exported kWh | Synthetic factor gCO2e/kWh | Allocated gCO2e |
| --- | ---: | ---: | ---: | ---: |
| First import | 0.5 | 0 | 400 | 200 |
| Second import | 0.25 | 0 | 200 | 50 |
| Export | 0 | 0.25 | 900 | 0 |

Total import is 0.75 kWh and allocated emissions are 250 gCO2e, giving exact
intensity **1000/3 gCO2e/kWh**. Exports remain a separate 0.25 kWh; they do not
offset imported energy or emissions. This is an energy-weighted ratio, not an
average of sample factors. The high factor during export changes no allocation.
Zero imported energy leaves intensity undefined. Missing, BAD or expired
factors produce null aggregate quantities rather than zero-carbon assertions.

From the repository root:

```bash
node machine_factory/domains/energyInfrastructure/tools/run_journal_carbon_scenario.mjs
node --test machine_factory/domains/energyInfrastructure/tools/test_journal_carbon.mjs
```

The scenario emits its complete input and result. The evaluator CLI accepts a
saved input with either supported ledger kind. The 23 new tests cover exact
weighting, export separation, replay/hold exclusion, acquisition/report clock
separation, source/receipt tampering, factor coverage/order, incompatible basis,
publication timing, unknown/expired factors and undefined zero-import intensity.

## Acceptance limits

All factors remain SYNTHETIC_PROVIDER / SYNTHETIC_FIXTURE_ONLY. No live provider,
rights-qualified service, geographical data, uncertainty model, independent
accounting review or operational forecast is introduced. The output explicitly
sets provider qualification and facility-consumption intensity qualification
false. The original FSGIM/OPC DI asset context remains provisional.

Imported-electricity accounting does not establish the facility's consumption
carbon intensity. Opening storage inventory carbon remains unknown, and storage
losses, generation attribution and inventory lineage are not reconciled here.
No measured reduction, target achievement or dispatch recommendation follows.
Reconstructed journals remain synthetic and unauthenticated: source hashes and
receipt replay do not prove full history, prevent rollback or establish physical
delivery. Any sealed package change invalidates old journals without migration.

Control remains DENY and operational authorization false. No actual engine,
protocol peer, physical equipment, provider, Large Model or RAG service is used.
All 43 integrated acceptance cases remain NOT_RUN; EI14/EI16/EI18 and domain
admission remain open. Required hardware remains simulated and template/generic
assets remain permitted in every case.

The separate [journal storage reconciliation](journal-storage.md) now verifies storage energy/loss balances and new charging attribution. It preserves unknown opening carbon and therefore does not qualify total storage inventory, delivered carbon or facility-consumption intensity.
