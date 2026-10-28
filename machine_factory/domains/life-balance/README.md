# LifeBalance operating environment and RAG guidance

Version 1.0.0 · Prepared 2026-10-28 · DESIGN_ONLY_NOT_DEPLOYED

Start with [the desired operating outcome](documents/workflow/desired-operating-outcome.md), then [the nutrition journey](documents/workflow/nutrition-optimization-example.md). Use [the interaction guidance template](templates/interaction-guidance.md) for every family, with its [family card](families/). Development tracking: [Machines #225](https://github.com/jateeter/RealityEngine_Machines/issues/225).

## Standard domain placement

Canonical design assets: `machine_factory/domains/life-balance/`. Existing executable definitions remain at `machines/domains/life-balance/`; this package does not modify them. Non-machine JSON belongs here, outside loader discovery.

The reference is the prepared IFRS Accounting document-workflow package (225 provisional candidates, document catalog, templates, family runbooks, lifecycle/dependencies, workflow contract) and its role-separated RAG ingestion manifest. This adapts that organization; it does not copy accounting rules or assume a shared deployment schema. The original factory folder is named `IFRS_Acccounting`; new domain names use lowercase kebab-case to match canonical runtime slugs.

## Contents

- `documents/workflow/`: desired outcome, worked example, universal interaction protocol, daily runbook and RAG policy.
- `templates/`: reusable guidance, subject profile, plan, observation, evidence receipt, action/approval and outcome review templates.
- `families/`: ten scoped guidance cards covering all 110 machines.
- `document-asset-catalog.json`, `document-dependencies.json`, `machine-document-duty-index.json`: asset ownership, lifecycle, lineage and explicit machine coverage.
- `agentic-workflow-contract.json`, `rag-evidence-contract.json`: design contracts; production connectors must implement/enforce them.
- `source-manifest.json`: external reference candidates and remaining evidence requirements; no full clinical-source corpus is included.
- `ingestion-manifest.json`: allowlisted local design documents with hashes and proposed collection routing. Not an executable ingestion request or claim that files are indexed.
- `examples/`: synthetic context and structured interaction example, excluded from production advice retrieval.
- `acceptance/`: designed scenarios, release criteria and actual package-integrity verification only.
- `asset-manifest.json`: checksum inventory excluding itself; `tools/verify_assets.py` checks package structure and references.

## Status and authority

These are desired behavior specifications and generated procedural guidance, not clinical recommendations, approved personal care plans, live agent bindings or proof of clinical benefit. A nutrition example illustrates planning and tracking; it does not prescribe nutrient targets. Clinical reference passages and personal records must be sourced, scoped and reviewed before personalized guidance. No runtime/agent schema is changed and no domain acceptance claim is added.

The IFRS pattern of one accountable owner, immutable revisions, independent review where required, staleness propagation, source receipts and separate document/native channels is preserved. Identity, consent and tool permissions must be enforced by production gateways; names/booleans in documents are not authorization.

## Validate locally

From this directory: `python3 tools/verify_assets.py`. This verifies file integrity, machine-duty coverage, dependency acyclicity and manifest links; it does not call a model, ingest documents, execute tools or certify live behavior. Production integration and three-engine acceptance remain under RealityEngine_CI and issue #225.
