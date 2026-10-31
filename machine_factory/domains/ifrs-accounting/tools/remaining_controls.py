"""Source-scoped remediation controls. Explicit judgments remain independently reviewed.

No universal valuation model, posting, filing, release or compliance certification.
Decimal results use scoped supporting records; native assertion fields are untouched.
"""
from pathlib import Path
from decimal import Decimal, localcontext
from datetime import date
import importlib.util

_spec = importlib.util.spec_from_file_location("ifrs_remaining_reporting", Path(__file__).with_name("reporting_controls.py"))
r = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(r)
require, text, money, monetary = r.require, r.text, r.money, r.monetary


def booleans(f, *keys):
    require(all(type(f.get(k)) is bool for k in keys), "Explicit evidence-backed judgments required: " + ", ".join(keys))


def supported(f):
    require(text(f.get("rationale")), "Entity-specific judgment rationale required")


def numbers(f, *keys, signed=False, same_date=True):
    rows = [f.get(k) for k in keys]
    values = [money(row, f["evidenceRefs"], signed=signed) for row in rows]
    require(len({row["currency"] for row in rows}) == 1, "Separate currencies; no implicit conversion")
    if same_date:require(len({row["asOf"] for row in rows}) == 1, "Measurement dates must agree")
    return values


def out(decision, **extra):return dict(decision=decision, **extra)

def mvalue(f, value, basis):return monetary(value, f[basis]["currency"], f[basis]["asOf"], f["evidenceRefs"])


def grant(f):
    booleans(f,"governmentGrantScopeConfirmed","futurePerformanceConditions","cashReceived")
    booleans(f,"conditionsMet" if f["futurePerformanceConditions"] else "receivable")
    require(f["governmentGrantScopeConfirmed"], "Assess tax assistance/other government transactions under their applicable section")
    value = numbers(f,"fairValue")[0]
    earned = f["conditionsMet"] if f["futurePerformanceConditions"] else f["receivable"]
    return out("GRANT_INCOME" if earned else "GRANT_LIABILITY" if f["cashReceived"] else "GRANT_NOT_YET_RECOGNISABLE", measurement=mvalue(f,value,"fairValue"), sourceControl="24.4–24.5")


def debt_modification(f):
    booleans(f,"substantialTermsAssessmentComplete","substantiallyDifferentTerms","tenPercentClaimedAsExplicitSMERule")
    supported(f)
    require(f["substantialTermsAssessmentComplete"] and not f["tenPercentClaimedAsExplicitSMERule"], "11.37 does not prescribe a universal ten-percent test; support the substantial-terms judgment")
    return out("EXTINGUISH_ORIGINAL_RECOGNISE_NEW" if f["substantiallyDifferentTerms"] else "NOT_SUBSTANTIAL_ON_SUPPORTED_ASSESSMENT", sourceControl="11.37", scope="Modification judgment only; subsequent measurement and implementation guidance assessed separately")


def variable_consideration(f):
    booleans(f,"highlyProbableEntitlement","currentReportingDateAssessment","consistentContractEstimationMethod")
    require(f["currentReportingDateAssessment"] and f["consistentContractEstimationMethod"] and f.get("estimationMethod") in {"EXPECTED_VALUE","MOST_LIKELY_AMOUNT"}, "Current entitlement assessment and supported consistent estimation method required")
    value = numbers(f,"estimatedVariableAmount")[0]
    return out("INCLUDE_ENTITLEMENT_SUPPORTED_AMOUNT" if f["highlyProbableEntitlement"] else "EXCLUDE_UNSUPPORTED_VARIABLE_AMOUNT", includedAmount=mvalue(f,value if f["highlyProbableEntitlement"] else Decimal(0),"estimatedVariableAmount"), sourceControl="23.28–23.31", scope="Transaction-price component only; not revenue recognition")


def asset_review(f):
    require(f.get("assetKind") in {"PPE","INTANGIBLE"}, "Inventory/goodwill/other asset impairment must use its specific requirements")
    booleans(f,"estimateChangeIndicators","impairmentIndicators","reportingDateIndicatorAssessmentComplete")
    require(f["reportingDateIndicatorAssessmentComplete"], "Reporting-date impairment indicator assessment required")
    result=out("REVIEW_ESTIMATES" if f["estimateChangeIndicators"] else "NO_TRIGGERED_ESTIMATE_REVIEW", sourceControl="17.19; 27.7–27.10", requiredSections=["27"], internalAnnualScheduling="SUPPLEMENTAL_NOT_AUTOMATIC_NORMATIVE_REMEASUREMENT")
    if f["assetKind"] == "INTANGIBLE":result["sourceControl"] = "18.24; 27.7–27.10"
    if f["impairmentIndicators"]:
        carrying,recoverable=numbers(f,"carryingAmount","recoverableAmount")
        result.update(impairmentAction="MEASURE_RECOVERABLE_AMOUNT", impairmentLoss=mvalue(f,max(Decimal(0),carrying-recoverable),"carryingAmount"))
    else:result["impairmentAction"]="NO_INDICATOR_TRIGGERED_MEASUREMENT"
    return result


def goodwill(f):
    booleans(f,"stagedAcquisition","acquisitionMeasurementReviewed","nciProportionateShareVerified")
    require(f["acquisitionMeasurementReviewed"] and f["nciProportionateShareVerified"], "Reviewed acquisition values and SME NCI measurement required")
    price,nci,net=numbers(f,"consideration","nci","identifiableNetAssets")
    prior,delta=Decimal(0),Decimal(0)
    if f["stagedAcquisition"]:
        prior,book=numbers(f,"previousInterestFV","previousInterestCarrying")
        require(f["previousInterestFV"]["currency"]==f["consideration"]["currency"] and f["previousInterestFV"]["asOf"]==f["consideration"]["asOf"] and f.get("previousOCIResolvedUnderApplicableSections") is True, "Acquisition-date scope and prior OCI disposition required")
        delta=prior-book
    excess=price+nci+prior-net
    require(excess>=0 or f.get("bargainReassessmentComplete") is True, "Reassess all acquisition inputs before recognising a bargain purchase gain")
    return out("GOODWILL" if excess>=0 else "BARGAIN_GAIN_AFTER_REASSESSMENT", goodwill=mvalue(f,max(excess,Decimal(0)),"consideration"), bargainGain=mvalue(f,max(-excess,Decimal(0)),"consideration"), previousInterestRemeasurement=mvalue(f,delta,"consideration"), sourceControl="19.22; 19.24; 19.29–19.30")


def acquisition_exceptions(f):
    supported(f)
    kind=f.get("acquiredItemType")
    require(kind in {"DEFERRED_TAX","EMPLOYEE_BENEFIT","OTHER_IDENTIFIABLE"}, "Assess acquired item under its specific recognition exception")
    if kind=="DEFERRED_TAX":return out("ROUTE_TO_SECTION_29_NOT_GENERIC_FV",requiredSections=["29"],sourceControl="19.20")
    if kind=="EMPLOYEE_BENEFIT":return out("ROUTE_TO_SECTION_28_NOT_GENERIC_FV",requiredSections=["28"],sourceControl="19.21")
    require(f.get("generalRecognitionAndFVAssessmentComplete") is True,"General acquisition recognition/fair-value assessment incomplete")
    return out("GENERAL_IDENTIFIABLE_ITEM_REQUIREMENTS",sourceControl="19.13–19.19",scope="Routing/recognition screen, not specialist tax or actuarial measurement")


def share_payment(f):
    booleans(f,"employeeOrSimilarServices")
    if not f["employeeOrSimilarServices"]:booleans(f,"goodsServicesFVReliable")
    require(f.get("equitySettled") is True,"Cash-settled transactions use separate requirements")
    supported(f)
    grant_date=r.day(f.get("grantDate")); service_date=r.day(f.get("goodsServicesDate"))
    basis="EQUITY_INSTRUMENT_FV" if f["employeeOrSimilarServices"] or not f["goodsServicesFVReliable"] else "GOODS_SERVICES_FV"
    return out(basis,measurementDate=grant_date.isoformat() if f["employeeOrSimilarServices"] else service_date.isoformat(),sourceControl="26.7–26.8",scope="Measurement basis/date selection; vesting, valuation and expense allocation separately assessed")


def contingent(f):
    require(f.get("stage") in {"ACQUISITION","SUBSEQUENT"} and f.get("classification") in {"EQUITY","LIABILITY","ASSET"},"Acquisition stage and Section 22 classification required")
    supported(f)
    booleans(f,"acquisitionFVWithoutUndueCostEffort")
    basis="FAIR_VALUE" if f["acquisitionFVWithoutUndueCostEffort"] else "MOST_LIKELY_AMOUNT"
    if f["stage"]=="ACQUISITION":
        key="fairValue" if basis=="FAIR_VALUE" else "mostLikelyAmount"
        value=numbers(f,key)[0]
        return out("ACQUISITION_"+basis,measurement=mvalue(f,value,key),sourceControl="19.26–19.28",requiredSections=["22"])
    require(f.get("reportingDateReviewComplete") is True,"Subsequent reporting-date review required; initial undue-cost basis is not reassessed")
    old=numbers(f,"previousCarrying")[0]
    if f["classification"]=="EQUITY":return out("EQUITY_NO_REMEASUREMENT",measurement=mvalue(f,old,"previousCarrying"),remeasurementDelta=mvalue(f,Decimal(0),"previousCarrying"),sourceControl="19.37(a)",requiredSections=["22"])
    key="currentFairValue" if basis=="FAIR_VALUE" else "currentMostLikelyAmount"
    value=numbers(f,key)[0]
    require(f[key]["currency"]==f["previousCarrying"]["currency"],"Currency mismatch")
    return out("SUBSEQUENT_"+basis,measurement=mvalue(f,value,key),remeasurementDelta=mvalue(f,value-old,key),statementRoute="PROFIT_OR_LOSS",sourceControl="19.37(b)",requiredSections=["22"])


def going_concern(f):
    booleans(f,"intendsLiquidation","intendsCeaseOperations","noRealisticAlternative","materialUncertainty","allAvailableInformationAssessed")
    require(f["allAvailableInformationAssessed"] and type(f.get("horizonMonths")) is int and f["horizonMonths"]>=12,"Assess all available future information for at least twelve months from reporting date")
    supported(f)
    if any(f[k] for k in ["intendsLiquidation","intendsCeaseOperations","noRealisticAlternative"]):
        require(f.get("nonGoingConcernFactDisclosed") is True and text(f.get("basisDescription")) and text(f.get("reasonDisclosure")) and f.get("separatelySupportedBasis") is True,"Disclose non-going-concern fact, separately supported preparation basis and reason; no automatic liquidation measurement")
        return out("NON_GOING_CONCERN_SEPARATELY_SUPPORTED_BASIS",sourceControl="3.8–3.9")
    require(not f["materialUncertainty"] or f.get("uncertaintyDisclosed") is True,"Disclose material going-concern uncertainties")
    return out("GOING_CONCERN_WITH_UNCERTAINTY_DISCLOSURE" if f["materialUncertainty"] else "GOING_CONCERN_ASSESSED",sourceControl="3.8–3.9")


def later_going_concern(f):
    value=going_concern(f);value.update(requiredSections=["03"],sourceControl="Section 32 event context; 3.8–3.9 going concern",scope="Deterioration flag alone is not an automatic basis override")
    return value


def liability_classification(f):
    require(f.get("currentNoncurrentPresentationUsed") is True,"Assess liquidity presentation separately under 4.4")
    names=["normalOperatingCycleSettlement","heldForTrading","dueWithinTwelveMonths","unconditionalRightToDeferAtLeastTwelveMonths"]
    yes=any(f.get(k) is True for k in names[:3]) or f.get(names[3]) is False
    if yes:return out("CURRENT_LIABILITY",sourceControl="4.7")
    booleans(f,*names)
    return out("NON_CURRENT_LIABILITY",sourceControl="4.8")


def oci(f):
    require(f.get("itemType") in {"FOREIGN_OPERATION_TRANSLATION","ACTUARIAL","PPE_REVALUATION","QUALIFYING_HEDGE"},"Identify OCI nature and applicable section")
    if f["itemType"]=="QUALIFYING_HEDGE":
        booleans(f,"hedgeReclassificationConditionsMet")
        return out("RECLASSIFY_WHEN_HEDGE_CONDITIONS_MET" if f["hedgeReclassificationConditionsMet"] else "RETAIN_HEDGE_OCI_PENDING_CONDITIONS",requiredSections=["11"],sourceControl="5.5(g); 11.69")
    deps={"FOREIGN_OPERATION_TRANSLATION":["30"],"ACTUARIAL":["28"],"PPE_REVALUATION":["17"]}
    return out("NO_SUBSEQUENT_RECLASSIFICATION_TO_PROFIT_OR_LOSS",requiredSections=deps[f["itemType"]],sourceControl="5.4(b); 5.5(g)")


def separate_policy(f):
    require(f.get("separateFinancialStatements") is True and f.get("investmentClass") in {"SUBSIDIARIES","ASSOCIATES","JOINT_ENTITIES"},"Separate-statement scope and investment class required")
    require(f.get("policy") in {"COST_LESS_IMPAIRMENT","FAIR_VALUE_PROFIT_OR_LOSS","EQUITY_METHOD"} and f.get("consistentWithinClass") is True and f.get("separateFSDisclosuresProvided") is True,"Choose one of three policies consistently within each class and disclose separate-statement methods/relationships")
    return out(f["policy"],sourceControl="9.26–9.27",requiredSections=["14"] if f["policy"]=="EQUITY_METHOD" else [])


def control_returns(f):
    booleans(f,"powerOverRelevantActivities","returnsMayVaryWithPerformance","abilityToUsePowerToAffectReturns","principalAgentAssessmentComplete","actingAsAgent")
    require(f["principalAgentAssessmentComplete"],"Principal/agent assessment required")
    supported(f)
    return out("CONTROL_ELEMENTS_MET" if all(f[k] for k in ["powerOverRelevantActivities","returnsMayVaryWithPerformance","abilityToUsePowerToAffectReturns"]) and not f["actingAsAgent"] else "CONTROL_ELEMENTS_NOT_ALL_MET",sourceControl="9.5–9.12",scope="Fixed contractual payments can still vary through credit/default exposure; no fixed-return shortcut")


def estimate_change(f):
    booleans(f,"priorPeriodError","measurementBasisChanged","affectsCarryingAssetLiabilityEquity","affectsFuturePeriods")
    require(not f["priorPeriodError"] and not f["measurementBasisChanged"],"Error correction or policy/basis change requires its separate Section 10 pathway")
    supported(f)
    return out("ADJUST_RELATED_CARRYING_AMOUNT_IN_CURRENT_PERIOD" if f["affectsCarryingAssetLiabilityEquity"] else "CURRENT_AND_FUTURE_PROSPECTIVE_PROFIT_OR_LOSS" if f["affectsFuturePeriods"] else "CURRENT_PERIOD_PROSPECTIVE_PROFIT_OR_LOSS",sourceControl="10.16–10.17")


def instrument_basis(f):
    require(f.get("partIConditionsAssessed") is True and f.get("arbitraryFairValueElection") is False,"SME permitted basis and Part I/II conditions must be assessed; no arbitrary full-IFRS fair-value election")
    kind=f.get("instrumentType")
    if kind=="PART_I_DEBT":
        booleans(f,"currentInstrument","financingTransaction")
        return out("UNDISCOUNTED_NET_OF_IMPAIRMENT" if f["currentInstrument"] and not f["financingTransaction"] else "AMORTISED_COST_EFFECTIVE_INTEREST",sourceControl="11.14(a)")
    if kind=="LOAN_COMMITMENT":return out("COST_LESS_IMPAIRMENT",sourceControl="11.14(b)")
    if kind=="QUALIFYING_EQUITY":
        booleans(f,"publiclyTraded","fairValueReliableWithoutUndueCost")
        return out("FAIR_VALUE_PROFIT_OR_LOSS" if f["publiclyTraded"] or f["fairValueReliableWithoutUndueCost"] else "COST_LESS_IMPAIRMENT",sourceControl="11.14(c)")
    require(kind=="PART_II","Identify permitted instrument category")
    return out("APPLY_PART_II_SPECIFIC_REQUIREMENTS",sourceControl="Section 11 Part II",scope="Routing only; no unconstrained fair-value option")


def hierarchy(f):
    inputs=f.get("inputs");require(isinstance(inputs,list) and bool(inputs),"Valuation input inventory required")
    for i in inputs:
        require(isinstance(i,dict) and type(i.get("level")) is int and i["level"] in {1,2,3} and type(i.get("significantToEntireMeasurement")) is bool,"Input level and whole-measurement significance judgments required")
    significant=[i["level"] for i in inputs if i["significantToEntireMeasurement"]]
    require(bool(significant),"Identify at least one significant input")
    return out("LEVEL_"+str(max(significant)),sourceControl="12.22",scope="Whole-measurement hierarchy; not a valuation calculation")


def inventory_formula(f):
    booleans(f,"ordinarilyInterchangeable","segregatedSpecificProject","costLayerEvidenceAvailable")
    require(f["costLayerEvidenceAvailable"],"Inventory/cost-layer evidence required")
    if not f["ordinarilyInterchangeable"] or f["segregatedSpecificProject"]:return out("SPECIFIC_IDENTIFICATION",sourceControl="13.17")
    require(f.get("formula") in {"FIFO","WEIGHTED_AVERAGE"} and f.get("consistentForSimilarNatureUse") is True,"FIFO or weighted average consistently for similar inventory; no LIFO")
    return out(f["formula"],sourceControl="13.18")


def influence(f):
    booleans(f,"control","jointControl","participationRightsAssessed","powerToParticipate")
    require(f["participationRightsAssessed"],"Participation rights and contrary evidence assessment required")
    if f["control"] or f["jointControl"]:return out("ASSESS_CONTROL_OR_JOINT_CONTROL_MODEL",requiredSections=["09" if f["control"] else "15"],sourceControl="14.2–14.3")
    raw=f.get("votingPercent");require(isinstance(raw,str),"Explicit voting percentage required")
    value=Decimal(raw);require(value.is_finite() and 0<=value<=100,"Voting percent outside supported range")
    if value>50:require(f.get("controlExclusionEvidence") is True and text(f.get("rationale")),"Support exclusion of control when majority voting rights are held")
    presumption=value>=20
    require(f["powerToParticipate"]==presumption or (f.get("clearRebuttalEvidence") is True and text(f.get("rebuttalRationale"))),"Clear evidence needed to rebut above/below twenty-percent presumption")
    return out("SIGNIFICANT_INFLUENCE" if f["powerToParticipate"] else "NO_SIGNIFICANT_INFLUENCE",sourceControl="14.2–14.3",requiredSections=["09"] if value>50 else [])


def associate_measurement(f):
    booleans(f,"separateFinancialStatements")
    if f["separateFinancialStatements"]:
        value=separate_policy(f);value.update(requiredSections=sorted(set(value.get("requiredSections",[])+["09"])),sourceControl="14.1; 9.26–9.27");return value
    require(f.get("associateScopeEstablished") is True and f.get("consistentAssociatePolicy") is True,"Associate scope and consistent class policy required")
    policy=f.get("policy");require(policy in {"COST_LESS_IMPAIRMENT","EQUITY_METHOD","FAIR_VALUE"},"Section 14 policy required")
    booleans(f,"publishedPriceQuotation")
    return out("FAIR_VALUE" if policy=="COST_LESS_IMPAIRMENT" and f["publishedPriceQuotation"] else policy,sourceControl="14.4–14.9",scope="Published quotation overrides cost model under 14.7; separate statements use 9.26")


def joint_arrangement(f):
    require(f.get("jointControlUnanimityAssessed") is True and f.get("jointControl") is True,"Contractual unanimity/joint-control evidence required")
    kind=f.get("arrangementType");require(kind in {"OPERATIONS","ASSETS","ENTITY"},"Establish arrangement type before allocation")
    require(f.get("rightsAndObligationsAssessed") is True,"Own/shared rights and obligations must be assessed, not a blanket ownership percentage")
    return out({"OPERATIONS":"RECOGNISE_OWN_ASSETS_LIABILITIES_EXPENSES_AND_SHARE_OF_REVENUE","ASSETS":"RECOGNISE_ASSET_SHARE_OWN_LIABILITIES_AND_SHARE_OF_JOINT_ITEMS","ENTITY":"APPLY_JOINT_ENTITY_INVESTMENT_POLICY"}[kind],sourceControl="15.3–15.9",scope="Classification/recognition routing; allocations must follow identified rights/obligations, not arbitrary proportioning")


def investment_property(f):
    booleans(f,"reliableFVWithoutUndueCost","restorationChangesResolvedUnder17And21")
    require(f["restorationChangesResolvedUnder17And21"],"Restoration obligations/cost changes need separate Section 17/21 evidence, not automatic double counting")
    if f["reliableFVWithoutUndueCost"]:return out("APPLY_RESTORED_FAIR_VALUE_MODEL",sourceControl="16.7–16.8",requiredSections=["12"])
    last,dep,imp,cap=numbers(f,"lastFairValueCarrying","depreciationSinceTransfer","impairmentSinceTransfer","supportedCapitalChanges",same_date=False)
    require(r.day(f["lastFairValueCarrying"]["asOf"])<=r.day(f["depreciationSinceTransfer"]["asOf"]) and f.get("changeOfCircumstancesDisclosed") is True,"Dated last-FV transfer cost and change-of-circumstances disclosure required")
    require(all(f[k]["asOf"] == f["depreciationSinceTransfer"]["asOf"] for k in ["impairmentSinceTransfer","supportedCapitalChanges"]), "Cost-basis adjustments must share the reporting date")
    value=last+cap-dep-imp;require(value>=0,"Depreciation/impairment exceeds supported cost basis")
    return out("LAST_FAIR_VALUE_BECOMES_COST",carryingAmount=mvalue(f,value,"depreciationSinceTransfer"),sourceControl="16.8",requiredSections=["17","21","27"])


def revaluation(f):
    require(text(f.get("assetId")) and f.get("assetId")==f.get("historyAssetId") and f.get("historyComplete") is True and f.get("entireClassRevaluationAssessed") is True and f.get("fvReliablyMeasured") is True,"Same-asset history, whole-class scope and supported fair value required")
    old,new,prior_loss,surplus=numbers(f,"carrying","revalued","priorPLDecreaseRemaining","revaluationSurplus")
    delta=new-old
    if delta>=0:pl=min(delta,prior_loss);oci_amount=delta-pl
    else:oci_amount=-min(-delta,surplus);pl=delta-oci_amount
    return out("REVALUATION_SPLIT_BY_SAME_ASSET_HISTORY",profitOrLoss=mvalue(f,pl,"revalued"),otherComprehensiveIncome=mvalue(f,oci_amount,"revalued"),closingSurplus=mvalue(f,surplus+oci_amount,"revalued"),sourceControl="17.15C–17.15D")


def components(f):
    require(f.get("majorComponentsAssessed") is True,"Major-component population assessment required")
    booleans(f,"significantlyDifferentConsumptionPatterns");supported(f)
    if f["significantlyDifferentConsumptionPatterns"]:
        require(f.get("componentCostsAllocated") is True and f.get("componentUsefulLivesSupported") is True,"Allocate cost and support component useful lives separately")
        return out("DEPRECIATE_MAJOR_COMPONENTS_SEPARATELY",sourceControl="17.16")
    return out("SINGLE_ASSET_DEPRECIATION_ON_ASSESSED_PATTERNS",sourceControl="17.16",scope="Numeric life differences alone are not the complete consumption-pattern assessment")


def internal_expenditure(f):
    booleans(f,"previouslyExpensed","formsPartOfOtherQualifyingAsset","otherAssetRecognitionCriteriaMet")
    if f["previouslyExpensed"]:return out("DO_NOT_REACTIVATE_PAST_EXPENSE",sourceControl="18.17")
    if f["formsPartOfOtherQualifyingAsset"]:
        section=f.get("otherAssetSection");require(section in {"13","17","23","34"},"Identify and evidence the applicable other-asset recognition section")
        return out("INCLUDE_IN_OTHER_QUALIFYING_ASSET" if f["otherAssetRecognitionCriteriaMet"] else "EXPENSE_OTHER_ASSET_CRITERIA_NOT_MET",requiredSections=[section],sourceControl="18.14–18.17")
    return out("EXPENSE_INTERNAL_INTANGIBLE_EXPENDITURE",sourceControl="18.14–18.17")


def amortisation(f):
    require(f.get("assetKind") in {"PPE","INTANGIBLE"},"Identify asset kind")
    booleans(f,"revenueBasedMethod")
    if f["assetKind"]=="PPE":
        return out("REVENUE_METHOD_NOT_APPROPRIATE_FOR_PPE" if f["revenueBasedMethod"] else "ASSESS_PPE_BENEFIT_CONSUMPTION_METHOD",requiredSections=["17"],sourceControl="17.22")
    if not f["revenueBasedMethod"]:return out("ASSESS_INTANGIBLE_BENEFIT_CONSUMPTION_METHOD",sourceControl="18.22")
    booleans(f,"rightExpressedAsRevenueMeasure","highRevenueBenefitConsumptionCorrelationDemonstrated")
    return out("REVENUE_METHOD_EXCEPTION_SUPPORTED_SUBJECT_TO_REVIEW" if f["rightExpressedAsRevenueMeasure"] or f["highRevenueBenefitConsumptionCorrelationDemonstrated"] else "REVENUE_METHOD_PRESUMPTION_NOT_REBUTTED",sourceControl="18.22A")


def noncash_distribution(f):
    booleans(f,"sameUltimateControlBeforeAfter","declaredPresentObligation","fairValueReliableWithoutUndueCost")
    if f["sameUltimateControlBeforeAfter"]:return out("OUTSIDE_22_18_SCOPE_COMMON_CONTROL",sourceControl="22.18B")
    if not f["declaredPresentObligation"]:return out("NO_DECLARED_PRESENT_DISTRIBUTION_OBLIGATION",sourceControl="22.18")
    require(f.get("phase") in {"INITIAL","REMEASUREMENT","SETTLEMENT"},"Distribution phase required")
    key="fairValue" if f["fairValueReliableWithoutUndueCost"] else "assetCarrying"
    value=numbers(f,key)[0]
    if not f["fairValueReliableWithoutUndueCost"]:require(f.get("fallbackFactAndReasonsDisclosed") is True,"Disclose inability to obtain supported fair value and undue-cost reasons")
    result=out("FAIR_VALUE_DISTRIBUTION" if key=="fairValue" else "PERMITTED_CARRYING_AMOUNT_DISTRIBUTION",liability=mvalue(f,value,key),sourceControl="22.18–22.20")
    if f["phase"]!="INITIAL":
        old=numbers(f,"previousDividendLiability")[0]
        require(f["previousDividendLiability"]["currency"]==f[key]["currency"],"Distribution currency mismatch")
        result["equityDistributionAdjustment"]=mvalue(f,value-old,key)
    if f["phase"]=="SETTLEMENT":
        carrying=numbers(f,"assetCarrying")[0];require(f["assetCarrying"]["currency"]==f[key]["currency"],"Settlement currency mismatch")
        result["profitOrLossGain"]=mvalue(f,value-carrying,key)
    return result


def plan_assets(f):
    require(f.get("reportingDateFVSupported") is True and f.get("valuedByDiscountingExpectedReturns") is False,"Plan assets require supported reporting-date fair value, not discounted expected return/contributions")
    opening,closing=numbers(f,"openingPlanAssets","closingFairValue",same_date=False)
    start,end=r.day(f.get("periodStart")),r.day(f.get("periodEnd"));require(start<=end and f["openingPlanAssets"]["asOf"]==f["periodStart"] and f["closingFairValue"]["asOf"]==f["periodEnd"],"Plan-asset opening/closing dates must match period")
    moves=f.get("movements");keys={"contributions","benefitsPaid","actualReturn","otherChanges"}
    require(isinstance(moves,dict) and set(moves)==keys and f.get("allMovementCategoriesAssessed") is True,"Explicit plan-asset movement categories required")
    total=opening
    for key,rows in moves.items():
        require(isinstance(rows,list),"Typed movement lists required")
        for row in rows:
            value=money(row,f["evidenceRefs"],signed=True)
            require(row["currency"]==f["closingFairValue"]["currency"] and start<=r.day(row["asOf"])<=end,"Plan-asset movement scope mismatch")
            require(key!="benefitsPaid" or value<=0,"Benefits paid must reduce plan assets in this signed rollforward")
            total+=value
    require(total==closing,"Plan-asset rollforward does not reconcile to independent closing fair value")
    return out("REPORTING_DATE_FV_AND_ROLLFORWARD_RECONCILED",closingFairValue=mvalue(f,total,"closingFairValue"),sourceControl="28.15(b); 28.41(f)",requiredSections=["12"])


def purchasing_power(f):
    require(f.get("hyperinflationScopeAssessed") is True and f.get("functionalCurrencyHyperinflationary") is True and f.get("method")=="GENERAL_PRICE_INDEX" and f.get("generalPurchasingPowerIndexSupported") is True,"Section 31 scope and a supported general price index required; not a closing FX-rate operation")
    require(f.get("itemType") in {"COMPARATIVE","HISTORICAL_NONMONETARY"},"Current monetary items and net monetary gain/loss need their separate Section 31 treatment")
    amount=numbers(f,"amount")[0]
    base,end=f.get("baseIndex"),f.get("reportingIndex")
    require(isinstance(base,dict) and isinstance(end,dict) and text(base.get("indexIdentity")) and base.get("indexIdentity")==end.get("indexIdentity"),"Consistent general price index identity required")
    b,e=Decimal(base["value"]),Decimal(end["value"])
    require(b.is_finite() and e.is_finite() and b>0 and e>0 and base.get("asOf")==f["amount"]["asOf"] and end.get("asOf")==f.get("reportingDate") and r.day(base["asOf"])<=r.day(end["asOf"]),"Positive dated base/reporting indices required")
    require(type(f.get("decimalPlaces")) is int and 0<=f["decimalPlaces"]<=12 and f.get("roundingMethod") in {"ROUND_HALF_EVEN","ROUND_HALF_UP"},"Explicit presentation rounding policy required")
    import decimal
    value=(amount*e/b).quantize(Decimal(1).scaleb(-f["decimalPlaces"]),rounding=getattr(decimal,f["roundingMethod"]))
    result=monetary(value,f["amount"]["currency"],f["reportingDate"],f["evidenceRefs"])
    return out("RESTATE_IN_CURRENT_PURCHASING_POWER_UNIT",restatedAmount=result,sourceControl="31.3–31.4",scope="General-price-index restatement only; no currency translation or complete hyperinflation statements")


def concession(f):
    require(f.get("grantorScopeAndResidualInterestAssessed") is True and f.get("rightsAllocationSupported") is True,"Grantor/control scope and contract-right allocation evidence required")
    booleans(f,"unconditionalGrantorCashRight","rightToChargeUsers")
    financial,intangible=f["unconditionalGrantorCashRight"],f["rightToChargeUsers"]
    require(financial or intangible,"No supported concession consideration right")
    keys=(["financialRightFV"] if financial else [])+(["userChargeRightFV"] if intangible else [])
    values=numbers(f,*keys);total=sum(values,Decimal(0))
    full=numbers(f,"totalConsiderationFV")[0]
    require(full==total and f["totalConsiderationFV"]["currency"]==f[keys[0]]["currency"] and f["totalConsiderationFV"]["asOf"]==f[keys[0]]["asOf"],"Allocated rights must reconcile without double counting")
    return out("MIXED_FINANCIAL_AND_INTANGIBLE_RIGHTS" if financial and intangible else "FINANCIAL_ASSET_RIGHT" if financial else "INTANGIBLE_ASSET_RIGHT",financialAsset=mvalue(f,values[0] if financial else Decimal(0),keys[0]),intangibleAsset=mvalue(f,values[-1] if intangible else Decimal(0),keys[0]),requiredSections=(["11"] if financial else [])+(["18"] if intangible else [])+["23"],sourceControl="34.13–34.16")


def engineering(f):
    require(f.get("treatAsAccountingMandate") is False,"STA/memory integrity is engineering, not a glossary accounting mandate")
    booleans(f,"engineeringIntegrityVerified")
    import json
    expected=json.loads((Path(__file__).resolve().parents[1]/"admission-source-manifest.json").read_text())["machineCount"]
    require(type(f.get("candidateMachineCount")) is int and f["candidateMachineCount"]==expected,"Use the actual candidate census; do not retain a stale 200-machine claim")
    return out("ENGINEERING_CONTROL_VERIFIED_NOT_ACCOUNTING_COMPLIANCE" if f["engineeringIntegrityVerified"] else "ENGINEERING_CHECK_REQUIRES_RESOLUTION",authorityClass="engineering-supplemental",sourceControl="Glossary authority boundary",scope="Does not replace native memory-integrity/runtime verification")


HANDLERS={
 "rem-grant":grant,"rem-debt-modification":debt_modification,"rem-variable-consideration":variable_consideration,"rem-asset-review":asset_review,
 "rem-goodwill":goodwill,"rem-acquisition-exceptions":acquisition_exceptions,"rem-share-payment":share_payment,"rem-contingent":contingent,
 "rem-going-concern":going_concern,"rem-liability-classification":liability_classification,"rem-oci":oci,"rem-separate-policy":separate_policy,
 "rem-control-returns":control_returns,"rem-estimate-change":estimate_change,"rem-instrument-basis":instrument_basis,"rem-fv-hierarchy":hierarchy,
 "rem-inventory-formula":inventory_formula,"rem-significant-influence":influence,"rem-associate-basis":associate_measurement,"rem-joint-arrangement":joint_arrangement,
 "rem-investment-property":investment_property,"rem-revaluation":revaluation,"rem-components":components,"rem-internal-expenditure":internal_expenditure,
 "rem-amortisation":amortisation,"rem-noncash-distribution":noncash_distribution,"rem-plan-assets":plan_assets,"rem-purchasing-power":purchasing_power,
 "rem-later-going-concern":later_going_concern,"rem-concession":concession,"rem-engineering":engineering}


def determine(control,facts):
    try:
        require(isinstance(facts,dict) and r.refs(facts.get("evidenceRefs")),"Scoped supporting evidence required")
        require(control in HANDLERS,"Unsupported remediation control")
        with localcontext() as context:
            context.prec=512
            value=HANDLERS[control](facts)
        return {"status":"ADVISORY","reviewRequired":True,"postingPerformed":False,"releasePerformed":False,**value}
    except (ValueError,TypeError,KeyError,ArithmeticError,AttributeError) as exc:
        return {"status":"UNRESOLVED","reason":str(exc),"reviewRequired":True,"postingPerformed":False,"releasePerformed":False}
