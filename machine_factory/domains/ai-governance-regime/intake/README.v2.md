# AIGovernanceRegime: Organizational Compliance & Hardening Repository Index

**Authoritative Reference:** *RealityEngine: Deterministic Pre-Execution Governance for Agentic AI with Temporally Bounded Incompleteness*, Version 0.18 (Working Draft, 19 November 2026)  
**Meta-Domain ID:** `ai-governance-regime` (`AIGovernanceRegime`)  
**Total Corpus Footprint:** `1,867` machines across `14` domains (`1,552` baseline + `315` governance machines)  
**ISRE Cell Band:** `[16960:17087]` (128 cells; zero overlap with clone space `[20480:86015]` or neuralese band `>= 86016`)

---

## 1. Repository & Audit Binder Artifact Index

| File Name | Category | Purpose & Scope |
| :--- | :--- | :--- |
| **`RealityEngine_V018_AIGovernanceRegime_Specification.md`** | Core Architecture | Complete governance analysis, global compliance gap analysis, initial 14-machine rules, Solid JSON-LD schemas, and 12-week baseline roadmap. |
| **`AIGovernanceRegime_Wrapper_Gap_Analysis.md`** | Threat & Wrapper Analysis | Evaluates `AIGovernanceRegime` against `T1–T22` and 2026 agentic threats, identifying 7 structural wrapper gaps (bootstrap, Source spoofing, `ASI09`, cross-domain cascades, vendor drift, key revocation). |
| **`AIGovernanceRegime_Hardening_Transition_Rules.md`** | Formal Specification | Defines ISRE cells `16987–16991` and formal interval-predicate transition rules for `M-GOV-15` (`BreakGlassEmergencyOverride`), `M-GOV-16` (`CrossDomainDelegationCap`), and `M-GOV-17` (`QuorumKeyRevocationLifecycle`). |
| **`AIGovernanceRegime_Hardening_Workplan.md`** | Implementation Plan | 8-week, 4-phase engineering workplan closing all 7 wrapper gaps across `RealityEngine_CPP`, `_Scala`, `_LSP`, `_CI`, `_Machines`, and `localAssetStorageStack`. |
| **`AIGovernanceRegime_Corpus_315_Machines.json`** | Machine Corpus | Hardened **315-machine** aDFA corpus (`262` cloneable templates + `53` fixture watchdogs) spanning 6 workflow families across all 13 operational domains plus 3 global meta-governance machines. |
| **`region-allocation.patch.json`** | Configuration Patch | RFC 6902 JSON Patch registering `[16960:17087]`, input Source mappings (`16960–16991`), OSRE monoid precedence (`17056–17059`), and updating total machine count to `1,867`. |
| **`AIGovernanceRegime_Asset_Shapes-v2.shacl.ttl`** | Schema & Validation | W3C SHACL shapes + SPARQL constraints validating `GovernanceAssetFrame`, `AIBOMManifest`, `TaskSufficiencyAndImpactDossier`, `AuditorEvidencePack`, `EmergencyEpochOverrideFrame` (`M-GOV-15`), and `QuorumKeyring` (`M-GOV-17`). |
| **`AIGovernanceRegime_SHACL_Suite_Documentation.md`** | Schema Documentation | Technical reference summarizing the SHACL shapes, cryptographic invariants, and embedded SPARQL constraints. |
| **`ISO42001_Statement_of_Applicability_Template.md`** | Certification Audit Binder | Standalone ISO/IEC 42001:2023 Statement of Applicability (SoA) mapping Annex A controls (`A.2–A.10`) directly to `M-GOV-13` Auditor Evidence Pack receipts. |

---

## 2. Hardened ISRE Cell Map (`[16960:17087]`)

* **Lifecycle & Quorum Lanes (`16960–16967`):** `lane_in_workflow`, `lane_re_pinned`, `lane_approved`, `lane_rework`, `lane_stale`, `lane_diff_rendered`, `lane_principal_distinct`, `lane_quorum_met`.
* **Technical & Compliance Gates (`16968–16978`):** `gate_3of3_parity`, `gate_kperf_to1`, `gate_kline_replay`, `gate_aibom_pinned`, `gate_task_sufficiency`, `comp_iso42005_signed`, `comp_eu_fria_signed`, `comp_bias_audit_signed`, `comp_high_risk_domain`, `egress_external_comm`, `egress_art50_marked`.
* **Operational Watchdogs (`16979–16983`):** `mon_mu_exhaust_rate`, `mon_t13_incident_cnt`, `mon_nearmiss_backlog`, `mon_latency_drift`, `mon_recert_ttl_rem`.
* **Action Requests (`16984–16986`):** `req_domain_admit`, `req_epoch_swap`, `req_audit_pack_seal`.
* **Hardening Extension Cells (`16987–16991`):** `gate_redteam_pass`, `gate_source_slsa_attested`, `mon_cross_domain_mu_agg`, `mon_vendor_canary_drift`, `lane_quorum_integrity_ok`.
* **OSRE Arbitrated Outputs (`17056–17059`):** `17056: HALT_PROMOTION` (`max`), `17057: REVOKE_EPOCH` (`max`), `17058: PERMIT_DEPLOY` (`min`), `17059: TRIGGER_INCIDENT` (`max`).

---

## 3. Repository Integration Sequence

1. **Apply Region & Manifest Patch:** Apply `region-allocation.patch.json` to `RealityEngine_Machines/domains/region-allocation.json` and `domain-manifest.json`.
2. **Load Hardened Corpus:** Import `AIGovernanceRegime_Corpus_315_Machines.json` into `RealityEngine_Machines` and verify `3-of-3` pass-set parity across `RealityEngine_CPP`, `RealityEngine_Scala`, and `RealityEngine_LSP`.
3. **Enable SHACL Gatekeeping:** Deploy `AIGovernanceRegime_Asset_Shapes-v2.shacl.ttl` inside `localAssetStorageStack` to validate every Solid pod write and continuation resume (`M-GOV-01` through `M-GOV-17`).
4. **Execute 8-Week Hardening Workplan:** Follow `AIGovernanceRegime_Hardening_Workplan.md` (Phases 1–4) to wire offline break-glass tokens, CRL revocation polling, SLSA Source attestations, behavioral canaries, and `AgentDojo` red-team gates.
