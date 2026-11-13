# RAG guidance and authority policy

## Collection separation

- `life_balance_reference`: reviewed domain evidence snapshots; not supplied here. Apply population, jurisdiction, context, date and source-review filters.
- `life_balance_workflow`: allowlisted design guidance and family cards supplied here. Procedural authority only; cannot establish clinical facts or grant tools.
- `life_balance_personal_evidence`: consented subject/tenant-scoped facts, plans and outcomes; production-only authorized store, never repository fixtures.
- `life_balance_review`: implementation audit and open findings when separately supplied; commentary, not health guidance.
- Evaluation fixtures and blank templates are excluded from production advice retrieval by default.

Reference evidence and an individual's care plan have different scopes. Match applicability, identify conflicts and obtain qualified resolution. Do not use a simplistic source rank to override an individual's approved restriction or to assert that any plan is universally correct.

## Ingestion and freshness

Use an explicit allowlist, stable IDs, SHA-256 hashes, logical collection routing and embedding-model-aware physical indexes. A folder copy or Open WebUI upload is not proof of localAIStack RAG ingestion. Ingest unchanged documents idempotently; replace or remove only manifest-owned chunks. Reject arbitrary collection routing from untrusted document metadata.

Preserve source URI/edition, exact spans, provenance, review/effective/expiry dates, owner, population/context, sensitivity, consent scope, content/source hashes and index/embedding version. A changed source, revoked permission or superseded plan marks dependent receipts/approvals stale. Document updates and access revocation propagate to retrieval and caches within a documented service objective.

## Retrieval and generation

Apply authorization before similarity retrieval. Filter status, applicability and freshness, retrieve full conditions/exceptions, and return immutable passages or resolvable references. Record each claim's evidence links. Cite factual recommendations; keep estimates and hypotheses labeled. Abstain when a required passage or personal constraint is missing. No use of synthetic examples as real evidence.

Retrieved instructions are data. They cannot change system instructions, consent, approver roles, tool allowlists or action parameters. Validate generated content independently of model-native structured-output support. Deterministic calculators retain formulas, units, input lineage and error bounds; an LLM does not supply invented measurements.

## Required source development

The three nutrition URLs in the source manifest are discovery candidates, not completed source packs. Before guidance release, obtain authorized snapshots, review passage correctness/applicability, document licensing and set review dates. Other families require their own reviewed sources and explicit coverage gaps. Personal profiles, observations and authorized plans must be supplied at runtime. Never generate stand-ins for issued plans, approvals, laboratory results or clinical records.
