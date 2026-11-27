# Conservative synthetic OT risk assessment

The [draft policy](generic-risk-policy.json), [assessment input](risk-assessment-fixture.json), [proposal bridge](risk-proposal-bridge.json) and [evaluator](../tools/assess_risk.mjs) add a bounded EI07/EI10 prerequisite. They replay selected evidence-quality, freshness, mapping and context conditions without treating a model assessment or transport security as operating authority. Assets retain the owner-selected ASHRAE 201/FSGIM reference projection and existing OPC UA DI source type facets. No normative model equivalence or independent security review is asserted.

## Evidence and posture boundaries

The existing [synthetic closed STIX bundle](synthetic-threat-fixture.json) is source-hash bound and checked against the already pinned licensed, explicitly non-normative schema implementation. It contains an infrastructure object, a vulnerability object and a generic `related-to` relationship. That relationship is used only to validate the declared references; the assessment does not infer exploitability, a real CVE, KEV/VEX status or asset safety from it. Infrastructure-to-reference-asset mapping and applicability are separate **synthetic assertions**, not equipment identity or applicability proof.

The only output postures are UNKNOWN and BLOCKED. A fresh explicit AFFECTED assertion with usable synthetic source/context can hold discretionary proposals as BLOCKED. Unresolved or unqualified NOT_AFFECTED assertions, absent findings, incomplete/empty feeds, bad/unknown/stale evidence and unavailable/revoked source objects never establish clearance. A supplied prior BLOCKED posture stays BLOCKED until a separate review mechanism exists; the utility has no unblock or risk-acceptance API. This is conservative qualitative treatment, not a calibrated likelihood/impact score or confirmation that a component is compromised.

Feed receipt, finding observation/receipt and evaluation order are checked with whole-second/millisecond UTC precision. The 2 s feed/finding thresholds are arbitrary generic fixture assumptions marked NOT_SECURITY_APPROVED, not approved incident response horizons. Freshness uses observation age for findings. Complete-feed metadata alone is not coverage or absence-of-threat proof. Objects modified after evaluation or marked revoked cannot support a current affected classification; their loss never clears a supplied prior block.

Topology, credential, firmware, policy, model, RAG and electrical-mode revision labels are carried explicitly. A change triggers reassessment and makes previous-context findings unusable. These labels and the prior posture are caller-supplied synthetic state, not authenticated inventory or a persistent incident latch. The current scope supports REF01 context modes only. All 20 scenario risks in the main risk register still require their complete prevention/detection/treatment/fallback review; this utility exercises selected freshness/mapping/revision conditions, not full risk coverage.

## Proposal composition and independent protection

The bridge reads a hash-bound assessment and the existing [generic storage proposal template](proposal-screen.md). Only synthetic clock fields may differ from that template; projection, topology and electrical mode must match. It applies only a stricter risk disposition, leaving the proposal, mode, PCC, protection state and all other state fields unchanged. No source file is mutated.

The default example is algebraically eligible before composition. The unresolved STIX applicability produces UNKNOWN, and the proposal screen then rejects further simulation with `RISK_NOT_CLEAR` and null calculations. Even the original algebraic result never granted operating approval. The bridge's treatment is a hold on discretionary proposals only: it does not disconnect equipment, suppress protection, invoke a course of action or execute an incident response. Unchanged synthetic protection fields are not evidence that physical independent protection actually continued to operate.

No model text is executed or promoted to policy. Descriptions and object names remain data; direct clearance overrides, invented reviewed evidence, policy clearance enablement and control/approval claims are rejected. Policy state fixes clearanceSupported=false, residualRiskAccepted=false, operatingAuthorityGranted=false and control DENY. This cannot substitute for actual feed provenance, qualified applicability analysis, authenticated human risk authority or native control gating.

## Reproduction and acceptance limits

```bash
python3 tools/build_risk_assessment.py --write
python3 tools/build_risk_assessment.py
node tools/assess_risk.mjs assets/risk-assessment-fixture.json
node tools/assess_risk.mjs assets/risk-proposal-bridge.json
node --test tools/test_risk_assessment.mjs
```

PASS means the synthetic contract evaluated; inspect posture, evidence reasons and the proposal's eligibility flags. Tests cover unresolved/affected/unqualified findings, stale/missing/revoked/future evidence, exact freshness boundaries, context changes, supplied block retention, identity/type mismatches, instruction-like text, policy tampering and unchanged protection/proposal input during composition. Structural/provenance errors throw before success. The software is an offline evaluator, not a network service or risk-assessment daemon.

Actual TAXII/KEV/VEX ingestion and provenance, identity/applicability qualification, threat coverage, calibrated risk review, incident escalation/clearance, durable state and signed decision receipts, principal/delegation enforcement, native protection/control behavior and adversarial model acceptance remain pending. There is no new network/runtime link. Security/engineering review is pending, all 43 behavioral cases remain NOT_RUN and corpus admission NOT_PERFORMED. Required hardware stays simulated and generic/template assets remain permitted in every case.
