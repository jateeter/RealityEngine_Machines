# EI04 TAXII resource templates

The [resource catalog](taxii-resource-catalog.json) covers all eleven property tables in the retained [TAXII 2.1 OASIS Standard HTML](https://docs.oasis-open.org/cti/taxii/v2.1/os/taxii-v2.1-os.html), dated 10 June 2021: nine resources and two supporting record types. These are cyber-information resources, not physical equipment classes. OASIS marks the corresponding DOCX as authoritative; this increment parses the official HTML rendition and does not claim full prose or errata review.

| Resource or record | Section | Kind |
| --- | --- | --- |
| error | 3.6.1 | resource |
| envelope | 3.7 | resource |
| discovery | 4.1.1 | resource |
| api-root | 4.2.1 | resource |
| status | 4.3.1 | resource |
| status-details | 4.3.1, second property table | supporting record |
| collections | 5.1.1 | resource |
| collection | 5.2.1 | resource |
| manifest | 5.3.1 | resource |
| manifest-record | 5.3.1, second property table | supporting record |
| versions | 5.8.1 | resource |

The [source receipt](taxii-source-receipt.json) pins URL, edition, bytes, encoding and SHA-256. The [original HTML](../intake/taxii21/taxii-v2.1-os.html) is retained byte-for-byte, including its copyright and redistribution Notices. It is Windows-1252, not UTF-8. No source document instructions or embedded content execute. Collection does not authorize or attest a RAG index; `ragIndexed` remains false.

## Reproduction and schema authority

[The generator](../tools/build_taxii_templates.py) reads property names, types and required flags from the exact source tables. It retains section and table-ordinal locators and creates [project JSON Schema definitions](taxii-resource.schema.json). These schemas are implementation aids authored by this project, not OASIS schemas or a replacement for normative prose. The retained standard and its Notices accompany the derived artifacts.

The schema selects a deliberately restricted synthetic fixture profile: unknown/custom fields are rejected; strings and lists are nonempty when supplied; counters are nonnegative safe JSON integers; timestamps are UTC. These choices are recorded separately from source-required property flags. For example, the source permits optional resource properties; omitting them is not evidence of a complete live service. Conditional and transport requirements still need review.

## Offline synthetic validation

[The resource fixture set](taxii-resource-fixtures.json) contains one instance of every resource/record type. The `complete` status is invented fixture metadata, not an execution receipt or an acceptance result. Discovery uses `.invalid` HTTPS URLs and no actual credentials or endpoints. STIX payloads reuse the explicitly synthetic closed bundle.

[The validator](../tools/validate_taxii_fixture.mjs) checks source integrity, project schema structure, complete fixture type coverage, status count reconciliation, supplied detail/count agreement and complete-versus-pending consistency. Discovery URLs must be explicit HTTPS URLs without credentials, query or fragments; a supplied default must appear in advertised roots. The selected API version must include TAXII 2.1, and listed collection/manifest media types must be STIX 2.1. These are project profile constraints, not a claim that all other TAXII configurations are invalid. Reported collection write capability does not grant project control authority.

Envelope objects are checked by the existing restricted STIX fixture validator. TAXII envelopes are not STIX bundles, and a bundle object cannot silently replace an envelope's object list. Pagination cursors remain opaque strings; no URL is fetched and no page traversal executes. Error status checking is limited to the selected profile's 4xx/5xx form.

```bash
python3 tools/build_taxii_templates.py --write
python3 tools/build_taxii_templates.py
node tools/validate_taxii_fixture.mjs assets/taxii-resource-fixtures.json
node --test tools/test_taxii_fixture.mjs
```

The hosted fixture suite also invokes the source/schema reproduction check. Python negative fixtures reject changed sources, missing classes, weakened required flags, fabricated clauses and false indexing/completion claims.

## Remaining acceptance work

SC16 now has STIX object/schema and TAXII resource-table catalogs, with full fulfillment still null. HTTP methods/status/header behavior, content negotiation, TLS/authentication/authorization, collection access policy, filters/sorting, pagination continuity, object version lifecycle, actual peer pins, SBOM/license review and integration receipts remain pending in EI05 and downstream work. STIX nested types, semantic/pattern conformance and all applicable prose/errata remain pending as previously recorded.

No network peer, threat feed, model, simulator or RAG interaction executes here. Control actions remain denied; no security or protocol conformance certificate, real threat assessment or authentic approval is fabricated. All 43 behavioral acceptance cases remain NOT_RUN, and EI04 remains open for full standards-defined class coverage and reviewed operational instances.
