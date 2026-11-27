# Journal-backed factor restatement and historical selection

The [revision evaluator](../tools/evaluate_journal_revisions.mjs) connects
[journal import accounting](journal-carbon.md) and
[storage reconciliation](journal-storage.md) to a bounded reporting history.
Every revision uses the same source-bound execution journal and accounting
basis. Revision inputs can change factor records and report time; they cannot
supply replacement meter intervals, journal events or storage states.

## Immutable evidence and recomputation

The first report must match the supplied baseline ledger, whose project digest
anchors the archive. Each later revision has a unique ID, a parent digest, a
content digest and strictly later availability time. It must change at least
one factor. Changed factors require new source revision labels and
nondecreasing publication times. Factor coverage/event order cannot change.
Reuse of an old source label for different content is rejected across the
entire history, including nonadjacent revisions.

For each report, the evaluator reconstructs the pinned journal and recalculates
import accounting and dependent storage reconciliation. It preserves historical
acquisition checks while evaluating factor validity at that report's time.
No stale cached storage allocation is silently carried into a corrected report.
The underlying journal, opening energy and applied storage states remain fixed.
The original fixture-only trajectory archive remains a separate supported tool.

The synthetic example corrects the charging-period factor from 400 to 300
gCO2e/kWh, with a new revision and publication time:

| Reporting snapshot | Imported kWh | Allocated import gCO2e | Import intensity gCO2e/kWh | New-charge allocation gCO2e |
| --- | ---: | ---: | ---: | ---: |
| Original | 1.5 | 500 | 1000/3 | 200 |
| Corrected | 1.5 | 400 | 800/3 | 150 |

Storage energy remains 4.825 kWh in both reports. Total remaining and delivered
carbon remain null in both: correcting a synthetic charging factor does not
resolve unknown opening carbon. New-charge allocation is still a subset of
import emissions and is not added as another emission.

## As-of semantics and unknown reports

`asOf` selects the latest report available at or before that cutoff. Quantified
snapshots later than the cutoff are omitted from the output; the selected
report cannot use a later correction. Before the first report, availability is
false and selected values are null. The archive revision count is an audit
count, not a quantified future report. All supplied revisions must be internally
valid and available by the separate archive evaluation time.

If the latest available correction has unknown/BAD/expired factors, it remains
the selected report with null accounting quantities. The evaluator does not
fall back to a prior eligible value and present it as current. An as-of view
selects a historical report; it does not requalify that report's factor validity
at the retrieval cutoff or assert live freshness or operating authority.

## Reproduction and limits

From the repository root:

```bash
node machine_factory/domains/energyInfrastructure/tools/run_journal_revision_scenario.mjs
node --test machine_factory/domains/energyInfrastructure/tools/test_journal_revisions.mjs
```

The scenario emits its archive input, an earlier as-of result and the latest
report. The evaluator CLI accepts a saved archive input JSON. The 27 new tests
cover dependent recomputation, unchanged energy and unknown carbon, temporal
selection boundaries, unknown-latest behavior, baseline/parent/hash/order
integrity, reused labels, coverage/publication changes, source tampering and
false forecast/target/authority claims. Inputs are capped at ten revisions and
2 MiB serialized API input. The CLI is a local reviewer tool, not an exposed
upload service or streaming archive store.

Project JSON hashes establish internal consistency, not signatures, trusted
timestamps, provider authenticity, full history or rollback prevention. A caller
can construct a different coherent archive; the tool does not authenticate its
baseline. No actual signed receipt or external cache is invalidated. Recomputed
storage accounting remains draft and unqualified, and opening-carbon lineage,
provider rights/geography/uncertainty and independent review remain pending.

Forecasts, adopted targets and native dispatch evidence are not admitted into
this archive. No actual engine, device, protocol peer, provider, gateway, Large
Model or RAG service is exercised. FSGIM/OPC DI integration remains provisional.
Control remains DENY, operating authority false and all 43 integrated acceptance
cases NOT_RUN. Required hardware stays simulated; template/generic assets remain
permitted throughout. Full simulated hardware coverage and admission stay open.
