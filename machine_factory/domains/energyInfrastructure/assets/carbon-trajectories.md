# Synthetic carbon revisions and separated trajectory series

The [reproducible archive](carbon-trajectories.json) and [evaluator](../tools/evaluate_carbon_trajectories.mjs) extend EI14 with a single-reporting-window factor revision chain, separately typed forecast/target examples, and synthetic historical decision references. The source is the [imported-electricity ledger](import-carbon-ledger.md), retaining its ASHRAE 201/FSGIM PCC Meter context and OPC UA DI source type facet. No normative property equivalence, real provider revision, model forecast, adopted target or actual device action is asserted.

## Preserve original reporting and declared availability

The original source file bytes are SHA-256 bound, and the first snapshot must reproduce the original ledger value exactly. Later records point to the immediately preceding snapshot digest, increase evaluation time, preserve meter inputs/ordering, source and accounting basis, and identify changed factors with new revision labels. A source revision label cannot name different factor contents within the same row/provider scope. Empty reporting revisions, rewritten baselines, altered meter evidence and broken chains fail validation. All snapshots run the source-bound ledger evaluator again.

Snapshot digests use this project's recursively sorted-object-key JSON representation, array order preserved, compact UTF-8 encoding and SHA-256. Independent Python/JavaScript implementations and a fixed digest vector check reproduction. This is a project serialization contract for the selected JSON inputs, **not** a claim of general RFC canonicalization, a digital signature, trusted timestamp or tamper-proof storage. Hashes identify values and detect internal inconsistency; they do not authenticate an author. The repository's reviewed bytes remain source provenance, not independent operational evidence.

The fixture preserves the original 1,625 gCO2e / 5 kWh = 325 gCO2e/kWh report. A synthetic revision changes interval 1's factor from 100 to 200 gCO2e/kWh under `fixture-v2`; the corrected report becomes 1,750 / 5 = 350 gCO2e/kWh. The original snapshot remains present. A declared reference at 00:31 UTC still binds the original 00:30:01 snapshot, not the correction available at 00:40:01. Referencing that later snapshot from the earlier reference is rejected. No action was executed, and declared availability times are synthetic metadata, not native receipt evidence.

Unknown corrected inputs produce an ineligible revision with null intensity while retaining the original known snapshot. Any correction flags dependent accounting for requalification before current-revision use, including the separate storage allocation; it does not automatically rewrite storage inventory or invalidate an external signed receipt. Existing meter freshness rules still apply at every revision's evaluation time; a long-delayed restatement can therefore be ineligible. Authenticated archival qualification that permits historical meter reuse without weakening real-time freshness is separate pending work. The checker does not extend a TTL or silently waive stale input policy to make a revision pass.

## Separate observations, forecasts and target examples

`observedRevisions` contains only evaluated synthetic observation ledgers. Forecast examples require a matching accounting basis with the distinct `SYNTHETIC_FORECAST` role, a vintage before their interval begins and explicit quality/value. An unknown forecast stays null. A past forecast remains a forecast in this retrospective archive and never becomes an observation merely because time advanced.

Target examples use a separate `SYNTHETIC_TARGET` role and a digest-bound, eligible, defined baseline available at issuance. They remain `DRAFT_EXAMPLE_NOT_ADOPTED`, with null owner/approval receipt and no control usability. The fixture's 300 gCO2e/kWh threshold and 310 forecast are arbitrary synthetic grammar examples, **not** the user's objective, a prediction, an approved emissions-reduction commitment or an operating threshold. Arrays can be empty: this contract does not require inventing a forecast, target or decision.

Observed, forecast and target records are returned in separate series and are never spliced into one emissions total or intensity path. Historical decision references can point only to an eligible observed snapshot already available at their declared time, and always fix `actionExecuted` to false and control to DENY. This is reference consistency, not immutable real dispatch evidence. Unsafe-schedule denials and native durable action receipts remain separate acceptance obligations.

## Reproduction and remaining acceptance

```bash
python3 tools/build_carbon_trajectories.py --write
python3 tools/build_carbon_trajectories.py
node tools/evaluate_carbon_trajectories.mjs assets/carbon-trajectories.json
node --test tools/test_carbon_trajectories.mjs
```

The generator reproduces inputs and digests, not claimed acceptance receipts. Tests cover the independent 325→350 arithmetic oracle, original-reference retention, unknown/stale corrections, fixed canonical vector, tampering even with recomputed digests, missing/reused source labels, chronological availability, series-role substitution and fabricated approval/action claims. Invalid inputs throw before success. No source files are mutated by evaluation.

Durable append-only/transactional storage, signatures and trusted receipt times, independently reviewed historic qualification, actual provider/model/vintage evidence, adopted owner targets, multi-window observed trajectories, uncertainty bands, optimization/safety constraints and native simulated behavior remain pending. The existing storage allocation remains a separate draft contract; this archive does not revise its inventory state. No network/runtime link is created. Engineering review is PENDING, control DENY, all 43 behavioral acceptance cases NOT_RUN and corpus admission NOT_PERFORMED. All required hardware remains simulated and generic/template assets remain permitted in every case.
