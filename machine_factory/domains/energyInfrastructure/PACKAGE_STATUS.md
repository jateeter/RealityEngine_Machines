# Package status and remaining decisions

## Current acceptance scope

The [owner-approved acceptance scope](acceptance/scope.json) governs this active document: **all required hardware is simulated**, and **template/generic assets may be used in every case**. EI04 must provide templates for each asset class defined by the associated applicable standards, with edition/clause traceability; EI18 must verify a simulated counterpart for every hardware dependency. Generic reference parameters replace site-specific prerequisites for corpus admission. Actual software execution and genuine admission/reviewer evidence remain mandatory. Physical equipment certification and field commissioning are separate future activities. Historical research notes retain their original research context and do not override this decision.

As of 24 November 2026: **DESIGN_PACKAGE_NOT_ADMITTED**, version 0.2.0.

Implemented package assets are the unchanged 187-definition clone, NIST PDF receipt, research-backed standards/public-implementation/RAG inventories, proposed lifecycle/security/agent/carbon contracts, documentary templates, 20 risk scenarios, 43 unexecuted acceptance cases and a ten-phase workplan. Actual offline integrity results are in [verification-summary.json](verification-summary.json). Its PASS applies only to package consistency and provenance.

Not performed: machine adaptation/new identity or allocation, source/service bootstrap, protocol/model/agent installation or integration, approved RAG extraction/indexing, current wire probes, native regression/reasoning, software/simulated-hardware tests, accredited conformance, site commissioning, production risk acceptance, domain admission, deployment, domain-specific release or deployment. The baseline source package and GitHub issue backlog are published; EI03 reference-scope additions proceed through their own PR.

## Blocking design decisions and evidence

| Decision/evidence | Accountable role | Closure needed |
|---|---|---|
| Canonical identity and factory mapping | Domain/corpus owner | EI02 selects energy-infrastructure → energyInfrastructure with tested resolver support; no active domain admission |
| Coexistence and native plan | Domain/corpus owner | EI02 records 170 adaptations/17 replacements, ENI identities and nonactive [86016,102400) windows; EI08 must author behavior and recheck/register candidate ranges |
| Generic reference scope, utility roles, voltage and device cohort | Grid/protection owner | Reviewed generic scenarios and applicable standards/profile editions; actual site agreements/certificates optional for corpus acceptance |
| Reference settings, sensing/time budgets and critical-load plan | Grid/protection reviewer | Reviewed generic parameters with explicit units, provenance and simulation validity; no claim they are universal normative limits |
| Normative source and provider rights | Standards/RAG/data owners | Lawful acquisition, embedding/retrieval/redistribution scope and current source approvals |
| Native 2030.5 or required DNP/market profile | Adapter owner | Actual selected peer/library, license/maintenance review, immutable pins, exact supported option matrix |
| Security and operational authority | OT/operations owners | Named risk owners, approved zones/conduits, calibrated detection and residual-risk decisions |
| Model/agent/RAG qualification | localAI/OpenClaw/assurance owners | Actual artifacts, scoped tools/ACLs, prompt-injection/grounding/fallback benchmark and transport evidence |
| Carbon method, provider and target path | Carbon/grid owner | Reviewed generic accounting boundary, replayable provider fixtures, ledger and approved reference trajectory; real regional connection optional |
| Admission integration runner and test capacity | CI/simulation owner | Real isolated driver, exact candidate corpus reachability and simulated-required-hardware coverage and actual software execution evidence |

Implementation inventory selections mean **selected candidates for evaluation**, not production commitments or certification. DNP3 public-source licensing and OpenDNP3 archival status are explicit constraints; no unrestricted maintained DNP stack or native-wire-certified 2030.5 pair has been selected. CUPID's NATS/JSON extensions are not native IEEE 2030.5 conformance proof.

Source inspection anchors: CI `c985c0d7b592013d4d830b079d5af1663d407b6c`; localAI `edcb3f54b2f8810ec47b891a42f1b8a2916c42ca`; OpenClaw `f52fb9ba339c06f6f01cd941d94fde89b31d6359`; Manager `443520d5c54c99f546de8c4d01bd1682ef1b1840`; asset stack `cb2c4bbb771ddb30a7900c7745cb29e08bafb517`. These identify inspected source, not active runtime state. Future implementation must recheck current contracts and exact endpoints.

## Backlog publication

The current detailed backlog is [acceptance/issues.json](acceptance/issues.json). Publication status and actual GitHub URLs are recorded there. The original published issue snapshot records all 24 workstreams as PLANNED; current source progress is tracked separately and all 43 behavioral cases remain NOT_RUN. EI04 template/class coverage and EI18 simulated-hardware coverage are required future deliverables, not claims that templates or models have been built.

## Published issue backlog

[Umbrella #264](https://github.com/jateeter/RealityEngine_Machines/issues/264) tracks the 24 workstreams [#265–#288](https://github.com/jateeter/RealityEngine_Machines/issues?q=is%3Aissue%20%22energyInfrastructure%22). [Issue index](acceptance/issues.json) records exact bodies, dependencies, primary case ownership and successful readback of all 25 published issues. [Coverage requirements](acceptance/coverage-requirements.json) enumerate obligations for all 47 standard entries and 43 cases; template/class and simulated-hardware fulfillment remain future work. No cases have run and the domain remains unadmitted.

## Source implementation progress

EI01 baseline is merged in [PR #289](https://github.com/jateeter/RealityEngine_Machines/pull/289), commit `eae885ea2f9ed8204bbe6c9c0a0de6fc2baa78c8`; its working branches were deleted. [Source-progress events](acceptance/progress.json) distinguish merged work from the original issue and phase planning snapshots.

EI03 now has [generic reference microgrids and authority](documents/workflow/reference-microgrids.md) and a [machine-readable scope](examples/reference-microgrids.json). These are scope specifications, not executed acceptance cases. EI02 now records [identity/coexistence](documents/workflow/identity-and-coexistence.md), [187 dispositions](machine-dispositions.json) and factory-path support. EI04 complete standards-defined class coverage remains pending; a partial public-model template library is now available below.

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


## Owner-selected FSGIM integration context

[ASHRAE Standard 201](assets/fsgim-integration.md), recorded as OP23, now governs the asset integration context. The current inventory has 47 standards/framework entries and 19 RAG source families. Crosswalks cover 19 reference roles, 112 SunSpec models and 58 OPC UA DI types. The original published backlog remains a historical snapshot; current context and source progress are explicit additions. Normative UML collection/equivalence, exact property/conformance mappings, reviewed operational instances and actual peer/simulator integration remain pending.


### Draft FSGIM asset/function bindings

[Four source-linked draft projections](assets/function-bindings.md) now cover the generic and three reference fixtures, with scoped identities, inactive functions, DI type facets and single-view resource accounting groups. This advances typed project bindings; normative model/property review, actual readings/units/time/boundaries, solver and protocol/runtime verification remain pending.
