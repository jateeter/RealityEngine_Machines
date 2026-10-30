"""Narrow deterministic controls for explicit, evidenced accounting facts.

Advisory determinations only. Source applicability, facts and output require
independent review. This is not a general IFRS accounting engine. Monetary
arithmetic is decimal and never enters the nominal token lane.
"""
from decimal import Decimal, InvalidOperation
from datetime import date


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
