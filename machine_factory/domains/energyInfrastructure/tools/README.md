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
