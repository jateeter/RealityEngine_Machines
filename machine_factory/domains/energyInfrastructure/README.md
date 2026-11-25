# Energy Infrastructure factory domain

## Current acceptance scope

The [owner-approved acceptance scope](acceptance/scope.json) governs this active document: **all required hardware is simulated**, and **template/generic assets may be used in every case**. EI04 must provide templates for each asset class defined by the associated applicable standards, with edition/clause traceability; EI18 must verify a simulated counterpart for every hardware dependency. Generic reference parameters replace site-specific prerequisites for corpus admission. Actual software execution and genuine admission/reviewer evidence remain mandatory. Physical equipment certification and field commissioning are separate future activities. Historical research notes retain their original research context and do not override this decision.

Version 0.2.0 · 24 November 2026 · **DESIGN_PACKAGE_NOT_ADMITTED**

This package defines the standards, security, model/RAG integration and evidence work needed to develop an integrated microgrid domain from the unchanged energy clone. Read [the report](<reports/Secure microgrid interoperability.md>), then [the admission workplan](WORKPLAN.md). The exact requested factory directory is `energyInfrastructure`; `energy-infrastructure` is the selected canonical slug under [the EI02 identity decision](identity-decision.json); folder mapping is explicit and grants no admission.

## Design and evidence map

| Asset | Purpose |
|---|---|
| [Report](<reports/Secure microgrid interoperability.md>) | NIST-guided synthesis and decisions |
| [Standards inventory](standards-inventory.json) | 46 standards/framework entries with applicability, editions, owner sources and gaps |
| [Implementation inventory](implementation-inventory.json) | 29 public implementation candidates with license/scope/maintenance limits |
| [Architecture](documents/workflow/architecture.md) | Interfaces, sensing and connected/island/black-start/reconnect lifecycle |
| [Security and dynamic risk](documents/workflow/security-and-dynamic-risk.md) | Zones/conduits, threat reassessment and deterministic command gate |
| [Agent/model contract](documents/workflow/agent-model-integration.md) | Scoped tools, local service boundaries and independent authorization |
| [RAG inventory](rag-source-manifest.json) and [governance](documents/workflow/rag-collection-and-governance.md) | 18 source families, 7 carbon providers, rights/scopes/collection states |
| [Carbon contract](documents/workflow/electricity-carbon-intensity.md) | Energy weighting, boundaries, storage/export and target/forecast separation |
| [Risk inventory](risk-register.json) | 20 scenarios, accountable roles, controls and case links |
| [Acceptance cases](acceptance/cases.json) | 43 proposed tests, all NOT_RUN |
| [Workplan](WORKPLAN.md) and [phase inventory](acceptance/workplan.json) | 10 evidence-gated phases to authoring, verification, admission and deployment |
| [Profile template](templates/interoperability-profile.json) and [DER example](examples/der-supervisory-profile.json) | Reusable documentary profile with site values deliberately unset |
| [Package status](PACKAGE_STATUS.md) | Actual scope, gaps and open decisions |
| [Verification summary](verification-summary.json) | Actual offline package-integrity result only |

## Preserve the clone and its authority boundary

`machines/` contains the 187 unchanged source JSON definitions plus the original README; [machine-import-manifest.json](machine-import-manifest.json) records their source commit, paths and hashes. The original README describes the initial 160-machine batch. Original names, ENX codes, category `energy`, vector allocations and agent references are preserved as provenance, not an independently addressable admitted domain. Runtime manifests and canonical source machines are unchanged.

[The supplied NIST PDF](intake/NIST.SP.1108r4_1.pdf) is the only collected external source. No approved RAG extract/index exists. Research URLs are discovery evidence, not acquired licensed standards or validated datasets. No protocol library, model gateway or controller has been installed or certified. Security/control requirements describe proposed behavior; package-integrity PASS does not prove them operational.

## Verify the package offline

```bash
python3 tools/verify_package.py --write-summary
```

The verifier checks checksums, JSON structure/identities/references, clone preservation, source-PDF provenance, local Markdown links and truthful planned states. It does not start engines, use credentials, ingest RAG content, run a model, access devices or claim electrical/security conformance. [asset-manifest.json](asset-manifest.json) hashes all package files except itself, its explicitly excluded verification output and OS/cache files; regeneration requires reviewed changes, not automatic acceptance of drift.

## Published issue backlog

[Umbrella #264](https://github.com/jateeter/RealityEngine_Machines/issues/264) tracks the 24 workstreams [#265–#288](https://github.com/jateeter/RealityEngine_Machines/issues?q=is%3Aissue%20%22energyInfrastructure%22). [Issue index](acceptance/issues.json) records exact bodies, dependencies, primary case ownership and successful readback of all 25 published issues. [Coverage requirements](acceptance/coverage-requirements.json) enumerate obligations for all 46 standard entries and 43 cases; template/class and simulated-hardware fulfillment remain future work. No cases have run and the domain remains unadmitted.

## Source implementation progress

EI01 baseline is merged in [PR #289](https://github.com/jateeter/RealityEngine_Machines/pull/289), commit `eae885ea2f9ed8204bbe6c9c0a0de6fc2baa78c8`; its working branches were deleted. [Source-progress events](acceptance/progress.json) distinguish merged work from the original issue and phase planning snapshots.

EI03 now has [generic reference microgrids and authority](documents/workflow/reference-microgrids.md) and a [machine-readable scope](examples/reference-microgrids.json). These are scope specifications, not executed acceptance cases. EI02 now records [identity/coexistence](documents/workflow/identity-and-coexistence.md), [187 dispositions](machine-dispositions.json) and factory-path support. EI04 standards-defined class templates remain future work.

## EI02 identity implementation

[The identity decision](identity-decision.json) selects `energy-infrastructure`, preserves `energyInfrastructure`, and coexists with accepted energy. [Dispositions](machine-dispositions.json) cover all 187 originals with new ENI identities and a collision-checked nonactive native plan. [Identity guidance](documents/workflow/identity-and-coexistence.md) documents mapping, rewiring and compatibility. Candidate machines, registered domain ranges and behavioral acceptance remain unimplemented.


## EI04 partial source-backed templates

[The public-model library](assets/README.md) now supplies 112 reproducible SunSpec templates, exact source hashes, retained license and 46 explicit coverage gaps. Complete normative class coverage and simulator bindings remain pending; EI04 stays open. Existing complete-delivery planning flags do not describe this supplemental partial library.
