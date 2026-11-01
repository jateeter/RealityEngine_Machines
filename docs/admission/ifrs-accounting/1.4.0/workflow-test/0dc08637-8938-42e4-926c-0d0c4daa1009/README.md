# TEST ONLY — completed domain approval workflow rehearsal

The operator explicitly waived independent sign-off for this testing run. No independent review was invented. All test approvals are labelled TEST_ONLY with productionApproval false.

The real prepare/submit/finalize state machine completed using disposable local Git repositories and clearly identified forge/native/toolchain fixtures. It copied and fingerprinted all 225 IFRS machines, recorded 53 test finding approvals and 68 test document approvals, ran 40 fixture gate events over two fixture scopes, generated a candidate ledger/archive, merged test branches locally and finalized a test-version tag and release fixture. The production source manifest remained experimental and unchanged.

The negative run intentionally failed the readiness-stage fixture with exit 7 and stopped before submit/finalize; no approval receipt was created. Production entrypoints reject TEST_ONLY state and WORKFLOW_FIXTURE scope evidence. Full contracts: 269 run, two live-runtime suites skipped, PASS.

Real native 3-of-3 parity, live CES, OWL toolchain execution, GitHub domain approval/release and live Manager Load Machines were not performed by the rehearsal. These records demonstrate workflow control flow, not production accounting acceptance or runtime correctness. Historical internal state names (including APPROVED_MERGED) are fixture states, always qualified by TEST_ONLY.

See test-workflow-summary.json, verification.json, operator-waiver.json and fixture event/log hashes. Reproduce using `scripts/approve-domain.sh test-run` as documented under `machine_factory/domains/ifrs-accounting/acceptance/test-workflow/`.
