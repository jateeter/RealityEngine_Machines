# IFRS runtime deployment and extension workspace

Current testing deployment: **1.4.0-test.1**. Machine-document version remains
1.4.0. Runtime JSON is copied and verified at
`machines/domains/ifrs-accounting/`; it is not mixed with deployment metadata.

- Frozen source payload: `deployments/1.4.0-test.1/machines/` (225 machines).
- Payload hashes and provenance: `deployments/1.4.0-test.1/payload-manifest.json`.
- Sanitized test approval evidence: `deployments/1.4.0-test.1/approval-evidence.json`.
- Immutable deployment receipt: `domains/deployments/ifrs-accounting/1.4.0-test.1.json` at repository root.
- Current deployment pointer: `domains/deployments/ifrs-accounting/current.json`.
- Git version: `deployment/ifrs-accounting/v1.4.0-test.1` after receipt merge and publication.

The entire factory remains **ACTIVE_FOR_FUTURE_EXTENSIONS**. Continue developing
the source dispositions, document catalog, RAG/agent integrations, tools,
templates, runbooks and acceptance assets in their existing locations here.
Frozen deployment payloads are immutable references; create a new version for
future extensions rather than editing or deleting a deployed snapshot.

Only runtime machine definitions belong in the canonical runtime directory.
The residual factory assets remain available to document/RAG connectors and
future domain work. This TEST_ONLY deployment does not grant production
accounting acceptance, close production findings, or mark the domain accepted.
