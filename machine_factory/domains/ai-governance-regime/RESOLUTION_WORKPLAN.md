# AIGovernanceRegime: Organizational Wrapper Hardening Workplan

**Authoritative Baseline:** *RealityEngine: Deterministic Pre-Execution Governance for Agentic AI with Temporally Bounded Incompleteness*, Version 0.18 (Working Draft, 19 November 2026)  
**Target Corpus:** `AIGovernanceRegime_Corpus_315_Machines.json` (1,867 total corpus machines across 14 domains)  
**ISRE Band:** `[16960:17087]` (Hardened cells `16987–16991` active)

---

## Executive Overview

This 8-week, 4-phase engineering and governance workplan closes the **seven organizational wrapper gaps** identified in `AIGovernanceRegime_Wrapper_Gap_Analysis.md` and integrates the expanded **315-machine specification** (`M-GOV-01` through `M-GOV-315`) into **RealityEngine**.

---

## Phase 1: Bootstrap, Key Custody & Quorum Revocation (Weeks 1–2)
*Closes Gap 1 (Bootstrap & Emergency Break-Glass) and Gap 7 (Key Custody & Quorum Revocation).*

| Workstream | Target Repositories & Files | Concrete Deliverables | Acceptance / Verification Gate |
| :--- | :--- | :--- | :--- |
| **1.1 Hardware Break-Glass Pipeline (`M-GOV-15`)** | `RealityEngine_CI` (`QUORUM_CONTRACT.md`), `localAssetStorageStack` | • Implement `EmergencyEpochOverrideFrame` schema requiring offline YubiHSM/TPM root signatures.<br>• Wire auto-expiry watchdog (`TTL <= 4h`) and mandatory post-hoc `M-GOV-04` ratification continuation. | Simulated quorum deadlock is bypassed via offline root token (`PERMIT_DEPLOY = 1.0`), and automatically reverts to `REVOKE_EPOCH = 1.0` at `T + 4h` if unratified. |
| **1.2 Quorum Keyring & CRL Source (`M-GOV-17`)** | `localAssetStorageStack`, `RealityEngine_CPP` (Sources) | • Build `QuorumKeyring` Solid pod container with CRL/OCSP revocation polling.<br>• Wire `lane_quorum_integrity_ok` (`ISRE 16991`) to immediately abort any `PARKED_ON_CONTINUATION` frame signed by a revoked principal. | Revoking a quorum member's key sets `16991 := 0.0` within one polling cycle, forcing `HALT_PROMOTION = 1.0` and escaping active frames to `rework`. |
| **1.3 Cross-Departmental Quorum Policy** | `RealityEngine_CI/docs/` | • Update `M-GOV-06` (`QuorumConsensusMonitor`) to enforce multi-unit signer diversity (minimum 1 signature each from Risk, Engineering, and Legal). | `M-GOV-06` rejects a `q-of-n` signature bundle if all signers belong to the same organizational department. |

---

## Phase 2: Cryptographic Source Attestation & Canary Probing (Weeks 3–4)
*Closes Gap 2 (Governance Source Spoofing) and Gap 6 (Closed-API Model & Vendor Drift).*

| Workstream | Target Repositories & Files | Concrete Deliverables | Acceptance / Verification Gate |
| :--- | :--- | :--- | :--- |
| **2.1 SLSA / in-toto Source Verification** | `localOpenClawStack` (`openclaw_side.py`), `RealityEngine_CPP` | • Upgrade the `Sources` semantic evaluator (`Section 4.6`) to verify `in-toto` / `SLSA` provenance attestations and TPM-backed SPIFFE IDs before folding cells `16968–16975`.<br>• Drive `gate_source_slsa_attested` (`ISRE 16988`). | Unsigned or spoofed CI/webhook payloads attempting to set `gate_3of3_parity = 1.0` are dropped by semantic evaluation (`16988 := 0.0`), blocking `M-GOV-04`. |
| **2.2 Closed-API Behavioral Canary Source** | `RealityEngine_Manager`, `RealityEngine_Machines` | • Implement a scheduled Canary Probe `Source` running deterministic behavioral benchmarks against closed-API frontier endpoints.<br>• Map cosine/logit/output drift metrics to `mon_vendor_canary_drift` (`ISRE 16990`). | Simulated silent model behavior change triggers `16990 > 0.15`, tripping `M-GOV-05` to `REVOKE_EPOCH = 1.0`. |

---

## Phase 3: Adversarial Onboarding & Cross-Domain Delegation (Weeks 5–6)
*Closes Gap 3 (Domain Modeling & Semantic Blind Spots) and Gap 5 (Multi-Agent & Cross-Domain Cascading Risk).*

| Workstream | Target Repositories & Files | Concrete Deliverables | Acceptance / Verification Gate |
| :--- | :--- | :--- | :--- |
| **3.1 Adversarial Red-Team Onboarding Gate** | `RealityEngine_CI`, `RealityEngine_Machines` (`M-GOV-01`) | • Integrate `AgentDojo` and domain-specific in-bounds harm (`T13`) counter-example suites into CI.<br>• Require signed red-team pass attestation (`gate_redteam_pass`, `ISRE 16987`) before `M-GOV-01` transitions a domain from `experimental` to `accepted`. | Attempting to admit a domain manifest with an unmitigated `T13` exfiltration test fails `16987 := 0.0`, locking `M-GOV-01` in `S_Err_Rework`. |
| **3.2 Cross-Domain Delegation & Blast-Radius Cap (`M-GOV-16`)** | `RealityEngine_CPP`, `RealityEngine_Scala`, `RealityEngine_LSP` | • Implement A2A transitive delegation tracking (`CapChain` attenuation depth & aggregate $\bar{\mu}$ summation across coupled domains).<br>• Feed aggregate cross-domain $\bar{\mu}$ to `mon_cross_domain_mu_agg` (`ISRE 16989`) and latch `M-GOV-16`. | Cascading A2A calls (`ai-services -> ifrs-accounting`) exceeding aggregate $\bar{\mu}$ set the `M-GOV-16` SR-latch, asserting `REVOKE_EPOCH = 1.0` until human reset. |

---

## Phase 4: Human-Review Anti-Fatigue UX & Full Corpus Parity (Weeks 7–8)
*Closes Gap 4 (Human Approver Coercion & Rubber-Stamping) and validates the 1,867-machine corpus.*

| Workstream | Target Repositories & Files | Concrete Deliverables | Acceptance / Verification Gate |
| :--- | :--- | :--- | :--- |
| **4.1 Review Queue Rate-Limiting & Dwell Attestation** | `localAssetStorageStack` (dokieli UI / lifecycle service) | • Enforce per-principal review rate limits, mandatory checklist attestation, and minimum dwell-time verification before setting `lane_diff_rendered = 1.0` (`ISRE 16965`). | Rapid-fire ("rubber-stamp") DPoP approval requests below dwell threshold are rejected (`429 / 403`) by the lifecycle gatekeeper. |
| **4.2 Apply Corpus Patch & Run 3-of-3 Regression** | `RealityEngine_Machines`, `_CPP`, `_Scala`, `_LSP` | • Apply `region-allocation.patch.json` (`[16960:17087]`) and load `AIGovernanceRegime_Corpus_315_Machines.json` (`1,867` total machines).<br>• Validate Solid pods against `AIGovernanceRegime_Asset_Shapes-v2.shacl.ttl` and run full `3-of-3` parity suites. | `C++`, `Scala`, and `Lisp` voting runtimes achieve 100% pass-set equality across all 1,867 machines with `TO-1` `p99 <= 820 ns`. |

---

## Summary of Closure Mapping

| Wrapper Gap | Primary Machine / Mechanism | Target ISRE Cell(s) | Target Week |
| :--- | :--- | :--- | :--- |
| **1. Bootstrap & Break-Glass** | `M-GOV-15` (`BreakGlassEmergencyOverride`) | `17056`, `17057`, `17058` | Week 1 |
| **2. Governance Source Spoofing** | `SLSA` / `in-toto` Source Evaluator | `16988` (`gate_source_slsa_attested`) | Week 3 |
| **3. Domain Spec Blind Spots (`T12`/`T13`)** | `AgentDojo` CI Gate in `M-GOV-01` | `16987` (`gate_redteam_pass`) | Week 5 |
| **4. Human Rubber-Stamping (`ASI09`)** | Rate-limited dokieli Diff & Dwell Gate (`M-GOV-11`) | `16965` (`lane_diff_rendered`) | Week 7 |
| **5. Multi-Agent Cascading Risk (`ASI07`/`08`)** | `M-GOV-16` (`CrossDomainDelegationCap` SR-Latch) | `16989` (`mon_cross_domain_mu_agg`) | Week 6 |
| **6. Closed-API Vendor Drift (`T19`)** | Behavioral Canary Probe Source (`M-GOV-05`) | `16990` (`mon_vendor_canary_drift`) | Week 4 |
| **7. Key Custody & Revocation (`T9`)** | `M-GOV-17` (`QuorumKeyRevocationLifecycle`) | `16991` (`lane_quorum_integrity_ok`) | Week 2 |
