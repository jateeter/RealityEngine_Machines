# Solid and dokieli review workflow decision

Decision ID: RE-ASSET-REVIEW-001  
Recorded: 2026-11-04  
Decision authority: owner direction in this development conversation  
Status: **architecture direction accepted; implementation and conformance pending**

RealityEngine will integrate **dokieli** as a document authoring, annotation,
and review surface and **Solid Community Server (CSS)** as the primary
integration point for IFRS document-workflow processes. Solid POD resources
will expose governed structured asset references, review cases, findings,
and workflow projections. Beacon will be the intended archive for referenced
document content, subject to verification of its deployed API, access,
versioning, integrity, and retention capabilities.

The desired execution model is an approved class of workflow guardrails
instantiated dynamically as **one Review Machine per review asset**. Each
instance receives its own case binding, dFSA behavior, triggers, and PE sources.
The instance carries the POD asset reference through deterministic
ISRE-to-OSRE recognition and authenticated agentic handoffs. Runtime generation
means deterministic instantiation of reviewed templates, not unrestricted
LLM-authored executable machines or self-issued permissions.

The structured reference travels in a durable, versioned execution binding.
Numeric vector cells express declared control predicates and recognition
results; they do not encode URLs, content hashes, credentials, financial
amounts, or capability grants. A committed machine output is joined to the
exact input binding before any external action is dispatched. No ambient
"latest document" lookup may replace the pinned binding at that boundary.

CSS is the primary process-facing integration point, not a second approval
authority. Governed commands submitted through the Solid-facing service are
validated and committed by the canonical IFRS lifecycle service. Beacon,
POD, and RAG projections do not independently approve documents. The existing
PE dispatch ledger remains delivery/audit infrastructure, not the review
state machine. Agent completions return as authorized PE source observations;
external agents do not directly write OSRE or resume a machine.

dokieli annotations become review inputs tied to exact document revisions.
Only authenticated, policy-checked lifecycle commands can turn them into
finding dispositions or approval decisions. Content transformations produce
new immutable revisions; review decisions can advance a review case without
changing its document bytes. Each subsequent agent action receives a scoped
context resolved from the same case lineage.

The detailed proposed mechanics, lifecycle, ownership, and acceptance criteria
are in [the Review Machine design](../machine_factory/domains/ifrs-accounting/review-machines/README.md).
The example and schema in that directory are design artifacts, not extensions
already accepted by native loaders or the current trigger-envelope schema.

This decision does not change existing machine definitions, native numeric
semantics, approval gates, corpus counts, or production admission. IFRS remains
TEST_ONLY. The prior independent-signoff waiver is limited to that testing
run; it does not authorize production self-approval. No live CSS, Beacon,
dokieli, or dynamic Review Machine deployment is claimed by this record.

Background: [Solid Protocol](https://solidproject.org/TR/protocol),
[Solid WAC](https://solidproject.org/TR/wac),
[dokieli](https://dokie.li/docs), and the repository's
[existing connected workflow](../machine_factory/domains/ifrs-accounting/CONNECTED_WORKFLOW.md).
The authoritative native boundaries remain in the sibling CI repository's
`SURFACE_SPEC.md`, `docs/EXTERNAL_INTEGRATION_CONTRACT.md`, and
`docs/INTEGRATION_ARCHITECTURE.md`; this decision proposes an implementation
within those boundaries rather than amending them.
