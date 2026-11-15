# Personal Health operating environment and RAG guidance

Version 1.0.0 · Canonical domain: `health-personal` · DESIGN_ONLY_NOT_DEPLOYED

Start with [the desired outcome](documents/workflow/desired-operating-outcome.md), [the daily resident/caregiver example](documents/workflow/daily-resident-care-example.md), and [the interaction template](templates/interaction-guidance.md). [The review](REVIEW.md) separates implemented contracts from open integration gaps.

## Standard placement and optimized delivery

Repository placement: `machine_factory/domains/health-personal/`. Executable originals stay in `machines/domains/health-personal/`. Non-machine JSON is deliberately outside runtime discovery. The organizational reference is the prepared IFRS Accounting document workflow/role-separated RAG package and the LifeBalance package; Personal Health semantics are independently audited, not copied from those domains.

Use one core interaction template with one relevant family card, the exact current native contract and authorized evidence. A single `semantic-inventory.json` supplies all 43 machine references, hashes, comparator/arbitration/encoding snapshots, sequence fingerprints and published buses. The ten groups are documentary assemblies, not changes to canonical `tagging.family`. Cards explain responsibilities and point to this inventory rather than duplicating mutable lane tables.

`document-asset-catalog.json` owns templates, fields and accountable roles. `document-dependencies.json` defines revision staleness. `agentic-workflow-contract.json` and `rag-evidence-contract.json` specify integration boundaries. `source-manifest.json` distinguishes existing nine-document localAIStack health seeding from additional candidate references and personal evidence still needed. `ingestion-manifest.json` allowlists procedural guidance only; it is not an ingestion command or deployment receipt. `acceptance/cases.json` provides expected evidence by case; `tools/verify_assets.py` checks package integrity and policy rejection fixtures offline.

## Authority and limitations

Generated desired-state guidance is not clinical authority, an issued care plan, a permission grant, an authenticated approval or a live acceptance result. RAG in trigger status fields means red/amber/green; retrieval-augmented generation is a separate mechanism. Native ordinals, continuous values, binary bits, temporal CESs, PASSTHROUGH arbitration and PE-owned async composition remain intact. Raw personal records stay outside the universal Reality Event.

No runtime JSON, production schema, source threshold, fan-out permission or clinical policy is changed here. Health-sensitive recommendations require applicable reviewed evidence and a qualified owner. No real personal records, source-text dumps, credentials, clinical thresholds invented by an LLM, or fake receipts are included.

## Verification

Run `python3 tools/verify_assets.py` from any directory. It checks inventory coverage, checksums, links, asset contracts, dependency acyclicity, RAG allowlist and offline policy guard cases. When installed at the standard repository path it also verifies all 43 source files and semantic fingerprints. Use `--repo /path/to/RealityEngine_Machines` for an explicit source comparison. It does not start engines, ingest content, call models, execute care actions or assess clinical benefit. See `verification-summary.json` for the actual run and its limits.
