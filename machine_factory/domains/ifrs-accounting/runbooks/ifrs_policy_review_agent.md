# ifrs_policy_review_agent: document stewardship

Accountable role: IFRS::Technical Accounting and Adoption Lead

Reviewer: IFRS::Financial Reporting and Disclosure Lead

Motivation: maintain correct, current, reconcilable evidence and reporting assets; expose unresolved issues before apparent completion.

## Edition and authority source register (SOURCE-REGISTER)

Why: Keep every accounting interpretation bound to an applicable edition and verified passages.

Authority: supporting-control; exact title/container is a workflow choice. Source control references: S00-C01, S00-C02, S00-C03, S00-C04, S00-C05, S00-C06, S00-C07, S00-C08, S00-C09.

Create/maintain: edition, sourceFiles, sourceHashes, authorityClasses, sourceGaps. Dependencies: authentic external inputs.

On period/evidence/fact/policy/source/review changes, reassess applicability, request missing authentic evidence, draft/revise, reconcile, and obtain exact-revision independent review. Superseding an input invalidates dependent approvals. Never manufacture third-party evidence or silently replace approved content.

## Source retrieval and citation review register (RAG-RECEIPTS)

Why: Make model interpretations challengeable and reproducible rather than trusting plausible answers.

Authority: supporting-control; exact title/container is a workflow choice. Source control references: S00-C01, S00-C02, S00-C03, S00-C04, S00-C05, S00-C06, S00-C07, S00-C08, S00-C09.

Create/maintain: queries, interactionIds, sourceIds, passages, indexProvenance, citationChecks, unresolved. Dependencies: SOURCE-REGISTER.

On period/evidence/fact/policy/source/review changes, reassess applicability, request missing authentic evidence, draft/revise, reconcile, and obtain exact-revision independent review. Superseding an input invalidates dependent approvals. Never manufacture third-party evidence or silently replace approved content.

## Entity accounting evidence register (EVIDENCE-REGISTER)

Why: Maintain an obtainable evidence trail without fabricating third-party facts.

Authority: supporting-control; exact title/container is a workflow choice. Source control references: S00-C01, S00-C02, S00-C03, S00-C04, S00-C05, S00-C06, S00-C07, S00-C08, S00-C09.

Create/maintain: evidenceItems, issuer, documentDate, sourceHash, scope, verificationStatus. Dependencies: authentic external inputs.

On period/evidence/fact/policy/source/review changes, reassess applicability, request missing authentic evidence, draft/revise, reconcile, and obtain exact-revision independent review. Superseding an input invalidates dependent approvals. Never manufacture third-party evidence or silently replace approved content.

## SME eligibility and public accountability assessment (ELIGIBILITY-MEMO)

Why: Prevent ineligible entities or reporting scopes from using an unsupported SME compliance assertion.

Authority: supporting-control; exact title/container is a workflow choice. Source control references: S01-C01, S01-C02, S01-C03, S01-C04, S01-C05, S01-C06, S01-C07.

Create/maintain: entityFacts, publicMarkets, fiduciaryBusiness, externalUsers, subsidiaryParentScope, conclusion. Dependencies: EVIDENCE-REGISTER, SOURCE-REGISTER.

On period/evidence/fact/policy/source/review changes, reassess applicability, request missing authentic evidence, draft/revise, reconcile, and obtain exact-revision independent review. Superseding an input invalidates dependent approvals. Never manufacture third-party evidence or silently replace approved content.

## Recognition measurement and exception judgment register (JUDGMENT-REGISTER)

Why: Preserve element definitions separately from recognition judgments and specific-section exceptions.

Authority: supporting-control; exact title/container is a workflow choice. Source control references: S02-C01, S02-C02, S02-C03, S02-C04, S02-C05, S02-C06, S02-C07, S02-C08, S02-C09, S02-C10, S02-C11, S02-C12, S02-C13, S02-C14, S02-C15, S02-C16, S02-C17, S02-C18, S02-C19, S02-C20, S02-C21, S02-C22, S02-C23, S02-C24, S02-C25.

Create/maintain: elementDefinitions, specificRules, recognitionBasis, uncertainties, exceptions, conclusions. Dependencies: EVIDENCE-REGISTER, SOURCE-REGISTER.

On period/evidence/fact/policy/source/review changes, reassess applicability, request missing authentic evidence, draft/revise, reconcile, and obtain exact-revision independent review. Superseding an input invalidates dependent approvals. Never manufacture third-party evidence or silently replace approved content.

## Undue cost or effort assessment record (COST-EFFORT-MEMO)

Why: Require explicit paragraph-specific relief and reassessment instead of generic convenience exceptions.

Authority: supporting-control; exact title/container is a workflow choice. Source control references: S02-C01, S02-C02, S02-C03, S02-C04, S02-C05, S02-C06, S02-C07, S02-C08, S02-C09, S02-C10, S02-C11, S02-C12, S02-C13, S02-C14, S02-C15, S02-C16, S02-C17, S02-C18, S02-C19, S02-C20, S02-C21, S02-C22, S02-C23, S02-C24, S02-C25.

Create/maintain: reliefParagraph, circumstances, incrementalCosts, userBenefits, reassessment, disclosureImpact. Dependencies: JUDGMENT-REGISTER.

On period/evidence/fact/policy/source/review changes, reassess applicability, request missing authentic evidence, draft/revise, reconcile, and obtain exact-revision independent review. Superseding an input invalidates dependent approvals. Never manufacture third-party evidence or silently replace approved content.

## Accounting policy election estimate and error register (POLICY-REGISTER)

Why: Keep policy choices consistent and distinguish retrospective corrections from prospective estimates.

Authority: supporting-control; exact title/container is a workflow choice. Source control references: S10-C01, S10-C02, S10-C03, S10-C04, S10-C05, S10-C06, S10-C07, S10-C08, S10-C09, S10-C10, S10-C11, S10-C12, S10-C13, S10-C14, S10-C15.

Create/maintain: policies, elections, measurementBases, estimateChanges, errors, effectiveDates, reasons. Dependencies: SOURCE-REGISTER, EVIDENCE-REGISTER.

On period/evidence/fact/policy/source/review changes, reassess applicability, request missing authentic evidence, draft/revise, reconcile, and obtain exact-revision independent review. Superseding an input invalidates dependent approvals. Never manufacture third-party evidence or silently replace approved content.

## Policy change and error restatement reconciliations (RESTATEMENT-PACK)

Why: Keep changes estimates and errors distinguishable and reconcile all affected comparative balances.

Authority: required-reporting-content; exact title/container is a workflow choice. Source control references: S10-C01, S10-C02, S10-C03, S10-C04, S10-C05, S10-C06, S10-C07, S10-C08, S10-C09, S10-C10, S10-C11, S10-C12, S10-C13, S10-C14, S10-C15.

Create/maintain: classification, affectedPeriods, lineItemAdjustments, openingEquity, comparatives, impracticability, disclosures. Dependencies: POLICY-REGISTER, EVIDENCE-REGISTER.

On period/evidence/fact/policy/source/review changes, reassess applicability, request missing authentic evidence, draft/revise, reconcile, and obtain exact-revision independent review. Superseding an input invalidates dependent approvals. Never manufacture third-party evidence or silently replace approved content.

## First time adoption opening position elections and reconciliations (FIRST-ADOPTION-PACK)

Why: Distinguish first adoption from an edition change and explain prior GAAP differences.

Authority: required-reporting-content; exact title/container is a workflow choice. Source control references: IFRS25-35-C01, IFRS25-35-C02, IFRS25-35-C03, IFRS25-35-C04, IFRS25-35-C05, IFRS25-35-C06, IFRS25-35-C07, IFRS25-35-C08, IFRS25-35-C09, IFRS25-35-C10, IFRS25-35-C11, IFRS25-35-C12, IFRS25-35-C13, IFRS25-35-C14, IFRS25-35-C15.

Create/maintain: firstStatements, transitionDate, openingPosition, mandatoryExceptions, optionalElections, impracticability, equityReconciliations, profitReconciliation, notes. Dependencies: EVIDENCE-REGISTER, POLICY-REGISTER.

On period/evidence/fact/policy/source/review changes, reassess applicability, request missing authentic evidence, draft/revise, reconcile, and obtain exact-revision independent review. Superseding an input invalidates dependent approvals. Never manufacture third-party evidence or silently replace approved content.

## Third edition effective date and transition election pack (EDITION-TRANSITION-PACK)

Why: Apply edition-specific prospective retrospective and relief paths without silently treating them as first adoption.

Authority: required-reporting-content; exact title/container is a workflow choice. Source control references: IFRS25-A-C01, IFRS25-A-C02, IFRS25-A-C03, IFRS25-A-C04, IFRS25-A-C05, IFRS25-A-C06, IFRS25-A-C07, IFRS25-A-C08, IFRS25-A-C09, IFRS25-A-C10, IFRS25-A-C11, IFRS25-A-C12, IFRS25-A-C13, IFRS25-A-C14, IFRS25-A-C15, IFRS25-A-C16.

Create/maintain: periodStart, adoptionDate, earlyAdoption, affectedSections, elections, comparatives, transitionAdjustments, disclosures, sourceGaps. Dependencies: SOURCE-REGISTER, POLICY-REGISTER.

On period/evidence/fact/policy/source/review changes, reassess applicability, request missing authentic evidence, draft/revise, reconcile, and obtain exact-revision independent review. Superseding an input invalidates dependent approvals. Never manufacture third-party evidence or silently replace approved content.
