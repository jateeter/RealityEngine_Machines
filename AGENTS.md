# Codex Guidance: RealityEngine_Machines

Read `claude.md` for the current codebase map and corpus contract context.

## Role

This repo is the canonical machine corpus, schema, trigger, and test-contract source for the engines and Manager workflows.

## Development Rules

- Treat machine IDs, schema fields, trigger shapes, and domain placement as cross-repo contracts.
- Avoid broad corpus rewrites unless explicitly requested.
- When changing schemas, update affected tests, docs, and engine loader expectations together.
- Prefer deterministic scripts and stable generated output.

## Bug Triage

- For missing machines, check schema validity, corpus path, runtime loader logs, and `/api/machines` for each engine.
- For PE source bootstrap issues, compare machine count, source count, and IDs separately.
- For stale fixture failures, verify against live registry-selected endpoints before updating expected data.

## Verification

Common commands:

```bash
npm run validate
npm run validate:strict
npm run test:contracts
npm run test:smoke
npm run test:integration
npm run test:e2e
```

## Artifact Hygiene

Do not commit generated reports, local runtime captures, or broad backfill output unless the user explicitly requests it.

