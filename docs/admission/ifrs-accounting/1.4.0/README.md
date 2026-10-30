# IFRS Accounting 1.4.0 admission decision

**FAILED_NOT_APPROVED.** The formal prepare run stopped at `preflight-interconnection_graph_test`: all 225 candidate machines have empty interconnection lists. No runtime reset, live CES recording, accepted release, or approval tag occurred. This is an attempted-admission record, not an approved-domain ledger.

Candidate source commit: `4ed4cab43d3cc32461331aba2b663637c6c07267`. CI source commit: `56fe64057d439c221a2f98ddabedd8b2b171b875`. Run: `5f70766e-7153-4628-a739-abcbbdc5248c`.

The experimental candidate includes the machine/domain, arbitration, semantic-bus and CES generator inventories, source manifest, reference document workflows and semantic ABoxes. All 225 original machine JSON definitions are preserved byte for byte. Bounded assertion tokens remain nominal levels 0, 0.5 and 1; financial quantities remain separately typed. Semantic projection now uses indexed bounded cells rather than integer tier/confidence properties.

Verified: 225 schemas; seven IFRS assertion/source-preservation tests; 21 approval workflow tests; 33 reference document lifecycle tests; IFRS ELK and HermiT consistency; current native engine build provenance. The full contract suite ran 242 tests with one connectivity failure and two skips. These results do not establish real financial-case acceptance or production agent deployment.

See `decision.json` for closure requirements and hashes; `state.json` and `events.json` retain actual commands, source revisions, timestamps and gate results. Full private build logs are deliberately excluded; the safe provenance result is included. Track closure in [Machines #229](https://github.com/jateeter/RealityEngine_Machines/issues/229) and [CI #670](https://github.com/jateeter/RealityEngine_CI/pull/670).

After closing the requirements, rerun `scripts/approve-domain.sh prepare` using a new evidence directory on committed clean feature branches, then use `submit` and `finalize` as documented in `docs/DOMAIN_APPROVAL_WORKFLOW.md`. Do not manufacture isolation exemptions or approval receipts.
