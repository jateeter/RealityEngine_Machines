# ifrs_assets_review_agent: document stewardship

Accountable role: IFRS::Nonfinancial Asset Accounting Lead

Reviewer: IFRS::Fair Value Measurement Lead

Motivation: maintain correct, current, reconcilable evidence and reporting assets; expose unresolved issues before apparent completion.

## Investment property classification transfer and mixed use record (PROPERTY-CLASSIFICATION)

Why: Support property classification and transfers from evidenced use and permitted measurement relief.

Authority: supporting-control; exact title/container is a workflow choice. Source control references: S16-C01, S16-C02, S16-C03, S16-C04, S16-C05, S16-C06, S16-C07, S16-C08, S16-C09, S16-C10, S16-C11, S16-C12.

Create/maintain: propertyFacts, use, mixedUse, reliableFairValue, undueCost, transferEvidence, model. Dependencies: EVIDENCE-REGISTER, POLICY-REGISTER.

On period/evidence/fact/policy/source/review changes, reassess applicability, request missing authentic evidence, draft/revise, reconcile, and obtain exact-revision independent review. Superseding an input invalidates dependent approvals. Never manufacture third-party evidence or silently replace approved content.

## Investment property measurement and disclosure rollforward (INVESTMENT-PROPERTY-SCHEDULE)

Why: Reconcile fair value or cost-model property movements and explain unavailable fair value.

Authority: required-reporting-content; exact title/container is a workflow choice. Source control references: S16-C01, S16-C02, S16-C03, S16-C04, S16-C05, S16-C06, S16-C07, S16-C08, S16-C09, S16-C10, S16-C11, S16-C12.

Create/maintain: opening, additions, transfers, valuations, depreciation, impairment, disposals, closing, notes. Dependencies: PROPERTY-CLASSIFICATION, VALUATION-PACK.

On period/evidence/fact/policy/source/review changes, reassess applicability, request missing authentic evidence, draft/revise, reconcile, and obtain exact-revision independent review. Superseding an input invalidates dependent approvals. Never manufacture third-party evidence or silently replace approved content.

## PPE component cost depreciation revaluation and disclosure register (PPE-SCHEDULE)

Why: Maintain component-level carrying amounts and movements with separate replacement and revaluation histories.

Authority: required-reporting-content; exact title/container is a workflow choice. Source control references: S17-C01, S17-C02, S17-C03, S17-C04, S17-C05, S17-C06, S17-C07, S17-C08, S17-C09, S17-C10, S17-C11, S17-C12, S17-C13, S17-C14, S17-C15, S17-C16, S17-C17, S17-C18, S17-C19, S17-C20, S17-C21, S17-C22.

Create/maintain: assetComponents, costs, readyForUse, estimates, depreciation, replacements, revaluations, disposals, closing, notes. Dependencies: EVIDENCE-REGISTER, POLICY-REGISTER, VALUATION-PACK.

On period/evidence/fact/policy/source/review changes, reassess applicability, request missing authentic evidence, draft/revise, reconcile, and obtain exact-revision independent review. Superseding an input invalidates dependent approvals. Never manufacture third-party evidence or silently replace approved content.

## Dismantling restoration and asset cost linkage record (RESTORATION-SCHEDULE)

Why: Link supported obligations to provision estimates and eligible asset cost without double counting.

Authority: supporting-control; exact title/container is a workflow choice. Source control references: S17-C01, S17-C02, S17-C03, S17-C04, S17-C05, S17-C06, S17-C07, S17-C08, S17-C09, S17-C10, S17-C11, S17-C12, S17-C13, S17-C14, S17-C15, S17-C16, S17-C17, S17-C18, S17-C19, S17-C20, S17-C21, S17-C22.

Create/maintain: obligations, recognition, measurement, discounting, assetCostLink, subsequentChanges. Dependencies: EVIDENCE-REGISTER, POLICY-REGISTER.

On period/evidence/fact/policy/source/review changes, reassess applicability, request missing authentic evidence, draft/revise, reconcile, and obtain exact-revision independent review. Superseding an input invalidates dependent approvals. Never manufacture third-party evidence or silently replace approved content.

## Finite life intangible cost amortisation and disclosure register (INTANGIBLE-SCHEDULE)

Why: Preserve finite-life estimates eligible expenditure exceptions and amortisation evidence.

Authority: required-reporting-content; exact title/container is a workflow choice. Source control references: S18-C01, S18-C02, S18-C03, S18-C04, S18-C05, S18-C06, S18-C07, S18-C08, S18-C09, S18-C10, S18-C11, S18-C12, S18-C13, S18-C14, S18-C15, S18-C16, S18-C17.

Create/maintain: assets, recognition, expenditureNature, otherAssetExceptions, lifeEstimates, method, revenueMethodRebuttal, amortisation, disposals, closing, notes. Dependencies: EVIDENCE-REGISTER, POLICY-REGISTER.

On period/evidence/fact/policy/source/review changes, reassess applicability, request missing authentic evidence, draft/revise, reconcile, and obtain exact-revision independent review. Superseding an input invalidates dependent approvals. Never manufacture third-party evidence or silently replace approved content.

## Impairment indicators recoverable amount allocation and reversal record (IMPAIRMENT-SCHEDULE)

Why: Keep indicators estimates CGU floors reversal caps and goodwill no-reversal evidence linked to asset balances.

Authority: required-reporting-content; exact title/container is a workflow choice. Source control references: IFRS25-27-C01, IFRS25-27-C02, IFRS25-27-C03, IFRS25-27-C04, IFRS25-27-C05, IFRS25-27-C06, IFRS25-27-C07, IFRS25-27-C08, IFRS25-27-C09, IFRS25-27-C10, IFRS25-27-C11, IFRS25-27-C12, IFRS25-27-C13, IFRS25-27-C14, IFRS25-27-C15, IFRS25-27-C16, IFRS25-27-C17, IFRS25-27-C18.

Create/maintain: scope, indicators, carryingAmounts, recoverableAmounts, cgus, allocationFloors, losses, reversals, caps, goodwill, notes. Dependencies: PPE-SCHEDULE, INTANGIBLE-SCHEDULE, GOODWILL-SCHEDULE, INVESTMENT-PROPERTY-SCHEDULE, INVENTORY-SCHEDULE.

On period/evidence/fact/policy/source/review changes, reassess applicability, request missing authentic evidence, draft/revise, reconcile, and obtain exact-revision independent review. Superseding an input invalidates dependent approvals. Never manufacture third-party evidence or silently replace approved content.
