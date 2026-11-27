# Synthetic imported-electricity carbon ledger

The [reproducible ledger input](import-carbon-ledger.json) and [evaluator](../tools/evaluate_carbon_ledger.mjs) implement the first bounded EI14 accounting arithmetic. They consume the [meter interval contract](meter-energy.md), which links the generic PCC Meter through the ASHRAE 201/FSGIM context and existing OPC UA DI source type facet. This is a project extension and synthetic retrospective accounting only, not a normative FSGIM property mapping, real provider integration, reported inventory or operational approval.

## Selected scope and compatibility

This implementation accepts only imported electricity at the generic facility PCC, a synthetic CO2e/GWP basis, direct attributional average factors, location-based reporting, a synthetic geography and observation role, and gCO2e/kWh units. Every factor repeats the complete accounting basis, and it must match the ledger's supported basis exactly. CO2, lifecycle, marginal, market-based, forecast/target, different geographies and different denominators are rejected rather than converted or silently combined. The synthetic GWP identifier is a fixture label, not a real assessment vintage or reviewed method.

Only `SYNTHETIC_PROVIDER` and `SYNTHETIC_FIXTURE_ONLY` rights are accepted. Each factor records a revision, exact interval window, publication time, validity horizon, quality and decimal intensity. Publication must be at or after the observed interval end and no later than evaluation; factors must cover precisely the meter interval. Expired, BAD/UNKNOWN or missing factor inputs make the entire ledger ineligible. A known numeric zero factor is distinct from a missing factor. The retrospective ledger uses factors published after the energy interval; it cannot claim they were available at dispatch time. Actual provider licenses, subscriptions, signatures, methods, uncertainty and revision authenticity remain unverified.

The base meter-interval bytes are hash-bound. Each row runs the full source-bound meter evaluator and must use the same meter, projection and scoped source identity as that base. Adjacent rows must share an identical endpoint record, including counter bytes, timestamps, identity, epoch and quality. Duplicated, reordered, overlapping, gapped or discontinuous records are rejected. This conservative complete-endpoint rule may exclude otherwise reconcilable data; no reconciliation is inferred. Every interval uses the ledger's evaluation time and its declared generic freshness/duration policy.

## Exact arithmetic and independent example

For each eligible row, allocated imported-electricity emissions are imported kWh multiplied by the compatible factor. Total intensity is total allocated emissions divided by total imported kWh. Factors are nonnegative decimal strings with up to 12 fractional digits and a maximum of 64 characters. Meter kWh preserves its full supported 13 fractional digits. Integer rational arithmetic avoids floating-point rounding, including repeating ratios; outputs encode reduced numerator/denominator strings in the units named by each field.

| Synthetic interval | Imported energy | Factor | Allocated emissions |
| --- | ---: | ---: | ---: |
| 00:00–00:15 UTC | 1.25 kWh | 100 gCO2e/kWh | 125 gCO2e |
| 00:15–00:30 UTC | 3.75 kWh | 400 gCO2e/kWh | 1,500 gCO2e |
| Total | 5 kWh | 325 gCO2e/kWh weighted | 1,625 gCO2e |

The arithmetic mean of the two factors, 250, is not the energy-weighted result. The example also has 0.75 kWh exported, recorded separately without subtracting energy or emissions and without an avoided-emissions credit. Zero total imported energy gives zero allocated emissions under known inputs but null intensity with `UNDEFINED_ZERO_IMPORTED_ENERGY`. Any unusable row makes all aggregate quantities null with `UNKNOWN_INPUT`; the evaluator does not drop the row and report a deceptively complete partial total. Factors and meter values remain synthetic, so these numbers do not describe measured performance or global emissions reduction.

## Reproduction and remaining acceptance

```bash
python3 tools/build_carbon_ledger.py --write
python3 tools/build_carbon_ledger.py
node tools/evaluate_carbon_ledger.mjs assets/import-carbon-ledger.json
node --test tools/test_carbon_ledger.mjs
```

PASS means the input passed offline structural/compatibility checks; inspect `eligible`, `intensityStatus` and row reasons. Structural, provenance, time-window, continuity and basis errors throw before success. Tests include independent unequal-weight, repeating-ratio, tiny/large decimal, zero-denominator, incompatible-basis, missing/stale-input and continuity oracles. The fixture generator reproduces only inputs; it does not generate expected accounting results or acceptance receipts.

Storage charging emissions/loss allocation, behind-the-meter generation/backup, final-consumption boundaries, source uncertainty, provider revisions beyond row labels, forecasts/targets, safety-constrained scheduling, native adapters and simulated hardware acceptance remain pending. This imported-electricity ledger cannot stand in for any of them. No network or runtime link is created. Engineering review is PENDING, control DENY and all 43 behavioral acceptance cases remain NOT_RUN; no corpus admission or standards compliance is asserted. Generic/template assets remain permitted and all required hardware remains simulated.

The separate [journal-derived accounting path](journal-carbon.md) now derives intervals from reconstructed simulation receipts. It preserves their acquisition-time freshness checks while evaluating factor validity at report time. The original generic fixture path and shared evaluation-time rules remain unchanged.
