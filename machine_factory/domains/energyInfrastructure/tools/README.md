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
