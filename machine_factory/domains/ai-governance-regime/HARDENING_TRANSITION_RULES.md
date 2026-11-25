# Formal Transition Rules: `AIGovernanceRegime` Hardening Machines (`M-GOV-15` to `M-GOV-17`)

**Authoritative Baseline:** *RealityEngine: Deterministic Pre-Execution Governance for Agentic AI with Temporally Bounded Incompleteness*, Version 0.18 (Working Draft, 19 November 2026)[^1]

---

## 1. Extended ISRE Input Cell Allocation (`16987–16991`)

To support the three hardening machines and close the organizational wrapper gaps without expanding outside the allocated `[16960:17087]` band, five reserved input cells (`16987–16991`) are activated:

| Cell Index | Signal Name | Type | Source & Validation Semantics |
| :--- | :--- | :--- | :--- |
| `16987` | `gate_redteam_pass` | Binary `{0,1}` | Adversarial Eval Source: `AgentDojo` & domain counter-example suite passed with 0 unmitigated `T13` bypasses. |
| `16988` | `gate_source_slsa_attested` | Binary `{0,1}` | Attestation Verifier Source: SPIFFE + TPM hardware attestation and `in-toto`/`SLSA` provenance verified for CI/Compliance inputs. |
| `16989` | `mon_xdomain_mu_agg` | Continuous `[0,1]` | Cross-Domain Watchdog Source: Normalized aggregate exposure budget consumed across coupled A2A delegation cones. |
| `16990` | `mon_canary_drift_score` | Continuous `[0,1]` | Behavioral Canary Source: Normalized behavioral divergence on deterministic canary prompts for closed-API / hosted endpoints (`> 0.15` = drift). |
| `16991` | `lane_quorum_integrity_ok` | Binary `{0,1}` | Quorum & CRL Source: `1.0` iff all active quorum signers are clean on CRL/OCSP (`T9`), belong to >= 2 distinct org units (`ASI09`), and meet minimum review dwell time. |

*Additionally, two existing cells are updated with strengthened semantics:*
* **`M-GOV-01` (`ImpactDossierLifecycle`)** now requires `v_{16987} in [1.0, 1.0]` (`gate_redteam_pass`) and `v_{16988} in [1.0, 1.0]` (`gate_source_slsa_attested`) before transitioning to `S_2 (ParkedReview)`.
* **`M-GOV-06` (`QuorumConsensusMonitor`)** now requires `v_{16991} in [1.0, 1.0]` (`lane_quorum_integrity_ok`) and `v_{16988} in [1.0, 1.0]` before asserting `PERMIT_DEPLOY` (`17058 := 1.0`).

---

## 2. Formal State-Machine Transition Rules (`M-GOV-15` through `M-GOV-17`)

### 15. `M-GOV-15` (`BreakGlassEmergencyOverride` — Cloneable Template)
* **Purpose:** Provides an auditable, time-bounded (`TTL <= 4 hours`) emergency bypass for zero-day containment (`T4, T6, T21`) using dual offline hardware root tokens (`lane_quorum_integrity_ok` + `gate_source_slsa_attested`), while automatically revoking the temporary epoch if post-hoc `q-of-n` quorum ratification fails before TTL expiry.
* **States:** `{S_0 (Standby), S_1 (EmergencyActive), S_2 (Ratified), S_err (ExpiredRevoked)}`
* **Transitions:**
  * `S_0 -> S_1`: `v_{16985} in [1.0, 1.0] AND v_{16988} in [1.0, 1.0] AND v_{16991} in [1.0, 1.0] AND v_{16966} in [1.0, 1.0] AND v_{16964} in [0.0, 0.0]`
    * **Output:** Write `17058 := 1.0` (`PERMIT_DEPLOY` for emergency patch), `17059 := 1.0` (`TRIGGER_INCIDENT` mandatory audit trail), and start 4-hour emergency lease timer.
  * `S_1 -> S_2` (Post-Hoc Ratification): `v_{16967} in [1.0, 1.0] AND v_{16968} in [1.0, 1.0] AND v_{16964} in [0.0, 0.0]`
    * **Output:** Write `17058 := 1.0` (Convert temporary emergency epoch to permanent standard epoch).
  * `S_1 -> S_err` (Lease Expiry or Tamper Escape): `v_{16964} in [1.0, 1.0] OR v_{16961} in [1.0, 1.0]`
    * **Output:** Write `17057 := 1.0` (`REVOKE_EPOCH`), `17056 := 1.0` (`HALT_PROMOTION`), `17058 := 0.0` (Force immediate fallback to prior verified epoch / fail-safe vector `s_safe`).

---

### 16. `M-GOV-16` (`CrossDomainDelegationCap` — Fixture Watchdog with SR Latch)
* **Purpose:** Prevents cascading multi-agent failures and budget multiplication across domain boundaries (`T20 / OWASP ASI07, ASI08`) by monitoring aggregate cross-domain exposure consumption (`v_{16989}`) and closed-API behavioral canary drift (`v_{16990}`).
* **States:** `{S_0 (Nominal), S_1 (DelegationThrottle), S_2 (CrossDomainBreachLatch)}`
* **Persistent State:** Feed-forward set-reset latch `Q_k = S_k OR (NOT R_k AND Q_{k-1})`.
* **Transitions:**
  * `S_0 -> S_1`: `v_{16989} in (0.70, 0.90] AND v_{16990} in [0.0, 0.15]`
    * **Output:** Log cross-domain approach on K-line; clamp child `CapChain` delegation depth.
  * `S_0 OR S_1 -> S_2`: `v_{16989} in (0.90, 1.0] OR v_{16990} in (0.15, 1.0]`
    * **Output:** Set latch `S_k = 1`; Write `17057 := 1.0` (`REVOKE_EPOCH`), `17059 := 1.0` (`TRIGGER_INCIDENT`), `17058 := 0.0`.
  * `S_2 -> S_0` (Human-Authorized Reset): `v_{16962} in [1.0, 1.0] AND v_{16966} in [1.0, 1.0] AND v_{16989} in [0.0, 0.50] AND v_{16990} in [0.0, 0.10]`
    * **Output:** Reset latch `R_k = 1`; Write `17058 := 1.0`.

---

### 17. `M-GOV-17` (`QuorumKeyRevocationLifecycle` — Cloneable Template)
* **Purpose:** Closes key-compromise and governance-continuity gaps (`T9 / Appendix D Item 5`) by continuously checking signer CRL/OCSP health (`v_{16991}`) and invalidating any parked continuation or active rule epoch signed by a revoked principal until key rotation completes.
* **States:** `{S_0 (KeysValid), S_1 (RevocationTriggered), S_2 (RotationParked), S_3 (KeysRotated)}`
* **Transitions:**
  * `S_0 -> S_1`: `v_{16991} in [0.0, 0.0]` (CRL/OCSP Source flags compromised signer key or violated org-unit diversity)
    * **Output:** Write `17056 := 1.0` (`HALT_PROMOTION`), `17057 := 1.0` (`REVOKE_EPOCH`), `17058 := 0.0`, `17059 := 1.0` (`TRIGGER_INCIDENT`).
  * `S_1 -> S_2`: `v_{16960} in [1.0, 1.0]`
    * **Output:** Park one-shot continuation `quorum_key_rotation` in Solid asset frame; invalidate all open continuations referencing the revoked WebID.
  * `S_2 -> S_3`: `v_{16962} in [1.0, 1.0] AND v_{16966} in [1.0, 1.0] AND v_{16991} in [1.0, 1.0] AND v_{16988} in [1.0, 1.0]`
    * **Output:** Write `17058 := 1.0` (Restore `PERMIT_DEPLOY` under rotated root-of-authority keys).

---

[^1]: *Authoritative Source Note:* All architectural references, ISRE cell allocations, SR-latch mechanics, and threat IDs (`T1–T22`) in this specification are grounded in **RealityEngine: Deterministic Pre-Execution Governance for Agentic AI with Temporally Bounded Incompleteness**, **Version 0.18 (Working Draft, 19 November 2026)**, which serves as the current authoritative specification.
