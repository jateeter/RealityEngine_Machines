# Untrusted model proposal data reviewed on a simulation clone

The [proposal reviewer](../tools/review_model_proposal.mjs) accepts a bounded
synthetic model-response text and a source-bound execution journal. It parses
only a flat JSON object containing three string values: `id`, `storagePowerKw`
and `expectedStateSHA256`. A state digest is mandatory here; the older unbound
component-fixture path is not admitted through this review boundary.

## Parsing and fail-closed behavior

Text is limited to 4 KiB UTF-8. The parser accepts JSON whitespace and standard
string escapes, rejects duplicate keys after escape decoding, and allows no
other fields, nesting, arrays, numeric values, trailing material, comments,
Markdown fences or tool-call envelopes. Identifier, decimal-power and digest
formats are bounded before any source journal is processed. There is no
heuristic extraction of JSON from surrounding instructions or model reasoning.

All text is untrusted data. A valid identifier such as `send_email` remains an
identifier; it is never resolved to a tool or instruction. Extra instructions,
completion claims, approval fields or retrieval context are not accepted as
proposal fields. No permissions follow from source text or caller labels.

Invalid model data returns ABSTAIN_INVALID_MODEL_DATA without processing the
source history. An unreconstructible history returns ABSTAIN_INVALID_SOURCE_HISTORY.
Conflicting intent or a simulation hold produces HOLD_SIMULATION_PROPOSAL.
There is no automatic retry, alternate provider, state refresh or relaxed-schema
fallback. Caller protocol/scope violations throw. Local CLI exit success means
the review completed, never approval; inspect `reviewDisposition` and the
explicit false authority/completion fields.

## Clone-only candidate evaluation

For valid data, the existing journal verifier reconstructs a separate in-memory
instance and evaluates exactly the proposed state-bound step on that clone.
State preconditions, freshness, engineering-envelope and risk/protection checks
still apply. A matching digest cannot make aged or blocked state usable.

A permitted hypothetical step returns SIMULATION_CANDIDATE_ONLY, its simulation
receipt and `hypotheticalStepApplied: true`. The clone is discarded; the input
journal and its state/counters remain unchanged. A historical request replay is
reported separately with no new hypothetical candidate. In every case,
`actionExecuted` is false, tool permissions empty, operational readiness false
and control DENY. A hypothetical `candidateReceipt.applied: true` is not an
actual completion or evidence that the proposed request was committed.

Source-history validation means internal hash/receipt consistency against the
current pinned package, not authenticated hardware, model-provider identity,
trusted timestamps, complete history or rollback protection. Output states
`sourceHistoryAuthenticated: false` and `providerAuthenticated: false`.

## Reproduction and acceptance limits

From the repository root:

```bash
node machine_factory/domains/energyInfrastructure/tools/run_model_review_scenario.mjs
node --test machine_factory/domains/energyInfrastructure/tools/test_model_proposal_review.mjs
```

The scenario emits synthetic input and its clone-only result, checking input
immutability. The reviewer CLI accepts a saved review JSON. Its 37 new tests
cover strict/escaped/duplicate JSON fields, exact byte bounds, injected envelopes
and completion claims, inert identifiers, stale and unsafe proposals, aged/risk
holds, replay/conflicting IDs, source-history failure, caller-scope misuse and
unchanged original histories. These are parser/composition tests, not actual
Large Model prompt-injection resilience or end-to-end agent acceptance.

No model is called and no production tool/agent endpoint is registered.
SYNTHETIC_UNTRUSTED_MODEL_TEXT and SIMULATION_REVIEW_ONLY are fixture scope
labels, not an authentication or tenant/role authorization service. No actual
provider identity, model provenance, rights-qualified RAG collection, retrieval
groundedness or confidential-site policy is established. Existing public model
review packets remain reference-only and not ready for operational model use.

Future model integration requires independently governed identity/scope,
provider/model provenance, source rights, confidentiality, authorization and
execution contracts; this review result cannot supply them. FSGIM/OPC DI asset
context remains provisional. No actual engine, peer, physical device, provider,
gateway, Large Model or vector/RAG service is exercised. Required hardware stays
simulated and generic/template assets remain allowed. All 43 integrated cases
remain NOT_RUN; agent/model acceptance and domain admission stay open.
