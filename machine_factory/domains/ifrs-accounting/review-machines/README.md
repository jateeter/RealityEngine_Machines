# Asset-scoped Review Machines

Design version: 0.1.0  
Recorded: 2026-11-04  
Status: accepted architectural direction; proposed implementation contracts

The owner has directed integration of dokieli and Solid Community Server into
RealityEngine's document-review workflows. The durable decision is
[RE-ASSET-REVIEW-001](../../../../docs/SOLID_DOKIELI_REVIEW_DECISION.md).
This directory remains an active factory extension. Nothing here is a deployed
machine, native loader extension, production approval, or verified Beacon API.

## Outcome and boundaries

A document can pass through extraction, interpretation, reconciliation,
verification, revision, reviewer disposition, and acceptance without losing
its identity, exact content revision, provenance, or authorization contour.
A reviewed guardrail template generates one asset-specific Review Machine
and its trigger/source bindings. dFSA recognition mediates each permitted
agentic action. An authenticated result returns as an observation for another
deterministic evaluation, rather than directly advancing the machine.

The review asset means one logical document in a tenant/entity/period and
workflow scope. A new content revision does not create a competing machine
for the same asset. A new review cycle has a fresh cycle ID and generation;
the prior cycle is fenced and retained. The initial implementation permits
one active cycle per asset and one in-flight action per Review Machine.
Parallel specialist actions require separate child task identities and an
explicit join contract; unrelated completions must never be merged into one
apparently satisfied gate.

Review Machines supplement the 225 existing IFRS accounting machines. They
coordinate asset review; they do not replace accounting determinations,
invent paragraph interpretations, post journals, file accounts, or release
financial statements. Accounting-family machines can submit contributions
and impact observations to a case through its governed interface.

## Responsibilities

| Component | Required responsibility |
| --- | --- |
| CSS / Solid POD | Primary process-facing asset and case resources; protected references, annotations, relationships, command proposals and projected receipts |
| dokieli | Human document/working-paper surface; exact-version annotations and review proposals |
| Beacon | Intended immutable originals, extraction renditions and transformed candidates; deployed guarantees must be verified |
| Canonical IFRS lifecycle service | Revisions, dependencies, findings, authorized decisions, case versions, transactions and projection outbox |
| Review Machine factory | Deterministically instantiate approved guardrail templates and validate concrete machine/trigger/source bundles |
| RE / PE | Native deterministic recognition, governed dispatch and configured source ingress |
| OpenClaw resident instantiator | Resolve the exact binding, create scoped task contexts, run permitted tools and return typed proposals |
| RAG | Authorized guidance/evidence retrieval pinned to source and index versions |
| Manager | Observe case/machine/context lineage, pending publication, source freshness and actionable failures |

CSS is the primary integration point for these processes: clients discover an
asset in its POD, submit a review command through the Solid-facing command
service, and observe its case/finding/receipt resources. A proposal container
can accept authorized immutable submissions; the canonical service consumes,
authenticates and deduplicates them. Alternatively a command endpoint can sit
alongside CSS. These are implementation alternatives, not claimed native CSS
workflow APIs. Select one transport for the initial slice and publish its
command/receipt contract.

Ordinary authorized POD writers must not be able to grant approval by editing
a case status or uploading a file named approved. Only the trusted projection
writer updates authoritative case views. Direct calls to archive, RAG, or
agent tools enforce the same task scope; they cannot bypass the Solid-facing
boundary using an unrestricted shared credential. User/admin power over POD
storage remains a trust boundary; preserve independent ledger checkpoints.

## The pointer through ISRE and OSRE

ISRE is the numeric perceptual snapshot consumed before recognition. OSRE is
the resolved, committed machine output. A POD URI is structured context, not
a numeric perceptual value. Pointer continuity therefore requires two
coordinated records:

1. **Control record:** declared predicate values in allocated PE input lanes,
   recognized by the dFSA and expressed through the approved output lanes.
2. **Binding record:** immutable execution metadata naming the POD resource,
   exact content revision/hash, review case/version, workflow/template version,
   dependencies, machine instance, authorized context and execution generation.

Both belong to one admitted work item. The binder durably commits a binding
and only then admits its observations to PE. Before the RE step, the
integration records a step-binding receipt connecting the effective machine
input snapshot to that binding, engine instance and execution generation.
On output, the dispatcher resolves that exact receipt. It must reject a
missing, ambiguous, stale or mismatched binding. A generation token may live
in trusted metadata; encoding it as a float is not an alternative.

The initial binder serializes admission per machine instance under a lease:
clear or fence the previous stage's sources, install the current binding,
admit the declared observation set, capture the actual effective snapshot,
and retain that binding until its output receipt is resolved. Verify that
snapshot against the admitted set before dispatch. A partially delivered set,
expired lease, conflicting contributor or background push must not dispatch
work against a different binding. A transport response alone does not prove
which values the RE consumed. These synchronization/fencing guarantees require
implementation and live tests; current PE ingress is not presumed transactional
with the document store.

This step-binding propagation is a **required new cross-runtime contract**.
Current generic trigger envelopes do not establish it. It needs a reviewed
metadata extension or a durable companion association supported by PE and
dispatch adapters. Do not silently add fields to existing strict envelopes.
Expose only stable contract fields across runtimes; implementation-specific
internal representations remain internal under the canonical surface spec.

The causal chain is:

```text
dokieli / authorized client
  -> Solid asset reference + review-command proposal
  -> canonical service: authenticate, version-check, persist work binding
  -> binder: configured source ingress + exact step-binding receipt
  -> ISRE predicates -> asset Review Machine dFSA -> committed OSRE
  -> PE trigger + durable binding association -> dispatch outbox
  -> OpenClaw resident instantiator -> scoped POD/Beacon/RAG tools
  -> immutable result proposal -> canonical validation + transition receipt
  -> configured completion source -> next ISRE -> next dFSA recognition
  -> POD/RAG publication from canonical outbox
```

The POD pointer is available throughout this chain by the binding identity;
OSRE does not contain or confer the pointer. The agent obtains the exact
structured reference only after the instantiator checks the committed output,
binding lineage and current authority. Each handoff names its predecessor
receipt and input revision. No agent chooses a new case merely by returning
a URI, machine ID or region offset.

Case version, content revision and execution generation are distinct. The
dispatch pins the pre-action case version; a successfully committed result
names its successor case version. Validation accepts that explicit successor
relation, not an unversioned lookup of the current case. Content changes fence
the old action and start a new attempt against the new revision.

## Guardrail class and dynamic instantiation

The reusable class is a reviewed, versioned bundle of a dFSA template, unique
CES patterns, trigger definitions, source schemas/mappings, role policy,
transition guards, source freshness rules, output semantics and conformance
cases. A configured compiler binds a class to one asset. The class hash and
compiler version identify what ran; an LLM cannot redefine its permissions,
triggers, source mappings or terminal states.

Instantiation proceeds as a reconciled deployment, not an assumed atomic set
of remote calls:

1. Authorize the review request and pin the asset revision, case and class.
   Derive an opaque stable instance identity from tenant/asset/workflow scope;
   record cycle, generation and target RE/PE instance separately. Avoid entity
   names or document titles in public machine IDs.
2. Reserve capacity, names and lane leases through the approved allocation
   authority. Generate a machine definition, triggers, source mappings,
   context policy and a deployment manifest. The payload cannot choose its
   vector regions. Refuse collisions, exhaustion or unsupported runtime APIs.
3. Validate schema, unique CES patterns, interconnections, output arbitration,
   role constraints, region allocation and semantic descriptions before load.
4. Record provisioning intent; install the components inactive, read them back
   and verify their hashes. Loading must not activate silent integration
   sources. Quarantine or compensate partially installed bundles.
5. Commit the asset-to-instance binding and READY receipt only when all parts
   agree. Then admit the first work observation. A machine output is actionable
   only while the manifest, generation and context grant remain current.
6. On completion/cancellation, fence workers, stop new dispatch, drain or
   quarantine pending results, snapshot evidence, deactivate sources and
   triggers, unload the machine and release leases. Retain durable tombstones.
   Reusing a slot requires a fresh generation, clearing prior values/history
   and cache state, and proof that late completions cannot address the new owner.

Dynamic trigger and source lifecycle support, safe runtime region allocation,
restart restoration, and cross-runtime load/unload parity are implementation
gates, not capabilities established by this document. A bounded preallocated
pool of per-asset slots is an acceptable first implementation of dynamic
instantiation. It preserves one live machine per asset while avoiding
uncontrolled growth of the universal vector. Queued assets must remain visibly
pending when the pool is full.

The machine registry exposes concrete active instances and their template,
case and lifecycle identities. The instance registry identifies RE/PE targets.
The arbitration registry and source mappings account for concrete lane leases.
The semantic-bus inventory records actual declared buses; a structured POD
reference is not automatically a native bus. The cesgen registry identifies
reviewed template conformance and applicable recorded shards. Static corpus
counts must not be incremented for every temporary case as if it were a new
accepted corpus machine. The distinction between installed definitions and
runtime instances needs explicit loader, catalog and Manager contract support.

Publish template semantics for the guardrail class and case-scoped instance
semantics for each deployment: instantiatedFrom, guardsAsset, usesRevision,
dispatchesAction, observesReceipt and fencedByGeneration. Concrete semantic
shards and instance manifests retain the same opaque identifiers and hashes.
New class behavior or corpus definitions follow ordinary corpus/domain
approval and affected CES-shard recording; instantiation does not bypass it.
Per-case machine instantiation itself is not a Git commit or release.

## Review sequence and deterministic gates

| Phase | Verified ISRE observation | dFSA-mediated OSRE outcome | Agent/context and required result |
| --- | --- | --- | --- |
| Intake | Registered asset, current binding, valid authority | Request intake verification | Fetch exact POD/Beacon revision; verify hash, type and provenance |
| Structure | Verified intake receipt for this generation | Request extraction/normalization | Produce immutable structured rendition with source locations and typed values |
| Prepare | Accepted rendition and applicable source snapshot | Request accounting preparation | Retrieve scoped RAG guidance; draft or reconcile only owned asset types |
| Verify | Candidate registered; required inputs still current | Request evidence and accounting checks | Validate arithmetic, citations, requirements and dependencies; record exceptions |
| Findings | Verification receipt/finding change admitted | Request disposition or rework | dokieli/reviewer proposals map to identified findings on exact revisions |
| Decision | Authorized decision recorded; required findings closed | Recognize accepted/rejected/blocked review outcome | Canonical service commits exact-revision decision; source reports that receipt |
| Publish | Accepted decision receipt still applicable | Request approved publication | Outbox projects POD/RAG; completion reports published or pending |
| Change | Verified upstream/source/policy change | Request impact assessment / recognize stale | Revalidate dependencies and supersede obsolete tasks; preserve history |

These are proposed logical outcomes, not numeric constants or schema-valid
CES definitions. The compiler must assign distinct CES patterns and declared
nominal encodings from an approved class; existing 0/0.5/1 semantics cannot be
repurposed as confidence, approval authority or money. No offsets are assigned
here. A transition-request output does not assert that its requested external
effect has completed. Completion requires its own authenticated receipt and
subsequent source observation. Rejection and failed checks remain explicit
branches; lack of an observation never means success.

An approval command and native recognition are different events. The
canonical service authorizes the decision; a later machine observes the
committed decision and can mediate publication. Alternatively a machine can
request the decision command, but the service still checks every gate. This
prevents an agent-generated success value from approving its own work.

## Multiple actions without cross-asset contamination

For a quarterly reconciliation, the same asset pointer reaches intake,
extraction, standards guidance, reconciliation, checking and reviewer tasks.
Each action gets a child context with only its required operations. Extraction
can read originals and create renditions; preparation can read relevant RAG
and create a draft; checking can write findings; a reviewer can submit a
decision. None inherits every permission of the root workflow.

The ledger binds every source observation to case/cycle/generation, machine,
stage, logical action ID, attempt, input revision, dependency snapshot and
result receipt. Multi-source input gates can be satisfied only by receipts
from the same binding and permitted predecessor actions. Source TTL is a
liveness constraint, not proof of business validity; dependency/revision and
authorization checks are also required. After restart, recover state and
bindings from durable checkpoints and verify them before restoring sources.
Do not replay destructive effects merely by replaying historical observations.

Parallel checks use distinct child IDs and immutable receipts. A canonical
join verifies the required set and records an aggregate receipt for the parent
source. It cannot combine a revenue check from one document with a citation
check from another. Downstream asset handoffs create new bindings to the next
asset and explicit input references to predecessors; they never mutate the
existing machine's identity mid-flight.

## Document and context protection

POD metadata includes immutable content identity, classification, provenance,
dependencies and review references. Store no bearer tokens or persistent
signed download URLs in pointers. Check access before listing/searching as
well as fetching. The resolver verifies authenticated principal, context,
entity/period/purpose, operation and exact version at every access, including
Beacon, historical versions, annotations, extraction text and RAG projections.
Allowlist archive destinations. Protect embeddings, caches and logs under the
same classification; model-provider egress requires explicit policy.

Access is the intersection of POD permission, archive policy, principal
authority, class policy and current context grant. The POD URI is an identity,
not a capability. Revocation fences future access and commit; already disclosed
content cannot be recalled. The proposed authorization epoch must be checked
by trusted services; it is not self-authenticating because it appears in JSON.

dokieli annotations bind selectors to both document revision and rendition
hash. Revisions do not silently move finding anchors. Re-anchoring is an
audited action with a new target. Human social approval annotations are
proposals until identity and policy checks succeed. Generic POD edits cannot
assert canonical decisions. Retrieved instructions cannot grant tool rights.

## Transformations, persistence and recovery

The [handoff example](handoff.example.json) conforms to the adjacent proposed
[design schema](handoff.schema.json). Its reserved `.invalid` POD addresses,
hashes and identifiers are synthetic. It is not a current PE trigger payload.
Use authenticated service identity, not JSON actor names, as authority.
Production validation must also check referenced resources and semantic
relationships; schema validation alone cannot establish correctness.

Define a canonical logical-request serialization before implementation. Its
hash includes operation, pinned inputs, class/policy, scope, generation and
required decision references; retry-specific attempt IDs, transport envelope
IDs and timestamps are excluded. Thus a new delivery attempt can reuse the
logical action ID without accidentally looking like a changed operation.
The illustrative hashes in the example are placeholders, not computed proof.
The context grant is a protected server-side record containing principal,
allowed operations/resources, entity/period/purpose, authorization epoch,
expiry and parent grant. Possessing its reference does not authorize its use.

For each operation: pin inputs and execution grant; perform external work
outside the database transaction; archive an immutable unapproved candidate;
then recheck state, authority, fences, required findings and dependencies.
Atomically commit the canonical transition, event, idempotency receipt and
projection outbox. Finally publish POD and RAG projections. Do not assume a
transaction across CSS, Beacon, lifecycle state and the vector runtimes.

| Failure | Required recovery |
| --- | --- |
| Duplicate logical handoff | Same request hash returns original receipt; changed request under same ID is rejected |
| Candidate stored but commit fails | Reconcile candidate by operation ID; retain unapproved or apply retention policy; no implied approval |
| Commit succeeds but publication fails | Keep committed state and pending publication; retry outbox without regenerating content |
| Concurrent document or case update | Reject expected-version mismatch; reconsider against new snapshot |
| Old worker or reused machine slot | Reject generation/lease mismatch even if source TTL has not elapsed |
| Lost, duplicate or reordered Solid notification | Reconcile from canonical sequence/checkpoint; notifications only wake processing |
| Approval remains historical but dependency changes | Mark current applicability stale and block current-approved retrieval |
| Partial machine provisioning | Do not admit observations; quarantine/compensate and reconcile intent |

For supported POD representations, use conditional writes with the server's
ETag and separately verify document content hashes. Test installed CSS
behavior. A stale conditional write triggers reconciliation, not overwrite.
Hash chains and ACLs do not alone make an administrator-controlled ledger
tamper-proof; retain protected backups/checkpoints and authenticated receipts.

The audit chain connects command, case binding, provisioning manifest,
source observation, step-binding receipt, CES/output, dispatch, context/tool
receipts, proposal, decision and publication receipt. Git services record
reviewed class definitions and deployment changes; private per-document
events remain in the protected ledger, with sanitized hashes/checkpoints
anchored where policy requires. No confidential asset content goes into Git.

## Delivery and acceptance

1. In `_Machines`, review the class contract, lifecycle and semantics before
   adding concrete templates. Keep these design schemas distinct from current
   native schemas. Pin the factory/compiler inputs and conformance fixtures.
2. In the canonical lifecycle service and resident OpenClaw runtime, implement
   bindings, source-to-step correlation, contexts, fences and transformation
   receipts. Reuse existing revision/dependency validation and SQLite
   transactions. The PE delivery ledger must not become a second case engine.
3. In CI, add CSS/Beacon adapters, bounded instance provisioning and the live
   native conformance harness. In PE/runtime repositories, add reviewed
   metadata associations, dynamic source/trigger lifecycle and restart/unload
   behavior. Verify all voting runtimes against the same observable contract.
4. Connect dokieli to protected case/annotation resources and governed commands.
   Connect RAG only after authorized exact-version resolution. Show case and
   machine/context lineage in Manager with pending/stale/quarantined states.
5. Demonstrate one synthetic reconciliation from POD intake through several
   agentic actions and approved-test publication; then demonstrate two assets
   concurrently with no binding or source contamination.

Acceptance requires evidence for: pointer continuity across every machine
boundary; missing-binding refusal; two-asset isolation; exact revision/hash
checks; changed dependencies; same-ID retries; wrong-ID/wrong-stage receipts;
out-of-order completions; expired/revoked workers; stale lane values after
slot reuse; source inactivity before ingress; concurrent reviewers; doctored
annotations; agent self-approval rejection; crashes before/after commit;
partial provisioning; pool exhaustion; unload/restart restoration; delayed
POD/RAG projection; and complete audit-chain reconstruction. Exercise actual
native ISRE/CES/OSRE and the scoped agent tools, not only a mock document loop.

The first implementation stays SYNTHETIC / TEST_ONLY. Ordinary independent
review and production admission remain required outside the explicit testing
waiver. Approval of this direction does not close the original accounting
findings or source-control obligations.

References: [Solid Protocol](https://solidproject.org/TR/protocol),
[Solid WAC](https://solidproject.org/TR/wac),
[Solid Notifications](https://solidproject.org/TR/notifications-protocol),
[dokieli](https://dokie.li/docs),
[Web Annotation](https://www.w3.org/TR/annotation-model/), and
[PROV-O](https://www.w3.org/TR/prov-o/).
