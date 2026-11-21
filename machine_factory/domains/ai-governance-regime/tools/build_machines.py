#!/usr/bin/env python3
"""Build the ai-governance-regime candidate machines from the specification.

    python3 tools/build_machines.py            # write machines/ and the manifests
    python3 tools/build_machines.py --check    # fail if the written files differ

Source of behavior: SPECIFICATION.md section 4.3 (M-GOV-01..14) and
HARDENING_TRANSITION_RULES.md (M-GOV-15..17 and the hardened preconditions of
M-GOV-01 and M-GOV-06). The intake corpora are not used for behavior
(REVIEW_QUEUE.md GOV-R01, GOV-R02); scope-decisions.json GOV-SD-04/05 records
the owner's choice of 17 machines on per-machine regions.

Every path from a machine's initial state to an output is one CES, and every
CES is one regular expression over Reality Events: a concatenation of event
symbols, each symbol a conjunction of interval predicates over the machine's
input elements. A disjunction in a guard becomes one CES per disjunct, so no
CES holds an alternation and no two CESs share a pattern. Where the
specification leaves a choice open, or a guard would be nondeterministic as
written, the resolution is recorded in semantic-amendments.json and cited from
the CES that carries it.

The transition rule these machines are written against is SURFACE_SPEC.md
"Boundaries: where a K-line starts and ends": the initial event is always
active; a non-initial event that fails to match is cleared; an intermediate
event that matches activates its successors and is cleared; a final event
that matches asserts its outputs and stays active while it keeps matching.
Lifecycle and gate signals are levels the PE holds while they are true, so a
chain r0 . r1 . r2 refills every step its prefix still holds, and a parked
path waits for its last symbol. A latch (an SR latch in the specification)
reads its own previous `latch` output through a PE-composed feedback element,
because a final event asserts only while it matches.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
OUT = PKG / "machines"
DOMAIN = "ai-governance-regime"
VERSION = "1.0.0"
CANDIDATE = "0.1.0"
BAND_START = 16960
INPUT_SLOT = 16          # input cells reserved per machine (cloneable rule 7)
OUTPUT_START = BAND_START + 17 * INPUT_SLOT          # 17232
OUTPUT_LEN = 8
AGG_INPUT_START = OUTPUT_START + 17 * OUTPUT_LEN     # 17368
EPS = 0.0001             # an open interval bound, made closed (semantic-amendments GOV-SA-01)

# Output elements of every governance machine. 0..3 are the domain verdicts
# (SPECIFICATION.md 4.2: 17056..17059), folded by GOV00; 4..7 are the machine's
# own status, which the specification states as states, not cells.
OUTPUTS = ["HALT_PROMOTION", "REVOKE_EPOCH", "PERMIT_DEPLOY", "TRIGGER_INCIDENT",
           "PARKED", "APPROACH", "LATCH", "REWORK"]
VERDICTS = OUTPUTS[:4]

# Signal: (specification cell, kind b=binary c=continuous, source, meaning)
SIGNALS = {
    "lane_in_workflow": (16960, "b", "lifecycle", "asset frame is active in workflow"),
    "lane_re_pinned": (16961, "b", "lifecycle", "upstream document SHA-256 changed (T16)"),
    "lane_approved": (16962, "b", "lifecycle", "human continuation resumed with a valid DPoP token"),
    "lane_stale": (16964, "b", "lifecycle", "continuation TTL or lease expired"),
    "lane_diff_rendered": (16965, "b", "lifecycle", "canonical diff rendered for the human reviewer"),
    "lane_principal_distinct": (16966, "b", "lifecycle", "approver != preparer and not an agent (T15)"),
    "lane_quorum_met": (16967, "b", "quorum monitor", "valid approval-quorum signatures >= q over the canonical bundle"),
    "gate_3of3_parity": (16968, "b", "CI", "C++, Scala and Lisp voting engines agree (3-of-3)"),
    "gate_kperf_to1": (16969, "b", "timing", "TO-1 p99 latency within its gate"),
    "gate_kline_replay": (16970, "b", "sandbox", "candidate rules fire on near misses, silent on nominal runs"),
    "gate_aibom_pinned": (16971, "b", "AIBOM", "model, quantization, tap and dictionary digests pinned"),
    "gate_task_sufficiency": (16972, "b", "manifest", "every declared hazard fiber-saturated or exposure-bounded"),
    "comp_iso42005_signed": (16973, "b", "compliance", "ISO/IEC 42005 impact assessment signed"),
    "comp_eu_fria_signed": (16974, "b", "compliance", "EU AI Act Art. 27 FRIA signed"),
    "comp_bias_audit_signed": (16975, "b", "compliance", "bias and data-lineage audit signed (Art. 10, ISO A.7)"),
    "comp_high_risk_domain": (16976, "b", "manifest", "target domain classified high-risk"),
    "egress_external_comm": (16977, "b", "boundary", "outbound ACP/MCP payload targets an external party"),
    "egress_art50_marked": (16978, "b", "boundary", "machine-readable AI provenance present (Art. 50)"),
    "mon_mu_exhaust_rate": (16979, "c", "watchdog", "normalized rate of exposure-budget exhaustions"),
    "mon_t13_incident_cnt": (16980, "c", "watchdog", "normalized count of confirmed in-bounds harm"),
    "mon_nearmiss_backlog": (16981, "c", "watchdog", "unresolved near-miss K-lines relative to ring capacity"),
    "mon_latency_drift": (16982, "c", "watchdog", "relative p99 drift above the gated baseline"),
    "mon_recert_ttl_rem": (16983, "c", "timer", "fraction of the recertification TTL remaining"),
    "req_domain_admit": (16984, "b", "action request", "proposal to admit a domain manifest"),
    "req_epoch_swap": (16985, "b", "action request", "proposal to swap the rule epoch"),
    "req_audit_pack_seal": (16986, "b", "action request", "proposal to seal an auditor evidence pack"),
    "gate_redteam_pass": (16987, "b", "adversarial eval", "red-team suite passed, no unmitigated T13 bypass"),
    "gate_source_slsa_attested": (16988, "b", "attestation", "source identity and provenance attested"),
    "mon_xdomain_mu_agg": (16989, "c", "cross-domain watchdog", "aggregate cross-domain exposure consumed"),
    "mon_canary_drift_score": (16990, "c", "canary", "behavioral drift on canary prompts"),
    "lane_quorum_integrity_ok": (16991, "b", "quorum and CRL", "signers clean on CRL/OCSP, diverse, dwell met"),
    "latch_q_prev": (None, "b", "PE feedback", "this machine's LATCH output at the previous step"),
}

# Predicate shorthands. A predicate is 1, 0, or (lo, hi), a closed interval.
def gt(x):  # open lower bound
    return (round(x + EPS, 4), 1.0)


def lt(x):  # open upper bound
    return (0.0, round(x - EPS, 4))


def le(x):
    return (0.0, x)


def ge(x):
    return (x, 1.0)


def out(*names):
    return list(names)


# ---------------------------------------------------------------- machines
# Each CES: id suffix, from-state, to-state, events (list of predicate dicts),
# outputs (names asserted), rag, spec citation, amendment ids.
MACHINES = [
    dict(n=1, stem="GOV01_impact-dossier-lifecycle", code="M-GOV-01", title="ImpactDossierLifecycle",
         kind="template", cls="governance-escalator", family="A-domain-onboarding-impact",
         asset="TaskSufficiencyAndImpactDossier", handoff="GOV02_task-sufficiency-gate",
         rule="SPECIFICATION.md 4.3 (1); HARDENING_TRANSITION_RULES.md section 1",
         desc="Impact dossier lifecycle for a domain admission: ISO/IEC 42005 and Art. 27 FRIA signed, red-team and source attestation passed, parked for human review, then approved by a distinct human principal or escaped to rework.",
         inputs=["lane_in_workflow", "req_domain_admit", "comp_iso42005_signed", "comp_eu_fria_signed",
                 "gate_redteam_pass", "gate_source_slsa_attested", "lane_approved", "lane_principal_distinct",
                 "lane_re_pinned", "lane_stale"],
         ces=[
             ("parked", "S1_Drafting", "S2_ParkedReview",
              [{"lane_in_workflow": 1, "req_domain_admit": 1},
               {"comp_iso42005_signed": 1, "comp_eu_fria_signed": 1, "gate_redteam_pass": 1,
                "gate_source_slsa_attested": 1, "lane_approved": 0, "lane_re_pinned": 0, "lane_stale": 0}],
              out("PARKED"), "AMBER", ["GOV-SA-02"]),
             ("approved", "S2_ParkedReview", "S3_Approved",
              [{"lane_in_workflow": 1, "req_domain_admit": 1},
               {"comp_iso42005_signed": 1, "comp_eu_fria_signed": 1, "gate_redteam_pass": 1,
                "gate_source_slsa_attested": 1, "lane_approved": 0, "lane_re_pinned": 0, "lane_stale": 0},
               {"lane_approved": 1, "lane_principal_distinct": 1, "lane_re_pinned": 0, "lane_stale": 0}],
              out("PERMIT_DEPLOY"), "GREEN", ["GOV-SA-03"]),
             ("rework-re-pinned", "S2_ParkedReview", "S_err_Rework",
              [{"lane_in_workflow": 1, "req_domain_admit": 1},
               {"comp_iso42005_signed": 1, "comp_eu_fria_signed": 1, "gate_redteam_pass": 1,
                "gate_source_slsa_attested": 1, "lane_approved": 0, "lane_re_pinned": 0, "lane_stale": 0},
               {"lane_re_pinned": 1}],
              out("HALT_PROMOTION", "REWORK"), "RED", []),
             ("rework-stale", "S2_ParkedReview", "S_err_Rework",
              [{"lane_in_workflow": 1, "req_domain_admit": 1},
               {"comp_iso42005_signed": 1, "comp_eu_fria_signed": 1, "gate_redteam_pass": 1,
                "gate_source_slsa_attested": 1, "lane_approved": 0, "lane_re_pinned": 0, "lane_stale": 0},
               {"lane_stale": 1}],
              out("HALT_PROMOTION", "REWORK"), "RED", []),
         ]),
    dict(n=2, stem="GOV02_task-sufficiency-gate", code="M-GOV-02", title="TaskSufficiencyGate",
         kind="template", cls="safety-compliance-checker", family="A-domain-onboarding-impact",
         asset="TaskSufficiencyAndImpactDossier", handoff="GOV03_socio-technical-bias-audit",
         rule="SPECIFICATION.md 4.3 (2)",
         desc="Task-sufficiency gate on a domain admission: permits when every declared hazard is fiber-saturated or exposure-bounded, halts otherwise.",
         inputs=["req_domain_admit", "gate_task_sufficiency"],
         ces=[
             ("verified", "S0_Idle", "S1_Verified", [{"req_domain_admit": 1, "gate_task_sufficiency": 1}],
              out("PERMIT_DEPLOY"), "GREEN", []),
             ("incomplete-hazard", "S0_Idle", "S_fail_IncompleteHazard",
              [{"req_domain_admit": 1, "gate_task_sufficiency": 0}], out("HALT_PROMOTION"), "RED", []),
         ]),
    dict(n=3, stem="GOV03_socio-technical-bias-audit", code="M-GOV-03", title="SocioTechnicalBiasAudit",
         kind="template", cls="safety-compliance-checker", family="A-domain-onboarding-impact",
         asset="TaskSufficiencyAndImpactDossier", handoff="GOV13_control-crosswalk-assembler",
         rule="SPECIFICATION.md 4.3 (3)",
         desc="Bias and data-lineage audit on a domain admission: exempt when the target domain is not high-risk, permits a high-risk domain only with a signed audit.",
         inputs=["req_domain_admit", "comp_high_risk_domain", "comp_bias_audit_signed"],
         ces=[
             ("exempt", "S0_Idle", "S1_Exempt", [{"req_domain_admit": 1, "comp_high_risk_domain": 0}],
              out("PERMIT_DEPLOY"), "GREEN", []),
             ("audited", "S0_Idle", "S2_Audited",
              [{"req_domain_admit": 1, "comp_high_risk_domain": 1, "comp_bias_audit_signed": 1}],
              out("PERMIT_DEPLOY"), "GREEN", []),
             ("bias-block", "S0_Idle", "S_fail_BiasBlock",
              [{"req_domain_admit": 1, "comp_high_risk_domain": 1, "comp_bias_audit_signed": 0}],
              out("HALT_PROMOTION"), "RED", []),
         ]),
    dict(n=4, stem="GOV04_rule-epoch-promotion", code="M-GOV-04", title="RuleEpochPromotion",
         kind="template", cls="governance-escalator", family="B-rule-epoch-aibom",
         asset="GovernanceAssetFrame", handoff="GOV06_quorum-consensus-monitor",
         rule="SPECIFICATION.md 4.3 (4)",
         desc="Rule-epoch promotion: 3-of-3 engine parity and K-line replay verified, AIBOM pinned, parked for the approval quorum, then promoted or rejected.",
         inputs=["req_epoch_swap", "gate_3of3_parity", "gate_kline_replay", "gate_aibom_pinned",
                 "lane_quorum_met", "lane_principal_distinct", "lane_re_pinned", "lane_stale"],
         ces=[
             ("awaiting-quorum", "S1_ReplayVerified", "S2_AwaitingQuorum",
              [{"req_epoch_swap": 1, "gate_3of3_parity": 1, "gate_kline_replay": 1},
               {"gate_aibom_pinned": 1, "lane_quorum_met": 0, "lane_principal_distinct": 1,
                "lane_re_pinned": 0, "lane_stale": 0}],
              out("PARKED"), "AMBER", ["GOV-SA-02"]),
             ("promoted", "S2_AwaitingQuorum", "S3_Promoted",
              [{"req_epoch_swap": 1, "gate_3of3_parity": 1, "gate_kline_replay": 1},
               {"gate_aibom_pinned": 1, "lane_quorum_met": 0, "lane_principal_distinct": 1,
                "lane_re_pinned": 0, "lane_stale": 0},
               {"lane_quorum_met": 1, "lane_principal_distinct": 1, "lane_re_pinned": 0, "lane_stale": 0}],
              out("PERMIT_DEPLOY"), "GREEN", ["GOV-SA-03"]),
             ("rejected-re-pinned", "S2_AwaitingQuorum", "S_err_Rejected",
              [{"req_epoch_swap": 1, "gate_3of3_parity": 1, "gate_kline_replay": 1},
               {"gate_aibom_pinned": 1, "lane_quorum_met": 0, "lane_principal_distinct": 1,
                "lane_re_pinned": 0, "lane_stale": 0},
               {"lane_re_pinned": 1}],
              out("HALT_PROMOTION", "REWORK"), "RED", []),
             ("rejected-stale", "S2_AwaitingQuorum", "S_err_Rejected",
              [{"req_epoch_swap": 1, "gate_3of3_parity": 1, "gate_kline_replay": 1},
               {"gate_aibom_pinned": 1, "lane_quorum_met": 0, "lane_principal_distinct": 1,
                "lane_re_pinned": 0, "lane_stale": 0},
               {"lane_stale": 1}],
              out("HALT_PROMOTION", "REWORK"), "RED", []),
             ("rejected-self-approval", "S2_AwaitingQuorum", "S_err_Rejected",
              [{"req_epoch_swap": 1, "gate_3of3_parity": 1, "gate_kline_replay": 1},
               {"gate_aibom_pinned": 1, "lane_quorum_met": 0, "lane_principal_distinct": 1,
                "lane_re_pinned": 0, "lane_stale": 0},
               {"lane_principal_distinct": 0}],
              out("HALT_PROMOTION", "REWORK"), "RED", []),
         ]),
    dict(n=5, stem="GOV05_aibom-provenance-pin", code="M-GOV-05", title="AIBOMProvenancePin",
         kind="template", cls="safety-compliance-checker", family="B-rule-epoch-aibom",
         asset="AIBOMManifest", handoff="GOV13_control-crosswalk-assembler",
         rule="SPECIFICATION.md 4.3 (5)",
         desc="AIBOM provenance pin on a domain admission or epoch swap: permits only when every model, quantization, tap and dictionary digest is pinned.",
         inputs=["req_domain_admit", "req_epoch_swap", "gate_aibom_pinned"],
         ces=[
             ("pinned-admit", "S0_Idle", "S1_Pinned", [{"req_domain_admit": 1, "gate_aibom_pinned": 1}],
              out("PERMIT_DEPLOY"), "GREEN", ["GOV-SA-04"]),
             ("pinned-epoch", "S0_Idle", "S1_Pinned", [{"req_epoch_swap": 1, "gate_aibom_pinned": 1}],
              out("PERMIT_DEPLOY"), "GREEN", ["GOV-SA-04"]),
             ("unpinned-admit", "S0_Idle", "S_fail_UnpinnedModel",
              [{"req_domain_admit": 1, "gate_aibom_pinned": 0}], out("HALT_PROMOTION"), "RED", ["GOV-SA-04"]),
             ("unpinned-epoch", "S0_Idle", "S_fail_UnpinnedModel",
              [{"req_epoch_swap": 1, "gate_aibom_pinned": 0}], out("HALT_PROMOTION"), "RED", ["GOV-SA-04"]),
         ]),
    dict(n=6, stem="GOV06_quorum-consensus-monitor", code="M-GOV-06", title="QuorumConsensusMonitor",
         kind="fixture", cls="safety-compliance-checker", family="B-rule-epoch-aibom",
         asset="GovernanceAssetFrame", handoff=None,
         rule="SPECIFICATION.md 4.3 (6); HARDENING_TRANSITION_RULES.md section 1",
         desc="Approval-quorum monitor on an epoch swap: permits only with the approval quorum met, a distinct principal, clean signer keys and attested sources; halts on any one missing.",
         inputs=["req_epoch_swap", "lane_quorum_met", "lane_principal_distinct", "lane_quorum_integrity_ok",
                 "gate_source_slsa_attested"],
         ces=[
             ("quorum-valid", "S0_Standby", "S1_QuorumValid",
              [{"req_epoch_swap": 1, "lane_quorum_met": 1, "lane_principal_distinct": 1,
                "lane_quorum_integrity_ok": 1, "gate_source_slsa_attested": 1}],
              out("PERMIT_DEPLOY"), "GREEN", []),
             ("violation-quorum", "S0_Standby", "S_fail_QuorumViolation",
              [{"req_epoch_swap": 1, "lane_quorum_met": 0}], out("HALT_PROMOTION"), "RED", []),
             ("violation-self-approval", "S0_Standby", "S_fail_QuorumViolation",
              [{"req_epoch_swap": 1, "lane_principal_distinct": 0}], out("HALT_PROMOTION"), "RED", []),
             ("violation-key-integrity", "S0_Standby", "S_fail_QuorumViolation",
              [{"req_epoch_swap": 1, "lane_quorum_integrity_ok": 0}], out("HALT_PROMOTION"), "RED", ["GOV-SA-05"]),
             ("violation-unattested", "S0_Standby", "S_fail_QuorumViolation",
              [{"req_epoch_swap": 1, "gate_source_slsa_attested": 0}], out("HALT_PROMOTION"), "RED", ["GOV-SA-05"]),
         ]),
    dict(n=7, stem="GOV07_exposure-budget-watchdog", code="M-GOV-07", title="ExposureBudgetWatchdog",
         kind="fixture", cls="signal-monitor", family="C-runtime-assurance", asset=None, handoff=None,
         rule="SPECIFICATION.md 4.3 (7)", latch=True,
         desc="Exposure-budget watchdog with an SR latch: reports the approach band, latches a revoke and an incident when the exhaustion rate breaches, and releases only on a distinct human approval with the rate back in band.",
         inputs=["mon_mu_exhaust_rate", "lane_approved", "lane_principal_distinct", "latch_q_prev"],
         ces=[
             ("approach", "S0_Nominal", "S1_Warning", [{"mon_mu_exhaust_rate": (0.0201, 0.05), "latch_q_prev": 0}],
              out("APPROACH"), "AMBER", ["GOV-SA-01"]),
             ("breach-set", "S0_Nominal|S1_Warning", "S2_BreachLatch", [{"mon_mu_exhaust_rate": gt(0.05)}],
              out("REVOKE_EPOCH", "TRIGGER_INCIDENT", "LATCH"), "RED", ["GOV-SA-01", "GOV-SA-06"]),
             ("breach-hold-unapproved", "S2_BreachLatch", "S2_BreachLatch",
              [{"latch_q_prev": 1, "lane_approved": 0}], out("REVOKE_EPOCH", "LATCH"), "RED", ["GOV-SA-06"]),
             ("breach-hold-not-distinct", "S2_BreachLatch", "S2_BreachLatch",
              [{"latch_q_prev": 1, "lane_principal_distinct": 0}], out("REVOKE_EPOCH", "LATCH"), "RED", ["GOV-SA-06"]),
             ("breach-hold-rate", "S2_BreachLatch", "S2_BreachLatch",
              [{"latch_q_prev": 1, "mon_mu_exhaust_rate": gt(0.02)}], out("REVOKE_EPOCH", "LATCH"), "RED", ["GOV-SA-06"]),
             ("breach-reset", "S2_BreachLatch", "S0_Nominal",
              [{"latch_q_prev": 1, "lane_approved": 1, "lane_principal_distinct": 1, "mon_mu_exhaust_rate": le(0.02)}],
              out(), "GREEN", ["GOV-SA-06"]),
         ]),
    dict(n=8, stem="GOV08_latency-gate-sentinel", code="M-GOV-08", title="LatencyGateSentinel",
         kind="fixture", cls="signal-monitor", family="C-runtime-assurance", asset=None, handoff=None,
         rule="SPECIFICATION.md 4.3 (8)",
         desc="Latency gate sentinel: halts while the TO-1 gate fails or p99 drift exceeds 0.10, permits while both are within their gate.",
         inputs=["gate_kperf_to1", "mon_latency_drift"],
         ces=[
             ("drift-gate-failed", "S0_WithinSLA", "S1_LatencyDrift", [{"gate_kperf_to1": 0}],
              out("HALT_PROMOTION"), "RED", []),
             ("drift-latency", "S0_WithinSLA", "S1_LatencyDrift", [{"mon_latency_drift": gt(0.10)}],
              out("HALT_PROMOTION"), "RED", ["GOV-SA-01"]),
             ("within-sla", "S1_LatencyDrift", "S0_WithinSLA", [{"gate_kperf_to1": 1, "mon_latency_drift": le(0.10)}],
              out("PERMIT_DEPLOY"), "GREEN", ["GOV-SA-07"]),
         ]),
    dict(n=9, stem="GOV09_near-miss-backlog-enforcer", code="M-GOV-09", title="NearMissBacklogEnforcer",
         kind="fixture", cls="signal-monitor", family="C-runtime-assurance", asset=None, handoff=None,
         rule="SPECIFICATION.md 4.3 (9)", latch=True,
         desc="Near-miss backlog enforcer with hysteresis: halts promotion when the unresolved backlog reaches 0.80 of ring capacity and holds until it falls below 0.50.",
         inputs=["mon_nearmiss_backlog", "latch_q_prev"],
         ces=[
             ("backlog-set", "S0_Nominal", "S1_BacklogThreshold", [{"mon_nearmiss_backlog": ge(0.80)}],
              out("HALT_PROMOTION", "LATCH"), "RED", ["GOV-SA-06"]),
             ("backlog-hold", "S1_BacklogThreshold", "S1_BacklogThreshold",
              [{"latch_q_prev": 1, "mon_nearmiss_backlog": ge(0.50)}], out("HALT_PROMOTION", "LATCH"), "RED", ["GOV-SA-06"]),
             ("backlog-reset", "S1_BacklogThreshold", "S0_Nominal",
              [{"latch_q_prev": 1, "mon_nearmiss_backlog": lt(0.50)}], out(), "GREEN", ["GOV-SA-01", "GOV-SA-06"]),
         ]),
    dict(n=10, stem="GOV10_synthetic-transparency-gate", code="M-GOV-10", title="SyntheticTransparencyGate",
         kind="template", cls="safety-compliance-checker", family="D-transparency-oversight",
         asset="EgressArt50Log", handoff="GOV13_control-crosswalk-assembler",
         rule="SPECIFICATION.md 4.3 (10)",
         desc="Synthetic-content transparency gate (EU AI Act Art. 50): permits internal traffic and marked external traffic, halts unmarked external traffic.",
         inputs=["egress_external_comm", "egress_art50_marked"],
         ces=[
             ("pass-internal", "S0_Idle", "S1_PassInternal", [{"egress_external_comm": 0}],
              out("PERMIT_DEPLOY"), "GREEN", ["GOV-SA-08"]),
             ("pass-marked", "S0_Idle", "S2_PassMarked", [{"egress_external_comm": 1, "egress_art50_marked": 1}],
              out("PERMIT_DEPLOY"), "GREEN", []),
             ("unmarked-block", "S0_Idle", "S_fail_UnmarkedBlock", [{"egress_external_comm": 1, "egress_art50_marked": 0}],
              out("HALT_PROMOTION"), "RED", []),
         ]),
    dict(n=11, stem="GOV11_human-review-anti-bias-gate", code="M-GOV-11", title="HumanReviewAntiBiasGate",
         kind="template", cls="safety-compliance-checker", family="D-transparency-oversight",
         asset="GovernanceAssetFrame", handoff="GOV13_control-crosswalk-assembler",
         rule="SPECIFICATION.md 4.3 (11)",
         desc="Human review gate: permits once the canonical diff is rendered to a distinct human principal, halts an approval given without a rendered diff.",
         inputs=["lane_diff_rendered", "lane_principal_distinct", "lane_approved"],
         ces=[
             ("diff-verified", "S0_AwaitingDiff", "S1_DiffVerified",
              [{"lane_diff_rendered": 1, "lane_principal_distinct": 1}], out("PERMIT_DEPLOY"), "GREEN", []),
             ("blind-approval-block", "S0_AwaitingDiff", "S_fail_BlindApprovalBlock",
              [{"lane_approved": 1, "lane_diff_rendered": 0}], out("HALT_PROMOTION"), "RED", []),
         ]),
    dict(n=12, stem="GOV12_serious-incident-responder", code="M-GOV-12", title="SeriousIncidentResponder",
         kind="template", cls="governance-escalator", family="E-incident-audit",
         asset="KLineIncidentArchive", handoff="GOV13_control-crosswalk-assembler",
         rule="SPECIFICATION.md 4.3 (12)", latch=True,
         desc="Serious-incident responder (EU AI Act Art. 73): contains on confirmed harm or a budget breach, parks the statutory notice, and closes only on a distinct human approval with no harm active.",
         inputs=["mon_t13_incident_cnt", "mon_mu_exhaust_rate", "lane_in_workflow", "lane_approved",
                 "lane_principal_distinct", "latch_q_prev"],
         ces=[
             ("contain-harm", "S0_Standby", "S1_Contained", [{"mon_t13_incident_cnt": gt(0.0)}],
              out("REVOKE_EPOCH", "TRIGGER_INCIDENT", "LATCH"), "RED", ["GOV-SA-01", "GOV-SA-06"]),
             ("contain-budget", "S0_Standby", "S1_Contained", [{"mon_mu_exhaust_rate": gt(0.05)}],
              out("REVOKE_EPOCH", "TRIGGER_INCIDENT", "LATCH"), "RED", ["GOV-SA-01", "GOV-SA-06"]),
             ("contained-hold", "S1_Contained", "S1_Contained", [{"latch_q_prev": 1, "lane_in_workflow": 0}],
              out("REVOKE_EPOCH", "TRIGGER_INCIDENT", "LATCH"), "RED", ["GOV-SA-06"]),
             ("notice-parked", "S1_Contained", "S2_NoticeParked",
              [{"latch_q_prev": 1, "lane_in_workflow": 1, "lane_approved": 0}],
              out("REVOKE_EPOCH", "PARKED", "LATCH"), "AMBER", ["GOV-SA-02", "GOV-SA-06"]),
             ("notice-hold-not-distinct", "S2_NoticeParked", "S2_NoticeParked",
              [{"latch_q_prev": 1, "lane_principal_distinct": 0}], out("REVOKE_EPOCH", "LATCH"), "RED", ["GOV-SA-06"]),
             ("notice-hold-harm", "S2_NoticeParked", "S2_NoticeParked",
              [{"latch_q_prev": 1, "mon_t13_incident_cnt": gt(0.0)}], out("REVOKE_EPOCH", "LATCH"), "RED", ["GOV-SA-06"]),
             ("closed", "S2_NoticeParked", "S3_Closed",
              [{"latch_q_prev": 1, "lane_in_workflow": 1, "lane_approved": 1, "lane_principal_distinct": 1,
                "mon_t13_incident_cnt": 0}], out(), "GREEN", ["GOV-SA-06"]),
         ]),
    dict(n=13, stem="GOV13_control-crosswalk-assembler", code="M-GOV-13", title="ControlCrosswalkAssembler",
         kind="template", cls="evidence-archive", family="E-incident-audit",
         asset="AuditorEvidencePack", handoff="GOV00_governance-verdict-aggregator",
         rule="SPECIFICATION.md 4.3 (13)",
         desc="Control crosswalk assembler: assembles an auditor evidence pack once parity, AIBOM and the impact assessment are in place, seals it on a distinct human approval, and halts an incomplete pack.",
         inputs=["req_audit_pack_seal", "gate_3of3_parity", "gate_aibom_pinned", "comp_iso42005_signed",
                 "lane_approved", "lane_principal_distinct", "lane_re_pinned"],
         ces=[
             ("assembling", "S0_Idle", "S1_Assembling",
              [{"req_audit_pack_seal": 1, "gate_3of3_parity": 1, "gate_aibom_pinned": 1, "comp_iso42005_signed": 1,
                "lane_approved": 0}],
              out("PARKED"), "AMBER", ["GOV-SA-02"]),
             ("sealed", "S1_Assembling", "S2_Sealed",
              [{"req_audit_pack_seal": 1, "gate_3of3_parity": 1, "gate_aibom_pinned": 1, "comp_iso42005_signed": 1,
                "lane_approved": 0},
               {"lane_approved": 1, "lane_principal_distinct": 1, "lane_re_pinned": 0}],
              out("PERMIT_DEPLOY"), "GREEN", []),
             ("incomplete-parity", "S0_Idle", "S_fail_IncompletePack",
              [{"req_audit_pack_seal": 1, "gate_3of3_parity": 0}], out("HALT_PROMOTION"), "RED", []),
             ("incomplete-aibom", "S0_Idle", "S_fail_IncompletePack",
              [{"req_audit_pack_seal": 1, "gate_aibom_pinned": 0}], out("HALT_PROMOTION"), "RED", []),
             ("incomplete-impact", "S0_Idle", "S_fail_IncompletePack",
              [{"req_audit_pack_seal": 1, "comp_iso42005_signed": 0}], out("HALT_PROMOTION"), "RED", []),
         ]),
    dict(n=14, stem="GOV14_periodic-recertification-timer", code="M-GOV-14", title="PeriodicRecertificationTimer",
         kind="fixture", cls="signal-monitor", family="A-domain-onboarding-impact", asset=None, handoff=None,
         rule="SPECIFICATION.md 4.3 (14)", latch=True,
         desc="Periodic recertification timer: opens the renewal window at 15% TTL remaining, latches a revoke on expiry, and restores only on a renewed TTL with a human approval.",
         inputs=["mon_recert_ttl_rem", "lane_approved", "latch_q_prev"],
         ces=[
             ("renewal-window", "S0_Current", "S1_RenewalWindow",
              [{"mon_recert_ttl_rem": (EPS, 0.15), "latch_q_prev": 0}], out("APPROACH"), "AMBER", ["GOV-SA-01"]),
             ("expired-set", "S0_Current|S1_RenewalWindow", "S2_ExpiredRevoked", [{"mon_recert_ttl_rem": 0}],
              out("REVOKE_EPOCH", "LATCH"), "RED", ["GOV-SA-06"]),
             ("expired-hold-ttl", "S2_ExpiredRevoked", "S2_ExpiredRevoked",
              [{"latch_q_prev": 1, "mon_recert_ttl_rem": le(0.15)}], out("REVOKE_EPOCH", "LATCH"), "RED", ["GOV-SA-06"]),
             ("expired-hold-unapproved", "S2_ExpiredRevoked", "S2_ExpiredRevoked",
              [{"latch_q_prev": 1, "lane_approved": 0}], out("REVOKE_EPOCH", "LATCH"), "RED", ["GOV-SA-06"]),
             ("recertified", "S2_ExpiredRevoked", "S0_Current",
              [{"latch_q_prev": 1, "mon_recert_ttl_rem": gt(0.15), "lane_approved": 1}], out(), "GREEN",
              ["GOV-SA-01", "GOV-SA-06"]),
         ]),
    dict(n=15, stem="GOV15_break-glass-emergency-override", code="M-GOV-15", title="BreakGlassEmergencyOverride",
         kind="template", cls="governance-escalator", family="H-hardening",
         asset="EmergencyEpochOverrideFrame", handoff="GOV04_rule-epoch-promotion",
         rule="HARDENING_TRANSITION_RULES.md section 2 (15)",
         desc="Break-glass emergency override: an attested, distinct principal with clean keys may permit an emergency epoch under a mandatory incident trail; post-hoc quorum and parity ratify it, and lease expiry or tamper revokes it.",
         inputs=["req_epoch_swap", "gate_source_slsa_attested", "lane_quorum_integrity_ok", "lane_principal_distinct",
                 "lane_stale", "lane_re_pinned", "lane_quorum_met", "gate_3of3_parity"],
         ces=[
             ("emergency-active", "S0_Standby", "S1_EmergencyActive",
              [{"req_epoch_swap": 1, "gate_source_slsa_attested": 1, "lane_quorum_integrity_ok": 1,
                "lane_principal_distinct": 1, "lane_stale": 0, "lane_re_pinned": 0, "lane_quorum_met": 0}],
              out("PERMIT_DEPLOY", "TRIGGER_INCIDENT"), "AMBER", ["GOV-SA-09", "GOV-SA-10"]),
             ("ratified", "S1_EmergencyActive", "S2_Ratified",
              [{"req_epoch_swap": 1, "gate_source_slsa_attested": 1, "lane_quorum_integrity_ok": 1,
                "lane_principal_distinct": 1, "lane_stale": 0, "lane_re_pinned": 0, "lane_quorum_met": 0},
               {"lane_quorum_met": 1, "gate_3of3_parity": 1, "lane_stale": 0}],
              out("PERMIT_DEPLOY"), "GREEN", []),
             ("expired-revoked", "S1_EmergencyActive", "S_err_ExpiredRevoked",
              [{"req_epoch_swap": 1, "gate_source_slsa_attested": 1, "lane_quorum_integrity_ok": 1,
                "lane_principal_distinct": 1, "lane_stale": 0, "lane_re_pinned": 0, "lane_quorum_met": 0},
               {"lane_stale": 1}],
              out("HALT_PROMOTION", "REVOKE_EPOCH", "REWORK"), "RED", []),
             ("tamper-revoked", "S1_EmergencyActive", "S_err_ExpiredRevoked",
              [{"req_epoch_swap": 1, "gate_source_slsa_attested": 1, "lane_quorum_integrity_ok": 1,
                "lane_principal_distinct": 1, "lane_stale": 0, "lane_re_pinned": 0, "lane_quorum_met": 0},
               {"lane_re_pinned": 1}],
              out("HALT_PROMOTION", "REVOKE_EPOCH", "REWORK"), "RED", []),
         ]),
    dict(n=16, stem="GOV16_cross-domain-delegation-cap", code="M-GOV-16", title="CrossDomainDelegationCap",
         kind="fixture", cls="signal-monitor", family="H-hardening", asset=None, handoff=None,
         rule="HARDENING_TRANSITION_RULES.md section 2 (16)", latch=True,
         desc="Cross-domain delegation cap with an SR latch: throttles delegation in the approach band, latches a revoke and an incident when aggregate exposure or canary drift breaches, and restores on a distinct human approval with both back in band.",
         inputs=["mon_xdomain_mu_agg", "mon_canary_drift_score", "lane_approved", "lane_principal_distinct",
                 "latch_q_prev"],
         ces=[
             ("delegation-throttle", "S0_Nominal", "S1_DelegationThrottle",
              [{"mon_xdomain_mu_agg": (0.7001, 0.90), "mon_canary_drift_score": le(0.15), "latch_q_prev": 0}],
              out("APPROACH"), "AMBER", ["GOV-SA-01"]),
             ("breach-exposure", "S0_Nominal|S1_DelegationThrottle", "S2_CrossDomainBreachLatch",
              [{"mon_xdomain_mu_agg": gt(0.90)}], out("REVOKE_EPOCH", "TRIGGER_INCIDENT", "LATCH"), "RED",
              ["GOV-SA-01", "GOV-SA-06"]),
             ("breach-canary", "S0_Nominal|S1_DelegationThrottle", "S2_CrossDomainBreachLatch",
              [{"mon_canary_drift_score": gt(0.15)}], out("REVOKE_EPOCH", "TRIGGER_INCIDENT", "LATCH"), "RED",
              ["GOV-SA-01", "GOV-SA-06"]),
             ("breach-hold-unapproved", "S2_CrossDomainBreachLatch", "S2_CrossDomainBreachLatch",
              [{"latch_q_prev": 1, "lane_approved": 0}], out("REVOKE_EPOCH", "LATCH"), "RED", ["GOV-SA-06"]),
             ("breach-hold-not-distinct", "S2_CrossDomainBreachLatch", "S2_CrossDomainBreachLatch",
              [{"latch_q_prev": 1, "lane_principal_distinct": 0}], out("REVOKE_EPOCH", "LATCH"), "RED", ["GOV-SA-06"]),
             ("breach-hold-exposure", "S2_CrossDomainBreachLatch", "S2_CrossDomainBreachLatch",
              [{"latch_q_prev": 1, "mon_xdomain_mu_agg": gt(0.50)}], out("REVOKE_EPOCH", "LATCH"), "RED", ["GOV-SA-06"]),
             ("breach-hold-canary", "S2_CrossDomainBreachLatch", "S2_CrossDomainBreachLatch",
              [{"latch_q_prev": 1, "mon_canary_drift_score": gt(0.10)}], out("REVOKE_EPOCH", "LATCH"), "RED", ["GOV-SA-06"]),
             ("breach-reset", "S2_CrossDomainBreachLatch", "S0_Nominal",
              [{"latch_q_prev": 1, "lane_approved": 1, "lane_principal_distinct": 1, "mon_xdomain_mu_agg": le(0.50),
                "mon_canary_drift_score": le(0.10)}], out("PERMIT_DEPLOY"), "GREEN", ["GOV-SA-06"]),
         ]),
    dict(n=17, stem="GOV17_quorum-key-revocation-lifecycle", code="M-GOV-17", title="QuorumKeyRevocationLifecycle",
         kind="template", cls="governance-escalator", family="H-hardening",
         asset="QuorumKeyring", handoff="GOV06_quorum-consensus-monitor",
         rule="HARDENING_TRANSITION_RULES.md section 2 (17)", latch=True,
         desc="Quorum key revocation lifecycle: on a compromised or non-diverse signer key it halts, revokes and raises an incident, parks the key rotation, and restores the permit only once rotation is approved by a distinct human with clean keys and attested sources.",
         inputs=["lane_quorum_integrity_ok", "lane_in_workflow", "lane_approved", "lane_principal_distinct",
                 "gate_source_slsa_attested", "latch_q_prev"],
         ces=[
             ("revocation-triggered", "S0_KeysValid", "S1_RevocationTriggered", [{"lane_quorum_integrity_ok": 0}],
              out("HALT_PROMOTION", "REVOKE_EPOCH", "TRIGGER_INCIDENT", "LATCH"), "RED", ["GOV-SA-06"]),
             ("revocation-hold", "S1_RevocationTriggered", "S1_RevocationTriggered",
              [{"latch_q_prev": 1, "lane_in_workflow": 0}], out("HALT_PROMOTION", "REVOKE_EPOCH", "LATCH"), "RED",
              ["GOV-SA-06"]),
             ("rotation-parked", "S1_RevocationTriggered", "S2_RotationParked",
              [{"latch_q_prev": 1, "lane_in_workflow": 1, "lane_approved": 0}],
              out("HALT_PROMOTION", "REVOKE_EPOCH", "PARKED", "LATCH"), "AMBER", ["GOV-SA-02", "GOV-SA-06"]),
             ("rotation-hold-not-distinct", "S2_RotationParked", "S2_RotationParked",
              [{"latch_q_prev": 1, "lane_principal_distinct": 0}], out("HALT_PROMOTION", "REVOKE_EPOCH", "LATCH"),
              "RED", ["GOV-SA-06"]),
             ("rotation-hold-unattested", "S2_RotationParked", "S2_RotationParked",
              [{"latch_q_prev": 1, "gate_source_slsa_attested": 0}], out("HALT_PROMOTION", "REVOKE_EPOCH", "LATCH"),
              "RED", ["GOV-SA-06"]),
             ("keys-rotated", "S2_RotationParked", "S3_KeysRotated",
              [{"latch_q_prev": 1, "lane_in_workflow": 1, "lane_approved": 1, "lane_principal_distinct": 1,
                "lane_quorum_integrity_ok": 1, "gate_source_slsa_attested": 1}], out("PERMIT_DEPLOY"), "GREEN",
              ["GOV-SA-06"]),
         ]),
]

# Nominal input values for fixtures: the quiet state every scenario starts from.
NOMINAL = {"lane_principal_distinct": 1, "lane_quorum_integrity_ok": 1, "gate_source_slsa_attested": 1,
           "gate_kperf_to1": 1, "mon_recert_ttl_rem": 1.0}

# Context a CES's fixture starts from, so a fail path isolates its one missing
# input instead of failing on every input at once: (machine, ces) -> levels.
FIXTURE_CONTEXT = {
    (6, "violation-self-approval"): {"lane_quorum_met": 1},
    (6, "violation-key-integrity"): {"lane_quorum_met": 1},
    (6, "violation-unattested"): {"lane_quorum_met": 1},
    (13, "incomplete-parity"): {"gate_aibom_pinned": 1, "comp_iso42005_signed": 1},
    (13, "incomplete-aibom"): {"gate_3of3_parity": 1, "comp_iso42005_signed": 1},
    (13, "incomplete-impact"): {"gate_3of3_parity": 1, "gate_aibom_pinned": 1},
    (3, "bias-block"): {},
}

# Values a CES's fixture uses at its last step instead of the interval midpoint,
# so a hold path is shown without its set condition also holding.
FIXTURE_VALUES = {
    (7, "breach-hold-rate"): {"mon_mu_exhaust_rate": 0.03},
    (16, "breach-hold-canary"): {"mon_canary_drift_score": 0.12},
}

# Extra scenarios per machine beyond one per CES: (name, steps, purpose).
NEGATIVES = {
    1: [("approval-without-review", [{"lane_in_workflow": 1, "req_domain_admit": 1, "lane_approved": 1}],
         "approval before the dossier is signed and parked does not permit"),
        ("self-approval", [{"lane_in_workflow": 1, "req_domain_admit": 1},
                           {"comp_iso42005_signed": 1, "comp_eu_fria_signed": 1, "gate_redteam_pass": 1},
                           {"lane_approved": 1, "lane_principal_distinct": 0}],
         "an approval by the preparer or an agent (T15) does not permit"),
        ("red-team-missing", [{"lane_in_workflow": 1, "req_domain_admit": 1},
                              {"comp_iso42005_signed": 1, "comp_eu_fria_signed": 1, "gate_redteam_pass": 0}],
         "the dossier does not park without the red-team gate (hardening)")],
    4: [("promotion-without-replay", [{"req_epoch_swap": 1, "gate_3of3_parity": 1, "gate_kline_replay": 0},
                                      {"gate_aibom_pinned": 1}, {"lane_quorum_met": 1}],
         "no promotion without the K-line replay gate")],
    7: [("latch-holds-in-band", [{"mon_mu_exhaust_rate": 0.5}, {"mon_mu_exhaust_rate": 0.01}],
         "the breach latch holds after the rate falls, until a distinct human approves"),
        ("latch-released", [{"mon_mu_exhaust_rate": 0.5}, {"mon_mu_exhaust_rate": 0.01},
                            {"mon_mu_exhaust_rate": 0.01, "lane_approved": 1}, {"mon_mu_exhaust_rate": 0.01}],
         "the latch releases on approval with the rate in band, and stays released")],
    9: [("hysteresis-hold", [{"mon_nearmiss_backlog": 0.9}, {"mon_nearmiss_backlog": 0.6}],
         "the halt holds between 0.50 and 0.80 once set"),
        ("hysteresis-no-set", [{"mon_nearmiss_backlog": 0.6}],
         "0.60 without a prior breach does not halt")],
    11: [("blind-approval-with-diff", [{"lane_approved": 1, "lane_diff_rendered": 1, "lane_principal_distinct": 0}],
          "an approval with a diff but by a non-distinct principal neither permits nor is a blind approval")],
    14: [("expiry-holds-after-renewal", [{"mon_recert_ttl_rem": 0.0}, {"mon_recert_ttl_rem": 0.5}],
          "a renewed TTL without approval keeps the epoch revoked")],
    17: [("rotation-without-approval", [{"lane_quorum_integrity_ok": 0}, {"lane_quorum_integrity_ok": 1},
                                        {"lane_in_workflow": 1}],
          "clean keys alone do not restore the permit; the rotation stays parked")],
}


# ---------------------------------------------------------------- encoding
def element(pred):
    """One Reality Event element for a predicate; None is a don't-care."""
    if pred is None:
        return {"value": 0.5, "threshold": 0.5, "comparatorType": "threshold"}
    if pred in (0, 1):
        return {"value": float(pred), "comparatorType": "equals"}
    lo, hi = pred
    if lo == hi:
        return {"value": float(lo), "comparatorType": "equals"}
    return {"value": round((lo + hi) / 2, 6), "threshold": round((hi - lo) / 2, 6), "comparatorType": "threshold"}


def accepts(el, x):
    """SURFACE_SPEC.md "Comparators" for the comparators these machines use."""
    c = el["comparatorType"]
    if c == "equals":
        return x == el["value"]
    if c == "threshold":
        return abs(el["value"] - x) <= el.get("threshold", 0.1) + 1e-12
    raise ValueError(c)


def symbol(pred_map, inputs):
    parts = []
    for name in inputs:
        p = pred_map.get(name)
        if p is None:
            continue
        if p in (0, 1):
            parts.append(f"{name}={p}")
        elif p[0] == p[1]:
            parts.append(f"{name}={p[0]:g}")
        else:
            parts.append(f"{name}∈[{p[0]:g},{p[1]:g}]")
    return "[" + " ∧ ".join(parts) + "]"


def vector(names, length=OUTPUT_LEN):
    v = [0.0] * length
    for n in names:
        v[OUTPUTS.index(n)] = 1.0
    return v


def regions(m):
    n = m["n"]
    inp = {"offset": BAND_START + INPUT_SLOT * (n - 1), "length": len(m["inputs"])}
    outp = {"offset": OUTPUT_START + OUTPUT_LEN * (n - 1), "length": OUTPUT_LEN}
    return inp, outp


def bits(m):
    return 8 if any(SIGNALS[s][1] == "c" for s in m["inputs"]) else 1


# ---------------------------------------------------------------- evaluator
def run(sequences, steps, latch_index=None, latch_out=0):
    """Drive the CESs over input vectors under the SURFACE_SPEC transition rule.

    Authoring self-check only: the engines are the authority (3-of-3), and this
    is what the fixtures are written against before they are measured.
    Returns the merged output per step (None where nothing asserted).
    """
    active = [{0} for _ in sequences]
    trace = []
    prev_latch = 0.0
    for x in steps:
        x = list(x)
        if latch_index is not None:
            x[latch_index] = prev_latch
        merged = None
        for si, seq in enumerate(sequences):
            evs = seq["events"]
            nxt = {0}
            for ei in sorted(active[si]):
                ev = evs[ei]
                if not all(accepts(el, xv) for el, xv in zip(ev["elements"], x)):
                    continue
                if ev.get("outputEvents"):
                    vec = ev["outputEvents"][0]["vector"]
                    merged = list(vec) if merged is None else [max(a, b) for a, b in zip(merged, vec)]
                    if ei != 0:
                        nxt.add(ei)
                pos = {e["id"]: i for i, e in enumerate(evs)}
                for nid in ev.get("nextEventIds", []):
                    nxt.add(pos[nid])
            active[si] = nxt
        trace.append(merged)
        if latch_index is not None:
            prev_latch = merged[latch_out] if merged else 0.0
    return trace


# ---------------------------------------------------------------- build
def build_machine(m):
    inputs = m["inputs"]
    inp, outp = regions(m)
    latch = m.get("latch", False)
    sequences, rules = [], []
    for cid, frm, to, events, outs, rag, amend in m["ces"]:
        sid = f"ces_{m['stem'][:5].lower()}_{cid.replace('-', '_')}"
        evs = []
        for i, pm in enumerate(events):
            ev = {"id": f"{sid}-e{i}", "isInitial": i == 0,
                  "elements": [element(pm.get(name)) for name in inputs],
                  "nextEventIds": [f"{sid}-e{i + 1}"] if i < len(events) - 1 else []}
            if i == len(events) - 1:
                ev["outputEvents"] = [{"id": f"{sid}-out", "vector": vector(outs)}]
            evs.append(ev)
        regex = " · ".join(symbol(pm, inputs) for pm in events)
        sequences.append({
            "id": sid, "name": f"{m['code']} {frm} → {to}", "schemaVersion": "1.0",
            "metadata": {"sourceFromState": frm, "sourceToState": to, "regularExpression": regex,
                         "specRule": m["rule"], "semanticAmendments": amend,
                         "asserts": outs or ["none (explicit release)"]},
            "events": evs})
        rules.append({"sequenceId": sid, "outputMatches": vector(outs), "ragStatusCode": rag,
                      "processStatus": {"GREEN": "info", "AMBER": "warning", "RED": "error"}[rag],
                      "description": f"{m['code']} {frm} → {to}: {regex}"})

    latch_index = inputs.index("latch_q_prev") if latch else None
    fixtures = build_fixtures(m, sequences, latch_index)
    semantics = []
    for name in inputs:
        cell, kind, source, meaning = SIGNALS[name]
        where = f"specification cell {cell}" if cell else "PE feedback of output LATCH"
        semantics.append(f"{name} ({'binary' if kind == 'b' else 'continuous [0,1]'}; {source}; {where}): {meaning}")

    interconnections = [{
        "id": f"{DOMAIN}.verdicts.{m['stem'][:5].lower()}", "type": "published-domain-bus-producer",
        "role": m["title"], "sourceMachine": m["stem"], "sourceOutputRegion": {"offset": outp["offset"], "length": 4},
        "targetInputElements": list(range(4 * (m["n"] - 1), 4 * m["n"])),
        "normalizedElements": [f"{m['code']} {v}" for v in VERDICTS],
        "purpose": f"Publish {m['code']}'s four verdict elements to the domain verdict aggregator.",
        "busId": f"{DOMAIN}.verdicts", "busTag": f"published-bus-{DOMAIN}-verdicts",
        "targetMachine": "GOV00 Governance Verdict Aggregator",
        "targetMachineFile": "GOV00_governance-verdict-aggregator.json",
        "targetInputRegion": {"offset": AGG_INPUT_START, "length": 68},
        "publishedOutputRegion": {"offset": AGG_INPUT_START + 68, "length": 4},
        "peCompositionRequired": True, "compositionOwner": "perception-engine",
        "dispatchMode": "asynchronous-no-wait",
        "privacyBoundary": "PE composes normalized verdict bits only; governance documents, signatures and principals stay in the Solid asset frames."}]
    if m.get("handoff"):
        interconnections.append({
            "id": f"{DOMAIN}.document.{m['stem'][:5].lower()}.{m['asset']}", "type": "document-workflow-handoff",
            "sourceMachine": m["stem"], "targetMachine": m["handoff"], "assetTypeId": m["asset"],
            "compositionOwner": "document-workflow-dispatcher",
            "purpose": f"Hand the frame's {m['asset']} to {m['handoff'][:5]}, its next consumer in the specification's evidence flow (SPECIFICATION.md sections 5-6); never infer a governance verdict from document content.",
            "nativeVectorWrite": False})

    metadata = {
        "category": DOMAIN, "domain": DOMAIN, "machineClass": m["cls"], "sequenceCount": len(sequences),
        "inputSemantics": semantics,
        "outputSemantics": [f"{i}: {o}" for i, o in enumerate(OUTPUTS)],
        "tags": [DOMAIN, m["family"], m["code"]] + (["fixture"] if m["kind"] == "fixture" else []),
        "tagging": {"schemaVersion": "1.0.0", "managedBy": "machine_factory/domains/ai-governance-regime",
                    "primaryDomain": DOMAIN, "family": m["family"], "machineCode": m["stem"][:5],
                    "workflowTags": [m["title"]], "validationTags": ["candidate-not-admitted"]},
        "governance": {"schemaVersion": "1.0.0", "ownerTeam": "AIGOV::Governance Steward",
                       "runbook": f"urn:re:aigov:runbook:{m['family']}:v1",
                       "escalationPolicy": "AIGOV::Governance Steward -> AIGOV::Approval Quorum; agents never resume an approval continuation (T15)",
                       "sla": {"ok": None, "info": None, "warning": None, "error": None},
                       "notes": "Owner roles are functional name strings pending the domain's staffing decision; the runbook URN resolves when runbooks/ is written (PACKAGE_STATUS.md step 6)."},
        "triggerConfig": {"processId": m["stem"], "processName": f"{m['code']} {m['title']}", "rules": rules},
        "interconnections": interconnections,
        "governanceSpec": {"machineCode": m["code"], "title": m["title"], "kind": m["kind"], "specRule": m["rule"],
                           "governedAssetType": m["asset"], "governedTargetDomain": "carried by the asset frame",
                           "agentCanResumeApproval": False},
        "conversion": {"candidateVersion": CANDIDATE, "builder": "tools/build_machines.py",
                       "transitionRule": "SURFACE_SPEC.md, Boundaries: where a K-line starts and ends",
                       "elementEncoding": "binary: equals; interval [lo,hi]: threshold, value (lo+hi)/2, threshold (hi-lo)/2; unconstrained: threshold 0.5 +/- 0.5",
                       "intakeEquivalents": "intake/corpus-312.json and corpus-315.json machines are not carried over (GOV-R01, GOV-R02)"},
    }
    if latch:
        metadata["latchFeedback"] = {
            "inputElement": latch_index, "fromOutputElement": OUTPUTS.index("LATCH"),
            "compositionOwner": "perception-engine", "peCompositionRequired": True,
            "rule": "Q(k) = S(k) or (not R(k) and Q(k-1)); the PE writes this machine's previous LATCH output into input element "
                    f"{latch_index} (an intra-machine bus cell, SURFACE_SPEC.md Cloneable machines). Needs live confirmation (GOV-R12)."}

    return {"version": VERSION, "machine": {
        "id": m["stem"], "name": m["stem"], "description": m["desc"],
        "arbiterRule": "PASSTHROUGH", "matchAlgorithm": "equals", "outputMergeTransformation": "or",
        "perceptualMapping": {"input": inp, "output": outp, "bitsPerElement": bits(m)},
        "sequences": sequences, "inputSequences": fixtures, "metadata": metadata}}


def scenario_vectors(m, steps, latch_index):
    inputs = m["inputs"]
    vecs, held = [], {}
    for st in steps:
        held.update(st)  # lifecycle and gate signals are levels held by the PE
        v = []
        for name in inputs:
            if name in held:
                p = held[name]
            else:
                p = NOMINAL.get(name, 0)
            if isinstance(p, tuple):  # pick an interior value of the interval
                lo, hi = p
                p = round(lo + (hi - lo) / 2, 4)
            v.append(float(p))
        vecs.append(v)
    return vecs


def latch_resolved(m, vecs, sequences, latch_index):
    """Fill the latch feedback element the way the PE would compose it."""
    if latch_index is None:
        return vecs, run(sequences, vecs)
    trace = run(sequences, vecs, latch_index, OUTPUTS.index("LATCH"))
    out, prev = [], 0.0
    for v, t in zip(vecs, trace):
        w = list(v)
        w[latch_index] = prev
        out.append(w)
        prev = t[OUTPUTS.index("LATCH")] if t else 0.0
    return out, trace


def build_fixtures(m, sequences, latch_index):
    scenarios = []
    for (cid, _frm, _to, events, _outs, _rag, _amend), seq in zip(m["ces"], sequences):
        steps = [dict(e) for e in events]
        ctx = FIXTURE_CONTEXT.get((m["n"], cid))
        if ctx:
            steps[0] = {**ctx, **steps[0]}
        if latch_index is not None and events[0].get("latch_q_prev") == 1:
            # reach the latched state first through a set CES of this machine
            setter = next(c for c in m["ces"] if "LATCH" in c[4] and c[3][0].get("latch_q_prev") is None)
            prime = {k: v for k, v in setter[3][0].items()}
            release = {k: None for k in prime}
            body = {k: v for k, v in events[0].items() if k != "latch_q_prev"}
            steps = [prime, {**{k: NOMINAL.get(k, 0) for k in release}, **body}]
        if (m["n"], cid) in FIXTURE_VALUES:
            steps[-1] = {**steps[-1], **FIXTURE_VALUES[(m["n"], cid)]}
        scenarios.append((f"{cid}", steps, f"drives {seq['id']}: {seq['metadata']['regularExpression']}", seq["id"]))
    for name, steps, purpose in NEGATIVES.get(m["n"], []):
        scenarios.append((name, steps, purpose, None))
    scenarios.append(("nominal", [{}], "the quiet state", None))

    fixtures, seen = [], {}
    for name, steps, purpose, target in scenarios:
        vecs = scenario_vectors(m, steps, latch_index)
        vecs, trace = latch_resolved(m, vecs, sequences, latch_index)
        final = trace[-1] or [0.0] * OUTPUT_LEN
        if target is not None:
            want = next(r for r in sequences if r["id"] == target)["events"][-1]["outputEvents"][0]["vector"]
            fired = trace[-1] is not None and all(f >= w for f, w in zip(final, want))
            if not fired:
                raise SystemExit(f"{m['stem']}: fixture {name} does not drive {target} (got {trace})")
        key = json.dumps(vecs)
        if key in seen:
            continue
        seen[key] = name
        meta = {"expectedOutputVector": final,
                "expectedOutputsByStep": [t or [0.0] * OUTPUT_LEN for t in trace],
                "purpose": purpose,
                "expectedEvaluationScope": "Isolated from reset; the expected outputs are computed by the package's authoring evaluator from SURFACE_SPEC's transition rule and must be confirmed 3-of-3 on the engines."}
        if target:
            meta["expectedSequenceId"] = target
        fixtures.append({"name": f"{m['stem'][:5].lower()}-{name}", "events": vecs, "metadata": meta})
    return fixtures


def build_aggregator(machines):
    inputs = [f"{m['stem'][:5]}.{v}" for m in machines for v in VERDICTS]
    idx = {name: i for i, name in enumerate(inputs)}
    halts = [f"{m['stem'][:5]}.HALT_PROMOTION" for m in machines]
    revokes = [f"{m['stem'][:5]}.REVOKE_EPOCH" for m in machines]
    sequences, rules = [], []

    def ces(sid, preds, vec, rag, desc):
        els = [element(preds.get(name)) for name in inputs]
        sequences.append({"id": sid, "name": desc, "schemaVersion": "1.0",
                          "metadata": {"regularExpression": "[" + " ∧ ".join(f"{k}={v}" for k, v in preds.items()) + "]",
                                       "specRule": "SPECIFICATION.md 4.2 (17056..17059 monoids)"},
                          "events": [{"id": f"{sid}-e0", "isInitial": True, "elements": els, "nextEventIds": [],
                                      "outputEvents": [{"id": f"{sid}-out", "vector": vec}]}]})
        rules.append({"sequenceId": sid, "outputMatches": vec, "ragStatusCode": rag,
                      "processStatus": {"GREEN": "info", "RED": "error"}[rag], "description": desc})

    for m in machines:
        c = m["stem"][:5]
        ces(f"ces_gov00_halt_{c.lower()}", {f"{c}.HALT_PROMOTION": 1}, [1.0, 0.0, 0.0, 0.0], "RED", f"{c} halts promotion")
        ces(f"ces_gov00_revoke_{c.lower()}", {f"{c}.REVOKE_EPOCH": 1}, [0.0, 1.0, 0.0, 0.0], "RED", f"{c} revokes the epoch")
        ces(f"ces_gov00_incident_{c.lower()}", {f"{c}.TRIGGER_INCIDENT": 1}, [0.0, 0.0, 0.0, 1.0], "RED", f"{c} raises an incident")
        preds = {f"{c}.PERMIT_DEPLOY": 1}
        preds.update({h: 0 for h in halts})
        preds.update({r: 0 for r in revokes})
        ces(f"ces_gov00_permit_{c.lower()}", preds, [0.0, 0.0, 1.0, 0.0], "GREEN",
            f"{c} permits and no machine halts or revokes")

    def fx(name, ones, purpose):
        v = [0.0] * len(inputs)
        for o in ones:
            v[idx[o]] = 1.0
        trace = run(sequences, [v])
        return {"name": f"gov00-{name}", "events": [v],
                "metadata": {"expectedOutputVector": trace[-1] or [0.0] * 4, "purpose": purpose,
                             "expectedEvaluationScope": "Authoring evaluator; confirm 3-of-3."}}

    fixtures = [fx("permit-only", ["GOV02.PERMIT_DEPLOY"], "a permit with no halt or revoke anywhere permits"),
                fx("permit-vetoed", ["GOV02.PERMIT_DEPLOY", "GOV10.HALT_PROMOTION"],
                   "any halt vetoes every permit (min monoid on PERMIT_DEPLOY)"),
                fx("revoke-incident", ["GOV07.REVOKE_EPOCH", "GOV07.TRIGGER_INCIDENT"], "revoke and incident fold by max"),
                fx("nominal", [], "nothing asserted")]
    composition = [{"role": m["title"], "sourceMachine": f"{m['stem']}.json",
                    "machineInputRegion": regions(m)[0], "machineOutputRegion": {"offset": regions(m)[1]["offset"], "length": 4},
                    "composedInputElements": list(range(4 * (m["n"] - 1), 4 * m["n"])),
                    "mapping": {f"activeOutput{i}": f"{m['code']} {v}" for i, v in enumerate(VERDICTS)}} for m in machines]
    inp = {"offset": AGG_INPUT_START, "length": len(inputs)}
    outp = {"offset": AGG_INPUT_START + len(inputs), "length": 4}
    return {"version": VERSION, "machine": {
        "id": "GOV00_governance-verdict-aggregator", "name": "GOV00_governance-verdict-aggregator",
        "description": "Folds the governance machines' verdicts onto the domain's four verdict elements: HALT_PROMOTION, REVOKE_EPOCH and TRIGGER_INCIDENT by max; PERMIT_DEPLOY only while some machine permits and none halts or revokes (min).",
        "arbiterRule": "PASSTHROUGH", "matchAlgorithm": "equals", "outputMergeTransformation": "or",
        "perceptualMapping": {"input": inp, "output": outp, "bitsPerElement": 1},
        "sequences": sequences, "inputSequences": fixtures,
        "metadata": {
            "category": DOMAIN, "domain": DOMAIN, "machineClass": "bridge", "sequenceCount": len(sequences),
            "inputSemantics": [f"{n}: composed by the PE from the producer's verdict output" for n in inputs],
            "outputSemantics": [f"{i}: {v} (specification cell {17056 + i})" for i, v in enumerate(VERDICTS)],
            "tags": [DOMAIN, "verdict-aggregator", "fixture"],
            "tagging": {"schemaVersion": "1.0.0", "managedBy": "machine_factory/domains/ai-governance-regime",
                        "primaryDomain": DOMAIN, "family": "domain-verdicts", "machineCode": "GOV00",
                        "validationTags": ["candidate-not-admitted"]},
            "governance": {"schemaVersion": "1.0.0", "ownerTeam": "AIGOV::Governance Steward",
                           "runbook": "urn:re:aigov:runbook:domain-verdicts:v1",
                           "escalationPolicy": "AIGOV::Governance Steward -> AIGOV::Approval Quorum",
                           "sla": {"ok": None, "info": None, "warning": None, "error": None}},
            "triggerConfig": {"processId": "GOV00_governance-verdict-aggregator",
                              "processName": "Governance domain verdicts", "rules": rules},
            "publishedDomainBus": {"id": f"{DOMAIN}.verdicts", "tag": f"published-bus-{DOMAIN}-verdicts",
                                   "domain": DOMAIN, "name": "AI governance verdict bus",
                                   "description": "Each governance machine's four verdict elements, composed by the PE.",
                                   "inputRegion": inp, "outputRegion": outp, "inputComposition": composition},
            "failSafeVector": {"HALT_PROMOTION": 1.0, "REVOKE_EPOCH": 1.0, "PERMIT_DEPLOY": 0.0, "TRIGGER_INCIDENT": 1.0},
            "conversion": {"candidateVersion": CANDIDATE, "builder": "tools/build_machines.py"},
        }}}


def render(doc):
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def outputs():
    files = {f"{m['stem']}.json": render(build_machine(m)) for m in MACHINES}
    files["GOV00_governance-verdict-aggregator.json"] = render(build_aggregator(MACHINES))
    return files


def main():
    ap = argparse.ArgumentParser(description="Build the ai-governance-regime candidate machines.")
    ap.add_argument("--check", action="store_true", help="fail if machines/ differs from a fresh build")
    args = ap.parse_args()
    files = outputs()
    if args.check:
        stale = [n for n, text in files.items() if not (OUT / n).is_file() or (OUT / n).read_text() != text]
        extra = [p.name for p in OUT.glob("*.json") if p.name not in files]
        for n in stale + extra:
            print(f"stale: machines/{n}")
        print("build: up to date" if not (stale or extra) else "build: run tools/build_machines.py")
        return 1 if stale or extra else 0
    OUT.mkdir(exist_ok=True)
    for p in OUT.glob("*.json"):
        if p.name not in files:
            p.unlink()
    for n, text in files.items():
        (OUT / n).write_text(text)
    print(f"wrote {len(files)} machines to {OUT.relative_to(PKG)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
