# `AIGovernanceRegime` Solid-Pod Asset SHACL Validation Suite Documentation

**Authoritative Baseline:** *RealityEngine: Deterministic Pre-Execution Governance for Agentic AI with Temporally Bounded Incompleteness*, **Version 0.18 (Working Draft, 19 November 2026)**  
**Companion Artifact:** `AIGovernanceRegime_Asset_Shapes.shacl.ttl` (W3C SHACL Turtle Specification)  
**Target Storage Layer:** `localAssetStorageStack` (Per-Instance W3C Solid Pods)

---

## Overview

The `AIGovernanceRegime_Asset_Shapes.shacl.ttl` validation suite enforces structural, cryptographic, and formal-methods invariants across all four Solid-pod asset types owned by **RealityEngine** instances inside `localAssetStorageStack`. Every governance asset is canonicalized under **RFC 8785 (JCS)**, pinned via HTTP `ETag` and `SHA-256`, and signed with **Ed25519** (`RFC 8032`) before any state transition or continuation resumption is permitted.

---

## Summary of Exported SHACL Shapes

### 1. `re:GovernanceAssetFrameShape`
* **Specification & Threat Coverage:** RealityEngine Section 6 (*Governed Dispatch: Asset Workflow Management*) & Threats `T2` (Token Replay), `T15` (Self-Approval), `T16` (Approval of Changed Document), and `T17` (Cross-Frame Access).
* **Structural & Cryptographic Rules:**
  * Validates `urn:re:asset:gov:` URNs, `M-GOV-*` template machine identifiers, and pinned upstream `ETag` / `SHA-256` digests (`re:pinnedArtifacts`).
  * Enforces strictly **one-shot continuations** (`re:oneShot true`) with monotonic generation counters.
  * Binds continuations to named voting engine runtimes (`RealityEngine_CPP`, `RealityEngine_Scala`, `RealityEngine_LSP`).
  * Mandates deterministic `rework` escape paths on document hash mismatch (`re:escapeOnHashMismatch "rework"`) or missing target engine (`re:escapeOnMissingEngine "rework"`).
* **Embedded SPARQL Invariants:**
  * **Quorum Threshold Verification:** Enforces Byzantine fault-tolerant bounds ($n \ge 3f + 1$, $q \ge 2f + 1$) and crash fault-tolerant bounds ($q \ge \lfloor n/2 floor + 1$).
  * **Agent Exclusion:** Blocks non-human agent WebIDs from resuming approval continuations via `re:excludedPrincipals`.

---

### 2. `re:AIBOMManifestShape`
* **Specification & Threat Coverage:** RealityEngine Section 12.2–12.5 (*Neuralese Reality Events & TopK Prism*), Acceptance Gates `TC-NEU-01` / `TC-NEU-02`, and Threat `T19` (Activations Steered Past Learned Rules).
* **Structural & Cryptographic Rules:**
  * Pins foundation model SHA-256 digests, quantization builds (e.g., `MLX-FP8`), neuralese tap layers, and 3-of-3 voting runtime binary hashes (`RealityEngine_CPP`, `RealityEngine_Scala`, `RealityEngine_LSP`).
  * Enforces `RFC 8785` canonicalization and `Ed25519` cryptographic proofs (`re:proof`).
  * **ISRE Band Collision Guard:** Enforces `re:isreBandOffset >= 86016`, preventing neuralese residual-stream bands from colliding with the `[20480:86015]` clone space or `[0:17087]` corpus space.
  * **TopK SAE Dictionary Gates:** Validates that `re:tcNeu01GatePass` is `true` (exact $k_f$ active features per tap) and `re:deadFeatureRateMeasured <= 0.20` (satisfying `TC-NEU-02`).

---

### 3. `re:TaskSufficiencyAndImpactDossierShape`
* **Specification & Regulatory Coverage:** RealityEngine Section 3.1 Proposition 1 (*Completeness is Saturation*), Section 5 (*Temporally Bounded Incompleteness*), `ISO/IEC 42005`, and `EU AI Act Articles 9, 14, and 27`.
* **Formal Sufficiency Disjunction (`sh:or`):**
  * Every declared hazard $h \in H(\omega_\tau)$ must satisfy one of two formal observation modes:
    1. **Fiber-Saturated (`FiberSaturated`):** Declares explicit `re:encodedIsreCells`, verified `re:sourceBindings`, and a formal `re:completenessArgument` showing $\ker(\pi) \subseteq T_c\Sigma$.
    2. **Temporally Bounded Incomplete (`TemporallyBoundedIncomplete`):** Declares unencoded context directions, a bounded logical exposure budget `re:exposureBudgetMu` ($\bar{\mu}$), a separatrix margin `re:separatrixMarginDelta` ($\delta$), a verified `re:returnPathSource`, and a non-empty domain fail-safe vector `re:failSafeVector` ($\mathbf{s}_{\text{safe}}$).
* **Embedded SPARQL Invariants:**
  * **Separation of Duties (`T15`):** Strictly enforces `preparerWebId != approverWebId` on the sign-off chain.
  * **Recertification Lease Validity:** Verifies that `recertificationExpiresAt` is strictly later than `approvalTimestamp`.

---

### 4. `re:AuditorEvidencePackShape`
* **Specification & Audit Coverage:** Machine `M-GOV-13` (*ControlCrosswalkAssembler*), `ISO/IEC 42001:2023 Annex A` (A.3–A.8), and `EU AI Act Articles 9–15, 26, 27, 50, 53, and 72–73`.
* **Sealed Container Rules:**
  * Verifies that every sealed audit pack binds all seven pinned cryptographic receipts under a canonical `RFC 8785` + `Ed25519` signature:
    1. `re:dossierReceipt` (Task-Sufficiency & Impact Dossier)
    2. `re:aibomReceipt` (AI Bill of Materials & SAE Dictionary Provenance)
    3. `re:walSegmentReceipt` (Durable Write-Ahead Record Segment)
    4. `re:quorumSignatureBundle` ($q$-of-$n$ Governance Quorum Sign-Offs)
    5. `re:parityCertificate3of3` (`C++`, `Scala`, `Lisp` Pass-Set Parity Record)
    6. `re:egressArt50Log` (Outbound Provenance / Watermark Boundary Log)
    7. `re:klineIncidentArchive` (Exported K-Line Episodes & Near-Miss Archive)
