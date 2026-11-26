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
