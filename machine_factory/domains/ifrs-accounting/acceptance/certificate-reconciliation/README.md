# Acceptance certificate reconciliation

The supplied five-page certificate is preserved unchanged and logged by SHA-256. It states unreserved acceptance. Before applying that statement to current finding closures, nine discrepancies/missing bindings must be reconciled with the reviewers. This record does not claim the reviewers are unauthentic and does not substitute a new accounting opinion.

| Item | Pages | Required reconciliation |
|---|---|---|
| CERT-01 — Exact candidate and finding coverage | 1, 5 | Bind an addendum to the current source candidate and the 68 document revisions; record supported decisions for each finding. |
| CERT-02 — Reviewer identity and evidence references | 1, 5 | Record reviewer identity/role, independence, decision date, scope and resolvable evidence references; no new identity-management system or cryptographic signature is required by this check. |
| CERT-03 — Native output contract | 2, 3, 5 | Correct the distinction between legacy labels, input tokens and bounded native outputs; review the actual machine event/output vectors. |
| CERT-04 — Machine/agent identity | 1, 2, 3 | Identify actual machine/agent IDs and distinguish recognizers, families, stewards and any separately reviewed seven-agent subset. |
| CERT-05 — Going-concern valuation override | 2 | Review the current corrected description and rem-going-concern cases; remove or separately evidence any different proposed implementation. |
| CERT-06 — Lease and internal-expenditure exceptions | 1, 3 | Explicitly reconcile STD-04/05 and DEEP-S18-23, including qualitative counterexamples and supported other-asset routes; do not treat omission as automatic rejection of those exceptions. |
| CERT-07 — Source-reference corrections | 3, 4 | Reconcile the current STD-01/source mapping and DEEP-23/DEEP-29 findings against complete version 3 and actual corrected descriptions. |
| CERT-08 — Native acceptance assertions | 1, 4, 5 | Treat the certificate as a review assertion, not runtime evidence. Supply any actual matching receipts or leave native verification to the next gated stage. |
| CERT-09 — Agent capabilities and governance | 4, 5 | Distinguish proposed architecture from implemented/verified capability and review the merged OpenClaw service/plugin/worker contracts. |

Machine IDs absent from the current corpus: `IFRS_Sec01_PrimaryFiduciary_Asset_Evaluator`, `IFRS_Sec03_GoingConcern_12Month_Continuity_Assessor`, `IFRS_Sec18_Internal_RD_Expense_Enforcer`. The existing public-market/SPPI/Pillar-Two IDs do exist; the issue is not a blanket identity mismatch.

The 68 sample-document hash/reproduction checks still pass. Accounting readiness still reports 53 findings without qualifying closure records. No findings were silently closed; no native runtimes were reset and no parity/CES/release evidence was fabricated.

Use `reviewer-addendum-template.json` for exact-version decisions. Actual independent reviewer/role strings suffice; fictional HR names must not be promoted into sign-off. A blanket statement can reference a complete exact-hash decision inventory, but it cannot establish unexecuted native parity.

Tracking: [issue #231](https://github.com/jateeter/RealityEngine_Machines/issues/231).

## Reviewer response received on main

`IFRS Issue #231 Reconciliation.pdf`, supplied in `f6d224b1`, has been checked. All nine named legacy/aggregate artifacts are absent from the current tracked candidate, so their declared hashes do not bind this implementation. Its ordinal finding groups do not match the actual STD-/DEEP- finding IDs. The response retains 2.0/3.0 native outputs, the unimplemented dual-key liquidation cascade and 29.38 Pillar Two reference. Its final conditional Phase 5 wording partially clarifies that native verification remains future work, but provides no execution receipts. `semantic-buses:write` is the JSON inventory command, not a cross-language binding generator.

No canonical finding can be closed from this response. See `reconciliation-response-review.json` for the exact nine artifact names/hashes and review results. Use the actual 53-finding/68-document `reviewer-addendum-template.json`; the reviewers can inspect current canonical files and bind decisions to their exact hashes. The original PDFs are preserved unchanged.

## Third reviewer response

`IFRS PR 232 Gate.pdf` (main commit `ad3ccf13`) correctly moves the liquidation/escrow features out of the active baseline and acknowledges native execution is pending. Those clarifications are recorded. The response still describes 128 machines and a different branch/path, supplies no full SHA-256 among its ten listed strings, invents 32 IDs and omits all 32 canonical DEEP IDs, and reassigns the meanings of the overlapping STD IDs. Binary-only assertions and native monetary floats would also change the preserved contract and are not applied.

See `third-response-review.json`. To eliminate ambiguity, `actual-candidate-review-facts.json` now supplies all 225 machine hashes, actual schema/manifest hashes, all 53 canonical contexts and all 68 exact document revisions/content hashes. These are reviewer inputs, not generated acceptance decisions. The existing addendum template remains the decision form.

## Fourth response completeness

`IFRS Accounting PR #232.pdf` corrects the machine count and retains scope deferrals. Completeness review finds zero matching artifact hashes among 15 entries (14 syntactically valid SHA-256 strings and one 63-character value), 13 absent paths, 32 unknown/32 omitted finding IDs, no complete 68-document decision inventory and remaining native/capability contradictions. See `FOURTH_RESPONSE_REVIEW.md` and `fourth-response-review.json`. No closures or native actions applied.
