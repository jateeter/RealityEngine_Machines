# Energy Infrastructure factory domain

## Current acceptance scope

The [owner-approved acceptance scope](acceptance/scope.json) governs this active document: **all required hardware is simulated**, and **template/generic assets may be used in every case**. EI04 must provide templates for each asset class defined by the associated applicable standards, with edition/clause traceability; EI18 must verify a simulated counterpart for every hardware dependency. Generic reference parameters replace site-specific prerequisites for corpus admission. Actual software execution and genuine admission/reviewer evidence remain mandatory. Physical equipment certification and field commissioning are separate future activities. Historical research notes retain their original research context and do not override this decision.

Version 0.3.0 · 25 November 2026 · **DESIGN_PACKAGE_NOT_ADMITTED**

This package defines the standards, security, model/RAG integration and evidence work needed to develop an integrated microgrid domain from the unchanged energy clone. Read [the report](<reports/Secure microgrid interoperability.md>), then [the admission workplan](WORKPLAN.md). The exact requested factory directory is `energyInfrastructure`; `energy-infrastructure` is the selected canonical slug under [the EI02 identity decision](identity-decision.json); folder mapping is explicit and grants no admission.

## Owner-selected energy integration context

[ASHRAE Standard 201 FSGIM](assets/fsgim-integration.md) is the integration context for appropriate energy assets, including [OPC UA DI type templates](assets/device-types.md). The architecture retains source-specific semantics and uses provisional project crosswalks rather than asserting normative equivalence.

## Design and evidence map

| Asset | Purpose |
|---|---|
| [Report](<reports/Secure microgrid interoperability.md>) | NIST-guided synthesis and decisions |
| [Standards inventory](standards-inventory.json) | 47 standards/framework entries with applicability, editions, owner sources and gaps |
| [Implementation inventory](implementation-inventory.json) | 29 public implementation candidates with license/scope/maintenance limits |
| [Architecture](documents/workflow/architecture.md) | Interfaces, sensing and connected/island/black-start/reconnect lifecycle |
| [Security and dynamic risk](documents/workflow/security-and-dynamic-risk.md) | Zones/conduits, threat reassessment and deterministic command gate |
| [Agent/model contract](documents/workflow/agent-model-integration.md) | Scoped tools, local service boundaries and independent authorization |
| [RAG inventory](rag-source-manifest.json) and [governance](documents/workflow/rag-collection-and-governance.md) | 19 source families, 7 carbon providers, rights/scopes/collection states |
| [Carbon contract](documents/workflow/electricity-carbon-intensity.md) | Energy weighting, boundaries, storage/export and target/forecast separation |
| [Risk inventory](risk-register.json) | 20 scenarios, accountable roles, controls and case links |
| [Acceptance cases](acceptance/cases.json) | 43 proposed tests, all NOT_RUN |
| [Workplan](WORKPLAN.md) and [phase inventory](acceptance/workplan.json) | 10 evidence-gated phases to authoring, verification, admission and deployment |
| [Profile template](templates/interoperability-profile.json) and [DER example](examples/der-supervisory-profile.json) | Reusable documentary profile with site values deliberately unset |
| [Package status](PACKAGE_STATUS.md) | Actual scope, gaps and open decisions |
| [Verification summary](verification-summary.json) | Actual offline package-integrity result only |

## Preserve the clone and its authority boundary

`machines/` contains the 187 unchanged source JSON definitions plus the original README; [machine-import-manifest.json](machine-import-manifest.json) records their source commit, paths and hashes. The original README describes the initial 160-machine batch. Original names, ENX codes, category `energy`, vector allocations and agent references are preserved as provenance, not an independently addressable admitted domain. Runtime manifests and canonical source machines are unchanged.

[The supplied NIST PDF](intake/NIST.SP.1108r4_1.pdf) and the source receipts under `assets/` distinguish original and supplemental collections. No approved RAG extract/index exists. Research URLs are discovery evidence, not acquired licensed standards or validated datasets. No protocol library, model gateway or controller has been installed or certified. Security/control requirements describe proposed behavior; package-integrity PASS does not prove them operational.

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


### EI04 synthetic instance contracts

[Generic instance schemas, fixtures and validation](assets/README.md#generic-instance-validation) now cover all 19 functional role templates and seven document templates, plus selected raw SunSpec point bindings. Hosted tests reject invalid units/references and fabricated execution/approval claims. Draft instance validation does not establish complete normative classes, complete device profiles, safety review or simulation execution; EI04 remains open.


### EI04 reference topology instances

[Three reference topology fixtures](assets/README.md#reference-topology-instances) now reproduce the declared microgrid role, bus, connection and voltage assumptions. Validation rejects orphan/duplicate connections and scenario drift. These are topology contracts only; normative class coverage, engineering review, solver execution and behavioral acceptance remain pending.


### EI04 threat information taxonomy

[SC16 class/schema coverage](assets/threat-classes.md) now catalogs 43 STIX top-level object/container classes with clause locators and 14 supporting schemas, preserving a pinned BSD-3-Clause OASIS snapshot. Offline synthetic validation executes against these explicitly non-normative schemas. TAXII, nested/prose/errata review, normative completion and actual risk/control integration remain pending. No behavioral acceptance case or live threat assessment was executed.


### EI04 TAXII resource taxonomy

[SC16 TAXII resource coverage](assets/taxii-resources.md) now includes nine resources and two supporting records, an unchanged official source snapshot with Notices, generated project schemas and offline synthetic fixtures. This is resource-table coverage only; full prose/errata, secure peer behavior, normative completion and behavioral acceptance remain pending.


### Draft FSGIM asset/function bindings

[Four source-linked draft projections](assets/function-bindings.md) now cover the generic and three reference fixtures, with scoped identities, inactive functions, DI type facets and single-view resource accounting groups. This advances typed project bindings; normative model/property review, actual readings/units/time/boundaries, solver and protocol/runtime verification remain pending.


## EI05 synthetic measurement semantics

[Four source-bound active-power snapshots](assets/power-snapshots.md) now exercise exact decimal W/kW normalization, net-import-positive signs, selected FSGIM accounting boundaries, timestamp ordering, observation-time freshness and null-preserving quality exclusion. This is offline project-contract validation only. Native property/peer mappings, engineering review, energy/carbon balance, simulated required hardware behavior and corpus admission remain pending; all 43 behavioral cases remain NOT_RUN.


## EI05 offline SunSpec active-power subset

[The selected model 103/203 decoder and register replay](assets/sunspec-power.md) now connect pinned W/W_SF definitions to draft FSGIM accounting views, preserving signed values, missing-value sentinels and exact decimal scale conversion. This is offline byte-level software evidence only. Secure peer pairs, native status/time mappings, full simulated device behavior, engineering review and admission remain pending; all 43 behavioral cases remain NOT_RUN.


## EI05 offline meter energy intervals

[Selected SunSpec import/export counters and exact interval differences](assets/meter-energy.md) now provide separate synthetic Wh/kWh quantities linked to the draft facility PCC Meter. Missing data, resets/rollovers, scale changes and stale endpoints never become zero-energy assertions. This is an offline accounting prerequisite; no carbon factor, native peer, complete device simulation or admission is verified. All 43 behavioral cases remain NOT_RUN.


## EI14 synthetic imported-electricity carbon ledger

[The bounded retrospective ledger](assets/import-carbon-ledger.md) now computes exact energy-weighted imported-electricity emissions/intensity from compatible synthetic meter intervals and factors. Imports/exports remain separate; incompatible, missing or stale inputs cannot become zero intensity. Real providers, uncertainty, storage allocation, trajectories, safety/behavioral acceptance and corpus admission remain pending. All 43 behavioral cases remain NOT_RUN.


## EI14 draft synthetic storage carbon allocation

[The source-bound well-mixed storage pool](assets/storage-carbon.md) carries synthetic charging emissions through declared charge/discharge conversion losses into delivered energy and remaining inventory, with exact allocation conservation checks. This is a draft retrospective policy, not measured SOC, additional inventory emissions or operational approval. Idle losses, opening-state lineage, uncertainty, durable state, native simulation and acceptance remain pending; all 43 behavioral cases remain NOT_RUN.


## EI14 synthetic revision and trajectory archive

[The source-bound archive](assets/carbon-trajectories.md) preserves original/corrected synthetic reports and historical snapshot references while keeping forecasts and unadopted target examples separate. Digests check internal consistency, not signatures or real dispatch evidence. Durable history, trusted times, historical meter qualification, actual forecasts/targets, uncertainty, safety and acceptance remain pending; all 43 behavioral cases remain NOT_RUN.


## EI10 draft deterministic proposal rejection

[The REF01 generic storage screen](assets/proposal-screen.md) rejects selected energy reserve/capacity, power/step/import/export, critical-service, state-quality and revision violations independently of claimed carbon benefit. Passing permits only further simulation under an unapproved generic profile; control remains DENY and no execution path exists. Native authorization, solver/device behavior, concurrency, reviewed envelopes and all 43 behavioral cases remain pending.


## EI07 conservative synthetic risk posture

[The pinned STIX assessment and proposal bridge](assets/risk-assessment.md) now exercise evidence freshness, applicability/mapping and context revision checks with UNKNOWN/BLOCKED postures only. Unresolved evidence holds discretionary proposals without changing electrical/protection state or granting clearance. Actual feed provenance, risk acceptance, durable incident state, native control and all 43 behavioral acceptance cases remain pending.


## EI13 public implementation review packets

[The bounded review-only source lookup](assets/public-model-review.md) now prepares exact-source excerpts from selected pinned SunSpec/OPC UA DI material with locators, parent hashes, dependency context and retained license notices. Normative/live/private/operating requests abstain before source text reads. No source is admitted for model use, no index/model answer is created, and authenticated RAG/LLM integration and all 43 behavioral cases remain pending.

EI18 partial execution: [offline storage simulated hardware component](assets/storage-component.md) now supplies deterministic energy state, selected SunSpec power readback, process-local replay and injected fault holds. This does not run the 43 integrated acceptance cases or fulfill full hardware coverage.
