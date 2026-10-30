"""Narrow deterministic controls for explicit, evidenced accounting facts.

Advisory determinations only. Source applicability, facts and output require
independent review. This is not a general IFRS accounting engine. Monetary
arithmetic is decimal and never enters the nominal token lane.
"""
from decimal import Decimal, InvalidOperation
from datetime import date
import json
from pathlib import Path


# One authoritative source-scope map for server and live verifier. Legacy names
# never override this mapping or select a source edition from caller text.
SOURCE_SECTIONS = {
    "trial-balance": "03", "section-1-eligibility": "01", "section-23-contract-cost": "23",
    "version-3-period-applicability": "A", "section-2-recognition-screen": "02", "section-2-substance-screen": "02",
    "section-1-fiduciary-screen": "01", "section-2-undue-cost-screen": "02", "section-12-bid-ask-screen": "12",
    "section-18-useful-life-screen": "18", "section-19-goodwill-life-screen": "19", "section-28-actuarial-policy-screen": "28",
    "section-3-compliance-evidence-screen": "03", "section-20-classification-screen": "20", "section-20-finance-initial-measurement": "20",
    "section-8-policy-materiality-screen": "08", "section-8-supplemental-capital-screen": "08",
    "section-29-pillar-two-screen": "29", "section-15-commitments-screen": "15", "section-23-allocation-basis-screen": "23",
}


def reference_mapping(facts):
    data = json.loads((Path(__file__).resolve().parents[1] / "source-reference-map.json").read_text())
    return next((m for m in data["machines"] if m["machineId"] == facts.get("machineId")), None)


def source_section(control, facts):
    if control == "source-reference-screen":
        mapping = reference_mapping(facts)
        return mapping["semanticSection"] if mapping else None
    return SOURCE_SECTIONS.get(control)


def amount(record):
    if not isinstance(record, dict) or not isinstance(record.get("amount"), str) or not record.get("currency") or not record.get("asOf"):
        raise ValueError("Typed monetary record required")
    try:
        value = Decimal(record["amount"])
    except InvalidOperation as exc:
        raise ValueError("Invalid decimal") from exc
    if not value.is_finite() or value < 0:
        raise ValueError("Finite nonnegative monetary amount required")
    return value


def valid_evidence_refs(refs):
    """Reference shape only; the connector verifies provenance."""
    return isinstance(refs, list) and bool(refs) and all(
        isinstance(ref, str) and bool(ref.strip()) for ref in refs
    )


def determine(control, facts):
    if not isinstance(facts, dict) or not valid_evidence_refs(facts.get("evidenceRefs")):
        return {"status": "UNRESOLVED", "reason": "Missing evidence references"}
    if control == "version-3-period-applicability":
        if facts.get("edition") != "IFRS_FOR_SMES_2025_THIRD_EDITION" or facts.get("annualPeriod") is not True:
            return {"status": "UNRESOLVED", "reason": "Third edition and annual reporting period must be explicit"}
        try:
            start = date.fromisoformat(facts["periodStart"])
            end = date.fromisoformat(facts["periodEnd"])
            if start > end:
                raise ValueError("Reversed reporting period")
        except (KeyError, TypeError, ValueError):
            return {"status": "UNRESOLVED", "reason": "Valid reporting period dates required"}
        if start < date(2027, 1, 1):
            if type(facts.get("earlyApplication")) is not bool or type(facts.get("earlyApplicationDisclosed")) is not bool:
                return {"status": "UNRESOLVED", "reason": "Early application election and disclosure evidence required"}
            decision = "EARLY_APPLICATION_SUBJECT_TO_REVIEW" if facts["earlyApplication"] and facts["earlyApplicationDisclosed"] else "THIRD_EDITION_APPLICATION_NOT_ESTABLISHED"
        else:
            decision = "EFFECTIVE_PERIOD_SUBJECT_TO_REVIEW"
        return {"status": "ADVISORY", "decision": decision, "sourceControl": "A1", "reviewRequired": True,
                "scope": "Effective date only; transition, eligibility and full compliance remain separate"}
    if control == "section-2-recognition-screen":
        if facts.get("element") not in {"asset", "liability"}:
            return {"status": "UNRESOLVED", "reason": "This screen covers assets and liabilities only"}
        if type(facts.get("specificSectionApplies")) is not bool:
            return {"status": "UNRESOLVED", "reason": "Specific-section applicability assessment required"}
        if facts["specificSectionApplies"]:
            return {"status": "UNRESOLVED", "reason": "Apply the identified specific-section requirements before a recognition determination", "sourceControl": "2.2"}
        keys = ["definitionMet", "relevantInformation", "faithfulRepresentation", "uncertaintyAssessed"]
        if any(type(facts.get(k)) is not bool for k in keys):
            return {"status": "UNRESOLVED", "reason": "Definition, relevance, representation and uncertainty judgments required"}
        if not facts["uncertaintyAssessed"]:
            return {"status": "UNRESOLVED", "reason": "Assess existence and measurement uncertainty; uncertainty alone is not an automatic prohibition"}
        decision = "GENERAL_RECOGNITION_SCREEN_PASSED_SUBJECT_TO_REVIEW" if all(facts[k] for k in keys) else "GENERAL_RECOGNITION_SCREEN_NOT_PASSED"
        return {"status": "ADVISORY", "decision": decision, "sourceControl": "2.2; 2.68–2.73", "reviewRequired": True, "postingPerformed": False}
    if control == "section-2-substance-screen":
        keys = ["legalFormDiffersFromSubstance", "substanceRepresented", "faithfulRepresentationAssessed"]
        if any(type(facts.get(k)) is not bool for k in keys):
            return {"status": "UNRESOLVED", "reason": "Substance and representation evidence required"}
        if not facts["faithfulRepresentationAssessed"] or not facts["substanceRepresented"]:
            return {"status": "UNRESOLVED", "reason": "Resolve economic-substance representation; legal form alone is insufficient", "sourceControl": "2.14–2.18"}
        return {"status": "ADVISORY", "decision": "SUBSTANCE_SCREEN_PASSED_SUBJECT_TO_REVIEW", "sourceControl": "2.14–2.18", "reviewRequired": True}
    if control == "section-1-fiduciary-screen":
        keys = ["holdsFiduciaryAssets", "broadGroupOfOutsiders", "primaryBusiness", "incidentalToPrimaryBusiness"]
        if any(type(facts.get(k)) is not bool for k in keys):
            return {"status": "UNRESOLVED", "reason": "Business purpose and outsider facts required; amount is not the criterion"}
        if facts["primaryBusiness"] and facts["incidentalToPrimaryBusiness"]:
            return {"status": "UNRESOLVED", "reason": "Contradictory primary/incidental assessment"}
        if facts["holdsFiduciaryAssets"] and facts["broadGroupOfOutsiders"]:
            if facts["primaryBusiness"]:
                decision = "FIDUCIARY_PUBLIC_ACCOUNTABILITY_CRITERION_MET"
            elif facts["incidentalToPrimaryBusiness"]:
                decision = "INCIDENTAL_ACTIVITY_DOES_NOT_ESTABLISH_PUBLIC_ACCOUNTABILITY"
            else:
                return {"status": "UNRESOLVED", "reason": "Primary-versus-incidental business assessment incomplete"}
        else:
            decision = "FIDUCIARY_PUBLIC_ACCOUNTABILITY_CRITERION_NOT_MET"
        return {"status": "ADVISORY", "decision": decision, "sourceControl": "1.3(b)–1.4", "reviewRequired": True,
                "scope": "Fiduciary criterion only; public-market status and full eligibility assessed separately"}
    if control == "section-2-undue-cost-screen":
        if type(facts.get("expressReliefApplies")) is not bool:
            return {"status": "UNRESOLVED", "reason": "Identify an express exemption and its applicability"}
        if not facts["expressReliefApplies"]:
            return {"status": "ADVISORY", "decision": "RELIEF_NOT_AVAILABLE", "sourceControl": "2.28–2.31", "reviewRequired": True}
        if facts.get("reliefParagraph") == "19.16":
            return {"status": "UNRESOLVED", "reason": "Assess the specific 19.16 relief and 19.38 disclosure route separately"}
        for key in ["reliefParagraph", "entitySpecificRationale", "userBenefitAssessment", "judgmentDate", "assessmentDate"]:
            if not isinstance(facts.get(key), str) or not facts[key].strip():
                return {"status": "UNRESOLVED", "reason": "Dated entity-specific cost/effort and user-benefit judgments required"}
        try:
            dated = date.fromisoformat(facts["judgmentDate"]) == date.fromisoformat(facts["assessmentDate"])
        except ValueError:
            dated = False
        keys = ["incrementalCostEffortSubstantiallyExceedsBenefits", "disclosureFactAndReasonsProvided"]
        if not dated or any(type(facts.get(k)) is not bool for k in keys):
            return {"status": "UNRESOLVED", "reason": "Fresh assessment and explicit judgment/disclosure evidence required"}
        if not facts["incrementalCostEffortSubstantiallyExceedsBenefits"]:
            decision = "RELIEF_NOT_JUSTIFIED"
        elif not facts["disclosureFactAndReasonsProvided"]:
            return {"status": "UNRESOLVED", "reason": "Disclose relief use and reasons"}
        else:
            decision = "RELIEF_SCREEN_PASSED_SUBJECT_TO_SPECIFIC_PARAGRAPH_REVIEW"
        return {"status": "ADVISORY", "decision": decision, "sourceControl": "2.28–2.31", "reviewRequired": True}
    if control in {"section-18-useful-life-screen", "section-19-goodwill-life-screen"}:
        if type(facts.get("lifeReliablyEstablished")) is not bool:
            return {"status": "UNRESOLVED", "reason": "Reliability judgment required"}
        raw = facts.get("estimatedYears")
        if not isinstance(raw, str):
            return {"status": "UNRESOLVED", "reason": "Explicit finite management estimate required; never default to ten"}
        try:
            years = Decimal(raw)
        except InvalidOperation:
            return {"status": "UNRESOLVED", "reason": "Invalid useful-life estimate"}
        if not years.is_finite() or years <= 0:
            return {"status": "UNRESOLVED", "reason": "Finite positive useful-life estimate required"}
        decision = "FINITE_LIFE_SCREEN_PASSED_SUBJECT_TO_REVIEW" if facts["lifeReliablyEstablished"] or years <= 10 else "UNRELIABLE_LIFE_ESTIMATE_EXCEEDS_TEN_YEAR_CAP"
        return {"status": "ADVISORY", "decision": decision, "estimatedYears": format(years, "f"), "reviewRequired": True,
                "sourceControl": "18.19–18.20" if control.startswith("section-18") else "19.34; 18.19–18.24",
                "scope": "Useful-life rule only; legal/contractual limits, amortisation and impairment assessed separately"}
    if control == "section-28-actuarial-policy-screen":
        if facts.get("policy") not in {"PROFIT_OR_LOSS", "OCI"}:
            return {"status": "UNRESOLVED", "reason": "Document an explicit permitted actuarial policy election"}
        if facts.get("appliedToAllPlansAndGainsLosses") is not True or facts.get("recognisedInPeriodOfOccurrence") is not True:
            return {"status": "UNRESOLVED", "reason": "Current-period recognition and consistent all-plan application required"}
        return {"status": "ADVISORY", "decision": "ACTUARIAL_" + facts["policy"] + "_POLICY_SCREEN_PASSED", "sourceControl": "28.24", "reviewRequired": True}
    if control == "section-12-bid-ask-screen":
        try:
            records = [facts[k] for k in ["bid", "ask", "selectedPrice"]]
            values = [amount(r) for r in records]
        except (KeyError, TypeError, ValueError):
            return {"status": "UNRESOLVED", "reason": "Typed bid, ask and selected-price records required"}
        if len({r["currency"] for r in records}) != 1 or len({r["asOf"] for r in records}) != 1 or values[0] > values[1]:
            return {"status": "UNRESOLVED", "reason": "Consistent quote currency/date and ordered spread required"}
        if not values[0] <= values[2] <= values[1]:
            return {"status": "ADVISORY", "decision": "PRICE_OUTSIDE_SPREAD", "sourceControl": "12.17", "reviewRequired": True}
        if facts.get("mostRepresentativeJudgment") is not True or not isinstance(facts.get("pricingRationale"), str) or not facts["pricingRationale"].strip():
            return {"status": "UNRESOLVED", "reason": "Representative-price judgment required; bid/ask is permitted, not mandatory"}
        return {"status": "ADVISORY", "decision": "REPRESENTATIVE_PRICE_SCREEN_PASSED", "amount": format(values[2], "f"), "currency": records[2]["currency"], "asOf": records[2]["asOf"], "sourceControl": "12.17", "reviewRequired": True}
    if control == "section-3-compliance-evidence-screen":
        return {"status": "UNRESOLVED", "reason": "Canonical approved workflow records must be evaluated by the authenticated service, never caller-supplied statuses"}
    if control == "section-20-classification-screen":
        if facts.get("inceptionAssessmentComplete") is not True or not isinstance(facts.get("risksRewardsRationale"), str) or not facts["risksRewardsRationale"].strip():
            return {"status": "UNRESOLVED", "reason": "Inception assessment of substance, indicators and countervailing features required"}
        if type(facts.get("substantiallyAllRisksRewardsTransferred")) is not bool or facts.get("indicatorsAndCountervailingFeaturesAssessed") is not True:
            return {"status": "UNRESOLVED", "reason": "Qualitative risks/rewards judgment required; 75% and 90% are not mandated cutoffs"}
        return {"status": "ADVISORY", "decision": "FINANCE_LEASE" if facts["substantiallyAllRisksRewardsTransferred"] else "OPERATING_LEASE",
                "sourceControl": "20.4–20.8", "reviewRequired": True, "scope": "Classification screen of explicit evidenced judgments, not inference from ratios"}
    if control == "section-20-finance-initial-measurement":
        if facts.get("partyRole") != "LESSEE" or facts.get("classification") != "FINANCE" or not isinstance(facts.get("classificationReviewRef"), str) or facts["classificationReviewRef"] not in facts["evidenceRefs"]:
            return {"status": "UNRESOLVED", "reason": "Evidenced finance-lease lessee classification required; operating leases use their separate model"}
        if type(facts.get("implicitRateDetermined")) is not bool:
            return {"status": "UNRESOLVED", "reason": "Discount-rate evidence required"}
        basis = "IMPLICIT" if facts["implicitRateDetermined"] else "INCREMENTAL_BORROWING"
        if facts.get("discountRateBasis") != basis or facts.get("qualifyingInitialDirectCostsAssessed") is not True:
            return {"status": "UNRESOLVED", "reason": "Use implicit rate when determinable, otherwise incremental borrowing rate; qualify direct costs"}
        try:
            fv, pv, costs = [facts[k] for k in ["fairValue", "minimumPaymentsPV", "initialDirectCosts"]]
            f, v, c = [amount(x) for x in [fv, pv, costs]]
            inception, commencement = date.fromisoformat(facts["inceptionDate"]), date.fromisoformat(facts["commencementDate"])
            if inception > commencement or fv["asOf"] != facts["inceptionDate"] or pv["asOf"] != facts["inceptionDate"] or costs["asOf"] != facts["commencementDate"] or len({x["currency"] for x in [fv, pv, costs]}) != 1:
                raise ValueError("Measurement date/currency mismatch")
        except (KeyError, TypeError, ValueError):
            return {"status": "UNRESOLVED", "reason": "Consistent typed inception values and commencement direct costs required"}
        base = min(f, v)
        return {"status": "ADVISORY", "decision": "FINANCE_INITIAL_MEASUREMENT_SUBJECT_TO_REVIEW", "asset": format(base+c, "f"), "liability": format(base, "f"), "currency": fv["currency"],
                "asOf": facts["commencementDate"], "sourceControl": "20.9–20.10", "reviewRequired": True, "postingPerformed": False,
                "scope": "Supplied independently evidenced PV, not a cash-flow discounting engine; subsequent measurement and other-section adjustments assessed separately"}
    if control == "source-reference-screen":
        mapping = reference_mapping(facts)
        if not mapping or facts.get("edition") != mapping["edition"]:
            return {"status": "UNRESOLVED", "reason": "Known machine and pinned third edition required"}
        refs = facts.get("claimedReferences")
        if not isinstance(facts.get("claimedSection"), str) or not isinstance(refs, list) or not refs or any(not isinstance(r, str) for r in refs):
            return {"status": "UNRESOLVED", "reason": "Explicit section and paragraph references required"}
        matches = facts["claimedSection"] == mapping["semanticSection"] and set(refs) == set(mapping["requiredReferences"])
        return {"status": "ADVISORY", "decision": "SOURCE_REFERENCE_MATCHES_PINNED_EDITION" if matches else "SOURCE_REFERENCE_MISMATCH",
                "sourceControl": "; ".join(mapping["requiredReferences"]), "semanticSection": mapping["semanticSection"], "reviewRequired": True,
                "scope": "Reference integrity only; does not determine derivative valuation or hedge eligibility/effectiveness"}
    if control == "section-8-policy-materiality-screen":
        if facts.get("consideredWithOtherStatementInformation") is not True or any(type(facts.get(k)) is not bool for k in ["couldInfluencePrimaryUserDecisions", "policyInformationDisclosed"]):
            return {"status": "UNRESOLVED", "reason": "Materiality judgment in the complete financial-statement context and disclosure evidence required"}
        decision = "NOT_REQUIRED_BY_8_5_SUBJECT_TO_OTHER_REQUIREMENTS"
        if facts["couldInfluencePrimaryUserDecisions"]:
            decision = "MATERIAL_POLICY_DISCLOSURE_SCREEN_PASSED" if facts["policyInformationDisclosed"] else "MATERIAL_POLICY_DISCLOSURE_MISSING"
        return {"status": "ADVISORY", "decision": decision, "sourceControl": "8.5", "reviewRequired": True}
    if control == "section-8-supplemental-capital-screen":
        if facts.get("treatAsMandatorySMESection8Coverage") is not False:
            return {"status": "UNRESOLVED", "reason": "No standalone Section 8 capital-management mandate identified; verify a specific basis before claiming mandatory coverage"}
        if facts.get("labelledEntitySupplemental") is not True or facts.get("materialityAndOtherDisclosureRequirementsAssessed") is not True:
            return {"status": "UNRESOLVED", "reason": "Label the supplemental control and separately assess applicable material information requirements"}
        return {"status": "ADVISORY", "decision": "SUPPLEMENTAL_NOT_STANDALONE_SECTION_8_MANDATE", "sourceControl": "Section 8 attribution boundary; 8.5 assessed separately",
                "authorityClass": "entity-supplemental", "reviewRequired": True}
    if control == "section-29-pillar-two-screen":
        if type(facts.get("withinScopeOfPillarTwoLegislation")) is not bool:
            return {"status": "UNRESOLVED", "reason": "Enacted/substantively enacted legislation and entity-scope assessment required"}
        if not facts["withinScopeOfPillarTwoLegislation"]:
            return {"status": "ADVISORY", "decision": "OUTSIDE_THIS_PILLAR_TWO_SCREEN", "sourceControl": "29.3A", "reviewRequired": True}
        keys = ["relatedDeferredTaxRecognised", "relatedDeferredTaxInformationDisclosed", "exceptionApplicationDisclosed", "relatedCurrentTaxSeparatelyDisclosed"]
        if any(type(facts.get(k)) is not bool for k in keys):
            return {"status": "UNRESOLVED", "reason": "Separate deferred-exception and current-tax disclosure evidence required"}
        passed = not facts[keys[0]] and not facts[keys[1]] and facts[keys[2]] and facts[keys[3]]
        return {"status": "ADVISORY", "decision": "PILLAR_TWO_EXCEPTION_AND_DISCLOSURES_SCREEN_PASSED" if passed else "PILLAR_TWO_EXCEPTION_OR_DISCLOSURE_GAP",
                "sourceControl": "29.3A; 29.42–29.43", "reviewRequired": True, "scope": "Pillar Two scope only; no tax computation or exemption for other income taxes"}
    if control == "section-15-commitments-screen":
        if type(facts.get("jointControlOfJointlyControlledEntity")) is not bool:
            return {"status": "UNRESOLVED", "reason": "Arrangement type and joint-control assessment required"}
        if not facts["jointControlOfJointlyControlledEntity"]:
            return {"status": "UNRESOLVED", "reason": "Assess the applicable other arrangement/investment model separately"}
        if any(type(facts.get(k)) is not bool for k in ["aggregateCommitmentsDisclosed", "includesShareOfJointCommitments"]):
            return {"status": "UNRESOLVED", "reason": "Aggregate commitments including jointly incurred share require disclosure evidence"}
        try:
            aggregate, share = facts["aggregateCommitments"], facts["jointCommitmentShare"]
            a, b = amount(aggregate), amount(share)
            if aggregate["currency"] != share["currency"] or aggregate["asOf"] != share["asOf"] or a < b:
                raise ValueError("Commitment scope mismatch")
        except (KeyError, TypeError, ValueError):
            return {"status": "UNRESOLVED", "reason": "Consistent aggregate/share commitments required"}
        passed = facts["aggregateCommitmentsDisclosed"] and facts["includesShareOfJointCommitments"]
        return {"status": "ADVISORY", "decision": "OPERATIVE_COMMITMENTS_DISCLOSURE_SCREEN_PASSED" if passed else "OPERATIVE_COMMITMENTS_DISCLOSURE_MISSING",
                "sourceControl": "15.19(d)", "reviewRequired": True, "sourceFidelityIssue": "Introduction summary does not erase the operative disclosure; independent source review required"}
    if control == "section-23-allocation-basis-screen":
        if facts.get("step4ScopeAssessed") is not True or facts.get("allocationExemptionApplies") is not False:
            return {"status": "UNRESOLVED", "reason": "Assess 23.40/23.41 exemptions and applicable series-variable requirements separately"}
        if facts.get("method") == "RELATIVE_SSP":
            if facts.get("contractStartSSPsSupported") is not True or facts.get("noSubsequentSSPReallocation") is not True or facts.get("relativeBasisRepresentsEntitlement") is not True:
                return {"status": "UNRESOLVED", "reason": "Supported contract-start SSPs, no subsequent SSP repricing and applicable entitlement assessment required"}
            decision = "RELATIVE_SSP_BASIS_SCREEN_PASSED"
        elif facts.get("method") == "ALTERNATIVE_DISCOUNT_VARIABLE":
            if facts.get("discountOrVariableAmount") is not True or facts.get("relativeBasisRepresentsEntitlement") is not False or facts.get("alternativeRepresentsEntitlement") is not True or not isinstance(facts.get("alternativeMethodRationale"), str) or not facts["alternativeMethodRationale"].strip():
                return {"status": "UNRESOLVED", "reason": "Alternative allocation requires supported discount/variable entitlement conditions under 23.47/23.48"}
            decision = "DISCOUNT_VARIABLE_ALTERNATIVE_SCREEN_PASSED"
        else:
            return {"status": "UNRESOLVED", "reason": "A legacy residual-approach label is not blanket authority for a full-IFRS residual SSP method"}
        return {"status": "ADVISORY", "decision": decision, "sourceControl": "23.42; 23.47–23.48", "reviewRequired": True, "scope": "Allocation-basis screen; no monetary allocation, revenue recognition or unsupported residual-method approval"}
    if control == "trial-balance":
        return {**reconcile_trial_balance(facts.get("rows")), "authorityClass": "supplemental-ledger-reconciliation", "reviewRequired": True}
    if control == "section-1-eligibility":
        keys = ["publicAccountability", "generalPurposeStatements", "jurisdictionPermits"]
        if any(type(facts.get(k)) is not bool for k in keys):
            return {"status": "UNRESOLVED", "reason": "Eligibility facts incomplete"}
        decision = "NOT_ELIGIBLE" if facts["publicAccountability"] or not facts["generalPurposeStatements"] or not facts["jurisdictionPermits"] else "ELIGIBLE_SUBJECT_TO_REVIEW"
        return {"status": "ADVISORY", "decision": decision, "sourceControl": "Section 1; publicly accountable entities cannot claim SME conformity even if local law permits"}
    if control == "section-23-contract-cost":
        money = facts.get("cost")
        value = amount(money)
        if facts.get("otherSectionApplies") is not False:
            return {"status": "UNRESOLVED", "reason": "Assess the applicable other section before applying this narrow control"}
        if facts.get("nature") == "obtaining":
            decision = "EXPENSE_WHEN_INCURRED"
            paragraph = "23.68"
        elif facts.get("nature") == "fulfilment":
            keys = ["directlyRelatedIdentifiableContract", "createsFutureResources", "recoveryExpected", "pastPerformance"]
            if any(type(facts.get(k)) is not bool for k in keys):
                return {"status": "UNRESOLVED", "reason": "Fulfilment conditions incomplete"}
            decision = "RECOGNISE_CONTRACT_COST_ASSET" if all(facts[k] for k in keys[:3]) and not facts["pastPerformance"] else "EXPENSE_WHEN_INCURRED"
            paragraph = "23.69–23.73"
        else:
            return {"status": "UNRESOLVED", "reason": "Cost nature unresolved"}
        return {"status": "ADVISORY", "decision": decision, "amount": format(value, "f"), "currency": money["currency"], "asOf": money["asOf"], "sourceControl": paragraph}
    return {"status": "UNRESOLVED", "reason": "Control not implemented; specialist review required"}


def reconcile_trial_balance(rows):
    if not rows:
        raise ValueError("Trial balance is missing")
    currencies = {row["currency"] for row in rows}
    dates = {row["asOf"] for row in rows}
    if len(currencies) != 1 or len(dates) != 1:
        raise ValueError("Separate currencies/dates before reconciliation")
    if any(row.get("side") not in {"debit", "credit"} or not valid_evidence_refs(row.get("evidenceRefs")) for row in rows):
        raise ValueError("Each balance requires side and evidence")
    debits = sum((amount(row) for row in rows if row["side"] == "debit"), Decimal("0"))
    credits = sum((amount(row) for row in rows if row["side"] == "credit"), Decimal("0"))
    return {"status": "BALANCED" if debits == credits else "UNRESOLVED_IMBALANCE", "debits": format(debits, "f"), "credits": format(credits, "f"), "difference": format(debits-credits, "f"), "currency": next(iter(currencies)), "asOf": next(iter(dates)), "postingPerformed": False}
