# AI governance regime (organizational wrapper)

Canonical domain: `ai-governance-regime` · Package `0.1.0-intake` · **INTAKE_NOT_ADMITTED**

This domain is the organizational wrapper around the RealityEngine. It turns the
obligations of the global AI-governance standards and frameworks into machines
and documents: ISO/IEC 42001, 42005 and 42006, NIST AI RMF and AI 600-1, the EU
AI Act, OWASP's Agentic Top 10, MITRE ATLAS, and the others listed in
[SPECIFICATION.md](SPECIFICATION.md) §2. Examples are impact assessments, AI
bills of materials, quorum-approved rule epochs, runtime watchdogs, egress
transparency, and auditor evidence packs.

It is also the **proof of workflow for new domain production** (see
[scope-decisions.json](scope-decisions.json)). Each factory step is carried out
here and recorded in [PACKAGE_STATUS.md](PACKAGE_STATUS.md), so the next domain
can follow it. The layout follows `../ifrs-accounting/`.

Start with [PACKAGE_STATUS.md](PACKAGE_STATUS.md), then
[REVIEW_QUEUE.md](REVIEW_QUEUE.md), which lists the intake findings that must be
settled before conversion.

## Contents

| Path | What it is |
|---|---|
| [SPECIFICATION.md](SPECIFICATION.md) | Architecture, gap analysis against the global frameworks, the threat model, base templates `M-GOV-01`–`14`, Solid JSON-LD schemas, and the baseline roadmap |
| [GAP_ANALYSIS.md](GAP_ANALYSIS.md) | The wrapper's threat and gap analysis: seven residual gaps |
| [HARDENING_TRANSITION_RULES.md](HARDENING_TRANSITION_RULES.md) | Input cells `16987`–`16991` and the transition rules for `M-GOV-15`–`17` |
| [RESOLUTION_WORKPLAN.md](RESOLUTION_WORKPLAN.md) | The 8-week, 4-phase workplan closing the seven gaps |
| [REVIEW_QUEUE.md](REVIEW_QUEUE.md) | Intake findings, open |
| [PACKAGE_STATUS.md](PACKAGE_STATUS.md) | Lifecycle, the production steps done and still to do |
| `schemas/governance-asset-shapes.shacl.ttl` + [`.md`](schemas/governance-asset-shapes.md) | SHACL shapes for the governance Solid-pod asset types, and their documentation |
| [templates/ISO42001-STATEMENT-OF-APPLICABILITY.md](templates/ISO42001-STATEMENT-OF-APPLICABILITY.md) | ISO/IEC 42001 Annex A Statement of Applicability template |
| `amendments/region-allocation.patch.json` + [`.md`](amendments/region-allocation.md) | Proposed ISRE band `[16960:17087]`; does not apply as written (GOV-R04) |
| `intake/` | Received inputs kept as received: both corpora (312 and 315 machines), both original READMEs, and the SoA release note |
| [admission-source-manifest.json](admission-source-manifest.json) | Every received file: its original name, its path here, its role and its sha256 |
| [machine-import-manifest.json](machine-import-manifest.json) | Conversion state: 0 canonical machines so far, the intake corpora, the seven workflow families, the proposed allocation |
| [scope-decisions.json](scope-decisions.json) | Owner decisions that define the package's scope |
| `tools/verify_package.py` | Offline integrity check |

The received files were renamed and moved, not edited. The documents still
refer to each other by their received names; `admission-source-manifest.json`
maps each received name to its path here.

## Verify

```bash
python3 tools/verify_package.py
```

This checks that every received file is present and unchanged, that every JSON
file parses, and that the two corpora are consistent (unique ids, stated counts,
315 ⊇ 312). It does not validate machines against the canonical schema, start
engines, or judge governance semantics.

## Authority and limitations

Nothing here is admitted corpus, and nothing is under `machines/domains/`. No
runtime JSON, region allocation, arbitration, or engine behavior is changed.
The received documents describe mechanisms, such as SPIFFE/TPM attestation,
offline root tokens, CRL polling sources, behavioral canaries, and C2PA egress
tagging. These are designs, not implemented infrastructure (GOV-R09). Passing
`verify_package.py` says the package is intact. It does not say the governance
is correct or that any framework is satisfied.
