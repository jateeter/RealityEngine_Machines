# threat-dynamics (factory package)

Threat classification and dynamic, reactive threat observability for agentic
systems, after NIST SP 2400-102e2026 ipd §4 (NISTAML.061–.067). A peer of
`ai-governance-regime`: this domain observes, governance decides.

- [SPECIFICATION.md](SPECIFICATION.md): machines, outputs, published lanes,
  simulated Sources.
- [PACKAGE_STATUS.md](PACKAGE_STATUS.md): the factory steps and what each
  produced.
- [REVIEW_QUEUE.md](REVIEW_QUEUE.md): open findings.
- `scope-decisions.json`, `semantic-amendments.json`,
  `admission-source-manifest.json`.
- `threat-sources.json`: a builder output. Change `tools/build_machines.py`.

```bash
python3 tools/build_machines.py          # write machines/ and threat-sources.json
python3 tools/build_machines.py --check
python3 tools/verify_machines.py
python3 tools/verify_package.py
```
