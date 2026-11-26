# Draft synthetic storage carbon allocation

The [reproducible input](storage-carbon-allocation.json) and [evaluator](../tools/evaluate_storage_carbon.mjs) extend EI14 with a bounded, retrospective storage accounting policy. Charging emissions come from the [exact synthetic imported-electricity ledger](import-carbon-ledger.md). The selected asset must be the draft FSGIM STORAGE_AC primary with separate inactive Load/Generator projections and its existing OPC UA DI source type facet. This does not instantiate equipment or assert normative FSGIM properties, a standards-approved allocation method, physical SOC or operational feasibility.

## Explicit policy and source boundaries

Only an explicitly known-empty **synthetic** initial inventory is supported. Unknown inventory cannot silently become empty or zero-carbon; nonzero opening inventories need traceable opening energy/carbon and are deferred. Source-ledger bytes are hash-bound, and that ledger's complete meter/factor compatibility, quality, time and continuity checks must pass. An unknown source ledger cannot supply zero-carbon charging.

Each charge allocation names a source ledger row and its exact interval end. Declared AC charging input must be positive and cannot exceed that row's imported energy. Stored energy must be positive and no greater than charging input; the difference is declared charge conversion loss. The source row's own factor determines charging emissions, rather than the two-row ledger's overall weighted factor. This is an explicit synthetic allocation of part of the meter import, not a measured feeder-to-battery flow. Source-budget checks apply within this evaluation only; durable cross-ledger allocation uniqueness is not implemented.

The project policy assumes a well-mixed stored-energy/carbon pool and carries **all** charging emissions, including emissions associated with conversion losses, to delivered energy. A charge adds stored energy and the emissions of its full AC input to the pool. A discharge removes a declared positive stored-energy quantity and its proportional share of carried emissions. Positive delivered AC energy cannot exceed removed energy; the difference is declared discharge conversion loss. All emissions removed from the pool are allocated to delivered AC energy. This choice raises delivered intensity when losses occur; it is a draft allocation convention requiring review, not a claim about physical carbon mass in a battery.

Events are strictly chronological, cannot occur after the explicit allocation evaluation time, and cannot be used for dispatch. The source ledger must have been evaluated no later than that evaluation. Retrospective source factors may have been published after charging; these records do not prove what was known when a device acted. No physical ramp, reserve, power or duration constraint is checked.

## Independent synthetic oracle

| Event | AC energy | Stored-energy change | Allocated charging/discharge emissions |
| --- | ---: | ---: | ---: |
| Charge from interval 1 at 100 gCO2e/kWh | 1 kWh input | +0.9 kWh | +100 gCO2e to pool |
| Charge from interval 2 at 400 gCO2e/kWh | 1 kWh input | +0.8 kWh | +400 gCO2e to pool |
| Partial discharge | 0.68 kWh delivered | -0.85 kWh | 250 gCO2e to delivery |

Final pool: 0.85 kWh and 250 gCO2e. Declared charge losses total 0.3 kWh and discharge losses 0.17 kWh. Thus 2 kWh input = 0.68 delivered + 0.85 remaining + 0.3 charge loss + 0.17 discharge loss. Allocated charging emissions of 500 gCO2e equal 250 delivered + 250 remaining. Delivered intensity is exactly `6250/17` gCO2e/kWh, not intrinsically zero. Reduced integer rationals preserve repeating ratios and tiny decimal allocations without floating-point rounding.

These are **allocation** conservation checks on declared synthetic inputs, not a physical microgrid or battery balance. The 500 gCO2e is already part of the upstream imported-electricity emissions ledger: carried/discharged amounts must not be added to that source inventory as newly emitted mass. The result fixes `additionalInventoryEmissions` to false and returns source hash, storage identity, policy, event/source-row lineage and final pool quantities. No export or avoided-emissions credit is applied.

## Reproduction and limits

```bash
python3 tools/build_storage_carbon.py --write
python3 tools/build_storage_carbon.py
node tools/evaluate_storage_carbon.mjs assets/storage-carbon-allocation.json
node --test tools/test_storage_carbon.mjs
```

Tests cover mixed charging factors, partial/full depletion, multiple withdrawals, lossless and tiny quantities, exact energy/emissions allocation, unknown sources, overdraw, invalid initial state, energy creation, chronology and false execution claims. Invalid inputs throw before a successful result, without mutating files or devices. A charge-only pool has no delivered intensity; full depletion removes carried emissions exactly.

Idle/self-discharge/auxiliary losses, pure-loss disposal, unknown/nonempty opening state, changing capacity/SOC/efficiency, degradation, dispatch feasibility, uncertainty, durable state/revision receipts, real provider inputs and native simulated device behavior remain pending. Unsupported loss events are rejected. The policy has not received independent engineering/accounting approval. All 43 behavioral cases remain NOT_RUN, control DENY and corpus admission NOT_PERFORMED. All required hardware remains simulated and generic/template assets remain permitted in every case.
