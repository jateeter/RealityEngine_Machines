# RealityEngine_Machines Guidance

Last reviewed: 2026-06-22

See `/Users/johnt/workspace/GitHub/claude.md` for the integrated application map. Update both this file and the root map when corpus ownership, schema contracts, or runtime test expectations change.

## Role

This repo is the canonical machine corpus and schema/test contract source for all RealityEngine implementations.

## Codebase Map

- `machines/`: canonical machine definitions — fully domain-organized, no files at the root (`tests/contracts/domain_organization_test.py` enforces this).
- `machines/core/`: reserved for cross-domain shared machines (currently empty).
- `machines/domains/<domain>/`: one directory per accepted manifest domain; a machine's `tagging.primaryDomain`/`metadata.category` must match its directory.
- `domains/`: domain organization/support files, including the generated `corpus-index.json` catalog (`npm run corpus-index:write` after corpus changes).
- `schemas/`: JSON schemas for machine and contract validation.
- `triggers/`: trigger definitions consumed by runtime and PE workflows.
- `tests/contracts/`: schema/contract validation.
- `tests/smoke/`: lightweight corpus/runtime checks.
- `tests/integration/`: live RE/PE integration tests.
- `tests/e2e/`: corpus-to-runtime workflows.
- `scripts/`: validation, backfill, and maintenance tools.
- `docs/`: corpus and operational documentation.

## Key Commands

```bash
npm run validate
npm run validate:strict
npm run semantic-buses:inventory
npm run test:contracts
npm run test:smoke
npm run test:integration
npm run test:e2e
```

## Runtime Contract

- Multi-engine tests should use `RE_REGISTRY_URL` when available.
- Single-engine tests should use explicit `RE_BASE_URL` and `PE_BASE_URL`.
- Machine ID, schema, trigger, and PE source expectations are cross-repo contracts.
- On-disk machine addressing is path-aware: every engine's `GET /api/machines/json/list` enumerates the corpus recursively and reports `relFile` (path relative to the machines root); `GET /api/machines/json/:name` accepts a basename and falls back to a recursive search, so corpus filenames must stay globally unique (`tests/integration/machine-json-listing.spec.ts` enforces both).
- `domains/domain-manifest.json` is the authoritative domain inventory; recursive corpus counts must match `currentMachineCount`, and unmanifested domains are validation failures.
- `domains/semantic-bus-registry.json` is the authoritative semantic-bus inventory; refresh it with `npm run semantic-buses:write` when semantic published buses change.
- Do not treat stale generated expectations as truth when live registry endpoints disagree.

## LSP Support

Use JSON schema support for machine/config files, TypeScript language server for scripts/tests, Bash language server for shell scripts, and markdown LSP for docs.

## Editing Rules

- Keep machine changes schema-valid and contract-tested.
- Avoid changing generated/backfilled corpus data without documenting the reason.
- When tests depend on live services, record which RE/PE endpoint source was used.
