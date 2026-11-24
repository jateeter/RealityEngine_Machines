# Secure agentic and large-model integration contract

## Current acceptance scope

The [owner-approved acceptance scope](../../acceptance/scope.json) governs this active document: **all required hardware is simulated**, and **template/generic assets may be used in every case**. EI04 must provide templates for each asset class defined by the associated applicable standards, with edition/clause traceability; EI18 must verify a simulated counterpart for every hardware dependency. Generic reference parameters replace site-specific prerequisites for corpus admission. Actual software execution and genuine admission/reviewer evidence remain mandatory. Physical equipment certification and field commissioning are separate future activities. Historical research notes retain their original research context and do not override this decision.

**PROPOSED_NOT_BOUND** · Models retrieve, explain and propose; deterministic policy, electrical feasibility and authorized operators control execution.

## Reuse inspected boundaries, qualify actual services

The inspected PE/OpenClaw integration uses ACP dispatch/callback envelopes and shared completion source `acp-openclaw-completion`, cells `[4210:4214]`, meanings `[completed, failed, confidence, actionClass]`. Preserve those meanings; new domain evidence must use reviewed source contracts rather than reinterpret cells. [CI integration](https://github.com/jateeter/RealityEngine_CI/blob/c985c0d7b592013d4d830b079d5af1663d407b6c/docs/OPENCLAW_INTEGRATION.md), [PE envelope builder](https://github.com/jateeter/RealityEngine_Manager/blob/443520d5c54c99f546de8c4d01bd1682ef1b1840/perception-engine/backend/src/triggers/envelopeBuilder.ts).

localAIStack exposes `/rag/ingest/text`, `/rag/ingest/file` and `/rag/query`, with collection/re-embedding support. Those general routes alone do not establish site/role/license filtering, clause-level lineage or safe grid advice. Source-declared model defaults are `nemotron-3-nano:4b-mlx` and `embeddinggemma-2:270m` (768-dimensional embeddings); these are inspection facts, not live selections. Verify the actual model inventory, runner, tokenizer, quantization, dimensions and digests before qualification. Preserve the host MLX policy where applicable. [localAI guidance](https://github.com/jateeter/localAIStack/blob/edcb3f54b2f8810ec47b891a42f1b8a2916c42ca/CLAUDE.md), [RAG routes](https://github.com/jateeter/localAIStack/blob/edcb3f54b2f8810ec47b891a42f1b8a2916c42ca/services/api/routers/rag.py), [embedding handling](https://github.com/jateeter/localAIStack/blob/edcb3f54b2f8810ec47b891a42f1b8a2916c42ca/services/api/core/embeddings.py).

Manager's document workflow separates scoped prologue/epilogue from model execution; the model holds no document credential and cannot approve/publish its own work. Asset lifecycle identity/integrity code supplies scoped expiring capabilities, DPoP replay protections, pinned revisions and receipts as reusable patterns. These are not yet a microgrid physical-command authorization service. [Manager driver](https://github.com/jateeter/RealityEngine_Manager/blob/443520d5c54c99f546de8c4d01bd1682ef1b1840/visualizer/backend/src/instantiation/openclaw.ts), [asset identity](https://github.com/jateeter/localAssetStorageStack/blob/cb2c4bbb771ddb30a7900c7745cb29e08bafb517/lifecycle/src/identity.js), [asset integrity](https://github.com/jateeter/localAssetStorageStack/blob/cb2c4bbb771ddb30a7900c7745cb29e08bafb517/lifecycle/src/integrity.js).

| Role | Allowed capability | Excluded authority |
|---|---|---|
| Standards/RAG steward | Submit source/extraction/lineage candidates | Self-approve authority, licensing or access |
| Operations analyst | Scoped observations, approved procedures, alarm explanation | Raw vector/device writes, switches, shells, field credentials |
| Forecast/optimization analyst | Typed candidate schedules and bounded sandbox solver | Invent limits/measurements or publish accepted setpoints |
| Cyber-risk analyst | Correlate provided evidence and draft rationale | Accept residual risk or directly isolate a feeder |
| Dispatch planner | Assemble evidence-bound typed proposal | Approve and execute its own physical action |
| Deterministic execution service | Validate and execute authorized bounded command classes | Arbitrary model URLs, shell code or policy mutation |
| Independent reviewer/operator | Approve exact action hash/revision within assigned scope | Reuse approval after material state/action change |
| Assurance/recovery analyst | Collect receipts, compare actual outcome and draft closeout | Treat model confidence/synthetic completion as field evidence |

## Bound every model and tool interaction

Create case/frame/continuation-specific capabilities scoped to site, asset set, role, operation and expiration. Separate planning, execution, evidence writing and review identities. Enforce permissions server-side; prompt text and tool descriptions are not authorization. Keep secrets and relay/field credentials outside context, traces and repository files. Allowlist hash-pinned tool manifests; deny arbitrary URLs, shells, packages, filesystem traversal, unsolicited messaging and network egress.

Validate model output as hostile serialized data with size/depth limits, required fields, enumerations, canonical IDs and units, range constraints and rejection of extra fields/executable content. Structured generation is useful but does not establish validity or safety. A proposal invokes a bounded deterministic solver and the local command gate; it never becomes an RE vector write or field API call directly. Scopes and approvals must still hold at execution time.

Pin model/weight, tokenizer, embedding, runner, quantization, prompts, tools, policy and source revisions plus licenses. Record evaluation and signed release provenance; do not execute remote model repository code by default. Cosign/Trivy/CycloneDX are proposed supporting candidates, not attestations already obtained. Qdrant and Ollama reuse remains subject to current transport and access qualification. vLLM is a future hardware-dependent alternative, not installed infrastructure.

NIST AI RMF/AI 600-1 support AI risk governance. Current checked OWASP 2026 LLM and agentic guidance motivates injection, tool/identity misuse, memory poisoning, supply-chain and cascading-failure cases. Map risks to actual tests rather than advertise framework compliance. [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework), [OWASP LLM 2026](https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/), [OWASP agentic 2026](https://genai.owasp.org/top-10-for-agentic-applications-2026/).

## Require evidence and preserve operation during AI loss

Record each answer's permitted context, retrieval results/page citations, model/tool/policy hashes, typed proposal, validation, approval, adapter decision and observed result. Tool or model completion alone cannot clear a real physical action. Synthetic tests remain labeled and isolated from production evidence.

Evaluate grounding/citation correctness, units and constraints, malformed output, poisoned documents/tool results/memory, cross-site leakage, privilege escalation, malicious model updates and resource exhaustion. For the fixed critical unauthorized-actuation/leakage suite, require zero unauthorized execution/disclosure. Noncritical explanation/forecast accuracy targets need representative data and approved tolerances; fluency is not an acceptance measure. On model/retrieval outage, local deterministic control and the still-valid approved schedule continue; hold new dependent discretionary proposals. Cloud fallback requires explicit deployment/data-processing approval and never silently receives private topology or records.
