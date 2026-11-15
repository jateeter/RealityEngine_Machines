# RAG and daily workflow policy

## Grounded guidance, not replacement control logic

Use the core interaction template with the current family card and exact native contract. The default localAIStack seed already contains nine health-oriented documents. Treat their actual source, review status, applicability and retrieval behavior as inputs to verify; do not invent a new claim that RAG is absent, or assume that seeded text supplies all clinical authority.

Keep reference knowledge, personal evidence, procedural guidance, implementation reviews and synthetic evaluation cases separate. Apply tenant/subject/role/consent filters before retrieval. Retain full conditions/exceptions, provenance, stable passage IDs and current source/index versions. Filenames or a generated citation alone do not substantiate a recommendation. A changed source or corrected observation invalidates affected summaries; revoked data must stop being retrievable within the documented service objective.

The proposed `health_personal_workflow` collection contains only allowlisted package guidance. Existing health seed collections remain untouched. Production personal records belong in an authorized store with scope/deletion controls, not this repository. Candidate reference URLs in the source manifest require snapshots, licensing checks, qualified review and applicability before personalized health guidance. These candidates are not indexed here.

## Daily cadence

Onboarding establishes goals, access, consent, approved instructions and burden limits. Morning review reconciles current plans and fresh/held/absent data. Scheduled or event-driven checks request necessary observations and propose scoped support. Urgent configured native events proceed independently of LLM/RAG. Evening review separates confirmation, decline, unresolved concern and unavailable service; weekly review considers usefulness, coverage and coordination burden.

Respect timezone/DST, quiet hours, pause/snooze, correction and deduplication. A missing reply is not consent or a safe observation. Sensitive child/adolescent and caregiver contexts use explicit delegation and compartmented records. A relative's access to routine tasks does not authorize access to all mental-health records.

## Revision and recovery policy

One owner maintains each subject/window/asset head. Drafts cite current authentic evidence; humans/tools authenticate decisions at their real boundary. Upstream corrections, source changes, plan supersession, consent revocation and approval expiry mark affected downstream artifacts stale. Historical outcomes remain historical; the next plan references their immutable revisions rather than creating a mutable dependency cycle.

Persist workflow state and correlate observation, native event, retrieval, proposal, approval, tool receipt, writeback and outcome. Retry only with bounded policy/idempotency. Wrong-subject, wrong-region, stale-revision, malformed or out-of-contract completion must not become a valid native value. Do not wait inside a PE cycle for an agent or use an unverified model output to suppress an urgent native path.
