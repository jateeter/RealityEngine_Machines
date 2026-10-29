# Desired outcome of the Personal Health environment

Status: desired full-featured operation. Existing machine contracts are observations/recognizers, not a claim of deployed clinical performance.

## A person remains informed and in control

Personal Health provides a coherent operating environment for a resident, patient, caregiver and authorized care team. It connects daily routines, observations, home conditions and access barriers to timely, understandable support. It should help a person live according to their own priorities and approved care plan while reducing the effort needed to coordinate care. Success combines useful routine support, reliable acknowledgement of concerns, preserved privacy, fewer unresolved coordination tasks and outcomes meaningful to the person. A machine firing, a model answering or a notification being sent is not itself an improved health outcome.

The daily view shows what is known, what is missing, which tasks were confirmed, what is awaiting review and who owns follow-up. The person can correct a record, decline a check-in, pause optional monitoring, inspect evidence, change preferences and revoke delegated access. Caregivers see only their authorized scope. A family relationship does not automatically confer access to private adolescent, mental-health or detailed sensor records.

## Two paths cooperate without compromising urgency

The deterministic path ingests machine-ready measurements/events, applies explicit projections and evaluates CESs. Personal Health has heterogeneous native inputs: binary bits, scalar values, fall ordinals, raw count threshold bands and continuous vitals. A generic severity scale cannot replace these representations. Native decisions follow the unchanged comparator, timing, region and arbitration contracts. PE owns source composition, presence, dispatch and completion; RE evaluates vector state. Published buses expose compact normalized classifications and lane-scoped cross-domain routing. Raw health records, staff notes and device telemetry remain in authorized source ledgers.

The advisory path uses scoped retrieval and an LLM to interpret context, explain existing signals, identify missing information and draft support options. It can assess non-machine-ready external observations through the explicit native projection, where allowed. It must not overwrite upstream machine output or substitute its own conclusion for RE evaluation. Urgent configured response must not wait for a retrieval request or model turn. If RAG, an agent or a network fails, the configured deterministic alert and human fallback remain visible and testable.

## A complete operational loop

The environment maintains versioned profile/consent, approved care instructions, observations with provenance, evidence receipts, action proposals, decisions, execution receipts and outcome reviews. One accountable owner maintains each subject/window/asset head; other services contribute references rather than competing master versions. Every material decision links to current source, plan and data revisions. Corrections preserve history and invalidate affected summaries or approvals.

Input analysts qualify evidence. Planners propose support. Authorized humans or preauthorized policy decide effects within scope. Tool workers execute only permitted actions and record durable idempotent receipts. Outcome reviewers compare intended actions with actual observations and experience. A drafting agent does not authenticate its own approval. A reminder is not proof of medication administration; a held measurement is not a fresh measurement; an absent observation is not a reassuring zero.

Daily coordination covers medication confirmation and access, hydration and food access, sleep/activity, home conditions, care transitions, chronic conditions, social/transport access, caregiver workload and child/adolescent support. Cross-domain buses connect Health Services, Community Services, Built Space, Transportation and LifeBalance only through explicit lane and permission contracts. A transport barrier, a physiological concern and a stable routine must not all produce the same generic response.

## An example outcome

A resident and caregiver agree which observations matter and which tasks they can manage. The morning view combines current authorized instructions, fresh readings and unknowns. A medication confirmation remains pending until an authentic observation resolves it. A hydration concern prompts context-sensitive follow-up using the existing target from an approved plan; the LLM does not invent a fluid prescription. A detected fall follows the configured safety route without waiting for generation. Authorized caregivers acknowledge and record what they actually did. At evening review, the system reports completed, declined, unresolved and unavailable items separately and proposes the next manageable step.

The desired weekly outcome is a more coherent, less burdensome support routine with fewer unowned concerns, rather than forced adherence or constant surveillance. Evidence of benefit must include actual user/caregiver experience and relevant outcomes, with data coverage and uncertainty. Clinical efficacy requires a separate qualified evaluation; technical conformance alone cannot establish it.

## Release boundary

Full-featured release requires source acquisition and scope enforcement, native semantic preservation, reproducible scoped evidence, actual provider/action execution, enforced approvals, durable completion, acknowledged escalation, correction/staleness propagation and recovery. The current source review establishes foundations and gaps. This package supplies desired behavior, reusable guidance and acceptance design; it does not promote the domain or certify deployment.
