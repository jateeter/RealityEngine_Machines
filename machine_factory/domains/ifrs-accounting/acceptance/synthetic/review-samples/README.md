# IFRS sample accounting documents and review dispositions

This packet contains all 68 catalogued document examples, the sample HR roster, the operator source-review attestation, technical exact-revision/hash checks, 147 case dispositions and 53 scoped development closures. All entity records and staff profiles are fictional.

The original limited core financial statements reconcile; topic cases are isolated scenarios and must not be consolidated into core figures. Some specialist workpapers explicitly identify missing analysis. Samples establish document shape and reproducible technical checks, not complete accounting acceptance.

- `manifest.json`: artifact and input hashes.
- `documents/<ASSET>/v1.json`: exact reference-lifecycle revision and content hash.
- `document-review.json`: all 68 technical reviews and outstanding substantive limitations.
- `case-annex.json`: all 320 expected-outcome checks; negative/unresolved cases remain guards.
- `contribution-dispositions.json`: all 147 development cases handled; historical runtime states unchanged (143 OPEN, 4 SUPERSEDED), zero canonical satisfaction claims.
- `finding-dispositions.json`: all 53 development contexts and scoped closures; zero admission closures.
- `requirement-dispositions.json`: all 595 controls still need independent applicability/accounting assessment.
- `HR_REVIEWERS.md` / `hr-reviewers.json`: proposed fictional staffing examples only.
- `operator-review-attestation.json`: records the operator statement against the earlier Git revision and file hashes.

Independent follow-up: https://github.com/jateeter/RealityEngine_Machines/issues/231. Original finding closure gates are preserved. Native acceptance and final approval are deferred as requested.

Run `python3 machine_factory/domains/ifrs-accounting/tools/build_review_samples.py --check` to detect altered artifacts or input drift.
