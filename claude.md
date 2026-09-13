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
- `domains/ces-contract-registry.json` records which CES output-stream contract shards exist — one per domain, one per configured test-environment corpus — and whether each still describes the corpus it was recorded against. Regenerate with `npm run ces-contracts:write`; `npm run ces-contracts:status` prints the summary. The shards themselves live in `../RealityEngine_CI/config/ces-contracts/` and are recorded from a live 3-of-3 quorum by `RealityEngine_CI/scripts/record-ces-contract-shards.sh` — this repo owns the corpus, not the runtimes.
- Adding, changing or removing a machine makes every shard covering it stale, and `tests/contracts/ces_contract_registry_test.py` fails naming the machines that moved. `unrecorded` is a tracked gap and does not fail; `stale` is a shard asserting something no longer true and does.
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

## MUST: every use of the word "registry" carries a qualifier

**The word "registry" MUST NEVER appear unqualified. Every single use of the
word takes a qualifier naming which registry is meant.**

This is a hard requirement, not a style preference. It applies to every
occurrence in every context, with no exceptions: prose, end-of-task summaries,
commit messages, PR bodies, issue titles and bodies, code comments, docstrings,
variable and function names, log lines, and documentation.

Wrong, in every case — these are all violations:

- "the registry"
- "a versioned registry"
- "the registry file" / "update the registry" / "registry-backed"
- "check the registry first"
- "registry drift"

Right — a qualifier every time:

- "the **instance** registry"
- "a versioned **cesgen** registry"
- "the **arbitration** registry"
- "**machine** registry drift"

If you type the word "registry" and the word immediately before it is not a
qualifier, stop and add one. Re-read every summary and every message for the
bare word before sending it — that is where this rule is actually broken, because
the surrounding context makes the referent feel obvious in the moment. That
feeling is exactly the assumption the rule exists to block.

Qualifiers currently in use. **This list is open, not exhaustive** — a registry
added later gets a qualifier too; nothing is ever promoted to being "the
registry" by virtue of being the one under discussion:

- **instance** registry — `/tmp/re-registry/re-registry.json`, served at
  `:5999/re-registry.json`. Running RE/PE instances with `re_url`/`pe_url`/ports,
  plus `services` and `allocation`. What `RE_REGISTRY_URL` points at.
- **machine** registry — the machines a runtime holds in memory, reported by
  `GET /api/machines`. Distinct from `GET /api/machines/json/list`, the on-disk
  corpus catalog.
- **cesgen** registry — `RealityEngine_Machines/domains/ces-contract-registry.json`.
  Which CES output-stream contract shards exist, what corpus each was recorded
  against, whether each is current.
- **arbitration** registry — `machines/domains/arbitration-registry.json`.
- **domain** registry — `machines/domains/domain-registry.json`.
- **semantic-bus** registry — `machines/domains/semantic-bus-registry.json`.
- **tag** registry — `RealityEngine_CI/docs/TAG_REGISTRY.md`.

## MUST: verify a merge beyond the hosted checks

**A green PR is not a verified PR. Never merge on the hosted checks alone.**

The hosted path does not exercise this system's integration points. A PR can show
every check green and still be unverified, because the checks that ran were a
security scan and — at most — a corpus gate. `localAIStack`, `localOpenClawStack`,
Ollama, Qdrant, MQTT, the OpenClaw ACP gateway and the multi-engine universe are
**not** reachable from the hosted runners, so nothing on that path can tell you
whether the change works where it has to work.

Observed repeatedly: RealityEngine_Machines PRs report exactly one check
(GitGuardian). That is not evidence about the corpus, the registries, the
engines, or any bridge.

Before merging, verify **locally**, and say in the PR which of these you ran and
what they returned:

- The repo's own gates — `validate-corpus.sh`, the contract suite,
  `npm test`, `make test`, `sbt test` — whichever the change touches.
- The integration points the change can reach: a live 3-of-3 universe, the
  local AI stack, the OpenClaw gateway, MQTT — whichever the change can affect.
- The specific behaviour the change claims, with the numbers it produced.

If an integration point cannot be exercised, **say so in the PR** and name it.
An unverified area that is named is a known gap; an unverified area that is
silent reads as tested.

A hosted green tells you the change did not break the hosted path. That is worth
having and is not the question being asked at merge time.
