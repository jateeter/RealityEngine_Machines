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
- `semantics/`: OWL semantic representation of machine behavior — `ontology/re-core.ttl` (TBox + action vocabulary) and generated `abox/<domain>/` Turtle files (`scripts/generate-owl.py`); see `docs/SEMANTIC_OWL_ROADMAP.md`.
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
- `domains/region-allocation.json` is the generated universal-vector allocation registry (reserved provider bands, cross-service PE source lanes, inter-domain bus lanes, frozen output-overlap baseline); regenerate with `npm run region-allocation:write` and let `tests/contracts/region_allocation_test.py` gate drift.
- On-disk machine addressing is path-aware: every engine's `GET /api/machines/json/list` enumerates the corpus recursively and reports `relFile` (path relative to the machines root); `GET /api/machines/json/:name` accepts a basename and falls back to a recursive search, so corpus filenames must stay globally unique (`tests/integration/machine-json-listing.spec.ts` enforces both).
- Name uniqueness is scope-relative, and the scopes are the contract
  (`tests/contracts/name_uniqueness_test.py`, #68): every **CES name is unique
  within its machine**, every **machine is unique within its domain**, and every
  **domain is unique within the universe** — including its `codePrefixes`, since
  a prefix claimed by two domains makes machine codes ambiguous. The same
  sequence id across different machines is fine and is used (`rs-set-sequence`
  appears in three flip-flops); within one machine it collapses two OWL
  individuals onto one IRI, which is the failure #65 fixed for trigger rules.
  Machine file stems are additionally **globally** unique — stronger than the
  policy, and required because `GET /api/machines/json/:name` resolves a bare
  basename. Names are the MVP identity mechanism; UUIDs are the intended
  direction.
- `domains/domain-manifest.json` is the authoritative domain inventory; recursive corpus counts must match `currentMachineCount`, and unmanifested domains are validation failures.
- **Adding a domain** follows a specified protocol — `RealityEngine_CI/MACHINE_CONCEPT.md` §9. It is the canonical statement of what a domain must supply (at least one machine, a manifest entry with non-colliding `codePrefixes`, a region allocation), what acceptance validates (semantic integrity, machine definitions, interconnectivity, arbitration), and when a domain must extend the regression corpus rather than relying on the standard-deployment twelve. `scripts/validate-corpus.sh` is the gate; a domain's `status` stays non-`accepted` until it passes. Do not restate the protocol here.
- `domains/semantic-bus-registry.json` is the authoritative semantic-bus inventory; refresh it with `npm run semantic-buses:write` when semantic published buses change.
- Do not treat stale generated expectations as truth when live registry endpoints disagree.

## LSP Support

Use JSON schema support for machine/config files, TypeScript language server for scripts/tests, Bash language server for shell scripts, and markdown LSP for docs.

## Editing Rules

- Keep machine changes schema-valid and contract-tested.
- Avoid changing generated/backfilled corpus data without documenting the reason.
- When tests depend on live services, record which RE/PE endpoint source was used.
