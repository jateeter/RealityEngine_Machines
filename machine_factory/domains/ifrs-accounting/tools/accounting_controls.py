"""Narrow deterministic controls for explicit, evidenced accounting facts.

Advisory determinations only. Source applicability, facts and output require
independent review. This is not a general IFRS accounting engine. Monetary
arithmetic is decimal and never enters the nominal token lane.
"""
from decimal import Decimal, InvalidOperation


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


def determine(control, facts):
    if not facts.get("evidenceRefs"):
        return {"status": "UNRESOLVED", "reason": "Missing evidence references"}
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
    if any(row.get("side") not in {"debit", "credit"} or not row.get("evidenceRefs") for row in rows):
        raise ValueError("Each balance requires side and evidence")
    debits = sum((amount(row) for row in rows if row["side"] == "debit"), Decimal("0"))
    credits = sum((amount(row) for row in rows if row["side"] == "credit"), Decimal("0"))
    return {"status": "BALANCED" if debits == credits else "UNRESOLVED_IMBALANCE", "debits": format(debits, "f"), "credits": format(credits, "f"), "difference": format(debits-credits, "f"), "currency": next(iter(currencies)), "asOf": next(iter(dates)), "postingPerformed": False}
