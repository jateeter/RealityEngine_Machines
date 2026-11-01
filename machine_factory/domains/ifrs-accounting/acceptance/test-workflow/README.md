# Domain approval workflow — test-only run

The operator explicitly waived independent sign-off for this verification/testing run. The verbatim statement and limits are recorded in `operator-waiver.json`. This authorizes test approvals, not production accounting acceptance.

Run from the Machines checkout with Bash 5:

```bash
/opt/homebrew/bin/bash scripts/approve-domain.sh test-run \
  --domain ifrs-accounting \
  --waiver-file machine_factory/domains/ifrs-accounting/acceptance/test-workflow/operator-waiver.json \
  --evidence /absolute/path/to/a/new/workflow-test-run
```

Use a new evidence directory every time. This command is stdlib-only and requires Git; it starts no engines, providers or hosted services. No real GitHub PR, release or tag is created by the test command.

## What the test exercises

It invokes the actual production `prepare`, `submit` and `finalize` functions using disposable local Git repositories. All 225 current IFRS machines are copied and fingerprinted. The test-only accounting decision ledger enumerates all 53 findings and 68 document types with APPROVED_FOR_WORKFLOW_TEST_ONLY, retaining the original source statuses. Native/toolchain gates and forge calls are explicitly labelled WORKFLOW_FIXTURE adapters; two fixture scopes exercise the scope-loop branches rather than claiming full native scope coverage.

| Transition | Test evidence |
|---|---|
| Prepare | Actual production control flow; fixture gate events with hashes; scoped input snapshots |
| Submit | Real local Git commits/pushes and evidence archive; simulated forge PR/candidate release |
| Merge | Real local Git merge into disposable main; no production branch modified |
| Finalize | Actual exact-tree/ledger checks; waiver marker instead of an invented reviewer approval; local test-version tag and simulated release |
| Catalog | Disposable domain manifest becomes accepted; source domain manifest stays unchanged |

The final summary is `test-workflow-summary.json`. Internal state files carry approvalContext TEST_ONLY and productionApproval false. Scope receipts state WORKFLOW_FIXTURE. The waiver is shown as WAIVED_FOR_WORKFLOW_TEST, never as an independent APPROVED review. Production submission/finalization reject test-only state, and production scope validation rejects fixture receipts by default.

The test does not measure actual CPP/LSP/Scala parity, record live CES, execute OWL tooling, exercise live Manager Load Machines, complete accounting analysis or publish production acceptance. Those are separate observations; the final summary explicitly records them as not run. Real source findings and document approvals are not changed by this rehearsal.

## Negative-path verification

Append `--fail-stage ifrs-accounting-readiness` or `--fail-stage domain-reasoning` to deliberately fail a fixture stage. The run must stop in FAILED_NOT_APPROVED before submission/finalization; no test approval receipt or release may appear. Existing real production guards are also covered by `domain_approval_test.py`; `domain_approval_rehearsal_test.py` verifies the full test path and isolation boundaries.
