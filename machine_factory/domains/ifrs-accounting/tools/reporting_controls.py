"""Typed reporting draft producers; source/fact completeness needs independent review.

No posting, release, legal dividend authorization or currency conversion occurs.
All money is decimal-string data outside the native assertion lane.
"""
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
import re


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def refs(value):
    return isinstance(value, list) and bool(value) and all(isinstance(r, str) and r.strip() for r in value)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def day(value):
    require(isinstance(value, str), "Explicit ISO date required")
    return date.fromisoformat(value)


def money(record, evidence, signed=False):
    require(isinstance(record, dict) and isinstance(record.get("amount"), str) and text(record.get("currency")), "Typed money record required")
    require(len(record["amount"]) <= 128 and re.fullmatch(r"-?[0-9]+(?:\.[0-9]+)?", record["amount"]) is not None, "Ordinary decimal strings up to 128 characters required; no implicit exponent/rounding conversion")
    day(record.get("asOf"))
    require(refs(record.get("evidenceRefs")) and set(record["evidenceRefs"]) <= set(evidence), "Every monetary record needs scoped supporting evidence")
    try:
        value = Decimal(record["amount"])
    except InvalidOperation as exc:
        raise ValueError("Invalid decimal") from exc
    require(value.is_finite() and (signed or value >= 0), "Finite monetary value with supported sign required")
    return value


def monetary(value, currency, as_of, evidence):
    return dict(amount=format(value, "f"), currency=currency, asOf=as_of, evidenceRefs=evidence)


def collection(rows, evidence):
    return {"records": rows, "evidenceRefs": evidence} if rows else {"assessment": "EXPLICITLY_ASSESSED_NO_ITEMS", "evidenceRefs": evidence}


def period(facts):
    start, end = day(facts.get("periodStart")), day(facts.get("periodEnd"))
    require(start <= end and text(facts.get("period")), "Ordered reporting dates and period label required")
    return start, end


def dividend(f, evidence):
    start, end = period(f); authorisation = day(f.get("authorisedForIssueDate"))
    require(end <= authorisation and f.get("populationsAssessed") is True, "Assessed dividend populations and authorisation date required")
    rows = f.get("proposedOrDeclared")
    require(isinstance(rows, list), "Proposed/declared population must be explicit, including an assessed empty list")
    ids, qualifying, declared, proposed, recognised = set(), [], [], [], []
    currency = f.get("presentationCurrency")
    require(text(currency), "Presentation currency required")
    for row in rows:
        require(isinstance(row, dict) and text(row.get("dividendId")) and row["dividendId"] not in ids, "Unique dividend identifiers required")
        ids.add(row["dividendId"])
        event = day(row.get("eventDate"))
        require(row.get("kind") in {"PROPOSED", "DECLARED"} and type(row.get("recognisedAsDistributionInPeriod")) is bool, "Dividend kind and recognition assessment required")
        if row["recognisedAsDistributionInPeriod"]:
            require(row["kind"] == "DECLARED" and start <= event <= end, "Recognition-in-period claim contradicts dividend event kind/date")
        money(row.get("dividendAmount"), evidence); money(row.get("perShare"), evidence)
        require(row["dividendAmount"]["currency"] == row["perShare"]["currency"] == currency and row["dividendAmount"]["asOf"] == row["perShare"]["asOf"] == row["eventDate"] and row.get("perShareBasisSupported") is True, "Amount/per-share scope and basis must agree")
        (declared if row["kind"] == "DECLARED" else proposed).append(row)
        if row["recognisedAsDistributionInPeriod"]:
            recognised.append(row)
        elif event <= authorisation:
            qualifying.append(row)
    preference = f.get("unrecognisedCumulativePreference")
    money(preference, evidence)
    require(preference["currency"] == currency and preference["asOf"] == f["periodEnd"], "Cumulative preference amount at reporting date required; do not infer zero")
    note = dict(proposedOrDeclaredUnrecognised=collection(qualifying, evidence), unrecognisedCumulativePreference=preference)
    content = dict(declared=collection(declared, evidence), proposed=collection(proposed, evidence), recognised=collection(recognised, evidence),
                   unrecognised=collection(qualifying, evidence), cumulativePreference=preference,
                   perShare=collection([dict(dividendId=r["dividendId"], amountPerShare=r["perShare"]) for r in qualifying], evidence),
                   periods=dict(period=f["period"], start=f["periodStart"], end=f["periodEnd"], authorisedForIssue=f["authorisedForIssueDate"]), note=note)
    return dict(qualifyingDividendCount=len(qualifying), unrecognisedProposedDeclaredAmount=format(sum((Decimal(r["dividendAmount"]["amount"]) for r in qualifying), Decimal("0")), "f"), decision="DIVIDEND_NOTE_DRAFT_READY_FOR_REVIEW", sourceControl="6.6(a)–(b)", documentAssetTypeId="DIVIDEND-REGISTER", documentContent=content,
                scope="Disclosure producer only; legality/distributable reserves and recognition are separately assessed")


def financing(f, evidence):
    start, end = period(f)
    require(f.get("populationCompletenessAssessed") is True and f.get("liabilitiesAriseFromFinancing") is True and text(f.get("classificationRationale")), "Assessed financing-liability population and classification evidence required")
    opening, closing = f.get("opening"), f.get("closing")
    first, last = money(opening, evidence), money(closing, evidence)
    currency = opening["currency"]
    require(opening["asOf"] == f["periodStart"] and closing["asOf"] == f["periodEnd"] and closing["currency"] == currency, "Opening/closing dates and currency must match the reporting period")
    keys = ["cash", "acquisitions", "fx", "fairValue", "other"]
    moves = f.get("movements")
    require(isinstance(moves, dict) and set(moves) == set(keys) and f.get("allMovementCategoriesAssessed") is True, "All five movement categories must be explicitly assessed")
    totals, views = {}, {}
    for key in keys:
        require(isinstance(moves[key], list), "Movement category must be an explicit list")
        total = Decimal("0")
        for row in moves[key]:
            total += money(row, evidence, signed=True)
            require(row["currency"] == currency and start <= day(row["asOf"]) <= end and text(row.get("description")), "Scoped dated movement and description required")
        totals[key] = total
        views[key] = dict(movements=collection(moves[key], evidence), total=monetary(total, currency, f["periodEnd"], evidence))
    calculated = first + sum(totals.values(), Decimal("0"))
    require(calculated == last, "Financing-liability opening plus movements does not reconcile to closing; no balancing plug")
    content = dict(openingBalances=opening, cashMovements=views["cash"], acquisitions=views["acquisitions"], fxChanges=views["fx"],
                   fairValueChanges=views["fairValue"], otherChanges=views["other"], closingBalances=closing)
    return dict(decision="FINANCING_RECONCILIATION_DRAFT_READY_FOR_REVIEW", sourceControl="7.19A", documentAssetTypeId="FINANCING-RECONCILIATION", documentContent=content,
                reconciledClosing=monetary(calculated, currency, f["periodEnd"], evidence), scope="Operator-pinned liability population; noncash categories are not financing cash flows")


def due_range(value):
    require(isinstance(value, dict), "Due-date range required")
    low, high = value.get("minimumDays"), value.get("maximumDays")
    require(type(low) is int and type(high) is int and 0 <= low <= high, "Ordered nonnegative due-date day ranges required")
    require(type(value.get("wideRangeAssessed")) is bool, "Wide-range judgment required; no universal numeric cutoff")
    if value["wideRangeAssessed"]:
        require(text(value.get("explanation")), "Explain wide ranges or supply supported narrower ranges")


def supplier_period(value, evidence, currency):
    require(isinstance(value, dict), "Supplier-finance period disclosures required")
    start, end = period(value)
    balances = value.get("balances")
    require(isinstance(balances, list) and len(balances) == 2 and {b.get("asOf") for b in balances if isinstance(b, dict)} == {value["periodStart"], value["periodEnd"]}, "Beginning and end supplier-finance balances required")
    for balance in balances:
        positions = balance.get("positions")
        require(isinstance(positions, list) and bool(positions), "Carrying amounts and statement line items required")
        for position in positions:
            carrying = money(position, evidence)
            require(position["currency"] == currency and position["asOf"] == balance["asOf"] and text(position.get("statementLine")), "Carrying-amount scope/line item required")
            paid = position.get("providerPaid")
            require(isinstance(paid, dict) and type(paid.get("impracticable")) is bool, "Provider-paid amount or specific impracticability assessment required")
            if paid["impracticable"]:
                require(paid.get("factDisclosed") is True and text(paid.get("basis")) and refs(paid.get("evidenceRefs")) and set(paid["evidenceRefs"]) <= set(evidence), "Impracticability fact and supported basis must be disclosed")
            else:
                number = money(paid, evidence)
                require(0 <= number <= carrying and paid["currency"] == currency and paid["asOf"] == balance["asOf"] and paid.get("statementLine") == position["statementLine"], "Provider-paid subset must match carrying amount scope and line item")
        ranges = balance.get("dueDateRanges")
        require(isinstance(ranges, dict) and text(ranges.get("comparabilityBasis")), "Comparable trade-payable population basis required")
        due_range(ranges.get("supplierFinance")); due_range(ranges.get("comparableTradePayables"))
    changes = value.get("nonCashChanges")
    require(isinstance(changes, list) and value.get("nonCashChangesAssessed") is True, "Types and effects of noncash changes must be assessed")
    for change in changes:
        money(change, evidence, signed=True)
        require(change["currency"] == currency and start <= day(change["asOf"]) <= end and text(change.get("changeType")) and text(change.get("description")), "Dated noncash change type/effect required")


def supplier(f, evidence):
    period(f)
    keys = ["arrangementScopeAssessed", "suppliersPaidByFinanceProvider", "entityPaysProviderUnderArrangement", "paymentTermsProvideEarlierOrExtendedTerms", "termsPopulationAssessed"]
    require(all(f.get(k) is True for k in keys) and f.get("solelyCreditEnhancement") is False and f.get("directSettlementInstrument") is False, "Assess actual supplier-finance characteristics; guarantees/credit-card settlements are not automatically supplier finance")
    require(f.get("transitionReliefClaimed") is False, "Do not import unverified opening/comparative relief; assess applicable version-3 transition separately")
    currency = f.get("presentationCurrency")
    require(text(currency), "Presentation currency required")
    terms = f.get("terms")
    require(isinstance(terms, list) and bool(terms), "Key terms and conditions required")
    for term in terms:
        require(text(term.get("arrangementId")) and text(term.get("keyTerms")) and type(term.get("dissimilarTerms")) is bool, "Arrangement-specific key terms and similarity assessment required")
        if term["dissimilarTerms"]:
            require(term.get("separatelyPresented") is True, "Dissimilar key terms must be disclosed separately")
    supplier_period(f, evidence, currency)
    comparative = f.get("comparative")
    supplier_period(comparative, evidence, currency)
    require(day(comparative["periodEnd"]) < day(f["periodStart"]), "Prior comparative period must precede current period")
    comparative_view = {**comparative, "nonCashChanges": collection(comparative["nonCashChanges"], evidence)}
    content = dict(terms=terms, carryingAmounts=f["balances"], statementLines=[dict(asOf=b["asOf"], lines=sorted({x["statementLine"] for x in b["positions"]})) for b in f["balances"]],
                   providerPaidAmounts=[dict(asOf=b["asOf"], amounts=[x["providerPaid"] for x in b["positions"]]) for b in f["balances"]],
                   dueDateRanges=[dict(asOf=b["asOf"], ranges=b["dueDateRanges"]) for b in f["balances"]], nonCashChanges=collection(f["nonCashChanges"], evidence),
                   comparatives=comparative_view, reliefs=dict(transitionReliefClaimed=False, providerPaidImpracticability=[dict(asOf=b["asOf"], statementLine=x["statementLine"], basis=x["providerPaid"]["basis"]) for b in f["balances"] for x in b["positions"] if x["providerPaid"]["impracticable"]] or "NONE_CLAIMED"))
    return dict(decision="SUPPLIER_FINANCE_NOTE_DRAFT_READY_FOR_REVIEW", sourceControl="7.19B–7.19C", documentAssetTypeId="SUPPLIER-FINANCE-NOTE", documentContent=content,
                scope="Single presentation-currency population and explicit comparative; no blanket impracticability or transition waiver")


def notes(f, evidence):
    require(f.get("systematicAsPracticableAssessed") is True and type(f.get("normalOrderUsed")) is bool, "Systematic-as-practicable presentation assessment required")
    if not f["normalOrderUsed"]:
        require(f.get("alternativeOrderSystematic") is True and text(f.get("alternativeOrderRationale")), "A justified systematic alternative ordering is permitted; document its basis")
    items, notes, links = f.get("statementItems"), f.get("notes"), f.get("crossReferences")
    require(isinstance(items, list) and bool(items) and isinstance(notes, list) and bool(notes) and isinstance(links, list), "Typed statement, note and cross-reference inventories required")
    item_ids = [i.get("itemId") for i in items]; note_ids = [n.get("noteId") for n in notes]
    require(all(text(x) for x in item_ids+note_ids) and len(set(item_ids)) == len(item_ids) and len(set(note_ids)) == len(note_ids), "Unique statement/note identifiers required")
    expected = set()
    for item in items:
        require(item.get("relatedNotePopulationAssessed") is True and isinstance(item.get("relatedNoteIds"), list), "Assess each item's related note information")
        for nid in item["relatedNoteIds"]:
            require(nid in note_ids, "Related note does not exist")
            expected.add((item["itemId"], nid))
    actual = set()
    for link in links:
        require(isinstance(link, dict) and link.get("itemId") in item_ids and link.get("noteId") in note_ids, "Dangling cross-reference")
        actual.add((link["itemId"], link["noteId"]))
    require(expected <= actual, "Each statement item must cross-reference its related note information")
    return dict(decision="SYSTEMATIC_NOTES_AND_CROSS_REFERENCES_SCREEN_PASSED", sourceControl="8.2–8.4", crossReferencesChecked=len(actual),
                scope="Structure and supplied reference inventory only; not full note content or compliance certification")


HANDLERS = {"section-6-dividend-note": dividend, "section-7-financing-reconciliation": financing,
            "section-7-supplier-finance-note": supplier, "section-8-note-structure-screen": notes}


def determine(control, facts):
    try:
        require(isinstance(facts, dict) and refs(facts.get("evidenceRefs")), "Scoped supporting evidence required")
        require(control in HANDLERS, "Unsupported reporting control")
        with localcontext() as context:
            context.prec = 512
            value = HANDLERS[control](facts, facts["evidenceRefs"])
        return {"status": "ADVISORY", "reviewRequired": True, "postingPerformed": False, "releasePerformed": False, **value}
    except (ValueError, TypeError, KeyError, InvalidOperation, AttributeError) as exc:
        return {"status": "UNRESOLVED", "reason": str(exc), "reviewRequired": True, "postingPerformed": False, "releasePerformed": False}
