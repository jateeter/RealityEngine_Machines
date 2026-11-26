# Offline package verification

Run from the energyInfrastructure package directory:

```bash
python3 tools/verify_package.py --write-summary
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tools -p 'test_verify_package.py'
python3 tools/seal_assets.py
```

The verifier checks source provenance, cloned bytes, issue/dependency/case references, the owner-approved simulation scope, and complete coverage obligations for standards-defined asset templates and simulated required hardware. It checks the recorded readback of published issues offline; it does not contact GitHub or execute any acceptance case. Template libraries and simulators are future EI04/EI18 deliverables, not inferred from coverage-requirement rows.

The ten tests include resealed negative fixtures so semantic rejection is demonstrated independently of checksum mismatch. They run in disposable temporary copies and do not alter the live package.

After intentional reviewed package changes, explicitly regenerate the byte inventory, then verify again:

```bash
python3 tools/seal_assets.py --write
python3 tools/verify_package.py --write-summary
```

Sealing records bytes only; it cannot approve behavior, source rights, security, risk or domain admission. The summary and manifest exclude themselves as documented in the manifest; OS/cache files are excluded. Actual behavioral results, templates and simulator catalogs remain unimplemented until their issues are completed with genuine evidence.

## Generic reference-scope specification

```bash
python3 tools/verify_reference_scope.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tools -p 'test_*.py'
```

The additional ten scope tests reject missing case/standard coverage, unknown roles or topology, generic admission authority, physical hardware prerequisites, normative taxonomy overclaims, untraceable nominal values and fabricated execution. Twenty tests cover package integrity and reference-scope consistency in total. They do not run the 43 behavioral acceptance cases.

## Identity and allocation plan

```bash
python3 tools/build_identity_plan.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tools -p 'test_identity_plan.py'
```

The identity checker verifies all 187 dispositions and current repository name/prefix/window collisions. It plans static windows only; no runtime machine, domain entry, agent, Source or admission evidence is authored. Use explicit `--write` only after reviewing decision/source changes, then reseal the package. The package verifier itself checks local plan reproducibility/consistency; current occupancy scanning requires the command above.


`build_asset_templates.py --write` reproduces the supplemental EI04 catalog from the pinned, hashed public SunSpec JSON snapshot and generic reference roles. Without `--write` it rejects drift, missing models, unsupported normative completion and fabricated simulator/evidence bindings. `test_asset_templates.py` exercises those rejection paths. This does not validate populated operational instances or execute simulations.

`validate_asset_instances.mjs <fixture.json>` validates synthetic generic asset/document bundles against `assets/asset-instance.schema.json` and catalog/reference semantics. Install the repository's locked Node dependencies with the established repository workflow; the validator uses existing Ajv. `node --test tools/test_asset_instances.mjs` from the domain folder exercises structural and semantic rejection paths. The CLI returns nonzero on invalid input. Validation is not simulation execution, engineering review or admission evidence.

`build_reference_instances.py --write` regenerates the three synthetic reference topology fixtures from the declared scenario role/connection/voltage scope and the generic instance fixture. Without `--write` it rejects inventory or content drift. Package verification invokes this reproduction check. Python tests exercise source/fixture drift, and Node instance tests exercise topology semantics. No solver or protocol endpoint executes.

`build_threat_templates.py --write` reproduces the SC16 threat class catalog from the exact OASIS public schema snapshot and checks every local dependency/JSON pointer. `validate_threat_fixture.mjs <fixture.json>` compiles the retained schemas offline and validates the restricted synthetic closed-bundle profile. `test_threat_templates.py` and `test_threat_fixture.mjs` exercise integrity, coverage and invalid object/reference/version paths. See the [profile limits](../assets/threat-classes.md); successful schema validation is not normative or operational assurance.

`build_taxii_templates.py --write` derives project schemas and eleven templates from the exact retained TAXII 2.1 HTML property tables. The no-write check rejects source/output drift. `validate_taxii_fixture.mjs <fixture.json>` validates the restricted synthetic resource set offline, including embedded STIX objects. `test_taxii_templates.py` and `test_taxii_fixture.mjs` cover source integrity, required flags, resource coverage, typed fields and semantic profile rejection. See [source authority and limitations](../assets/taxii-resources.md).

`build_device_templates.py --write` reproduces all DI type templates and declaration/dependency metadata from pinned DI/core NodeSets, retaining scoped identities and modelling rules. `build_fsgim_context.py --write` reproduces the owner-selected Standard 201 context, role/source-class crosswalks and applicability dispositions from pinned supplementary evidence. Both no-write checks reject drift, missing coverage or invented execution/equivalence claims. See [DI limits](../assets/device-types.md) and [FSGIM source authority](../assets/fsgim-integration.md). Neither runs a UA server or SHACL inference engine.

`build_function_bindings.py --write` reproduces four canonical draft FSGIM asset/function projections from the existing context and fixtures. Without `--write` it rejects source/output drift. `validate_function_bindings.mjs <projection.json>` checks source hashes/fixtures, scoped identity, context functions, DI type facets and accounting selections without execution. `test_function_bindings.py` and `test_function_bindings.mjs` cover reproduction and semantic failure cases. See [profile limits](../assets/function-bindings.md).


## EI05 synthetic measurement semantics

[Four source-bound active-power snapshots](../assets/power-snapshots.md) now exercise exact decimal W/kW normalization, net-import-positive signs, selected FSGIM accounting boundaries, timestamp ordering, observation-time freshness and null-preserving quality exclusion. This is offline project-contract validation only. Native property/peer mappings, engineering review, energy/carbon balance, simulated required hardware behavior and corpus admission remain pending; all 43 behavioral cases remain NOT_RUN.


## EI05 offline SunSpec active-power subset

[The selected model 103/203 decoder and register replay](../assets/sunspec-power.md) now connect pinned W/W_SF definitions to draft FSGIM accounting views, preserving signed values, missing-value sentinels and exact decimal scale conversion. This is offline byte-level software evidence only. Secure peer pairs, native status/time mappings, full simulated device behavior, engineering review and admission remain pending; all 43 behavioral cases remain NOT_RUN.


## EI05 offline meter energy intervals

[Selected SunSpec import/export counters and exact interval differences](../assets/meter-energy.md) now provide separate synthetic Wh/kWh quantities linked to the draft facility PCC Meter. Missing data, resets/rollovers, scale changes and stale endpoints never become zero-energy assertions. This is an offline accounting prerequisite; no carbon factor, native peer, complete device simulation or admission is verified. All 43 behavioral cases remain NOT_RUN.


## EI14 synthetic imported-electricity carbon ledger

[The bounded retrospective ledger](../assets/import-carbon-ledger.md) now computes exact energy-weighted imported-electricity emissions/intensity from compatible synthetic meter intervals and factors. Imports/exports remain separate; incompatible, missing or stale inputs cannot become zero intensity. Real providers, uncertainty, storage allocation, trajectories, safety/behavioral acceptance and corpus admission remain pending. All 43 behavioral cases remain NOT_RUN.


## EI14 draft synthetic storage carbon allocation

[The source-bound well-mixed storage pool](../assets/storage-carbon.md) carries synthetic charging emissions through declared charge/discharge conversion losses into delivered energy and remaining inventory, with exact allocation conservation checks. This is a draft retrospective policy, not measured SOC, additional inventory emissions or operational approval. Idle losses, opening-state lineage, uncertainty, durable state, native simulation and acceptance remain pending; all 43 behavioral cases remain NOT_RUN.


## EI14 synthetic revision and trajectory archive

[The source-bound archive](../assets/carbon-trajectories.md) preserves original/corrected synthetic reports and historical snapshot references while keeping forecasts and unadopted target examples separate. Digests check internal consistency, not signatures or real dispatch evidence. Durable history, trusted times, historical meter qualification, actual forecasts/targets, uncertainty, safety and acceptance remain pending; all 43 behavioral cases remain NOT_RUN.
