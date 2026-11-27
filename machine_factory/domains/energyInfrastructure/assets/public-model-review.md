# Public model review context packets

The [review-only policy](public-model-review-policy.json), [example query](public-model-review-query.json) and [lookup](../tools/prepare_review_context.py) implement an EI13 preparation step over already collected public implementation/model sources. This is on-demand source lookup for a domain reviewer, **not** an admitted RAG collection, generated answer, embedding/index pipeline or model integration. Source receipts keep `ragIndexed: false`; no stored text/vector index or approved model knowledge is created.

## Source inventory and bounded extraction

| Review source | Selected original bytes | Source role and notices |
| --- | --- | --- |
| SUNSPEC_SELECTED | Model 103 and 203 JSON at commit `90b4a331dcca1d6eac69c1bead952fddcc5852e0` | Public implementation point definitions; complete retained Apache-2.0 license accompanies returned results |
| OPCUA_DI | DI 1.05.0 XML at `ed0b821f6a6f1f0c440c442ed95a9146ae8b7f8d`, with exact required core 1.05.04 bytes checked | Formal NodeSet fragments, not runtime/conformance proof; embedded OPC Foundation MIT notice accompanies results |

SunSpec excerpts preserve a complete selected point value, JSON Pointer, model/point identity, parent SHA-256, group label and same-group scale-factor context. DI excerpts preserve a complete selected serialized XML node, NodeId locator, namespace-qualified identity, attributes/model/dependency context and aliases. Core bytes/dependency identity are checked; core nodes are not offered as retrieval candidates. XML DTD/entity declarations and automatic remote loads are not supported. Namespace identifiers and XML references do not create network connections.

Serialization is explicitly labelled: JSON value serialization and ElementTree XML serialization are **not** verbatim source prose/bytes. Parent file hash and exact locator ground each excerpt; parser/extractor/runtime versions are returned. Inherited type requirements, surrounding prose and complete normative constraints are not resolved. Every excerpt is marked incomplete context, without normative authority. ASHRAE 201 remains the integration context, including OPC UA DI; no ASHRAE normative text/UML, normative class equivalence or complete standards coverage is supplied by these public source fragments.

## Filtering, ranking and abstention

The query must declare the fixed public scope, no site, DOMAIN_REVIEWER role, implementation-review purpose and implementation-reference question type. These are **test scope labels, not authenticated identities or production ACLs**. Only the two fixed source IDs are supported. Nonpublic scopes, other roles/purposes, restricted/unknown sources, normative requirements, live operational state and operating advice abstain before source text reads or ranking. A disabled source also abstains before text reads. No DNP3 material, restricted draft, licensed full-text standard, site record, telemetry or credential store is opened.

Ranking is deterministic lexical conjunction over selected source identity and excerpt text. It is not semantic relevance, a proof of answerability or an LLM answer. Missing lexical support abstains instead of fabricating a citation. Limits cover query length/token count, result count, complete excerpt bytes and total packet bytes. Oversized excerpts are omitted with coverage counts; source qualifiers/notices are not silently truncated to fit. If the whole packet exceeds its bound, the packet abstains.

Returned source text is labelled untrusted data, never an instruction hierarchy or tool permission. The packet fixes readyForModelUse=false, normativeAuthority=false, answerGenerated=false, embeddingCreated=false, toolPermissionsGranted=[] and control DENY. It carries full applicable retained source notices, not a conclusion that embedding, training, export or operational retrieval rights were independently approved. A human still needs source authenticity/rights/fidelity review before any production RAG-state transition.

## Citation and change checks

`verify_review_packet(packet, query)` rebuilds the packet from the current query, policy and exact original bytes. Fabricated excerpts, locators, parent hashes, removed notices, changed query scope, source/policy changes or disabled sources invalidate reuse. A parser/runtime change can also require regeneration. This is deterministic packet consistency, not author authentication, a signature, source admission or retrieval-quality certification. No durable deletion service exists because no model/vector/text index is created here.

```bash
python3 tools/build_review_lookup.py --write
python3 tools/build_review_lookup.py
python3 tools/prepare_review_context.py assets/public-model-review-query.json
python3 -m unittest discover -s tools -p test_review_lookup.py
```

Tests check real pinned W/W_SF definitions and DI abstract DeviceType/core context, exact parent locators/notices, deterministic bounds, pre-read scope/source denial using a fixture with no source texts, tamper/change/revocation invalidation and disabled model/index policy. They do not demonstrate authenticated cross-tenant isolation or adversarial LLM behavior: all available source data is public, and no model is connected.

The 19-family RAG inventory remains a broader collection plan. Normative source admission, approved excerpts/fidelity, authenticated source/tenant/site/role entitlements, embeddings, localAI/OpenClaw retrieval, grounded model answers, conflict handling, benchmark holdouts, actual deletion/supersession services and independent review remain pending. No network/runtime link is created. All 43 behavioral acceptance cases stay NOT_RUN and corpus admission NOT_PERFORMED. Required hardware remains simulated and generic/template assets remain permitted in every case.
