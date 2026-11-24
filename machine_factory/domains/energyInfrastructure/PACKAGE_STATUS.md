# Package status and remaining decisions

## Current acceptance scope

The [owner-approved acceptance scope](acceptance/scope.json) governs this active document: **all required hardware is simulated**, and **template/generic assets may be used in every case**. EI04 must provide templates for each asset class defined by the associated applicable standards, with edition/clause traceability; EI18 must verify a simulated counterpart for every hardware dependency. Generic reference parameters replace site-specific prerequisites for corpus admission. Actual software execution and genuine admission/reviewer evidence remain mandatory. Physical equipment certification and field commissioning are separate future activities. Historical research notes retain their original research context and do not override this decision.

As of 24 November 2026: **DESIGN_PACKAGE_NOT_ADMITTED**, version 0.2.0.

Implemented package assets are the unchanged 187-definition clone, NIST PDF receipt, research-backed standards/public-implementation/RAG inventories, proposed lifecycle/security/agent/carbon contracts, documentary templates, 20 risk scenarios, 43 unexecuted acceptance cases and a ten-phase workplan. Actual offline integrity results are in [verification-summary.json](verification-summary.json). Its PASS applies only to package consistency and provenance.

Not performed: machine adaptation/new identity or allocation, source/service bootstrap, protocol/model/agent installation or integration, approved RAG extraction/indexing, current wire probes, native regression/reasoning, software/simulated-hardware tests, accredited conformance, site commissioning, production risk acceptance, domain admission, deployment, Git commit or source-package publication. The GitHub issue backlog is published; source-package documentation remains local pending EI01.

## Blocking design decisions and evidence

| Decision/evidence | Accountable role | Closure needed |
|---|---|---|
| Canonical identity and camelCase factory mapping | Domain/corpus owner | Approve slug/mapping or package arrangement; current tools require lowercase kebab-case |
| Coexistence or replacement of original energy domain | Domain/corpus owner | Approve 187-machine dispositions, unique identities/codes, nonoverlapping lanes or migration/retirement |
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

The current detailed backlog is [acceptance/issues.json](acceptance/issues.json). Publication status and actual GitHub URLs are recorded there. All 24 implementation workstreams remain PLANNED and all 43 behavioral cases remain NOT_RUN. EI04 template/class coverage and EI18 simulated-hardware coverage are required future deliverables, not claims that templates or models have been built.

## Published issue backlog

[Umbrella #264](https://github.com/jateeter/RealityEngine_Machines/issues/264) tracks the 24 workstreams [#265–#288](https://github.com/jateeter/RealityEngine_Machines/issues?q=is%3Aissue%20%22energyInfrastructure%22). [Issue index](acceptance/issues.json) records exact bodies, dependencies, primary case ownership and successful readback of all 25 published issues. [Coverage requirements](acceptance/coverage-requirements.json) enumerate obligations for all 46 standard entries and 43 cases; template/class and simulated-hardware fulfillment remain future work. No cases have run and the domain remains unadmitted.
