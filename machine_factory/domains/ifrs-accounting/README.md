# IFRS document asset workflows

[Read the behavior sweep and 68-asset inventory](DOCUMENT_BEHAVIOR_REVIEW.md).

Updated candidates: **225 machine JSONs (version 1.4.0), 225 agent JSONs, 16 families and 1,459 document duties**. Native execution, approved bounded numeric encoding and PRECEDENCE/MAX remain unchanged. The PE analyst binding is preserved; document operations use a separate schema-supported binding and sidecar.

## Contents

- `machines/domains/ifrs-accounting/`: replacement native machine candidates with inline document-workflow contracts.
- `agents/ifrs-accounting/`: corresponding agent candidates, proactive motivations/duties and document bindings.
- `document-asset-catalog.json`: 68 asset types, source/control references, fields, owners, dependencies and triggers.
- `families/` and `runbooks/`: accountable family workflows and readable maintenance duties.
- `templates/`: explicit draft templates, with unresolved fields; no actual client financial documents.
- `tools/document_workflow.py`: local outbox, validated native-observation assessment adapter, immutable revision store, review/staleness guards and draft renderer.
- `schemas/`: matching candidate agent schema and workflow/context/event/revision/money contracts.
- `semantics/document-workflows.ttl`: independent documentary RDF graph, not a regenerated native corpus ontology.
- `source-requirements.json`: corrected 595-control review snapshot used as source context.
- `agentic-workflow-contract.json`: execution stages, ownership, permissions and integration boundaries.
- `proofs/`: actual schema/assembly/lifecycle checks and the scope of their claims.

Original repositories and live engines were not modified. The new metadata requires a document dispatcher/tool connector to execute automatically. The local reference executor is supplied and tested; financial evaluators, live RAG and reviewer connectors are separate integration work. Existing accounting acceptance findings remain open.

## Run the incomplete example

From this bundle directory, using a new scratch store:

```bash
python3 tools/document_workflow.py plan --store /tmp/ifrs-document-example --context examples/context.json --request examples/period-open-request.json
python3 tools/document_workflow.py draft --store /tmp/ifrs-document-example --context examples/context.json --request examples/source-draft-request.json
python3 tools/document_workflow.py render --store /tmp/ifrs-document-example --context examples/context.json --request examples/source-draft-request.json
```

This creates tasks and a deliberately incomplete source-register draft. It does not approve anything. For a recognizer observation, use `observe --machine machines/domains/ifrs-accounting/<machine>.json` with an observation request containing machineId, sequenceId, outputVector and providerRef. Observation output is an assessment request, not an accounting fact or approval.

`request-review` requires assetTypeId and expectedRevision. `approve` is an independent-review/operator operation, forbidden to drafting agents; it requires the exact revision/hash, assigned reviewer, evidence/citation/reconciliation checks, no unresolved items and matching RAG source/index provenance. Production connectors must enforce these rights. Library name/boolean checks are not identity or accounting proof.

## Reproduce and verify

From the original workspace root:

```bash
python3 outputs/ifrs-document-workflows/reproduce/build_document_workflows.py --workspace-root "$PWD"
python3 outputs/ifrs-document-workflows/tools/verify_update.py
python3 outputs/ifrs-document-workflows/tools/test_document_workflow.py
```

The builder depends on the prior `outputs/ifrs-standard-coverage` and `outputs/ifrs-section-deep-review` snapshots retained in this workspace. The Node schema verifier uses the staging Ajv runtime. RDF projection uses rdflib. Do not put generated document content into numeric PE completions or treat native tokens as financial evidence.

## Verification results

All 225 machine files, 225 agent files and 225 workflow facets pass JSON Schema validation; four example contracts also pass. Static checks verify all 68 asset types, 38 sections, 595 control references, the acyclic dependency graph, one accountable family per asset and 1,459 duty links. The 33 mechanical lifecycle/observation-adapter tests pass. Regeneration is byte-identical, including the sorted documentary RDF graph. Native sequences, regions, numerical encoding/bands, arbitration, PE binding and completion format are unchanged. See `verification-summary.json` and `proofs/`. No financial accounting or live three-engine acceptance was performed.

Runbook URNs now resolve to version 2 files through `runbook-resolution.json`; prior version references are retained in machine governance metadata. `machine-change-index.json` records all before/after hashes.
