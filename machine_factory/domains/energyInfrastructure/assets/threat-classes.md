# EI04 threat information classes

The [threat class catalog](threat-class-catalog.json) adds 57 source-backed schema templates under SC16. It enumerates 19 domain objects, two relationship objects, 18 cyber-observable objects, three meta objects and the bundle container, with section locators to the [STIX 2.1 OASIS Standard of 10 June 2021](https://docs.oasis-open.org/cti/stix/v2.1/os/stix-v2.1-os.html), sections 4–8. Fourteen supporting schemas retain their separate identities rather than being asserted as additional top-level objects. These are information classes, not physical microgrid equipment classes. Incident and course-of-action are explicitly marked as limited stubs in the 2021 standard; the reserved course-of-action action property is rejected by the synthetic profile and cannot convey automation authority.

The unmodified public schemas and README come from the [OASIS TC Open Repository snapshot](https://github.com/oasis-open/cti-stix2-json-schemas/tree/9af1db41b7b86c06324f899649ae83480134f66e), retained with its [BSD-3-Clause license](../intake/public-models/stix21/LICENSE) and [source hashes](stix-source-receipt.json). OASIS labels this schema repository non-normative. The normative standard was consulted for classification and section locators; its full prose was not copied into this repository. Schema behavior may differ from normative requirements or errata, which require separate review.

Each template identifies its original schema, the locations of required-property declarations and the complete local schema dependency graph. Conditional requirements are preserved in the original schemas rather than flattened into misleading universally required property lists. Every source reference and JSON pointer must resolve locally. No schema is fetched during validation.

## Executable synthetic profile

[The fixture](synthetic-threat-fixture.json) contains a generic identity, infrastructure, vulnerability and relationship. These have synthetic UUIDs and descriptions; no real incident, CVE, attribution or operational risk finding is asserted. The [offline validator](../tools/validate_threat_fixture.mjs) checks the exact schema snapshot hashes, compiles all 57 schemas with existing Ajv dependencies, validates the bundle and known object types, rejects duplicate IDs and unresolved references, and checks version and timestamp ordering. Fractional timestamp comparisons preserve submillisecond precision.

The project profile requires an explicitly synthetic envelope, a closed bundle, explicit STIX 2.1 versions, 1–128 objects and at most one MiB of UTF-8 JSON text. Unresolved external references and custom object types are rejected by this profile, although other STIX uses may permit them. These restrictions are project assumptions, not quotations from the standard.

Ajv runs with `unicodeRegExp: false` because the pinned upstream core schema uses an escaped hyphen outside a character class that is invalid in Unicode regex mode. Source files remain unchanged. Ajv formats handle email/URI formats; an explicit bounded IDN hostname check uses Node's domain-to-ASCII conversion and DNS-label syntax, without DNS queries. Schema validation does not validate STIX patterns, all reference type/relationship semantics, deterministic SCO IDs, revocation/version history, markings/access policy or all prose requirements. It is not STIX conformance certification.

```bash
python3 tools/build_threat_templates.py --write
python3 tools/build_threat_templates.py
node tools/validate_threat_fixture.mjs assets/synthetic-threat-fixture.json
node --test tools/test_threat_fixture.mjs
```

No threat feeds, external endpoints, models, RAG index or control systems are contacted. No autonomous response is authorized: template authority is analyst review only, automatic control actions are denied and execution receipts remain null. This provides typed inputs for future dynamic risk work; it does not implement that risk workflow or attest the security of a live grid.

## Remaining acceptance work

SC16 is now partially reviewed for STIX object/schema coverage. [TAXII resource property tables](taxii-resources.md) now have a source-backed catalog and synthetic profile; full transport/prose review and service/peer selection remain pending. Nested extension/type taxonomy, all normative prose and applicable errata, complete fixture coverage, secure peer integration, cross-standard mappings, threat assessment and authentic runtime/admission evidence remain pending. All 43 behavioral acceptance cases remain NOT_RUN. Full EI04 completion is not asserted.

The source receipt records a second supplemental public-model snapshot, separate from the original RAG family receipts. No extraction/indexing/retrieval approval is implied by collection, and no restricted DNP3 material was collected.
