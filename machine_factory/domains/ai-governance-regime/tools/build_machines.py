#!/usr/bin/env python3
"""Build the ai-governance-regime candidates: machines, agent behaviors, Sources, workflows.

    python3 tools/build_machines.py            # write everything below
    python3 tools/build_machines.py --check    # fail if any written file differs

Writes, from the tables in this file:
  machines/*.json                        17 governance machines and GOV00
  agent-candidates/ai-governance-regime/ one runtime-neutral agent behavior per
                                         agent (schemas/agent-behavior.schema.json)
  governance-sources.json                every input signal: its kind, producer,
                                         whether it exists today, its consumers
  agentic-workflow-contract.json         workflows W1-W7: frames, steps, agents,
                                         human steps, the processes they govern

Behavior: SPECIFICATION.md 4.3 and HARDENING_TRANSITION_RULES.md, connected per
CONNECTED_WORKFLOW.md (owner, 2026-11-21: every workflow and Source in v1).
Every path to an output is one CES and every CES is one regular expression over
Reality Events; a disjunction is one CES per disjunct. Order the obligations
need is a chain: an agent step completes before review, review dwells before
approval, a breach is sustained before it trips. Waiting happens only where the
transition rule allows it (SURFACE_SPEC.md, "Boundaries"): on an initial event
that keeps matching, or on a final event that keeps matching.

Templates (cloneable) reserve input cells 2-7 for the asset lifecycle's frame
lanes and report through their continuation and their writeBack only, never by
bus (CONTINUATIONS_APPROVAL_CHAIN.md). Their other inputs are frame facts and
the step agent's completion, which the lifecycle writes into the clone's
block (GOV-R19). Fixtures read Sources directly, dispatch watchdog agents from
a CES, and publish their verdicts to GOV00.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
OUT = PKG / "machines"
AGENTS = PKG / "agent-candidates" / "ai-governance-regime"
DOMAIN = "ai-governance-regime"
VERSION = "1.0.0"
CANDIDATE = "0.2.0"
BAND_START = 16960
INPUT_SLOT = 16
N_MACHINES = 17
OUTPUTS = ["HALT_PROMOTION", "REVOKE_EPOCH", "PERMIT_DEPLOY", "TRIGGER_INCIDENT", "PARKED", "APPROACH",
           "LATCH", "REWORK", "AGENT_REQUESTED", "OVERDUE"]
OUTPUT_LEN = len(OUTPUTS)
OUTPUT_START = BAND_START + N_MACHINES * INPUT_SLOT                 # 17232
AGG_INPUT_START = OUTPUT_START + N_MACHINES * OUTPUT_LEN            # 17402
VERDICTS = OUTPUTS[:4]
EPS = 0.0001
DWELL = 2       # steps a reviewer is shown the parked state before an approval counts (ASI09)
DEBOUNCE = 3    # consecutive breach observations before a watchdog trips
TTL_MS = 300000

LANES = ["lane_in_workflow", "lane_re_pinned", "lane_approved", "lane_rework", "lane_step_running", "lane_stale"]

# Signals produced by a peer domain rather than by a service (GOV-SD-11, observe vs
# decide): threat-dynamics observes, this domain decides. Emitted as producerDomain
# in governance-sources.json only; the machines' inputSemantics are unchanged.
PRODUCER_DOMAIN = {
    "gate_redteam_pass": "threat-dynamics",
    "mon_canary_drift_score": "threat-dynamics",
    "mon_xdomain_mu_agg": "threat-dynamics",
}

# signal: (kind b/c, delivery, producer, status, meaning)
# delivery: lane (lifecycle frame lane), fact (frame fact the lifecycle writes into a
# clone), sensor (a PE Source on a fixture), feedback (PE-composed own output).
# status: exists / partial / new, for the producer as of 2026-11-21.
SIGNALS = {
    "lane_in_workflow": ("b", "lane", "localAssetStorageStack lifecycle, lane 2", "exists", "the asset is in its workflow"),
    "lane_re_pinned": ("b", "lane", "localAssetStorageStack lifecycle, lane 3", "exists", "a frame document has been re-pinned (T16)"),
    "lane_approved": ("b", "lane", "localAssetStorageStack lifecycle, lane 4", "exists", "approved by a distinct human principal"),
    "lane_rework": ("b", "lane", "localAssetStorageStack lifecycle, lane 5", "exists", "rework requested"),
    "lane_step_running": ("b", "lane", "localAssetStorageStack lifecycle, lane 6", "exists", "a step is running"),
    "lane_stale": ("b", "lane", "localAssetStorageStack lifecycle, lane 7", "exists", "the head is STALE (continuation TTL or lease expired)"),
    "lane_principal_distinct": ("b", "fact", "lifecycle extension: approver != preparer and not an agent (T15)", "new", "the acting principal is distinct from the preparer and human"),
    "lane_diff_rendered": ("b", "fact", "GOV11 diff renderer completion, carried by the frame", "new", "the canonical diff of the exact revision was shown to the reviewer"),
    "quorum_valid": ("b", "fact", "GOV06 verdict, carried by the frame", "new", "the approval quorum for this frame is valid"),
    "gate_3of3_parity": ("b", "fact", "RealityEngine_CI regression run report (parity stages)", "partial", "C++, LSP and Scala agree 3-of-3 on the candidate"),
    "gate_aibom_pinned": ("b", "fact", "AIBOM verifier over the frame's AIBOM document", "new", "every model, quantization, tap and dictionary digest is pinned"),
    "comp_iso42005_signed": ("b", "fact", "document-workflow close of the frame's ISO/IEC 42005 assessment", "partial", "ISO/IEC 42005 impact assessment signed"),
    "comp_eu_fria_signed": ("b", "fact", "document-workflow close of the frame's Art. 27 FRIA", "partial", "EU AI Act Art. 27 FRIA signed"),
    "comp_bias_audit_signed": ("b", "fact", "document-workflow close of the frame's bias audit", "partial", "bias and data-lineage audit signed"),
    "comp_high_risk_domain": ("b", "fact", "domain-manifest.json classification (new attribute)", "new", "the target domain is high-risk"),
    "req_domain_admit": ("b", "fact", "scripts/approve-domain.sh prepare (admission request)", "partial", "a domain admission is requested"),
    "req_epoch_swap": ("b", "fact", "scripts/approve-domain.sh deploy / domains/deployments (epoch request)", "partial", "a rule-epoch swap is requested"),
    "req_audit_pack_seal": ("b", "fact", "cut-release.sh / audit request", "partial", "an auditor evidence pack seal is requested"),
    "req_egress": ("b", "fact", "A2A/MCP boundary: an outbound message is pending (GOV-R13)", "new", "an outbound message awaits the transparency gate"),
    "egress_external_comm": ("b", "fact", "A2A/MCP boundary classifier", "new", "the message targets an external party"),
    "egress_art50_marked": ("b", "fact", "A2A/MCP boundary: provenance header check", "new", "machine-readable AI provenance is present (Art. 50)"),
    "gate_redteam_pass": ("b", "fact", "adversarial evaluation (AgentDojo and the domain suite)", "new", "red-team suite passed, no unmitigated T13 bypass"),
    "gate_source_slsa_attested": ("b", "fact", "provenance attestation (verify-build-provenance.py today; SLSA/in-toto new)", "partial", "Sources and builds are attested"),
    "lane_quorum_integrity_ok": ("b", "fact", "keyring Source: re_pki CRL plus signer keys, org units, dwell", "partial", "signer keys clean, diverse, dwell met"),
    "mon_t13_incident_cnt": ("c", "fact", "incident triage completion (GOV07/GOV16 agents)", "new", "normalized count of confirmed in-bounds harm"),
    "src_req_epoch_swap": ("b", "sensor", "scripts/approve-domain.sh deploy (epoch request)", "partial", "a rule-epoch swap is requested"),
    "src_quorum_integrity_ok": ("b", "sensor", "keyring Source: re_pki CRL plus signer keys, org units, dwell", "partial", "signer keys clean, diverse, dwell met"),
    "src_slsa_attested": ("b", "sensor", "provenance attestation", "partial", "Sources and builds are attested"),
    "mon_mu_exhaust_rate": ("c", "sensor", "engines' exposure budget (Design in V0.18)", "new", "normalized rate of exposure-budget exhaustions"),
    "gate_kperf_to1": ("b", "sensor", "per-step latency gate (corpus-parity-loop timings today)", "partial", "TO-1 p99 latency within its gate"),
    "mon_latency_drift": ("c", "sensor", "per-step latency drift", "partial", "relative p99 drift above the gated baseline"),
    "mon_nearmiss_backlog": ("c", "sensor", "near-miss K-line classification over engine K-line histories", "partial", "unresolved near-miss K-lines relative to ring capacity"),
    "mon_recert_ttl_rem": ("c", "sensor", "domains/approvals and approval tags (time since last approval)", "exists", "fraction of the recertification TTL remaining"),
    "mon_xdomain_mu_agg": ("c", "sensor", "aggregate cross-domain exposure", "new", "aggregate cross-domain exposure consumed"),
    "mon_canary_drift_score": ("c", "sensor", "canary prompts (localAIStack /observations/drift records drift today)", "partial", "behavioral drift on canary prompts"),
    "operator_approved": ("b", "sensor", "governance console: operator release approval", "new", "a distinct human operator approved the release of a latched watchdog"),
    "operator_distinct": ("b", "sensor", "governance console: operator identity check", "new", "the approving operator is distinct and human"),
    "latch_q_prev": ("b", "feedback", "PE: this machine's LATCH output at the previous step", "new", "previous LATCH output"),
    "spare": ("b", "fact", "none", "exists", "spare cell, always 0"),
}


def gt(x):
    return (round(x + EPS, 4), 1.0)


def lt(x):
    return (0.0, round(x - EPS, 4))


def le(x):
    return (0.0, x)


def ge(x):
    return (x, 1.0)


def rep(pred, k):
    return [dict(pred) for _ in range(k)]


class Alt(tuple):
    """An alternation at one position of a CES chain (GOV-SA-25): ((label, predicate), ...).

    Each alternative is its own Reality Event; every event of the previous position
    lists all of them as next-active, and each lists every event of the next position.
    At position 0 they are all initial (R = (a+b)c); at the last, all final (R = a(b+c)).
    """


def alt(**named):
    return Alt(named.items())


def preds_at(pos):
    """The predicates at one chain position: one, or one per alternative."""
    return [pm for _, pm in pos] if isinstance(pos, Alt) else [pos]


def C(cid, frm, to, events, outs, rag, amend=(), dispatch=False):
    return dict(id=cid, frm=frm, to=to, events=events, outs=list(outs), rag=rag, amend=list(amend), dispatch=dispatch)


def agent_ces(ctx, done, failed, outs_requested=("AGENT_REQUESTED",), extra=()):
    """The step agent's own CESs: requested while it runs, and its failure."""
    run = {**ctx, "lane_step_running": 1, done: 0}
    return [
        C("agent-requested", "S0_Init", "S1_AgentRunning", [run], outs_requested, "AMBER", extra, dispatch=True),
        C("agent-failed", "S1_AgentRunning", "S_err_StepFailed", [run, {failed: 1}], ["PARKED", "REWORK"], "RED",
          ["GOV-SA-13"]),
    ]


def review_ces(parked, approve, ctx_wf, park_outs=("PARKED",), approve_outs=("PERMIT_DEPLOY",), extra=()):
    """Parked review with a dwell, approval, escapes, blind and post-approval tamper."""
    return [
        C("parked", "S1_Prepared", "S2_ParkedReview", [parked], park_outs, "AMBER", ["GOV-SA-02", *extra]),
        C("approved", "S2_ParkedReview", "S3_Approved", rep(parked, DWELL) + [approve], approve_outs, "GREEN",
          ["GOV-SA-03", "GOV-SA-14", *extra]),
        C("rework-re-pinned", "S2_ParkedReview", "S_err_Rework", [parked, {"lane_re_pinned": 1}],
          ["HALT_PROMOTION", "REWORK"], "RED"),
        C("rework-stale", "S2_ParkedReview", "S_err_Rework", [parked, {"lane_stale": 1}],
          ["HALT_PROMOTION", "REWORK"], "RED"),
        C("blind-approval", "S2_ParkedReview", "S_fail_BlindApproval",
          [{**ctx_wf, "lane_diff_rendered": 0, "lane_approved": 0}, {"lane_approved": 1, "lane_diff_rendered": 0}],
          ["HALT_PROMOTION"], "RED", ["GOV-SA-14"]),
        C("tampered-after-approval", "S3_Approved", "S_err_Rework",
          [{**ctx_wf, **approve}, {"lane_approved": 1, "lane_re_pinned": 1}], ["HALT_PROMOTION", "REWORK"], "RED",
          ["GOV-SA-15"]),
    ]


def latch_ces(cid, frm, to, set_events, set_outs, holds, release, amend=(), dispatch=False):
    """An SR latch as one closed CES (GOV-SA-24, superseding GOV-SA-06's feedback cell).

    Q(k) = S(k) or (not R(k) and Q(k-1)), held in the CES's own active events:
      * set: the chain `set_events`; its final event asserts `set_outs`;
      * hold: one event per negated literal of the release condition, each asserting
        its outputs (the latched vector). Every hold event, and the set chain's final
        event, lists every hold event and the release in its next-active list, so
        while any release literal is still false some hold event matches and re-arms
        the whole cluster. The union of negated literals is held without a feedback
        cell, and the latch asserts on every latched step (it merges by `or` over any
        other CES of the machine and over GOV-SA-23's idle zeros);
      * release: one event, the release conjunction, asserting `release[1]`.
    Every next-active reference stays inside this CES (closed events, owner 2026-11-27).
    """
    c = C(cid, frm, to, set_events, set_outs, "RED", ["GOV-SA-24", *amend], dispatch)
    c["latchGraph"] = {"holds": [(name, dict(lit), list(outs)) for name, lit, outs in holds],
                       "release": (dict(release[0]), list(release[1]))}
    return c


# ---------------------------------------------------------------- the machines
W = {"lane_in_workflow": 1}
# GOV05's request, (domain admission | epoch swap): two initial events in one CES (GOV-SA-25).
REQ05 = alt(admit={"lane_in_workflow": 1, "req_domain_admit": 1, "lane_step_running": 1, "aibom_assembled": 0},
            epoch={"lane_in_workflow": 1, "req_epoch_swap": 1, "lane_step_running": 1, "aibom_assembled": 0})

P01 = {"lane_in_workflow": 1, "req_domain_admit": 1, "prep_completed": 1, "sections_unresolved": 0,
       "comp_iso42005_signed": 1, "comp_eu_fria_signed": 1, "gate_redteam_pass": 1, "gate_source_slsa_attested": 1,
       "lane_diff_rendered": 1, "lane_approved": 0, "lane_re_pinned": 0, "lane_stale": 0}
A_HUMAN = {"lane_approved": 1, "lane_principal_distinct": 1, "lane_re_pinned": 0, "lane_stale": 0}

P04 = {"lane_in_workflow": 1, "req_epoch_swap": 1, "gate_3of3_parity": 1, "replay_completed": 1, "replay_pass": 1,
       "gate_aibom_pinned": 1, "quorum_valid": 0, "lane_re_pinned": 0, "lane_stale": 0}
P13 = {"lane_in_workflow": 1, "req_audit_pack_seal": 1, "pack_assembled": 1, "missing_receipts": 0,
       "lane_diff_rendered": 1, "lane_approved": 0, "lane_re_pinned": 0, "lane_stale": 0}
P12 = {"lane_in_workflow": 1, "bundle_exported": 1, "notice_drafted": 1, "lane_approved": 0, "lane_stale": 0}
E15 = {"lane_in_workflow": 1, "req_epoch_swap": 1, "gate_source_slsa_attested": 1, "lane_quorum_integrity_ok": 1,
       "lane_principal_distinct": 1, "emergency_open": 1, "ratification_queued": 1, "quorum_valid": 0,
       "lane_re_pinned": 0, "lane_stale": 0}
P17 = {"lane_in_workflow": 1, "invalidation_done": 1, "keyring_ready": 1, "lane_approved": 0, "lane_stale": 0}

MACHINES = [
    dict(n=1, stem="GOV01_impact-dossier-lifecycle", code="M-GOV-01", title="ImpactDossierLifecycle",
         kind="template", cls="governance-escalator", family="A-domain-onboarding-impact", workflow="W1",
         asset="TaskSufficiencyAndImpactDossier", handoff="GOV13_control-crosswalk-assembler",
         rule="SPECIFICATION.md 4.3 (1); HARDENING_TRANSITION_RULES.md section 1",
         desc="Impact dossier for a domain admission: the dossier preparer drafts the ISO/IEC 42005 assessment and the Art. 27 FRIA, the signed dossier with red-team and attestation gates parks for a review that must dwell on a rendered diff, and a distinct human approves; re-pin, staleness, blind approval and tamper after approval escape.",
         facts=["req_domain_admit", "lane_principal_distinct", "lane_diff_rendered", "comp_iso42005_signed",
                "comp_eu_fria_signed", "gate_redteam_pass", "gate_source_slsa_attested"],
         completion=[("prep_completed", "the dossier draft is complete"), ("prep_failed", "the agent's step failed"),
                     ("sections_unresolved", "sections left unresolved for the author")],
         agent=dict(id="aigov-dossier-preparer", role="step-agent", mode="supervised-act",
                    title="Impact dossier preparer",
                    objective="Draft the frame's ISO/IEC 42005 impact assessment and EU AI Act Art. 27 fundamental-rights impact assessment for the domain under admission, from its domain manifest, declared hazards and corpus, leaving unresolved what the evidence does not settle.",
                    capabilities=["frame.read", "pod.read", "pod.write", "frame.return.write", "rag.query"],
                    actions=["Draft the impact assessment and FRIA documents in the frame under the pinned ETag.",
                             "Mark every section the evidence does not settle as unresolved for the author."]),
         ces=[*agent_ces({"lane_in_workflow": 1, "req_domain_admit": 1}, "prep_completed", "prep_failed"),
              C("agent-incomplete", "S1_AgentRunning", "S_err_Rework",
                [{"lane_in_workflow": 1, "req_domain_admit": 1, "lane_step_running": 1, "prep_completed": 0},
                 {"prep_completed": 1, "sections_unresolved": 1}], ["REWORK"], "AMBER"),
              *review_ces(P01, A_HUMAN, W)]),
    dict(n=2, stem="GOV02_task-sufficiency-gate", code="M-GOV-02", title="TaskSufficiencyGate",
         kind="template", cls="safety-compliance-checker", family="A-domain-onboarding-impact", workflow="W1",
         asset="TaskSufficiencyAndImpactDossier", handoff="GOV03_socio-technical-bias-audit",
         rule="SPECIFICATION.md 4.3 (2)",
         desc="Task-sufficiency gate on a domain admission: the hazard-sufficiency analyst runs, and the verdict follows its completed analysis: permit when every declared hazard is fiber-saturated or exposure-bounded, halt when gaps remain.",
         facts=["req_domain_admit"],
         completion=[("analysis_completed", "the analysis is complete"), ("analysis_failed", "the agent's step failed"),
                     ("hazards_sufficient", "every declared hazard is fiber-saturated or exposure-bounded"),
                     ("hazard_gaps", "at least one hazard is neither")],
         agent=dict(id="aigov-hazard-sufficiency-analyst", role="step-agent", mode="supervised-act",
                    title="Hazard-sufficiency analyst",
                    objective="Establish, for the domain under admission, whether every declared hazard is fiber-saturated or exposure-bounded (Proposition 1), citing the corpus and the hazard set; report gaps, never fill them.",
                    capabilities=["frame.read", "pod.read", "pod.write", "frame.return.write", "kline.read", "rag.query"],
                    actions=["Write the task-sufficiency analysis into the frame's dossier.",
                             "Report hazards_sufficient or hazard_gaps with citations."]),
         ces=[*agent_ces({"lane_in_workflow": 1, "req_domain_admit": 1}, "analysis_completed", "analysis_failed"),
              C("verified", "S1_AgentRunning", "S2_Verified",
                [{"lane_in_workflow": 1, "req_domain_admit": 1, "lane_step_running": 1, "analysis_completed": 0},
                 {"analysis_completed": 1, "hazards_sufficient": 1, "hazard_gaps": 0}], ["PERMIT_DEPLOY"], "GREEN"),
              C("incomplete-hazard", "S1_AgentRunning", "S_fail_IncompleteHazard",
                [{"lane_in_workflow": 1, "req_domain_admit": 1, "lane_step_running": 1, "analysis_completed": 0},
                 {"analysis_completed": 1, "hazard_gaps": 1}], ["HALT_PROMOTION"], "RED")]),
    dict(n=3, stem="GOV03_socio-technical-bias-audit", code="M-GOV-03", title="SocioTechnicalBiasAudit",
         kind="template", cls="safety-compliance-checker", family="A-domain-onboarding-impact", workflow="W1",
         asset="TaskSufficiencyAndImpactDossier", handoff="GOV05_aibom-provenance-pin",
         rule="SPECIFICATION.md 4.3 (3)",
         desc="Bias and data-lineage audit on a domain admission: a domain that is not high-risk is exempt; for a high-risk domain the bias-audit preparer drafts the audit, a human signs it, and an unsigned audit at lease expiry blocks the admission.",
         facts=["req_domain_admit", "comp_high_risk_domain", "comp_bias_audit_signed"],
         completion=[("audit_drafted", "the audit draft is complete"), ("audit_failed", "the agent's step failed")],
         agent=dict(id="aigov-bias-audit-preparer", role="step-agent", mode="supervised-act",
                    title="Bias-audit preparer",
                    objective="Draft the data-lineage and bias audit (EU AI Act Art. 10, ISO/IEC 42001 A.7) for a high-risk domain under admission, from its training and evaluation lineage; the signature is a human's.",
                    capabilities=["frame.read", "pod.read", "pod.write", "frame.return.write", "rag.query"],
                    actions=["Draft the bias and data-lineage audit document in the frame."]),
         ces=[C("exempt", "S0_Idle", "S1_Exempt",
                [{"lane_in_workflow": 1, "req_domain_admit": 1, "comp_high_risk_domain": 0}], ["PERMIT_DEPLOY"], "GREEN"),
              *agent_ces({"lane_in_workflow": 1, "req_domain_admit": 1, "comp_high_risk_domain": 1}, "audit_drafted",
                         "audit_failed"),
              C("audited", "S1_Drafted", "S2_Audited",
                [{"lane_in_workflow": 1, "req_domain_admit": 1, "comp_high_risk_domain": 1, "audit_drafted": 1,
                  "comp_bias_audit_signed": 0},
                 {"comp_bias_audit_signed": 1, "lane_re_pinned": 0}], ["PERMIT_DEPLOY"], "GREEN"),
              C("bias-block", "S1_Drafted", "S_fail_BiasBlock",
                [{"lane_in_workflow": 1, "req_domain_admit": 1, "comp_high_risk_domain": 1,
                  "comp_bias_audit_signed": 0, "lane_stale": 0},
                 {"lane_stale": 1, "comp_bias_audit_signed": 0}], ["HALT_PROMOTION", "REWORK"], "RED", ["GOV-SA-16"])]),
    dict(n=4, stem="GOV04_rule-epoch-promotion", code="M-GOV-04", title="RuleEpochPromotion",
         kind="template", cls="governance-escalator", family="B-rule-epoch-aibom", workflow="W2",
         asset="GovernanceAssetFrame", handoff="GOV13_control-crosswalk-assembler",
         rule="SPECIFICATION.md 4.3 (4)",
         desc="Rule-epoch promotion: the replay analyst replays the candidate rules on near-miss K-lines; with 3-of-3 parity and a pinned AIBOM the epoch parks for the approval quorum, which must hold through a dwell before promotion; re-pin and staleness reject.",
         facts=["req_epoch_swap", "gate_3of3_parity", "gate_aibom_pinned", "quorum_valid"],
         completion=[("replay_completed", "the replay is complete"), ("replay_failed", "the agent's step failed"),
                     ("replay_pass", "candidate rules fire on near misses and stay silent on nominal runs")],
         agent=dict(id="aigov-replay-analyst", role="step-agent", mode="supervised-act",
                    title="K-line replay analyst",
                    objective="Replay the candidate rule epoch on the near-miss K-lines in a sandbox universe and report whether it fires on every near miss and stays silent on nominal runs.",
                    capabilities=["frame.read", "pod.read", "frame.return.write", "kline.read", "regression.report.read"],
                    actions=["Run the sandbox replay and write its report to the frame's return."]),
         ces=[*agent_ces({"lane_in_workflow": 1, "req_epoch_swap": 1}, "replay_completed", "replay_failed"),
              C("replay-rejected", "S1_AgentRunning", "S_err_Rejected",
                [{"lane_in_workflow": 1, "req_epoch_swap": 1, "lane_step_running": 1, "replay_completed": 0},
                 {"replay_completed": 1, "replay_pass": 0}], ["HALT_PROMOTION", "REWORK"], "RED"),
              C("parity-missing", "S1_Replayed", "S_err_Rejected",
                [{"lane_in_workflow": 1, "req_epoch_swap": 1, "replay_completed": 1, "gate_3of3_parity": 0}],
                ["HALT_PROMOTION"], "RED"),
              C("aibom-missing", "S1_Replayed", "S_err_Rejected",
                [{"lane_in_workflow": 1, "req_epoch_swap": 1, "replay_completed": 1, "gate_aibom_pinned": 0}],
                ["HALT_PROMOTION"], "RED"),
              C("awaiting-quorum", "S1_Replayed", "S2_AwaitingQuorum", [P04], ["PARKED"], "AMBER", ["GOV-SA-02"]),
              C("promoted", "S2_AwaitingQuorum", "S3_Promoted",
                rep(P04, DWELL) + [{"quorum_valid": 1, "lane_re_pinned": 0, "lane_stale": 0}], ["PERMIT_DEPLOY"],
                "GREEN", ["GOV-SA-03", "GOV-SA-14"]),
              C("rejected-re-pinned", "S2_AwaitingQuorum", "S_err_Rejected", [P04, {"lane_re_pinned": 1}],
                ["HALT_PROMOTION", "REWORK"], "RED"),
              C("rejected-stale", "S2_AwaitingQuorum", "S_err_Rejected", [P04, {"lane_stale": 1}],
                ["HALT_PROMOTION", "REWORK"], "RED")]),
    dict(n=5, stem="GOV05_aibom-provenance-pin", code="M-GOV-05", title="AIBOMProvenancePin",
         kind="template", cls="safety-compliance-checker", family="B-rule-epoch-aibom", workflow="W1,W2",
         asset="AIBOMManifest", handoff="GOV04_rule-epoch-promotion",
         rule="SPECIFICATION.md 4.3 (5)",
         desc="AIBOM provenance pin on a domain admission or an epoch swap: the AIBOM assembler collects every digest, and the verdict follows its completion and the verifier: permit only when nothing is unpinned and the verifier agrees.",
         facts=["req_domain_admit", "req_epoch_swap", "gate_aibom_pinned"],
         completion=[("aibom_assembled", "the AIBOM is assembled"), ("aibom_failed", "the agent's step failed"),
                     ("unpinned_items", "the assembler found items it could not pin")],
         agent=dict(id="aigov-aibom-assembler", role="step-agent", mode="supervised-act",
                    title="AIBOM assembler",
                    objective="Assemble the frame's AI bill of materials: every foundation model, quantization, residual tap, SAE dictionary and voting-engine runtime digest in use, with its source; list anything that cannot be pinned.",
                    capabilities=["frame.read", "pod.read", "pod.write", "frame.return.write", "registry.read",
                                  "regression.report.read"],
                    actions=["Write the AIBOM document into the frame.", "Report unpinned items."]),
         ces=[C("agent-requested", "S0_Idle", "S1_AgentRunning", [REQ05], ["AGENT_REQUESTED"], "AMBER",
                ["GOV-SA-25"], dispatch=True),
              C("agent-failed", "S1_AgentRunning", "S_err_StepFailed",
                [{"lane_in_workflow": 1, "lane_step_running": 1, "aibom_assembled": 0}, {"aibom_failed": 1}],
                ["PARKED", "REWORK"], "RED", ["GOV-SA-13"]),
              C("pinned", "S1_AgentRunning", "S2_Pinned",
                [REQ05, {"aibom_assembled": 1, "unpinned_items": 0, "gate_aibom_pinned": 1}], ["PERMIT_DEPLOY"], "GREEN",
                ["GOV-SA-25"]),
              C("unpinned", "S1_AgentRunning", "S_fail_UnpinnedModel",
                [{"lane_in_workflow": 1, "lane_step_running": 1, "aibom_assembled": 0},
                 {"aibom_assembled": 1, "unpinned_items": 1}], ["HALT_PROMOTION"], "RED"),
              C("verifier-disagrees", "S1_AgentRunning", "S_fail_UnpinnedModel",
                [{"lane_in_workflow": 1, "lane_step_running": 1, "aibom_assembled": 0},
                 {"aibom_assembled": 1, "unpinned_items": 0, "gate_aibom_pinned": 0}], ["HALT_PROMOTION"], "RED",
                ["GOV-SA-17"])]),
    dict(n=6, stem="GOV06_quorum-consensus-monitor", code="M-GOV-06", title="QuorumConsensusMonitor",
         kind="fixture", cls="safety-compliance-checker", family="B-rule-epoch-aibom", workflow="W2",
         asset=None, handoff=None, rule="SPECIFICATION.md 4.3 (6); HARDENING_TRANSITION_RULES.md section 1",
         desc="Approval-quorum monitor on an epoch swap: dispatches the quorum bundle assembler, then permits only when, after the bundle is ready, signatures from Risk, Engineering and Legal have all arrived with no preparer among the signers, clean signer keys and attested Sources.",
         facts=["src_req_epoch_swap", "src_quorum_integrity_ok", "src_slsa_attested"],
         completion=[("bundle_ready", "the canonical (JCS) bundle is ready and routed"),
                     ("bundle_failed", "the agent failed"), ("signed_risk", "a Risk signature arrived"),
                     ("signed_engineering", "an Engineering signature arrived"), ("signed_legal", "a Legal signature arrived"),
                     ("signer_is_preparer", "a signer is the preparer")],
         agent=dict(id="aigov-quorum-bundle-assembler", role="watchdog-agent", mode="supervised-act",
                    title="Quorum bundle assembler",
                    objective="Canonicalize (RFC 8785) the epoch-swap approval bundle, route it to the required signers in Risk, Engineering and Legal, and report each signature's arrival; never sign.",
                    capabilities=["pe.completion.write", "pe.observations.read", "human.notify", "pki.crl.read"],
                    actions=["Canonicalize and route the approval bundle.", "Report signature arrivals by org unit."]),
         ces=[C("bundle-requested", "S0_Standby", "S1_Collecting", [{"src_req_epoch_swap": 1, "bundle_ready": 0}],
                ["AGENT_REQUESTED"], "AMBER", dispatch=True),
              C("bundle-failed", "S0_Standby", "S_fail_QuorumViolation",
                [{"src_req_epoch_swap": 1, "bundle_ready": 0}, {"bundle_failed": 1}], ["HALT_PROMOTION", "REWORK"], "RED"),
              *[C(f"quorum-valid-after-{unit}", "S1_Collecting", "S2_QuorumValid",
                  [{"src_req_epoch_swap": 1, "bundle_ready": 1, f"signed_{unit}": 0},
                   {"signed_risk": 1, "signed_engineering": 1, "signed_legal": 1, "signer_is_preparer": 0,
                    "src_quorum_integrity_ok": 1, "src_slsa_attested": 1}], ["PERMIT_DEPLOY"], "GREEN", ["GOV-SA-18"])
                for unit in ("risk", "engineering", "legal")],
              C("violation-self-signer", "S1_Collecting", "S_fail_QuorumViolation",
                [{"src_req_epoch_swap": 1, "signer_is_preparer": 1}], ["HALT_PROMOTION"], "RED"),
              C("violation-key-integrity", "S1_Collecting", "S_fail_QuorumViolation",
                [{"src_req_epoch_swap": 1, "src_quorum_integrity_ok": 0}], ["HALT_PROMOTION"], "RED", ["GOV-SA-05"]),
              C("violation-unattested", "S1_Collecting", "S_fail_QuorumViolation",
                [{"src_req_epoch_swap": 1, "src_slsa_attested": 0}], ["HALT_PROMOTION"], "RED", ["GOV-SA-05"])]),
    dict(n=7, stem="GOV07_exposure-budget-watchdog", code="M-GOV-07", title="ExposureBudgetWatchdog",
         kind="fixture", cls="signal-monitor", family="C-runtime-assurance", workflow="W3", asset=None, handoff=None,
         rule="SPECIFICATION.md 4.3 (7)",
         desc="Exposure-budget watchdog with an SR latch: reports the approach band, trips on a sustained breach, dispatches incident triage, and releases only after triage and a distinct operator's approval with the rate back in band.",
         facts=["mon_mu_exhaust_rate", "operator_approved", "operator_distinct"],
         completion=[("triage_completed", "incident triage is complete"), ("confirmed_harm", "triage confirmed in-bounds harm")],
         agent=dict(id="aigov-incident-triage", role="watchdog-agent", mode="advise", title="Incident triage agent",
                    objective="Summarize a latched exposure-budget breach from the K-lines around it, say whether in-bounds harm occurred, and propose containment for the operator; take no action.",
                    capabilities=["pe.completion.write", "pe.observations.read", "kline.read", "rag.query"],
                    actions=["Write a triage summary and the confirmed_harm finding."]),
         ces=[C("approach", "S0_Nominal", "S1_Warning", [{"mon_mu_exhaust_rate": (0.0201, 0.05)}],
                ["APPROACH"], "AMBER", ["GOV-SA-01"]),
              latch_ces("breach", "S0_Nominal|S1_Warning", "S2_BreachLatch",
                        rep({"mon_mu_exhaust_rate": gt(0.05)}, DEBOUNCE), ["REVOKE_EPOCH", "TRIGGER_INCIDENT", "LATCH"],
                        [("triage-pending", {"triage_completed": 0}, ["REVOKE_EPOCH", "LATCH", "AGENT_REQUESTED"]),
                         ("harm", {"triage_completed": 1, "confirmed_harm": 1, "operator_approved": 0},
                          ["REVOKE_EPOCH", "TRIGGER_INCIDENT", "LATCH"]),
                         ("unapproved", {"operator_approved": 0}, ["REVOKE_EPOCH", "LATCH"]),
                         ("not-distinct", {"operator_distinct": 0}, ["REVOKE_EPOCH", "LATCH"]),
                         ("rate", {"mon_mu_exhaust_rate": gt(0.02)}, ["REVOKE_EPOCH", "LATCH"])],
                        ({"triage_completed": 1, "operator_approved": 1, "operator_distinct": 1,
                          "mon_mu_exhaust_rate": le(0.02)}, []),
                        ["GOV-SA-01", "GOV-SA-19"], dispatch=True)]),
    dict(n=8, stem="GOV08_latency-gate-sentinel", code="M-GOV-08", title="LatencyGateSentinel",
         kind="fixture", cls="signal-monitor", family="C-runtime-assurance", workflow="W3", asset=None, handoff=None,
         rule="SPECIFICATION.md 4.3 (8)",
         desc="Latency gate sentinel: halts on a sustained TO-1 gate failure or p99 drift above 0.10, and permits again after a sustained return within the gate.",
         facts=["gate_kperf_to1", "mon_latency_drift"], completion=[], agent=None,
         ces=[C("drift-gate-failed", "S0_WithinSLA", "S1_LatencyDrift", rep({"gate_kperf_to1": 0}, DEBOUNCE),
                ["HALT_PROMOTION"], "RED", ["GOV-SA-19"]),
              C("drift-latency", "S0_WithinSLA", "S1_LatencyDrift", rep({"mon_latency_drift": gt(0.10)}, DEBOUNCE),
                ["HALT_PROMOTION"], "RED", ["GOV-SA-01", "GOV-SA-19"]),
              C("within-sla", "S1_LatencyDrift", "S0_WithinSLA",
                rep({"gate_kperf_to1": 1, "mon_latency_drift": le(0.10)}, 2), ["PERMIT_DEPLOY"], "GREEN",
                ["GOV-SA-07", "GOV-SA-19"])]),
    dict(n=9, stem="GOV09_near-miss-backlog-enforcer", code="M-GOV-09", title="NearMissBacklogEnforcer",
         kind="fixture", cls="signal-monitor", family="C-runtime-assurance", workflow="W3", asset=None, handoff=None,
         rule="SPECIFICATION.md 4.3 (9)",
         desc="Near-miss backlog enforcer with hysteresis: halts promotion on a sustained backlog of 0.80 of ring capacity, dispatches near-miss triage, and holds until the backlog falls below 0.50.",
         facts=["mon_nearmiss_backlog"],
         completion=[("triage_completed", "the triage pass is complete")],
         agent=dict(id="aigov-near-miss-triage", role="watchdog-agent", mode="advise", title="Near-miss triage agent",
                    objective="Classify and resolve unresolved near-miss K-lines and draft candidate rules for the next rule-epoch promotion (W2); resolving K-lines lowers the backlog Source.",
                    capabilities=["pe.completion.write", "kline.read", "rag.query"],
                    actions=["Classify near-miss K-lines.", "Draft candidate rules for a W2 frame."]),
         ces=[latch_ces("backlog", "S0_Nominal", "S1_BacklogThreshold", rep({"mon_nearmiss_backlog": ge(0.80)}, 2),
                        ["HALT_PROMOTION", "LATCH"],
                        [("triage-pending", {"triage_completed": 0}, ["HALT_PROMOTION", "LATCH", "AGENT_REQUESTED"]),
                         ("backlog", {"mon_nearmiss_backlog": ge(0.50)}, ["HALT_PROMOTION", "LATCH"])],
                        ({"triage_completed": 1, "mon_nearmiss_backlog": lt(0.50)}, []),
                        ["GOV-SA-01", "GOV-SA-19"], dispatch=True)]),
    dict(n=10, stem="GOV10_synthetic-transparency-gate", code="M-GOV-10", title="SyntheticTransparencyGate",
         kind="template", cls="safety-compliance-checker", family="D-transparency-oversight", workflow="W4",
         asset="EgressArt50Log", handoff="GOV13_control-crosswalk-assembler", rule="SPECIFICATION.md 4.3 (10)",
         desc="Synthetic-content transparency gate (EU AI Act Art. 50), per outbound message: permits internal and marked external messages; for an unmarked external message the provenance tagger marks it or holds it.",
         facts=["req_egress", "egress_external_comm", "egress_art50_marked"],
         completion=[("tag_completed", "the tagger finished"), ("tag_failed", "the agent's step failed"),
                     ("message_held", "the tagger held the message")],
         agent=dict(id="aigov-egress-provenance-tagger", role="step-agent", mode="supervised-act",
                    title="Egress provenance tagger",
                    objective="Add machine-readable AI provenance (Art. 50, C2PA where applicable) to an outbound external message, or hold it when provenance cannot be asserted.",
                    capabilities=["frame.read", "frame.return.write", "egress.message.annotate", "egress.message.hold"],
                    actions=["Annotate the message with provenance.", "Hold a message whose provenance cannot be asserted."]),
         ces=[C("pass-internal", "S0_Idle", "S1_PassInternal",
                [{"lane_in_workflow": 1, "req_egress": 1, "egress_external_comm": 0}], ["PERMIT_DEPLOY"], "GREEN",
                ["GOV-SA-08"]),
              C("pass-marked", "S0_Idle", "S2_PassMarked",
                [{"lane_in_workflow": 1, "req_egress": 1, "egress_external_comm": 1, "egress_art50_marked": 1}],
                ["PERMIT_DEPLOY"], "GREEN"),
              *agent_ces({"lane_in_workflow": 1, "req_egress": 1, "egress_external_comm": 1, "egress_art50_marked": 0},
                         "tag_completed", "tag_failed"),
              C("tagged", "S1_AgentRunning", "S2_PassMarked",
                [{"lane_in_workflow": 1, "req_egress": 1, "egress_external_comm": 1, "egress_art50_marked": 0,
                  "lane_step_running": 1, "tag_completed": 0},
                 {"tag_completed": 1, "egress_art50_marked": 1, "message_held": 0}], ["PERMIT_DEPLOY"], "GREEN"),
              C("held", "S1_AgentRunning", "S_fail_UnmarkedBlock",
                [{"lane_in_workflow": 1, "req_egress": 1, "egress_external_comm": 1, "egress_art50_marked": 0,
                  "lane_step_running": 1, "tag_completed": 0},
                 {"tag_completed": 1, "message_held": 1}], ["HALT_PROMOTION"], "RED"),
              C("unmarked-block", "S1_AgentRunning", "S_fail_UnmarkedBlock",
                [{"lane_in_workflow": 1, "req_egress": 1, "egress_external_comm": 1, "egress_art50_marked": 0,
                  "lane_step_running": 1, "tag_completed": 0},
                 {"tag_completed": 1, "egress_art50_marked": 0, "message_held": 0}], ["HALT_PROMOTION"], "RED")]),
    dict(n=11, stem="GOV11_human-review-anti-bias-gate", code="M-GOV-11", title="HumanReviewAntiBiasGate",
         kind="template", cls="safety-compliance-checker", family="D-transparency-oversight", workflow="W4",
         asset="GovernanceAssetFrame", handoff="GOV13_control-crosswalk-assembler", rule="SPECIFICATION.md 4.3 (11)",
         desc="Human review gate: the diff renderer shows the canonical diff of the exact revision; an approval counts only after the reviewer has been shown it for the dwell, by a distinct human; approval without a diff, or in the same step as the diff, is blocked.",
         facts=["lane_principal_distinct"],
         completion=[("diff_rendered", "the canonical diff was rendered and shown"), ("render_failed", "rendering failed")],
         agent=dict(id="aigov-diff-renderer", role="deterministic-tool", mode="advise", title="Canonical diff renderer",
                    objective="Render the canonical (RFC 8785) diff of the exact pinned revision under review and present it to the reviewer; deterministic, no model.",
                    capabilities=["frame.read", "pod.read", "frame.return.write"],
                    actions=["Render and present the canonical diff of the pinned revision."]),
         ces=[*agent_ces({"lane_in_workflow": 1}, "diff_rendered", "render_failed"),
              C("diff-verified", "S1_DiffShown", "S2_DiffVerified",
                rep({"lane_in_workflow": 1, "diff_rendered": 1, "lane_approved": 0}, DWELL) +
                [{"lane_approved": 1, "lane_principal_distinct": 1, "diff_rendered": 1}], ["PERMIT_DEPLOY"], "GREEN",
                ["GOV-SA-14"]),
              C("blind-approval-block", "S0_AwaitingDiff", "S_fail_BlindApprovalBlock",
                [{"lane_in_workflow": 1, "diff_rendered": 0, "lane_approved": 0},
                 {"lane_approved": 1, "diff_rendered": 0}], ["HALT_PROMOTION"], "RED"),
              C("rushed-approval-block", "S0_AwaitingDiff", "S_fail_BlindApprovalBlock",
                [{"lane_in_workflow": 1, "diff_rendered": 0, "lane_approved": 0},
                 {"lane_approved": 1, "diff_rendered": 1}], ["HALT_PROMOTION"], "RED", ["GOV-SA-14"]),
              C("self-approval-block", "S0_AwaitingDiff", "S_fail_BlindApprovalBlock",
                [{"lane_in_workflow": 1, "lane_approved": 1, "lane_principal_distinct": 0}], ["HALT_PROMOTION"], "RED")]),
    dict(n=12, stem="GOV12_serious-incident-responder", code="M-GOV-12", title="SeriousIncidentResponder",
         kind="template", cls="governance-escalator", family="E-incident-audit", workflow="W5",
         asset="KLineIncidentArchive", handoff="GOV13_control-crosswalk-assembler", rule="SPECIFICATION.md 4.3 (12)",
         desc="Serious-incident responder (EU AI Act Art. 73), per incident frame: contains while harm is active, the incident responder exports the K-line bundle and drafts the notice, the notice parks for a distinct human, and the frame closes on approval with no harm active; the statutory clock (the stale lane) running out first is overdue.",
         facts=["mon_t13_incident_cnt", "lane_principal_distinct"],
         completion=[("bundle_exported", "the K-line bundle is exported"), ("notice_drafted", "the Art. 73 notice is drafted"),
                     ("responder_failed", "the agent's step failed")],
         agent=dict(id="aigov-incident-responder", role="step-agent", mode="supervised-act", title="Incident responder",
                    objective="For the incident frame: export the self-verifying K-line bundle around the incident, draft the Art. 73 notice with its timeline, and keep the statutory clock visible; the notice is filed by a human.",
                    capabilities=["frame.read", "pod.read", "pod.write", "frame.return.write", "kline.read",
                                  "pe.observations.read"],
                    actions=["Export the K-line bundle into the frame.", "Draft the statutory notice."]),
         ces=[C("contain-harm", "S0_Standby", "S1_Contained", [{"mon_t13_incident_cnt": gt(0.0)}],
                ["REVOKE_EPOCH", "TRIGGER_INCIDENT"], "RED", ["GOV-SA-01"]),
              *agent_ces({"lane_in_workflow": 1}, "bundle_exported", "responder_failed",
                         outs_requested=("AGENT_REQUESTED", "REVOKE_EPOCH")),
              C("notice-parked", "S1_Contained", "S2_NoticeParked", [P12], ["PARKED", "REVOKE_EPOCH"], "AMBER",
                ["GOV-SA-02"]),
              C("closed", "S2_NoticeParked", "S3_Closed",
                [P12, {"lane_approved": 1, "lane_principal_distinct": 1, "mon_t13_incident_cnt": 0, "lane_stale": 0}],
                [], "GREEN", ["GOV-SA-20"]),
              C("notice-overdue", "S2_NoticeParked", "S_err_Overdue", [P12, {"lane_stale": 1}],
                ["OVERDUE", "TRIGGER_INCIDENT", "REVOKE_EPOCH"], "RED", ["GOV-SA-21"])]),
    dict(n=13, stem="GOV13_control-crosswalk-assembler", code="M-GOV-13", title="ControlCrosswalkAssembler",
         kind="template", cls="evidence-archive", family="E-incident-audit", workflow="W5",
         asset="AuditorEvidencePack", handoff="GOV01_impact-dossier-lifecycle", rule="SPECIFICATION.md 4.3 (13)",
         desc="Control crosswalk assembler: with parity, AIBOM and the impact assessment in place, the crosswalk assembler builds the auditor evidence pack; a complete pack parks for a review that dwells on the rendered diff, and a distinct human seals it.",
         facts=["req_audit_pack_seal", "gate_3of3_parity", "gate_aibom_pinned", "comp_iso42005_signed",
                "lane_principal_distinct", "lane_diff_rendered"],
         completion=[("pack_assembled", "the pack is assembled"), ("assembler_failed", "the agent's step failed"),
                     ("missing_receipts", "receipts are missing from the pack")],
         agent=dict(id="aigov-control-crosswalk-assembler", role="step-agent", mode="supervised-act",
                    title="Control crosswalk assembler",
                    objective="Collect the receipts (dossiers, AIBOM, parity certificate, WAL segments, egress log, incident archive) into the auditor evidence pack, mapped to ISO/IEC 42001 Annex A (the SoA template), NIST AI RMF and the EU AI Act; list missing receipts.",
                    capabilities=["frame.read", "pod.read", "pod.write", "frame.return.write", "regression.report.read",
                                  "kline.read"],
                    actions=["Assemble the evidence pack in the frame.", "Report missing receipts."]),
         ces=[C(f"incomplete-{name}", "S0_Idle", "S_fail_IncompletePack",
                [{"lane_in_workflow": 1, "req_audit_pack_seal": 1, sig: 0}], ["HALT_PROMOTION"], "RED")
              for name, sig in (("parity", "gate_3of3_parity"), ("aibom", "gate_aibom_pinned"),
                                ("impact", "comp_iso42005_signed"))] +
             [*agent_ces({"lane_in_workflow": 1, "req_audit_pack_seal": 1, "gate_3of3_parity": 1, "gate_aibom_pinned": 1,
                          "comp_iso42005_signed": 1}, "pack_assembled", "assembler_failed"),
              C("missing-receipts", "S1_AgentRunning", "S_err_Rework",
                [{"lane_in_workflow": 1, "req_audit_pack_seal": 1, "gate_3of3_parity": 1, "gate_aibom_pinned": 1,
                  "comp_iso42005_signed": 1, "lane_step_running": 1, "pack_assembled": 0},
                 {"pack_assembled": 1, "missing_receipts": 1}], ["REWORK"], "AMBER"),
              *review_ces(P13, A_HUMAN, W)]),
    dict(n=14, stem="GOV14_periodic-recertification-timer", code="M-GOV-14", title="PeriodicRecertificationTimer",
         kind="fixture", cls="signal-monitor", family="A-domain-onboarding-impact", workflow="W7", asset=None,
         handoff=None, rule="SPECIFICATION.md 4.3 (14)",
         desc="Periodic recertification timer: at 15% TTL remaining it dispatches the renewal scheduler to open a renewal admission frame; expiry latches a revoke, expiry without a renewal window first is overdue, and the epoch is restored only on a renewed TTL with an operator's approval.",
         facts=["mon_recert_ttl_rem", "operator_approved"],
         completion=[("renewal_frame_open", "a renewal admission frame is open")],
         agent=dict(id="aigov-renewal-scheduler", role="watchdog-agent", mode="supervised-act", title="Renewal scheduler",
                    objective="Open a renewal admission frame (W1) for the domain whose recertification window has opened, carrying its last approved dossier as the base revision.",
                    capabilities=["pe.completion.write", "lifecycle.frame.open", "registry.read"],
                    actions=["Open the renewal admission frame."]),
         ces=[C("renewal-window", "S0_Current", "S1_RenewalWindow",
                [{"mon_recert_ttl_rem": (EPS, 0.15), "renewal_frame_open": 0}],
                ["APPROACH", "AGENT_REQUESTED"], "AMBER", ["GOV-SA-01"], dispatch=True),
              C("renewal-open", "S1_RenewalWindow", "S1_RenewalWindow",
                [{"mon_recert_ttl_rem": (EPS, 0.15), "renewal_frame_open": 1}], ["APPROACH"], "AMBER",
                ["GOV-SA-01"]),
              *[latch_ces(cid, frm, "S2_ExpiredRevoked", ev, outs,
                          [("ttl", {"mon_recert_ttl_rem": le(0.15)}, ["REVOKE_EPOCH", "LATCH"]),
                           ("unapproved", {"operator_approved": 0}, ["REVOKE_EPOCH", "LATCH"])],
                          ({"mon_recert_ttl_rem": gt(0.15), "operator_approved": 1}, []), amend)
                for cid, frm, ev, outs, amend in (
                    ("expired", "S0_Current|S1_RenewalWindow", [{"mon_recert_ttl_rem": 0}], ["REVOKE_EPOCH", "LATCH"],
                     ["GOV-SA-01"]),
                    ("expired-without-window", "S0_Current",
                     [{"mon_recert_ttl_rem": gt(0.15)}, {"mon_recert_ttl_rem": 0}],
                     ["REVOKE_EPOCH", "LATCH", "OVERDUE"], ["GOV-SA-01", "GOV-SA-22"]))]]),
    dict(n=15, stem="GOV15_break-glass-emergency-override", code="M-GOV-15", title="BreakGlassEmergencyOverride",
         kind="template", cls="governance-escalator", family="H-hardening", workflow="W6",
         asset="EmergencyEpochOverrideFrame", handoff="GOV04_rule-epoch-promotion",
         rule="HARDENING_TRANSITION_RULES.md section 2 (15)",
         desc="Break-glass emergency override: an attested, distinct principal with clean keys requests it, the break-glass coordinator opens the emergency epoch and queues its ratification, the emergency permits under a mandatory incident trail, post-hoc quorum and parity ratify it, and the lease (the stale lane) or a tamper revokes it.",
         facts=["req_epoch_swap", "gate_source_slsa_attested", "lane_quorum_integrity_ok", "lane_principal_distinct",
                "quorum_valid", "gate_3of3_parity"],
         completion=[("emergency_open", "the emergency epoch is open and its lease started"),
                     ("ratification_queued", "a W2 ratification frame is queued"),
                     ("coordinator_failed", "the agent's step failed")],
         agent=dict(id="aigov-break-glass-coordinator", role="step-agent", mode="supervised-act",
                    title="Break-glass coordinator",
                    objective="Open the emergency epoch after the two root-token holders have acted, start its lease, and queue the post-hoc ratification as a rule-epoch promotion frame (W2); never extend a lease.",
                    capabilities=["frame.read", "frame.return.write", "lifecycle.frame.open", "human.notify"],
                    actions=["Open the emergency epoch and start its lease.", "Queue the ratification frame."]),
         ces=[*agent_ces({"lane_in_workflow": 1, "req_epoch_swap": 1, "gate_source_slsa_attested": 1,
                          "lane_quorum_integrity_ok": 1, "lane_principal_distinct": 1, "lane_re_pinned": 0,
                          "lane_stale": 0}, "emergency_open", "coordinator_failed"),
              C("emergency-active", "S1_AgentRunning", "S2_EmergencyActive",
                [{"lane_in_workflow": 1, "req_epoch_swap": 1, "gate_source_slsa_attested": 1,
                  "lane_quorum_integrity_ok": 1, "lane_principal_distinct": 1, "lane_re_pinned": 0, "lane_stale": 0,
                  "lane_step_running": 1, "emergency_open": 0}, E15],
                ["PERMIT_DEPLOY", "TRIGGER_INCIDENT"], "AMBER", ["GOV-SA-09", "GOV-SA-10"]),
              C("ratified", "S2_EmergencyActive", "S3_Ratified",
                [E15, {"quorum_valid": 1, "gate_3of3_parity": 1, "lane_stale": 0, "lane_re_pinned": 0}],
                ["PERMIT_DEPLOY"], "GREEN"),
              C("lease-expired", "S2_EmergencyActive", "S_err_ExpiredRevoked", [E15, {"lane_stale": 1}],
                ["HALT_PROMOTION", "REVOKE_EPOCH", "REWORK", "OVERDUE"], "RED"),
              C("tamper-revoked", "S2_EmergencyActive", "S_err_ExpiredRevoked", [E15, {"lane_re_pinned": 1}],
                ["HALT_PROMOTION", "REVOKE_EPOCH", "REWORK"], "RED")]),
    dict(n=16, stem="GOV16_cross-domain-delegation-cap", code="M-GOV-16", title="CrossDomainDelegationCap",
         kind="fixture", cls="signal-monitor", family="H-hardening", workflow="W3", asset=None, handoff=None,
         rule="HARDENING_TRANSITION_RULES.md section 2 (16)",
         desc="Cross-domain delegation cap with an SR latch: in the approach band it dispatches the delegation clamp; a sustained exposure or canary breach trips a revoke and an incident, released on a distinct operator's approval with both back in band.",
         facts=["mon_xdomain_mu_agg", "mon_canary_drift_score", "operator_approved", "operator_distinct"],
         completion=[("delegation_clamped", "delegation depth was clamped")],
         agent=dict(id="aigov-delegation-clamp", role="watchdog-agent", mode="supervised-act", title="Delegation clamp agent",
                    objective="Reduce the delegation depth of the A2A chains driving cross-domain exposure into the approach band, after the operator's approval; report what was clamped.",
                    capabilities=["pe.completion.write", "pe.observations.read", "delegation.clamp", "human.notify"],
                    actions=["Clamp A2A delegation depth on the offending chains."]),
         ces=[C("delegation-throttle", "S0_Nominal", "S1_DelegationThrottle",
                [{"mon_xdomain_mu_agg": (0.7001, 0.90), "mon_canary_drift_score": le(0.15),
                  "delegation_clamped": 0}], ["APPROACH", "AGENT_REQUESTED"], "AMBER", ["GOV-SA-01"], dispatch=True),
              C("delegation-clamped", "S1_DelegationThrottle", "S1_DelegationThrottle",
                [{"mon_xdomain_mu_agg": (0.7001, 0.90), "delegation_clamped": 1}], ["APPROACH"],
                "AMBER", ["GOV-SA-01"]),
              *[latch_ces(cid, "S0_Nominal|S1_DelegationThrottle", "S2_CrossDomainBreachLatch",
                          rep({signal: gt(limit)}, DEBOUNCE), ["REVOKE_EPOCH", "TRIGGER_INCIDENT", "LATCH"],
                          [("unapproved", {"operator_approved": 0}, ["REVOKE_EPOCH", "LATCH"]),
                           ("not-distinct", {"operator_distinct": 0}, ["REVOKE_EPOCH", "LATCH"]),
                           ("exposure", {"mon_xdomain_mu_agg": gt(0.50)}, ["REVOKE_EPOCH", "LATCH"]),
                           ("canary", {"mon_canary_drift_score": gt(0.10)}, ["REVOKE_EPOCH", "LATCH"])],
                          ({"operator_approved": 1, "operator_distinct": 1, "mon_xdomain_mu_agg": le(0.50),
                            "mon_canary_drift_score": le(0.10)}, ["PERMIT_DEPLOY"]), ["GOV-SA-01", "GOV-SA-19"])
                for cid, signal, limit in (("breach-exposure", "mon_xdomain_mu_agg", 0.90),
                                           ("breach-canary", "mon_canary_drift_score", 0.15))]]),
    dict(n=17, stem="GOV17_quorum-key-revocation-lifecycle", code="M-GOV-17", title="QuorumKeyRevocationLifecycle",
         kind="template", cls="governance-escalator", family="H-hardening", workflow="W6",
         asset="QuorumKeyring", handoff="GOV15_break-glass-emergency-override",
         rule="HARDENING_TRANSITION_RULES.md section 2 (17)",
         desc="Quorum key revocation, per rotation frame: halts and revokes while a signer key is compromised, the key rotation coordinator invalidates every parked continuation the revoked principal signed and prepares the rotated keyring, which parks for a review dwell, and a distinct human approves the rotation with clean keys and attested Sources.",
         facts=["lane_quorum_integrity_ok", "gate_source_slsa_attested", "lane_principal_distinct"],
         completion=[("invalidation_done", "every affected parked continuation is invalidated"),
                     ("keyring_ready", "the rotated keyring is prepared"), ("coordinator_failed", "the agent's step failed")],
         agent=dict(id="aigov-key-rotation-coordinator", role="step-agent", mode="supervised-act",
                    title="Key rotation coordinator",
                    objective="Invalidate every parked continuation signed by the revoked principal and prepare the rotated quorum keyring for approval; never approve the rotation.",
                    capabilities=["frame.read", "pod.read", "pod.write", "frame.return.write", "pki.crl.read",
                                  "lifecycle.continuation.invalidate", "human.notify"],
                    actions=["Invalidate continuations signed by the revoked principal.", "Prepare the rotated keyring."]),
         ces=[C("revoked", "S0_KeysValid", "S1_RevocationTriggered", [{"lane_quorum_integrity_ok": 0}],
                ["HALT_PROMOTION", "REVOKE_EPOCH", "TRIGGER_INCIDENT"], "RED"),
              *agent_ces({"lane_in_workflow": 1}, "invalidation_done", "coordinator_failed",
                         outs_requested=("AGENT_REQUESTED", "HALT_PROMOTION", "REVOKE_EPOCH")),
              C("rotation-parked", "S1_RevocationTriggered", "S2_RotationParked", [P17],
                ["PARKED", "HALT_PROMOTION", "REVOKE_EPOCH"], "AMBER", ["GOV-SA-02"]),
              C("keys-rotated", "S2_RotationParked", "S3_KeysRotated",
                rep(P17, DWELL) + [{"lane_approved": 1, "lane_principal_distinct": 1, "lane_quorum_integrity_ok": 1,
                                    "gate_source_slsa_attested": 1, "lane_stale": 0}], ["PERMIT_DEPLOY"], "GREEN",
                ["GOV-SA-14"]),
              C("rotation-unattested", "S2_RotationParked", "S2_RotationParked",
                [P17, {"lane_approved": 1, "gate_source_slsa_attested": 0}], ["HALT_PROMOTION", "REVOKE_EPOCH"], "RED"),
              C("rotation-overdue", "S2_RotationParked", "S_err_Overdue", [P17, {"lane_stale": 1}],
                ["OVERDUE", "HALT_PROMOTION", "REVOKE_EPOCH"], "RED")]),
]

# GOV-SA-23 (proposed): every machine's output region is latched by the engines
# (GOV-SD-19), so a decision would hold after its conditions end. Each machine
# carries one idle CES: a single event that accepts any input and asserts the
# all-zero vector. Outputs merge by `or`, so it never masks another CES; on a
# step where nothing else asserts it clears the region, and a decision lasts
# exactly as long as its condition. A latch is unaffected: its hold cluster
# (GOV-SA-24) asserts LATCH on every step the latch is set.
for _m in MACHINES:
    _m["ces"].append(C("idle", "any", "Idle", [{}], [], "GREEN", ["GOV-SA-23"]))

FIXTURE_PRODUCERS = [m for m in MACHINES if m["kind"] == "fixture"]

NOMINAL = {"lane_principal_distinct": 1, "lane_quorum_integrity_ok": 1, "gate_source_slsa_attested": 1,
           "src_quorum_integrity_ok": 1, "src_slsa_attested": 1, "gate_kperf_to1": 1, "mon_recert_ttl_rem": 1.0,
           "operator_distinct": 1}

FIXTURE_CONTEXT = {
    (6, "violation-self-signer"): {"bundle_ready": 1},
    (13, "incomplete-parity"): {"gate_aibom_pinned": 1, "comp_iso42005_signed": 1},
    (13, "incomplete-aibom"): {"gate_3of3_parity": 1, "comp_iso42005_signed": 1},
    (13, "incomplete-impact"): {"gate_3of3_parity": 1, "gate_aibom_pinned": 1},
    (4, "parity-missing"): {"gate_aibom_pinned": 1},
    (4, "aibom-missing"): {"gate_3of3_parity": 1},
}
FIXTURE_VALUES = {
    (7, "breach-hold-rate"): {"mon_mu_exhaust_rate": 0.03},
    (16, "breach-exposure-hold-canary"): {"mon_canary_drift_score": 0.12},
    (16, "breach-exposure-hold-exposure"): {"mon_xdomain_mu_agg": 0.6},
    (16, "breach-canary-hold-canary"): {"mon_canary_drift_score": 0.12},
    (16, "breach-canary-hold-exposure"): {"mon_xdomain_mu_agg": 0.6},
    # Hold at the expired TTL (0 satisfies the hold literal TTL <= 0.15), so the cell has two levels.
    (14, "expired-without-window-hold-ttl"): {"mon_recert_ttl_rem": 0.0},
}
NEGATIVES = {
    1: [("approval-without-dwell", [P01, A_HUMAN], "an approval after a single parked step does not permit"),
        ("self-approval", rep(P01, DWELL) + [{"lane_approved": 1, "lane_principal_distinct": 0}],
         "an approval by the preparer or an agent (T15) does not permit"),
        ("red-team-missing", [{**P01, "gate_redteam_pass": 0}], "the dossier does not park without the red-team gate")],
    4: [("promotion-without-dwell", [P04, {"quorum_valid": 1}], "a quorum in the step after parking does not promote")],
    6: [("signatures-before-bundle", [{"src_req_epoch_swap": 1, "bundle_ready": 0, "signed_risk": 1,
                                       "signed_engineering": 1, "signed_legal": 1}],
         "signatures that arrive before the bundle is ready do not make a quorum")],
    7: [("single-sample-breach", [{"mon_mu_exhaust_rate": 0.5}], "one breach sample does not trip the latch"),
        ("release-before-triage", rep({"mon_mu_exhaust_rate": 0.5}, DEBOUNCE) +
         [{"mon_mu_exhaust_rate": 0.01, "operator_approved": 1}],
         "an approval before triage completes does not release the latch")],
    11: [("approval-after-one-step", [{"lane_in_workflow": 1, "diff_rendered": 1}, {"lane_approved": 1}],
          "an approval one step after the diff does not meet the dwell")],
    14: [("expiry-holds-after-renewal", [{"mon_recert_ttl_rem": 0.0}, {"mon_recert_ttl_rem": 0.5}],
          "a renewed TTL without approval keeps the epoch revoked")],
    16: [("single-canary-spike", [{"mon_canary_drift_score": 0.5}], "one canary spike does not trip")],
}


# ---------------------------------------------------------------- layout
def layout(m):
    """Input element names by index. Templates: 2-7 the frame lanes; facts in 0-1
    then after the completion lane, which starts at 8 and is contiguous."""
    facts, comp = list(m["facts"]), [f for f, _ in m["completion"]]
    if m["kind"] == "template":
        head = facts[:2] + ["spare"] * (2 - len(facts[:2]))
        names = head + LANES + comp + facts[2:]
        comp_start = 8
    else:
        names = facts + comp + (["latch_q_prev"] if m.get("latch") else [])
        comp_start = len(facts)
    if len(names) > INPUT_SLOT:
        raise SystemExit(f"{m['stem']}: {len(names)} inputs exceed {INPUT_SLOT}")
    return names, comp_start


def regions(m):
    names, _ = layout(m)
    inp = {"offset": BAND_START + INPUT_SLOT * (m["n"] - 1), "length": len(names)}
    outp = {"offset": OUTPUT_START + OUTPUT_LEN * (m["n"] - 1), "length": OUTPUT_LEN}
    return inp, outp


def kind_of(name, m):
    comp = dict(m["completion"])
    if name in comp:
        return "b"
    return SIGNALS[name][0]


# ---------------------------------------------------------------- encoding + evaluator
def element(pred):
    if pred is None:
        return {"value": 0.5, "threshold": 0.5, "comparatorType": "threshold"}
    if pred in (0, 1):
        return {"value": float(pred), "comparatorType": "equals"}
    lo, hi = pred
    if lo == hi:
        return {"value": float(lo), "comparatorType": "equals"}
    return {"value": round((lo + hi) / 2, 6), "threshold": round((hi - lo) / 2, 6), "comparatorType": "threshold"}


def accepts(el, x):
    c = el["comparatorType"]
    if c == "equals":
        return x == el["value"]
    if c == "threshold":
        return abs(el["value"] - x) <= el.get("threshold", 0.1) + 1e-12
    raise ValueError(c)


def symbol(pred_map, names):
    parts = []
    for name in names:
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


def regex(events, names):
    out, i = [], 0
    while i < len(events):
        j = i
        while j + 1 < len(events) and events[j + 1] == events[i]:
            j += 1
        s = ("(" + " | ".join(symbol(pm, names) for pm in preds_at(events[i])) + ")"
             if isinstance(events[i], Alt) else symbol(events[i], names))
        out.append(s if j == i else f"{s}{{{j - i + 1}}}")
        i = j + 1
    return " · ".join(out)


def vector(names_on, length=OUTPUT_LEN, labels=OUTPUTS):
    v = [0.0] * length
    for n in names_on:
        v[labels.index(n)] = 1.0
    return v


def run(sequences, steps, latch_index=None, latch_out=0):
    """Drive CESs over input vectors under SURFACE_SPEC's transition rule.

    Authoring self-check only; the engines (3-of-3) are the authority. Returns
    the machine's output region after each step. The output is latched
    (GOV-SD-19): a step on which a CES asserts writes the merged vector, and a
    step on which none asserts keeps the last vector written; None only before
    the first write. The GOV-SA-06 feedback cell reads that latched region.
    """
    initials = [{i for i, e in enumerate(seq["events"]) if e.get("isInitial")} for seq in sequences]
    active = [set(ini) for ini in initials]
    trace, prev_latch, latched = [], 0.0, None
    for x in steps:
        x = list(x)
        if latch_index is not None:
            x[latch_index] = prev_latch
        merged = None
        for si, seq in enumerate(sequences):
            evs = seq["events"]
            pos = {e["id"]: i for i, e in enumerate(evs)}
            nxt = set(initials[si])
            for ei in sorted(active[si]):
                ev = evs[ei]
                if not all(accepts(el, xv) for el, xv in zip(ev["elements"], x)):
                    continue
                if ev.get("outputEvents"):
                    vec = ev["outputEvents"][0]["vector"]
                    merged = list(vec) if merged is None else [max(a, b) for a, b in zip(merged, vec)]
                    if ei not in initials[si]:
                        nxt.add(ei)
                for nid in ev.get("nextEventIds", []):
                    nxt.add(pos[nid])
            active[si] = nxt
        if merged is not None:
            latched = merged
        trace.append(latched)
        if latch_index is not None:
            prev_latch = latched[latch_out] if latched else 0.0
    return trace


# ---------------------------------------------------------------- agents
def sensor_id(m):
    return f"aigov.{m['stem'][:5].lower()}.{m['agent']['id'].removeprefix('aigov-')}.completion"


def write_back(m):
    names, start = layout(m)
    inp, _ = regions(m)
    region = {"offset": inp["offset"] + start, "length": len(m["completion"])}
    sid = sensor_id(m)
    provider = "asset-lifecycle" if m["kind"] == "template" else "agent-runtime"
    name = f"{m['agent']['title']} completion ({m['stem'][:5]})"
    return {"type": "pe-sensor", "provider": provider, "sensorId": sid, "name": name, "region": region,
            "semantics": [f for f, _ in m["completion"]], "ttlMs": TTL_MS, "normalization": "already-normalized-0-1",
            "ingest": {"endpoint": "/api/integrations/completions", "method": "POST", "triggerPush": False,
                       "compactPush": True},
            "sourceMapping": {"id": sid.replace(".", "-"), "sensorId": sid, "name": name, "region": region,
                              "ttlMs": TTL_MS}}


def agent_binding(m):
    a = m["agent"]
    act = a["mode"] in ("supervised-act", "automated-act")
    trig = next(f"ces_{m['stem'][:5].lower()}_{c['id'].replace('-', '_')}" for c in m["ces"] if c["dispatch"])
    return {"agent": a["id"], "mode": a["mode"], "trigger": trig, "allowedActions": a["actions"],
            "writeBack": write_back(m),
            "riskControls": {"requiresHumanApproval": act, "requiresRunbook": True, "maxAutonomy": a["mode"],
                             "blockedWhenRag": []},
            "autonomyPolicy": {"mode": a["mode"], "stage": 2 if act else 1, "writeBackType": "pe-sensor",
                               "canWriteBack": True, "canStageActions": act, "canExecuteActions": False,
                               "requiresHumanApproval": act, "requiresRunbook": True, "blockedWhenRag": []}}


PROHIBITIONS = [
    "Never approve, resume, capture or close a continuation; approvals belong to distinct humans (T15).",
    "Never write vector values directly; your result reaches the engines only through your completion contract.",
    "Read and write frame documents only through the asset lifecycle with the step's capability, under the pinned ETag.",
    "Leave unresolved what the evidence does not settle; never invent thresholds, signatures or receipts.",
]


def behavior(m):
    a, wb = m["agent"], write_back(m)
    inp, outp = regions(m)
    seqs = [f"ces_{m['stem'][:5].lower()}_{c['id'].replace('-', '_')}" for c in m["ces"] if c["dispatch"]]
    fields = [{"semantic": f, "valueType": "binary", "normalization": "binary",
               "extract": {"jsonPointer": f"/{f}", "responseKey": f}, "target": {"sensorId": wb["sensorId"],
               "region": wb["region"], "index": i}} for i, (f, _) in enumerate(m["completion"])]
    contract = ("Return one structured line per completion field as `<field>: 0|1` ("
                + ", ".join(f"{f}: {meaning}" for f, meaning in m["completion"]) +
                "), then `rationale: <one sentence>`. The machine, not you, decides what follows.")
    instructions = "\n".join([
        f"You are the {a['title'].lower()} for the RealityEngine AI governance regime ({m['code']} {m['title']}, workflow {m['workflow']}).",
        "", "OBJECTIVE", a["objective"], "", "YOU MAY", *[f"- {x}" for x in a["actions"]], "",
        "YOU MUST NOT", *[f"- {p}" for p in PROHIBITIONS]])
    frame_step = m["kind"] == "template"
    return {
        "schemaVersion": "1.0.0", "behaviorId": a["id"], "role": a["role"], "agentId": a["id"],
        "displayName": a["title"], "domain": DOMAIN,
        "machine": {"id": m["stem"], "file": f"{m['stem']}.json", "machineClass": m["cls"], "inputRegion": inp,
                    "outputRegion": outp, "cloneable": frame_step},
        "dispatch": {"mode": "frame-step" if frame_step else "ces-trigger", "triggerSequenceIds": seqs,
                     **({"frameScopes": ["frame:read", "pod:read", "pod:write", "frame:return"]
                         if "pod.write" in a["capabilities"] else ["frame:read", "pod:read", "frame:return"]}
                        if frame_step else {}),
                     "workflow": m["workflow"], "humanApprovalRequired": a["mode"] != "advise"},
        "capabilities": a["capabilities"],
        "reasoning": {"objective": a["objective"], "instructions": instructions, "outputContract": contract,
                      "sequenceCatalog": [{"sequenceId": f"ces_{m['stem'][:5].lower()}_{c['id'].replace('-', '_')}",
                                           "label": c["to"], "rag": c["rag"],
                                           "outputIndex": OUTPUTS.index(c["outs"][0]) if c["outs"] else 0,
                                           "action": " + ".join(c["outs"]) or "release"}
                                          for c in m["ces"] if any(f in e for e in c["events"]
                                                                   for f, _ in m["completion"])],
                      "prohibitions": PROHIBITIONS},
        "agentBinding": agent_binding(m),
        "responseMapping": {"schemaVersion": "1.0.0", "responseContract": "structured-keys", "mode": a["mode"],
                            "fields": fields},
        "provenance": {"builder": "machine_factory/domains/ai-governance-regime/tools/build_machines.py",
                       "candidateVersion": CANDIDATE, "specRule": m["rule"]},
    }


# ---------------------------------------------------------------- machines
def build_machine(m):
    names, comp_start = layout(m)
    inp, outp = regions(m)
    latch = m.get("latch", False)
    sequences, rules = [], []
    for c in m["ces"]:
        sid = f"ces_{m['stem'][:5].lower()}_{c['id'].replace('-', '_')}"
        evs = []
        graph = c.get("latchGraph")
        for pm in ([lit for _, lit, _ in graph["holds"]] + [graph["release"][0]]) if graph else []:
            unknown = set(pm) - set(names)
            if unknown:
                raise SystemExit(f"{m['stem']} {c['id']}: predicates on {sorted(unknown)} not in the input")
        cluster = ([f"{sid}-h-{name}" for name, _, _ in graph["holds"]] + [f"{sid}-release"]) if graph else []
        pos_ids = [[f"{sid}-e{i}-{label}" for label, _ in pos] if isinstance(pos, Alt) else [f"{sid}-e{i}"]
                   for i, pos in enumerate(c["events"])]
        for i, pos in enumerate(c["events"]):
            items = list(pos) if isinstance(pos, Alt) else [(None, pos)]
            for k, (_label, pm) in enumerate(items):
                unknown = set(pm) - set(names)
                if unknown:
                    raise SystemExit(f"{m['stem']} {c['id']}: predicates on {sorted(unknown)} not in the input")
                last = i == len(c["events"]) - 1
                eid = pos_ids[i][k]
                ev = {"id": eid, "isInitial": i == 0, "elements": [element(pm.get(n)) for n in names],
                      "nextEventIds": list(pos_ids[i + 1]) if not last else list(cluster)}
                if last:
                    ev["outputEvents"] = [{"id": f"{eid}-out" if len(items) > 1 else f"{sid}-out",
                                           "vector": vector(c["outs"])}]
                evs.append(ev)
        if graph:
            for name, lit, outs in graph["holds"]:
                evs.append({"id": f"{sid}-h-{name}", "isInitial": False,
                            "elements": [element(lit.get(n)) for n in names], "nextEventIds": list(cluster),
                            "outputEvents": [{"id": f"{sid}-h-{name}-out", "vector": vector(outs)}]})
            rel, rel_outs = graph["release"]
            evs.append({"id": f"{sid}-release", "isInitial": False, "elements": [element(rel.get(n)) for n in names],
                        "nextEventIds": [], "outputEvents": [{"id": f"{sid}-release-out", "vector": vector(rel_outs)}]})
        rx = regex(c["events"], names)
        if graph:
            holds_rx = " | ".join(symbol(lit, names) for _, lit, _ in graph["holds"])
            rx = f"{rx} · ({holds_rx})* · {symbol(graph['release'][0], names)}"
        sequences.append({"id": sid, "name": f"{m['code']} {c['frm']} → {c['to']}", "schemaVersion": "1.0",
                          "metadata": {"sourceFromState": c["frm"], "sourceToState": c["to"], "regularExpression": rx,
                                       "length": len(evs), "specRule": m["rule"],
                                       "semanticAmendments": c["amend"],
                                       "asserts": c["outs"] or ["none (explicit release)"],
                                       **({"dispatchesAgent": m["agent"]["id"]} if c["dispatch"] else {})},
                          "events": evs})
        rule = {"sequenceId": sid, "outputMatches": vector(c["outs"]), "ragStatusCode": c["rag"],
                "processStatus": {"GREEN": "info", "AMBER": "warning", "RED": "error"}[c["rag"]],
                "description": f"{m['code']} {c['frm']} → {c['to']}: {rx}"}
        if c["dispatch"]:
            rule["dispatchAgent"] = m["agent"]["id"]
        rules.append(rule)

    latch_index = names.index("latch_q_prev") if latch else None
    fixtures = build_fixtures(m, sequences, names, latch_index)
    semantics = []
    for i, n in enumerate(names):
        comp = dict(m["completion"])
        if n in LANES:
            semantics.append(f"reserved: {n} (lifecycle frame lane {i}; {SIGNALS[n][4]})")
        elif n in comp:
            semantics.append(f"{n} (binary; {m['agent']['id']} completion via {sensor_id(m)}): {comp[n]}")
        else:
            k, delivery, producer, status, meaning = SIGNALS[n]
            semantics.append(f"{n} ({'binary' if k == 'b' else 'continuous [0,1]'}; {delivery}: {producer}; {status}): {meaning}")

    interconnections = []
    if m["kind"] == "fixture":
        k = FIXTURE_PRODUCERS.index(m)
        interconnections.append({
            "id": f"{DOMAIN}.verdicts.{m['stem'][:5].lower()}", "type": "published-domain-bus-producer",
            "role": m["title"], "sourceMachine": m["stem"], "sourceOutputRegion": {"offset": outp["offset"], "length": 4},
            "targetInputElements": list(range(4 * k, 4 * k + 4)),
            "normalizedElements": [f"{m['code']} {v}" for v in VERDICTS],
            "purpose": f"Publish {m['code']}'s verdicts to the domain verdict aggregator.",
            "busId": f"{DOMAIN}.verdicts", "busTag": f"published-bus-{DOMAIN}-verdicts",
            "targetMachine": "GOV00 Governance Verdict Aggregator",
            "targetMachineFile": "GOV00_governance-verdict-aggregator.json",
            "targetInputRegion": {"offset": AGG_INPUT_START, "length": 4 * len(FIXTURE_PRODUCERS)},
            "publishedOutputRegion": {"offset": AGG_INPUT_START + 4 * len(FIXTURE_PRODUCERS), "length": 4},
            "peCompositionRequired": True, "compositionOwner": "perception-engine",
            "dispatchMode": "asynchronous-no-wait",
            "privacyBoundary": "PE composes normalized verdict bits only."})
    if m.get("handoff"):
        interconnections.append({
            "id": f"{DOMAIN}.document.{m['stem'][:5].lower()}.{m['asset']}", "type": "document-workflow-handoff",
            "sourceMachine": m["stem"], "targetMachine": m["handoff"], "assetTypeId": m["asset"],
            "compositionOwner": "document-workflow-dispatcher",
            "purpose": f"Hand the frame's {m['asset']} to {m['handoff'][:5]}, its next consumer (agentic-workflow-contract.json {m['workflow']}); never infer a governance verdict from document content.",
            "nativeVectorWrite": False})

    md = {
        "category": DOMAIN, "domain": DOMAIN, "machineClass": m["cls"], "sequenceCount": len(sequences),
        "inputSemantics": semantics, "outputSemantics": [f"{i}: {o}" for i, o in enumerate(OUTPUTS)],
        "tags": [DOMAIN, m["family"], m["code"], m["workflow"]] + (["fixture"] if m["kind"] == "fixture" else []),
        "tagging": {"schemaVersion": "1.0.0", "managedBy": "machine_factory/domains/ai-governance-regime",
                    "primaryDomain": DOMAIN, "family": m["family"], "machineCode": m["stem"][:5],
                    "workflowTags": [m["title"], m["workflow"]], "validationTags": ["candidate-not-admitted"]},
        "governance": {"schemaVersion": "1.0.0", "ownerTeam": "AIGOV::Governance Steward",
                       "runbook": f"urn:re:aigov:runbook:{m['family']}:v1",
                       "escalationPolicy": "AIGOV::Governance Steward -> AIGOV::Approval Quorum; agents never resume an approval continuation (T15)",
                       "sla": {"ok": None, "info": None, "warning": None, "error": None}},
        "triggerConfig": {"processId": m["stem"], "processName": f"{m['code']} {m['title']}", "rules": rules},
        "interconnections": interconnections,
        "governanceSpec": {"machineCode": m["code"], "title": m["title"], "kind": m["kind"], "workflow": m["workflow"],
                           "specRule": m["rule"], "governedAssetType": m["asset"],
                           "governedTargetDomain": "carried by the asset frame", "agentCanResumeApproval": False},
        "conversion": {"candidateVersion": CANDIDATE, "builder": "tools/build_machines.py",
                       "transitionRule": "SURFACE_SPEC.md, Boundaries: where a K-line starts and ends",
                       "elementEncoding": "binary: equals; interval [lo,hi]: threshold, value (lo+hi)/2, threshold (hi-lo)/2; unconstrained: threshold 0.5 +/- 0.5",
                       "dwellSteps": DWELL, "debounceSteps": DEBOUNCE},
    }
    if m.get("agent"):
        md["agentBinding"] = agent_binding(m)
        md["aiTrigger"] = md["agentBinding"]["trigger"]
        md["dispatchableAgent"] = m["agent"]["id"]
        md["agentBehavior"] = f"agent-candidates/{DOMAIN}/{m['agent']['id']}.agent.json"
    if m["kind"] == "template":
        md["frameInputs"] = {"lanes": "input cells 2-7, written by the lifecycle (reserved)",
                             "facts": "every other non-completion input, written into the clone's block by the lifecycle's frame source (GOV-R19)",
                             "completion": f"input cells {comp_start}..{comp_start + len(m['completion']) - 1}, the step agent's completion"}
    if latch:
        md["latchFeedback"] = {"inputElement": latch_index, "fromOutputElement": OUTPUTS.index("LATCH"),
                               "compositionOwner": "perception-engine", "peCompositionRequired": True,
                               "rule": "Q(k) = S(k) or (not R(k) and Q(k-1)); the PE writes this machine's previous LATCH output into this element (GOV-R12)."}
    return {"version": VERSION, "machine": {
        "id": m["stem"], "name": m["stem"], "description": m["desc"], "arbiterRule": "PASSTHROUGH",
        "matchAlgorithm": "equals", "outputMergeTransformation": "or",
        "perceptualMapping": {"input": inp, "output": outp,
                              "bitsPerElement": 8 if any(kind_of(n, m) == "c" for n in names) else 1},
        "sequences": sequences, "inputSequences": fixtures, "metadata": md}}


def scenario_vectors(m, names, steps):
    vecs, held = [], {}
    for st in steps:
        held.update(st)
        v = []
        for n in names:
            p = held.get(n, NOMINAL.get(n, 0))
            if isinstance(p, tuple):
                p = round(p[0] + (p[1] - p[0]) / 2, 4)
            v.append(float(p))
        vecs.append(v)
    return vecs


def resolve(m, vecs, sequences, latch_index):
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


def build_fixtures(m, sequences, names, latch_index):
    scenarios = []
    for c, seq in zip(m["ces"], sequences):
        graph = c.get("latchGraph")
        if graph:
            rel, rel_outs = graph["release"]
            pre = [dict(e) for e in c["events"]]
            scenarios.append((f"{c['id']}-set", pre, f"sets {seq['id']}", seq["id"]))
            for name, lit, outs in graph["holds"]:
                step = {**rel, **lit, **FIXTURE_VALUES.get((m["n"], f"{c['id']}-hold-{name}"), {})}
                scenarios.append((f"{c['id']}-hold-{name}", pre + [step],
                                  f"holds {seq['id']} while {name}", (seq["id"], outs)))
            scenarios.append((f"{c['id']}-release", pre + [dict(rel)], f"releases {seq['id']}",
                              (seq["id"], rel_outs, c["outs"])))
            continue
        if any(isinstance(pos, Alt) for pos in c["events"]):
            import itertools
            choices = [list(pos) if isinstance(pos, Alt) else [(None, pos)] for pos in c["events"]]
            for path in itertools.product(*choices):
                label = "-".join(lb for lb, _ in path if lb)
                scenarios.append((f"{c['id']}-{label}", [dict(pm) for _, pm in path],
                                  f"drives {seq['id']} by {label}: {seq['metadata']['regularExpression']}", seq["id"]))
            continue
        steps = [dict(e) for e in c["events"]]
        ctx = FIXTURE_CONTEXT.get((m["n"], c["id"]))
        if ctx:
            steps[0] = {**ctx, **steps[0]}
        if latch_index is not None and c["events"][0].get("latch_q_prev") == 1:
            setter = next(s for s in m["ces"] if "LATCH" in s["outs"] and s["events"][0].get("latch_q_prev") is None)
            prime = [dict(e) for e in setter["events"]]
            reset_keys = {k for e in prime for k in e}
            body = {k: v for k, v in c["events"][0].items() if k != "latch_q_prev"}
            steps = prime + [{**{k: NOMINAL.get(k, 0) for k in reset_keys}, **body}]
        if (m["n"], c["id"]) in FIXTURE_VALUES:
            steps[-1] = {**steps[-1], **FIXTURE_VALUES[(m["n"], c["id"])]}
        scenarios.append((c["id"], steps, f"drives {seq['id']}: {seq['metadata']['regularExpression']}", seq["id"]))
    for name, steps, purpose in NEGATIVES.get(m["n"], []):
        scenarios.append((name, steps, purpose, None))
    scenarios.append(("nominal", [{}], "the quiet state", None))

    fixtures, seen = [], set()
    for name, steps, purpose, target in scenarios:
        vecs, trace = resolve(m, scenario_vectors(m, names, steps), sequences, latch_index)
        final = trace[-1] or [0.0] * OUTPUT_LEN
        if isinstance(target, tuple):
            # A latch hold or release (GOV-SA-24): the final step asserts its outputs, and a
            # release leaves none of the set outputs it does not itself assert.
            want = vector(target[1])
            if trace[-1] is None or not all(f >= w for f, w in zip(final, want)):
                raise SystemExit(f"{m['stem']}: fixture {name} does not assert {target[1]}: {trace}")
            if len(target) == 3:
                stuck = [o for o in target[2] if o not in target[1] and final[OUTPUTS.index(o)] >= 0.5]
                if stuck:
                    raise SystemExit(f"{m['stem']}: fixture {name} leaves {stuck} latched after release: {trace}")
            target = target[0]
        elif target is not None:
            want = vector(next(c for c in m["ces"]
                               if f"ces_{m['stem'][:5].lower()}_{c['id'].replace('-', '_')}" == target)["outs"])
            if trace[-1] is None or not all(f >= w for f, w in zip(final, want)):
                raise SystemExit(f"{m['stem']}: fixture {name} does not drive {target}: {trace}")
        key = json.dumps(vecs)
        if key in seen:
            continue
        seen.add(key)
        meta = {"expectedOutputVector": final, "expectedOutputsByStep": [t or [0.0] * OUTPUT_LEN for t in trace],
                "purpose": purpose,
                "expectedEvaluationScope": "Isolated from reset; expected outputs computed by the package's authoring evaluator from SURFACE_SPEC's transition rule, to be confirmed 3-of-3 on the engines."}
        if target:
            meta["expectedSequenceId"] = target
        fixtures.append({"name": f"{m['stem'][:5].lower()}-{name}", "events": vecs, "metadata": meta})
    return fixtures


def build_aggregator():
    prods = FIXTURE_PRODUCERS
    inputs = [f"{p['stem'][:5]}.{v}" for p in prods for v in VERDICTS]
    halts = [f"{p['stem'][:5]}.HALT_PROMOTION" for p in prods]
    revokes = [f"{p['stem'][:5]}.REVOKE_EPOCH" for p in prods]
    sequences, rules = [], []

    def ces(sid, preds, vec, rag, desc):
        sequences.append({"id": sid, "name": desc, "schemaVersion": "1.0",
                          "metadata": {"regularExpression": "[" + " ∧ ".join(f"{k}={v}" for k, v in preds.items()) + "]",
                                       "length": 1, "specRule": "SPECIFICATION.md 4.2 (17056..17059 monoids)"},
                          "events": [{"id": f"{sid}-e0", "isInitial": True,
                                      "elements": [element(preds.get(n)) for n in inputs], "nextEventIds": [],
                                      "outputEvents": [{"id": f"{sid}-out", "vector": vec}]}]})
        rules.append({"sequenceId": sid, "outputMatches": vec, "ragStatusCode": rag,
                      "processStatus": {"GREEN": "info", "RED": "error"}[rag], "description": desc})

    for p in prods:
        c = p["stem"][:5]
        ces(f"ces_gov00_halt_{c.lower()}", {f"{c}.HALT_PROMOTION": 1}, [1.0, 0.0, 0.0, 0.0], "RED", f"{c} halts promotion")
        ces(f"ces_gov00_revoke_{c.lower()}", {f"{c}.REVOKE_EPOCH": 1}, [0.0, 1.0, 0.0, 0.0], "RED", f"{c} revokes the epoch")
        ces(f"ces_gov00_incident_{c.lower()}", {f"{c}.TRIGGER_INCIDENT": 1}, [0.0, 0.0, 0.0, 1.0], "RED",
            f"{c} raises an incident")
        preds = {f"{c}.PERMIT_DEPLOY": 1, **{h: 0 for h in halts}, **{r: 0 for r in revokes}}
        ces(f"ces_gov00_permit_{c.lower()}", preds, [0.0, 0.0, 1.0, 0.0], "GREEN", f"{c} permits and no fixture halts or revokes")
    ces("ces_gov00_idle", {}, [0.0, 0.0, 0.0, 0.0], "GREEN", "nothing folds: the verdict clears (GOV-SA-23)")

    def fx(name, ones, purpose):
        v = [1.0 if n in ones else 0.0 for n in inputs]
        t = run(sequences, [v])
        return {"name": f"gov00-{name}", "events": [v], "metadata": {"expectedOutputVector": t[-1] or [0.0] * 4,
                "expectedOutputsByStep": [t[-1] or [0.0] * 4], "purpose": purpose,
                "expectedEvaluationScope": "Authoring evaluator; confirm 3-of-3."}}

    fixtures = [fx("permit-only", ["GOV06.PERMIT_DEPLOY"], "a permit with no halt or revoke permits"),
                fx("permit-vetoed", ["GOV06.PERMIT_DEPLOY", "GOV08.HALT_PROMOTION"], "any halt vetoes every permit"),
                fx("revoke-incident", ["GOV07.REVOKE_EPOCH", "GOV07.TRIGGER_INCIDENT"], "revoke and incident fold by max"),
                fx("nominal", [], "nothing asserted")]
    inp = {"offset": AGG_INPUT_START, "length": len(inputs)}
    outp = {"offset": AGG_INPUT_START + len(inputs), "length": 4}
    comp = [{"role": p["title"], "sourceMachine": f"{p['stem']}.json", "machineInputRegion": regions(p)[0],
             "machineOutputRegion": {"offset": regions(p)[1]["offset"], "length": 4},
             "composedInputElements": list(range(4 * k, 4 * k + 4)),
             "mapping": {f"activeOutput{i}": f"{p['code']} {v}" for i, v in enumerate(VERDICTS)}} for k, p in enumerate(prods)]
    return {"version": VERSION, "machine": {
        "id": "GOV00_governance-verdict-aggregator", "name": "GOV00_governance-verdict-aggregator",
        "description": "Folds the governance fixtures' verdicts onto the domain's four verdict elements: halt, revoke and incident by max; permit only while some fixture permits and none halts or revokes. Templates do not publish here: a clone leaves only by continuation or termination (GOV-R17).",
        "arbiterRule": "PASSTHROUGH", "matchAlgorithm": "equals", "outputMergeTransformation": "or",
        "perceptualMapping": {"input": inp, "output": outp, "bitsPerElement": 1},
        "sequences": sequences, "inputSequences": fixtures,
        "metadata": {"category": DOMAIN, "domain": DOMAIN, "machineClass": "bridge", "sequenceCount": len(sequences),
                     "inputSemantics": [f"{n}: composed by the PE from the fixture's verdict output" for n in inputs],
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
                                            "description": "Each governance fixture's four verdict elements, composed by the PE.",
                                            "inputRegion": inp, "outputRegion": outp, "inputComposition": comp},
                     "failSafeVector": {"HALT_PROMOTION": 1.0, "REVOKE_EPOCH": 1.0, "PERMIT_DEPLOY": 0.0,
                                        "TRIGGER_INCIDENT": 1.0},
                     "conversion": {"candidateVersion": CANDIDATE, "builder": "tools/build_machines.py"}}}}


# ---------------------------------------------------------------- manifests
WORKFLOWS = [
    ("W1", "Domain admission", "one frame per domain admission or renewal",
     ["GOV02", "GOV03", "GOV05", "GOV01", "GOV11"], "scripts/approve-domain.sh prepare / finalize",
     "approve-domain.sh admits only on the frame's closed, approved state", "an admission request (req_domain_admit) or a W7 renewal"),
    ("W2", "Rule-epoch promotion", "one frame per rule epoch",
     ["GOV05", "GOV04", "GOV11"], "scripts/approve-domain.sh deploy / domains/deployments",
     "a deployment proceeds only on the frame's promoted state and GOV06's quorum verdict", "an epoch-swap request (req_epoch_swap), a W3 near-miss rule draft, or a W6 ratification"),
    ("W3", "Runtime assurance", "no frame; watchdog fixtures GOV07, GOV08, GOV09, GOV16",
     [], "the live engines' exposure budget, latency and delegation",
     "GOV00 halts or revokes; agents advise, the delegation clamp acts after approval", "the fixtures' Sources"),
    ("W4", "Egress transparency", "one frame per outbound external message; GOV11 as the review step of every approving workflow",
     ["GOV10"], "the A2A/MCP boundary", "an unmarked external message is held", "an outbound message (req_egress)"),
    ("W5", "Incident and audit", "an incident frame; an audit-pack frame per release or audit",
     ["GOV12", "GOV13", "GOV11"], "Art. 73 notices; cut-release.sh and release-manifest.py",
     "a release is cut only with a sealed evidence pack", "GOV00 TRIGGER_INCIDENT, a release, or an audit request"),
    ("W6", "Hardening", "an emergency frame; a key-rotation frame",
     ["GOV15", "GOV17", "GOV11"], "emergency deployments; approval-quorum keys",
     "an emergency epoch lives only for its lease unless W2 ratifies it", "a break-glass request; a keyring revocation (the CRL Source)"),
    ("W7", "Recertification", "opens a W1 renewal frame", [], "every admitted domain's annual recertification",
     "an expired domain's epoch is revoked until re-admitted", "GOV14's renewal window"),
]


def workflow_contract():
    by_code = {m["stem"][:5]: m for m in MACHINES}
    out = []
    for wid, title, frame, steps, governs, gate, opened_by in WORKFLOWS:
        agents = sorted({m["agent"]["id"] for m in MACHINES if m.get("agent") and wid in m["workflow"].split(",")})
        out.append({"id": wid, "title": title, "frame": frame, "openedBy": opened_by,
                    "steps": [{"template": f"{by_code[s]['stem']}.json", "agent": by_code[s]["agent"]["id"],
                               "humanStep": by_code[s]["agent"]["mode"] != "advise"} for s in steps],
                    "fixtures": [f"{m['stem']}.json" for m in MACHINES if m["kind"] == "fixture" and wid in m["workflow"].split(",")],
                    "agents": agents, "governs": governs, "gate": gate})
    return {"schemaVersion": "1.0.0", "domain": DOMAIN, "candidateVersion": CANDIDATE,
            "scope": "Every workflow and Source in v1 (owner, 2026-11-21; scope-decisions.json GOV-SD-07).",
            "rules": ["Agents prepare; distinct humans approve (T15).",
                      "A template's result leaves its clone only through the frame's continuation or the agent's completion.",
                      "Each agent is a runtime-neutral behavior (schemas/agent-behavior.schema.json); runtimes render it.",
                      "The integration hooks into approve-domain.sh, deployments and cut-release.sh are changes to those repositories, for the owner to approve."],
            "workflows": out}


# ---------------------------------------------------------------- simulated Sources (GOV-SD-16)
def sample(pattern, frequency, amplitude, dc_offset, t):
    """A simulated Source's sample at t = globalStep (SURFACE_SPEC "Simulated source: the sample")."""
    period = 1.0 / frequency if frequency > 0 else 1.0
    phase = math.fmod(t / period, 1.0)
    if pattern == "constant":
        return dc_offset
    if pattern == "binary":
        return 1.0 if phase < 0.5 else 0.0
    if pattern == "square":
        return dc_offset + amplitude * (1.0 if phase < 0.5 else -1.0)
    raise ValueError(pattern)


def fit_source(seq):
    """The deterministic waveform that reproduces one cell's values at t = 0..n-1 exactly.

    constant; binary (1 for k steps, then 0); or square between two levels a and b
    (dcOffset (a+b)/2, amplitude (a-b)/2: a for k steps, then b). For 0/1 cells the
    square is exact (0.5 +- 0.5), which the `equals` comparator needs; a continuous
    level is reproduced to within 1e-9, and the caller checks the machine behaves alike.
    """
    if all(v == seq[0] for v in seq):
        return ("constant", 1.0, 0.0, seq[0])
    a = seq[0]
    b = next(v for v in seq if v != a)
    if any(v not in (a, b) for v in seq):
        raise SystemExit(f"no deterministic simulated Source reproduces {seq}: more than two levels")

    def matches(f):
        return any(all(abs(sample(*spec, t) - v) < 1e-9 for t, v in enumerate(seq))
                   for spec in (("binary", f, 0.0, 0.0), ("square", f, (a - b) / 2, (a + b) / 2)))

    def spec_for(f):
        binary = ("binary", f, 0.0, 0.0)
        if all(abs(sample(*binary, t) - v) < 1e-9 for t, v in enumerate(seq)):
            return binary
        return ("square", f, (a - b) / 2, (a + b) / 2)

    # Integer half-periods first: a for k steps, then b.
    for k in range(1, len(seq) + 1):
        if matches(1.0 / (2 * k)):
            return spec_for(1.0 / (2 * k))
    # Then f = i/100, where the a/b runs need not be equal (e.g. 0.8: a, b, b). Only
    # frequencies whose every sampled phase sits 0.05 clear of the 0.5 threshold and of
    # a wrap are taken, so the level is exact under floating point on every engine.
    for i in range(1, 100):
        phases = [(t * i) % 100 for t in range(1, len(seq))]
        if all(5 <= ph <= 45 or 55 <= ph <= 95 for ph in phases) and matches(i / 100):
            return spec_for(i / 100)
    raise SystemExit(f"no deterministic simulated Source reproduces {seq}")


def simulations(built):
    """One simulation per fixture: a simulated Source per input cell, through the ISRE.

    Every governance input is a simulated Source until its producer exists (GOV-SD-16).
    The fixtures are machine-granularity; each becomes a simulation whose Sources
    reproduce its input vectors exactly, checked here, with the latched expected
    outputs. The GOV-SA-06 feedback cell has no Source: the engine feeds it from the
    machine's own latched output.
    """
    out = []
    for doc in built:
        m = doc["machine"]
        code = m["name"][:5].lower()
        inp = m["perceptualMapping"]["input"]
        sem = m["metadata"].get("inputSemantics", [])
        labels = [x.split(" ", 1)[0] for x in sem]
        fb = m["metadata"].get("latchFeedback")
        skip = fb["inputElement"] if fb else None
        args = (fb["inputElement"], fb["fromOutputElement"]) if fb else ()
        for f in m.get("inputSequences", []):
            cols = list(zip(*f["events"]))
            sources = []
            for i, col in enumerate(cols):
                if i == skip:
                    continue
                pattern, freq, amp, dc = fit_source(list(col))
                signal = labels[i] if i < len(labels) else f"element{i}"
                sources.append({"type": "simulated", "id": f"gov-sim-{f['name']}-{i}",
                                "name": f"{signal} ({f['name']})",
                                "region": {"offset": inp["offset"] + i, "length": 1},
                                "pattern": pattern, "frequency": freq, "amplitude": amp, "dcOffset": dc})
            composed = []
            for t in range(len(f["events"])):
                v = [0.0] * inp["length"]
                for src in sources:
                    v[src["region"]["offset"] - inp["offset"]] = sample(
                        src["pattern"], src["frequency"], src["amplitude"], src["dcOffset"], t)
                if skip is not None:
                    v[skip] = f["events"][t][skip]
                composed.append(v)
            trace = run(m["sequences"], composed, *args)
            if trace != run(m["sequences"], f["events"], *args):
                raise SystemExit(f"{m['name']}: simulation {f['name']} does not behave as its fixture")
            width = m["perceptualMapping"]["output"]["length"]
            out.append({"name": f["name"], "machine": m["name"], "steps": len(f["events"]),
                        "purpose": f["metadata"].get("purpose"), "sources": sources,
                        "feedbackCell": (inp["offset"] + skip) if skip is not None else None,
                        "expectedOutputsByStep": [t or [0.0] * width for t in trace]})
    return out


def sources_manifest(built=()):
    uses = {}
    for m in MACHINES:
        names, _ = layout(m)
        inp, _ = regions(m)
        for i, n in enumerate(names):
            if n in dict(m["completion"]) or n == "spare":
                continue
            uses.setdefault(n, []).append({"machine": m["stem"], "inputElement": i, "cell": inp["offset"] + i})
    sigs = []
    for n, (k, delivery, producer, status, meaning) in SIGNALS.items():
        if n not in uses:
            continue
        sig = {"signal": n, "kind": "binary" if k == "b" else "continuous", "delivery": delivery,
               "producer": producer, "status": status, "meaning": meaning, "consumers": uses[n]}
        if n in PRODUCER_DOMAIN:
            sig["producerDomain"] = PRODUCER_DOMAIN[n]
        sigs.append(sig)
    comps = [{"sensorId": sensor_id(m), "agent": m["agent"]["id"], "machine": m["stem"],
              "provider": write_back(m)["provider"], "region": write_back(m)["region"],
              "fields": [f for f, _ in m["completion"]], "status": "new"} for m in MACHINES if m.get("agent")]
    sims = simulations(built)
    return {"schemaVersion": "1.0.0", "domain": DOMAIN, "candidateVersion": CANDIDATE,
            "scope": "Every Source in v1 (GOV-SD-07). status: exists / partial / new for the producer as of 2026-11-21.",
            "counts": {"signals": len(sigs), "exists": sum(s["status"] == "exists" for s in sigs),
                       "partial": sum(s["status"] == "partial" for s in sigs),
                       "new": sum(s["status"] == "new" for s in sigs), "completionSources": len(comps),
                       "simulations": len(sims)},
            "simulationRule": ("GOV-SD-16: until its producer exists, every input is a SURFACE_SPEC simulated Source "
                               "through the ISRE, one per input cell, deterministic in globalStep (constant, binary, "
                               "square). Drive: reset RE and PE, create the simulation's sources, push `steps` times; "
                               "the machine's output region after each push is expectedOutputsByStep (outputs are "
                               "latched, GOV-SD-19). The feedbackCell has no Source: the engine feeds it."),
            "signals": sigs, "completionSources": comps, "simulations": sims}


def render(doc):
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def outputs():
    built = [build_machine(m) for m in MACHINES]
    agg = build_aggregator()
    files = {OUT / f"{m['stem']}.json": render(b) for m, b in zip(MACHINES, built)}
    files[OUT / "GOV00_governance-verdict-aggregator.json"] = render(agg)
    for m in MACHINES:
        if m.get("agent"):
            files[AGENTS / f"{m['agent']['id']}.agent.json"] = render(behavior(m))
    files[PKG / "governance-sources.json"] = render(sources_manifest([agg] + built))
    files[PKG / "agentic-workflow-contract.json"] = render(workflow_contract())
    return files


def main():
    ap = argparse.ArgumentParser(description="Build the ai-governance-regime candidates.")
    ap.add_argument("--check", action="store_true", help="fail if a written file differs from a fresh build")
    args = ap.parse_args()
    files = outputs()
    managed = {OUT: set(), AGENTS: set()}
    for p in files:
        if p.parent in managed:
            managed[p.parent].add(p.name)
    if args.check:
        stale = [p for p, t in files.items() if not p.is_file() or p.read_text() != t]
        extra = [p for d, keep in managed.items() if d.is_dir() for p in d.glob("*.json") if p.name not in keep]
        for p in stale + extra:
            print(f"stale: {p.relative_to(PKG)}")
        print("build: up to date" if not (stale or extra) else "build: run tools/build_machines.py")
        return 1 if stale or extra else 0
    for d, keep in managed.items():
        d.mkdir(parents=True, exist_ok=True)
        for p in d.glob("*.json"):
            if p.name not in keep:
                p.unlink()
    for p, t in files.items():
        p.write_text(t)
    print(f"wrote {sum(1 for p in files if p.parent == OUT)} machines, "
          f"{sum(1 for p in files if p.parent == AGENTS)} agent behaviors, 2 manifests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
