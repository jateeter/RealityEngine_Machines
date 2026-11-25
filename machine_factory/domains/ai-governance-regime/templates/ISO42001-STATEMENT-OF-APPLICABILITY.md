# ISO/IEC 42001:2023 Statement of Applicability (SoA) Template

* **Organization / System Scope:** RealityEngine Deterministic Pre-Execution Governance Deployment (`instanceUUID` / `ruleEpoch`)
* **Governing Meta-Domain:** `ai-governance-regime` (`AIGovernanceRegime`, 312 machines, ISRE `[16960:17087]`)
* **Primary Audit Evidence Container:** `https://pod.enterprise.org/instances/{instanceUUID}/governance/audit-packs/audit-pack-{epochId}.jsonld` (sealed by `M-GOV-13`, canonicalized per `RFC 8785`, signed via `Ed25519`)
* **Authoritative Baseline:** RealityEngine: Deterministic Pre-Execution Governance for Agentic AI with Temporally Bounded Incompleteness, Version 0.18 (Working Draft, 19 November 2026)

---

## 1. Annex A Control Mapping Matrix

| Control ID | ISO/IEC 42001 Annex A Control Objective | Applicable? | Implementation Mechanism in RealityEngine (`AIGovernanceRegime`) | `M-GOV-13` Evidence Pack Artifact & Verification Method |
| :--- | :--- | :--- | :--- | :--- |
| **A.2.2 – A.2.4** | **AI Policy** (Development, alignment, and periodic review of AI policy) | **Yes** | Domain manifests (`ω_τ`) codify enforceable organizational policy as deterministic interval predicates; `M-GOV-14` enforces annual recertification leases. | **`dossierReceipt` & `quorumSignatureBundle`:** Verifies policy sign-off by human governance quorum (`q-of-n` Ed25519 signatures) and active recertification TTL (`mon_recert_ttl_rem > 0`). |
| **A.3.2 – A.3.3** | **Internal Organization** (AI roles, responsibilities, and reporting of concerns) | **Yes** | Solid Asset Frames enforce cryptographic separation of duties (`approver_webid != preparer_webid`, `T15`); agents are barred from `approve`/`deploy` continuations; `M-GOV-12` routes serious incidents. | **`quorumSignatureBundle` & `klineIncidentArchive`:** DPoP token principal logs prove human-only approval authority and document escalation trails for hazard hits (`Ch`). |
| **A.4.2 – A.4.6** | **Resources for AI Systems** (Data, tooling, compute, and human resources) | **Yes** | `M-GOV-05` (`AIBOMProvenancePin`) pins exact SHA-256 digests for foundation models, quantizations, residual taps, SAE dictionaries (`TC-NEU-01`/`02`), and 3-of-3 runtime binaries. | **`aibomReceipt` & `parityCertificate3of3`:** Cryptographically verifies exact model/dictionary provenance and C++/Scala/Lisp voting engine build hashes. |
| **A.5.2 – A.5.5** | **Assessing Impacts of AI Systems** (AI system impact assessment process & documentation) | **Yes** | `M-GOV-01` (`ImpactDossierLifecycle`) & `M-GOV-02` (`TaskSufficiencyGate`) block domain admission until ISO 42005 Impact Assessments and `Prop. 1` fiber-saturation / `μ̄` analyses are signed. | **`dossierReceipt` (`task_sufficiency_dossier.jsonld`):** Validates SHACL-conformant `re:iso42005Assessment` and `re:euAiActArt27Fria` records pinned to `ω_τ` SHA-256. |
| **A.6.1.2 – A.6.1.3** | **AI System Life Cycle** (Objectives and processes for responsible design & development) | **Yes** | `M-GOV-04` (`RuleEpochPromotion`) gates rule updates (`τ -> τ'`) on sandbox K-line near-miss replay (`S6`), `3-of-3` parity, and atomic pointer swaps. | **`parityCertificate3of3` & `quorumSignatureBundle`:** Proves candidate rules fired on near misses, stayed silent on nominal runs, and passed `3-of-3` regression before deployment. |
| **A.6.2.2 – A.6.2.5** | **System Requirements, Architecture & Verification** (Safety bounds, V&V, deployment) | **Yes** | `M-GOV-02` & `M-GOV-08` enforce declared hazard sets `H(ω_τ)`, fail-safe vectors (`s_safe`), conserved exposure budgets (`μ̄`), and `kperf` `TO-1` latency gates. | **`dossierReceipt` & `walSegmentReceipt`:** Confirms declared `μ̄`/`δ`/`s_safe` parameters and records `kperf` `p50/p99/p999` gate pass status. |
| **A.6.2.6** | **Human Oversight & Operation** (Human-in-the-loop controls and override mechanisms) | **Yes** | One-shot Solid continuations (`Section 6`), `M-GOV-11` (`HumanReviewAntiBiasGate` mandatory canonical diff rendering), and `OSRE` `HALT_PROMOTION`/`REVOKE_EPOCH` overrides. | **`walSegmentReceipt` & `quorumSignatureBundle`:** Demonstrates `lane_diff_rendered = 1.0` prior to human DPoP approval and deterministic fail-safe assertion on override. |
| **A.6.2.7 – A.6.2.8** | **Technical Documentation & Event Logging** (Automated, tamper-evident runtime logs) | **Yes** | Durable Write-Ahead Record (`TO-12`) + `fsync`ed, hash-chained `localAssetStorageStack` event logs with `RFC 8785` + `Ed25519` receipts. | **`walSegmentReceipt`:** Provides contiguous, hash-chained pre-execution admission decisions (`admit | reject | ssafe`) and logical `RE-Clock` stamps. |
| **A.7.2 – A.7.5** | **Data for AI Systems** (Data acquisition, quality, provenance, and preparation) | **Yes** | `M-GOV-03` (`SocioTechnicalBiasAudit`) & `M-GOV-05` enforce dataset SHA-256 pinning, license tracking, and bias audit receipts for high-risk domains. | **`aibomReceipt` (`re:trainingAndEvalDataLineage`):** Links training/evaluation dataset hashes directly to signed bias-audit receipts. |
| **A.8.2 – A.8.5** | **Information for Interested Parties** (Transparency, disclosures, and incident reporting) | **Yes** | `M-GOV-10` (`SyntheticTransparencyGate`) blocks external egress lacking provenance/C2PA headers (EU AI Act Art. 50); `M-GOV-12` manages statutory incident notices (Art. 73). | **`egressArt50Log` & `klineIncidentArchive`:** Verifies outbound provenance tagging on external communications and logs containment/notification timelines for incidents. |
| **A.9.2 – A.9.4** | **Use of AI Systems** (Intended use enforcement and operational monitoring) | **Yes** | Inbound ACP/MCP boundary (`S1`), egress allowlists (`T13`), `M-GOV-07` (`μ̄` watchdog), and `M-GOV-09` (near-miss backlog enforcer) constrain runtime operation to declared bounds. | **`walSegmentReceipt` & `klineIncidentArchive`:** Evidences continuous monitoring of `μ̄` exhaustion rates, near-miss ring utilization, and automated `ssafe` clamping. |
| **A.10.2 – A.10.3** | **Third-Party and Customer Relationships** (Supplier governance and shared responsibilities) | **Yes** | `M-GOV-05` pins upstream open-weight/API model versions and external MCP/Solid Sources; `TLS 1.3`/`mTLS` and `SPIFFE` authenticate cross-boundary dependencies. | **`aibomReceipt`:** Documents exact third-party model identifiers, build digests, and cryptographic trust boundaries. |

---

## 2. Auditor Verification Procedure (`M-GOV-13` Pack Inspection)

To validate conformity during an ISO/IEC 42001 Stage 2 certification audit, an external auditor executes three deterministic checks against the Solid pod container:

1. **Cryptographic Integrity:** Canonicalize `audit-pack-{epochId}.jsonld` via `RFC 8785` (JCS) and verify the `Ed25519` signature against the organization's root-of-authority public key.
2. **SHACL Schema Conformance:** Validate the pack and all seven linked receipts against `re:AuditorEvidencePackShape` in `AIGovernanceRegime_Asset_Shapes.shacl.ttl` to confirm zero missing artifacts, valid Byzantine/crash quorum thresholds, and `approver != preparer`.
3. **Deterministic Replay Spot-Check:** Select any `walSegmentReceipt` or `klineIncidentArchive` episode, load the pinned `epochId` rule bundle across `RealityEngine_CPP`, `RealityEngine_Scala`, and `RealityEngine_LSP`, and verify bit-identical `OSRE` output reproduction from initial state `S_0` (`Appendix B`).

---

## 3. Certification Sign-Off Record

| Role | Principal WebID | Canonical Receipt Hash (`SHA-256`) | Signature Algorithm | Date |
| :--- | :--- | :--- | :--- | :--- |
| **Preparer (AI Governance Lead)** | `https://id.enterprise.org/profile/ai-gov-lead#me` | `[PENDING_SIGNATURE]` | `Ed25519` (`RFC 8785`) | `YYYY-MM-DD` |
| **Approver (Chief Risk Officer)** | `https://id.enterprise.org/profile/chief-risk-officer#me` | `[PENDING_SIGNATURE]` | `Ed25519` (`RFC 8785`) | `YYYY-MM-DD` |
| **External Lead Auditor** | `https://id.auditor.org/profile/lead-auditor#me` | `[PENDING_SIGNATURE]` | `Ed25519` (`RFC 8785`) | `YYYY-MM-DD` |
