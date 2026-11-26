# Workplan for simulation-based verified domain admission

Version 0.2.0 · **PLAN_NOT_EXECUTED**

Owner-approved scope: every required hardware component is **simulated required hardware**. Template/generic assets may be used in **all 43 cases**. Required asset classes and their templates derive from the associated applicable standards. Physical procurement, customer-site/OEM records, CHIL/PHIL laboratories and physical commissioning are not corpus-admission prerequisites.

The detailed [issue index](acceptance/issues.json), [scope decision](acceptance/scope.json), [phase inventory](acceptance/workplan.json), and [acceptance cases](acceptance/cases.json) are the executable-work backlog. All cases remain NOT_RUN. Actual software/model/adapter/engine execution and authentic independent review/admission evidence remain required. Simulation results are explicitly labeled and do not certify physical equipment.

## Establish identity and reference assets

Preserve the requested factory directory `energyInfrastructure`. Admission/deployment tools currently require lowercase kebab-case; `energy-infrastructure` is selected by [EI02](identity-decision.json), with an explicit mapping to the preserved factory folder. The disposition inventory chooses coexistence and covers all 187 seeds. New runtime authoring still requires its own identity, Source and semantic contracts. Use unique stems, explicit deployment IDs, category, prefixes and allocations; review shared bus arbitration.

The 187 originals remain unchanged under `machines/`, including the inherited README. All retain category energy and legacy identities/allocations. They lack explicit machine.id required by deployment packaging and contain placeholder material. Build a separate reviewed JSON-only candidate payload; preserve the clone and import manifest.

EI03 defines generic reference microgrids and accountable roles. EI04 enumerates each asset class defined by associated applicable standards, traces edition/clause, and provides templates with properties/units, modes/interfaces, topology/authority, security/faults, parameters/uncertainty and simulator/case mappings. Standards with no asset taxonomy get an explicit disposition. Cross-standard class mappings preserve semantics. Generic templates may stand in for all site/OEM/utility/hazard/calibration/operating evidence fixtures, while authoritative standards, lawful rights and authentic software/admission receipts remain genuine.

EI18 closes complete hardware-dependency coverage with versioned simulated counterparts, independent model/oracle checks, fidelity limits and pairwise software protocol tests. Preliminary models must be available to EI16/EI17 before those suites run; EI18's final coverage verification depends on their results. No physical-device acquisition is required.

## Evidence-gated workstreams

| Issue | Phases | Required outcome | Blocked by |
|---|---|---|---|
| [EI01](https://github.com/jateeter/RealityEngine_Machines/issues/265) | WP01 | Publish the specification baseline and issue traceability | None |
| [EI02](https://github.com/jateeter/RealityEngine_Machines/issues/266) | WP01 | Resolve canonical identity and 187 inherited machine dispositions | None |
| [EI03](https://github.com/jateeter/RealityEngine_Machines/issues/267) | WP01 | Define generic reference microgrids and accountable authorities | None |
| [EI04](https://github.com/jateeter/RealityEngine_Machines/issues/268) | WP02 | Build the standards-derived asset catalog and template library | EI02, EI03 |
| [EI05](https://github.com/jateeter/RealityEngine_Machines/issues/269) | WP03 | Freeze interoperability profiles and implementation selections | EI03, EI04 |
| [EI06](https://github.com/jateeter/RealityEngine_Machines/issues/270) | WP03 | Define simulation safety envelopes and operating lifecycle | EI03, EI04, EI05 |
| [EI07](https://github.com/jateeter/RealityEngine_Machines/issues/271) | WP03 | Specify security architecture and dynamic threat assessment | EI03, EI04, EI05 |
| [EI08](https://github.com/jateeter/RealityEngine_Machines/issues/272) | WP04 | Author candidate machines and composition contracts | EI02, EI05, EI06, EI07 |
| [EI09](https://github.com/jateeter/RealityEngine_Machines/issues/273) | WP05 | Implement adapters and trusted observation normalization | EI05, EI06, EI08 |
| [EI10](https://github.com/jateeter/RealityEngine_Machines/issues/274) | WP05 | Enforce deterministic command authorization and feasibility | EI06, EI07, EI09 |
| [EI11](https://github.com/jateeter/RealityEngine_Machines/issues/275) | WP05 | Provide durable execution readback and recovery | EI09, EI10 |
| [EI12](https://github.com/jateeter/RealityEngine_Machines/issues/276) | WP05 | Integrate scoped agents and qualified models | EI07, EI08, EI10, EI11 |
| [EI13](https://github.com/jateeter/RealityEngine_Machines/issues/277) | WP02, WP05 | Implement governed RAG collection retrieval and evaluation | EI04, EI07, EI12 |
| [EI14](https://github.com/jateeter/RealityEngine_Machines/issues/278) | WP04, WP05 | Implement carbon accounting and trajectory contracts | EI04, EI06, EI09, EI10 |
| [EI15](https://github.com/jateeter/RealityEngine_Machines/issues/279) | WP05 | Qualify transport identities and software supply chains | EI05, EI07, EI09, EI12, EI13 |
| [EI16](https://github.com/jateeter/RealityEngine_Machines/issues/280) | WP06 | Run integrated microgrid simulation acceptance | EI09, EI10, EI11, EI12, EI13, EI14, EI15 |
| [EI17](https://github.com/jateeter/RealityEngine_Machines/issues/281) | WP06 | Run adversarial OT agent and model acceptance | EI07, EI09, EI10, EI11, EI12, EI13, EI14, EI15 |
| [EI18](https://github.com/jateeter/RealityEngine_Machines/issues/282) | WP06 | Provide and verify every simulated required hardware component | EI05, EI06, EI15, EI16, EI17 |
| [EI19](https://github.com/jateeter/RealityEngine_Machines/issues/283) | WP07 | Stage canonical candidate and sibling contract updates | EI08, EI14, EI16, EI17, EI18 |
| [EI20](https://github.com/jateeter/RealityEngine_Machines/issues/284) | WP07, WP08 | Build genuine simulation-backed domain admission runner | [EI19](https://github.com/jateeter/RealityEngine_Machines/issues/283) |
| [EI21](https://github.com/jateeter/RealityEngine_Machines/issues/285) | WP08 | Run official preparation and exact-source native regression | EI19, EI20 |
| [EI22](https://github.com/jateeter/RealityEngine_Machines/issues/286) | WP09 | Finalize independently reviewed tested-head admission | [EI21](https://github.com/jateeter/RealityEngine_Machines/issues/285) |
| [EI23](https://github.com/jateeter/RealityEngine_Machines/issues/287) | WP10 | Package immutable accepted software deployment | [EI22](https://github.com/jateeter/RealityEngine_Machines/issues/286) |
| [EI24](https://github.com/jateeter/RealityEngine_Machines/issues/288) | WP10 | Demonstrate simulated commissioning recovery and requalification | [EI23](https://github.com/jateeter/RealityEngine_Machines/issues/287) |

Each issue carries detailed implementation, responsible repositories/roles, acceptance criteria, case/risk/standard traceability and evidence requirements. No date or named assignee is invented. Sources and standards rights remain real requirements; generic assets remove customer-site and physical-hardware prerequisites.

## Use the actual admission protocol and distinguish its stages

The authoritative procedure is [MACHINE_CONCEPT §9](https://github.com/jateeter/RealityEngine_CI/blob/c985c0d7b592013d4d830b079d5af1663d407b6c/MACHINE_CONCEPT.md), current implementation [approval.py](https://github.com/jateeter/RealityEngine_Machines/blob/ebb75ee8ea34c13c86a5e3364eb83b550ad96693/scripts/domain-approval/approval.py), [scope.py](https://github.com/jateeter/RealityEngine_Machines/blob/ebb75ee8ea34c13c86a5e3364eb83b550ad96693/scripts/domain-approval/scope.py), and [deployment.py](https://github.com/jateeter/RealityEngine_Machines/blob/ebb75ee8ea34c13c86a5e3364eb83b550ad96693/scripts/domain-approval/deployment.py). Supporting domain metadata currently lives in root `domains/`; older narrative paths must not be copied blindly.

`plan`/`prepare` require a nonaccepted manifest entry, architecture domain-registry entry and canonical candidate JSON already under `machines/domains/<slug>`. They do not convert this factory clone automatically. Stage these reviewed candidates in development branches/worktrees as WP07, without marking accepted. Include display/description, code prefixes, default autonomy, classes, source-data default and PE ingest pattern; keep manifest count and region/arbitration/semantic-bus declarations consistent. A new accepted domain also requires the localAI domain-baseline generator/update under its owner's contract. Inspect every affected sibling implementation before cross-repo contract changes.

Before `prepare`, verify git/gh/Python/Node/Ajv/ROBOT availability; named branches in Machines and CI rebased on fetched `origin/main`; clean committed tracked protected candidate inputs; no untracked protected admission input; unused domain version; canonical sibling CI checkout and executable scope runner; a new evidence directory outside both repos; and a regression profile containing an actual candidate-domain machine. Use the current repository's own gates, including strict corpus/schema/contracts, one-CES-one-pattern, name/domain/region/semantic/arbitration checks and reasoning. Refresh materialized domain/semantic-bus/arbitration/cesgen views using their own producers where required rather than treating stale views as runtime authority.

`prepare` and its scope runner stop development services and start fresh exact-scope C++, LSP and Scala runtimes. **Explicit authorization for these resets is required before executing `--allow-runtime-reset`; this planning request has not run them.** The generic scope boot uses `--no-openclaw --no-local-ai --fresh`: it intentionally does not qualify the grid adapters, agent or RAG path. `DOMAIN_INTEGRATION_RUNNER` is mandatory and must be a reviewed executable that starts/uses isolated required services and asserts real source/adapter/provider/action behavior. There is no pass-by-default hook.

Bind receipts to exact domain/scope/machine fingerprints, instance-registry URL, actual voter set, ISRE/OSRE parity and domainIntegration PASS plus hash-bound artifacts. Derive endpoints from the live instance registry; do not hardcode them or equate HTTP health with behavior. C++, LSP and Scala are voters; Rust and Manager followers remain nonvoting and require applicable conformance evidence. Native regression parity is separate from pairwise software-wire tests and simulated-hardware behavior validation. Physical equipment certification is outside this corpus-acceptance scope. The orchestrator conservatively recertifies all known CES scopes because shared vector space can affect unchanged peers.

`submit` requires human evidence review and publishes draft PRs; it neither merges nor self-approves. Merge CI evidence first, then the exact reviewed/tested Machines head through branch protection. `finalize` verifies independent approval, tested heads, merged-main ancestry and a digest-bound ledger before approval release. TEST_ONLY/WORKFLOW_FIXTURE evidence cannot authorize production. Post-admission `package-deployment`/`deploy`/`check-deployment`/`publish-deployment` manage immutable accepted runtime versions; they are not a shortcut for first admission. Retain factory assets for extensions; rollback is a new reviewed version and physical compensation needs current-state analysis.

## Review-only command templates

Replace every angle-bracket token with a reviewed value; the snippets are not commands executed by this package. `--sign-tag` follows release signing policy. Each publication/reset/deployment step is a future authorized action with the concrete reviewed artifacts.

```bash
/opt/homebrew/bin/bash scripts/approve-domain.sh plan --domain <slug> --version <domain-semver>
DOMAIN_INTEGRATION_RUNNER=<absolute-reviewed-suite> /opt/homebrew/bin/bash scripts/approve-domain.sh prepare --domain <slug> --version <domain-semver> --evidence <new-absolute-directory-outside-repos> --scope-runner <absolute-path-to-scripts/domain-approval/run-scope.sh> --regression-profile <profile-name-without-corpus.txt> --allow-runtime-reset
/opt/homebrew/bin/bash scripts/approve-domain.sh submit --evidence <same-directory> --evidence-reviewed
/opt/homebrew/bin/bash scripts/approve-domain.sh finalize --evidence <same-directory> --sign-tag
/opt/homebrew/bin/bash scripts/approve-domain.sh package-deployment --domain <slug> --version <deployment-semver> --approval-context PRODUCTION --source-dir <reviewed-json-only-directory> --write
/opt/homebrew/bin/bash scripts/approve-domain.sh deploy --payload-manifest <repo-payload-manifest> --approval-evidence <repo-finalized-approval-copy>
# Only after reviewing successful dry run, deploy's --write performs the copy.
/opt/homebrew/bin/bash scripts/approve-domain.sh check-deployment --domain <slug> --version <deployment-semver>
/opt/homebrew/bin/bash scripts/approve-domain.sh publish-deployment --domain <slug> --version <deployment-semver> --sign-tag
```

`reconcile-counts --domain <slug> --version <semver> --approval-context PRODUCTION_CANDIDATE [--write]` can stage/check counts but never approve a domain. `test-run` is disposable explicitly marked workflow rehearsal only. Do not use it to generate purported production conformance evidence.

## Close evidence at the appropriate level

AC01–AC08 cover operating lifecycle, protocol profiles, sensing and degraded communications; AC09–AC25 cover endpoint/command/AI/physical threats; AC26–AC35 cover carbon accounting and constraints; AC36–AC43 cover RAG/model confidentiality and behavior, artifact/transport evidence, native corpus parity, admission authenticity and recovery. Each case records its required test level, owner, stimulus, pass criteria and evidence. Numerical engineering values remain GENERIC_REFERENCE_PROFILE_REQUIRED. The fixed critical deny/leakage suite requires zero unauthorized operations/disclosures, without implying that all possible attacks are eliminated.

After source, policy, topology, firmware, model or standard-profile changes, evaluate impact and invalidate dependent receipts; repeat affected software, simulation and simulated-commissioning gates rather than reuse stale approvals. Keep raw evidence outside source, publish only sanitized required immutable receipts, and name skipped/unexercised integration areas. No actual field or model integration, native parity, HIL, certification, PR submission or production admission was performed in this package step.

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


## Owner-selected FSGIM integration context

[ASHRAE Standard 201](assets/fsgim-integration.md), recorded as OP23, now governs the asset integration context. The current inventory has 47 standards/framework entries and 19 RAG source families. Crosswalks cover 19 reference roles, 112 SunSpec models and 58 OPC UA DI types. The original published backlog remains a historical snapshot; current context and source progress are explicit additions. Normative UML collection/equivalence, exact property/conformance mappings, reviewed operational instances and actual peer/simulator integration remain pending.


### Draft FSGIM asset/function bindings

[Four source-linked draft projections](assets/function-bindings.md) now cover the generic and three reference fixtures, with scoped identities, inactive functions, DI type facets and single-view resource accounting groups. This advances typed project bindings; normative model/property review, actual readings/units/time/boundaries, solver and protocol/runtime verification remain pending.


## EI05 synthetic measurement semantics

[Four source-bound active-power snapshots](assets/power-snapshots.md) now exercise exact decimal W/kW normalization, net-import-positive signs, selected FSGIM accounting boundaries, timestamp ordering, observation-time freshness and null-preserving quality exclusion. This is offline project-contract validation only. Native property/peer mappings, engineering review, energy/carbon balance, simulated required hardware behavior and corpus admission remain pending; all 43 behavioral cases remain NOT_RUN.
