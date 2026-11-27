# RealityEngine_Machines Scripts Guidance

This directory contains corpus validation, backfill, and maintenance scripts.

- Keep scripts deterministic and explicit about input/output paths.
- Avoid rewriting large corpus areas without a clear user request.
- Prefer live checks that resolve engines from the instance registry (`RE_REGISTRY_URL`) when scripts validate runtime behavior.
- Use TypeScript or Bash language servers as appropriate.

## The cesgen registry and machine-factory candidates

`build-ces-contract-registry.py` discovers every RealityEngine_CI `config/*-corpus.txt` as a test-environment scope. So **a change that adds a corpus manifest, or changes what a scope resolves, regenerates `domains/ces-contract-registry.json` in the same change set.** RealityEngine_CI#877 did not, and every CI regression run stopped in `validate-machines` until #315.

**A machine-factory candidate is outside every registry check until it is admitted** (owner, 2026-11-27). A selection entry that resolves to `machine_factory/domains/*/machines/` is left out of the scope's members, fingerprint, counts and unresolved entries (`candidatePolicy`), so factory work in progress never makes the registry stale. RealityEngine_CI records candidates in a shard's `candidates` section, outside its `corpusFingerprint`, and compares them non-gating. At admission the machine moves to `machines/domains/<slug>/`, resolves from the corpus root first and joins the scope.

## Standing rules

The standing rules are in
`../../RealityEngine_CI/docs/ENGINEERING_CONTRACT.md`, which is
authoritative. They are not listed or summarised here, so this file never
falls behind the contract. Read it before changing anything here.
