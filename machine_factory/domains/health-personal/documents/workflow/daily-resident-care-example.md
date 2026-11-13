# Daily resident support with agentic AI and RAG

All people, observations and outcomes below are synthetic. This describes the intended operating environment, not a performed clinical run or individualized health advice. No medication dose, fluid volume, physiological threshold or emergency number is invented here.

## Situation and desired result

Morgan lives at home and chooses support from caregiver Sam for selected daily tasks. Morgan wants a manageable routine, clear ownership of unresolved concerns and fewer repeated questions. An authorized professional care plan supplies any clinical targets and instructions; no such issued plan is included in this package. Morgan grants Sam limited medication-confirmation and daily-task access, not unrestricted journal access. The trial's user-chosen operational goal is that each selected task is confirmed, declined or assigned a follow-up owner by evening. This goal does not establish medication efficacy, hydration adequacy or fall prevention.

## Morning: resolve scope before interpretation

The environment loads the current consent, plan and source-presence state. A HealthKit-derived reading is displayed with source time, unit, provenance and freshness. A removed scope is absent, not a zero-valued reading. A locked scope may retain held values under the bridge contract; the user interface labels them held/stale and does not describe them as new measurements. Production enforcement must avoid the bridge's development-open configuration when authentication is required.

The medication schedule is read from authentic approved instructions. A dispenser or caregiver event can be evidence of a recorded action, but the system must not infer ingestion from a reminder or a schedule. A missing confirmation is represented as unresolved, not automatically translated into a missed-dose clinical fact. The native medication adapter uses its declared pending/delayed and past-grace semantics only when the required observation and applicable plan are available.

The input analyst asks for the smallest missing fact. If the caregiver confirms a task, the record retains who reported it, when, what it establishes and what it does not. Contradictory reports are preserved and assigned for resolution. The LLM cannot order an extra dose or change the authorized schedule.

## Hydration: distinguish concern from access barrier

The hydration agent uses the current approved intake target only if applicable and available. It retrieves authorized observations and reviewed guidance rather than deriving a personalized target from general prose. `HydrationMonitor` uses its native two-bit projection; PE combines its output with activity, sleep and food-access status for `HydrationRiskResponseInterconnect`. The declared output lanes distinguish urgent hydration check, electrolyte review, access support and stable monitoring.

Suppose Morgan reports difficulty reaching drinking water. That observation is an access constraint requiring verification, not proof of a clinical condition. The planner proposes an authorized caregiver check and, where appropriate, a home-access task. It explains that the exact native bus must match the actual supplied context; this story does not claim every water-access report activates a particular CES. A stable output must not create unnecessary clinical/community work. An access-support output must not be silently converted into electrolyte advice.

RAG returns the current relevant plan and scoped reference passages, with document/chunk IDs, source versions, source/content hashes, index snapshot and applicability. The existing localAIStack health seed is a useful starting collection, but filenames alone are not sufficient evidence receipts for a personalized decision. If scoped evidence is unavailable, the system states that limitation and can organize an already-authorized task without pretending to supply new clinical guidance.

## A possible fall: preserve the native safety path

The fall pipeline begins with authentic sensor input, not an LLM-generated narrative. `FallSensorMotionPreaggregator` bins raw counts through threshold bands into a motion ordinal. `FallDetection` separately evaluates temporal motion/stillness evidence and emits a tier and confidence. These remain ordinal values: a RED tier is not a generic scalar one. The configured stillness source, sensor validity and timing must be demonstrated; the current HealthKit bridge does not supply a producer for raw fall-motion lane 4300.

If a configured RED sequence is observed in an accepted test, the deterministic alert route proceeds without waiting for RAG or model generation. The configured response owner receives an event with evidence and acknowledgement requirements. An LLM may provide a grounded explanation after the event, but it cannot suppress, downgrade, fabricate or mark the safety response complete. No claim of “confirmed injury” follows solely from the machine label. The relevant operational policy must resolve response timing and contacts before deployment; placeholder runbooks are not usable escalation destinations.

## Supervised execution and follow-up

Sam can acknowledge the permitted task only within the granted role. Approval references the exact action parameters, subject, revision/hash and expiry. The worker executes once using an idempotency key, persists a receipt and validates completion against the request. A notification receipt proves delivery/acceptance at that boundary, not that Sam arrived or Morgan received care. A follow-up observation or authentic acknowledgement resolves the next state.

If Sam is unavailable, the configured fallback owns the handoff. Provider outages, denied approval, cancellation, duplicate callbacks and restart each preserve explicit state. Urgent-response permissions must be defined separately from optional coaching permissions; this example does not create new authority to contact people or services.

## Evening: report the outcome honestly

The summary compares the selected tasks with confirmed reports and open questions. It might say: “Your selected routine has two confirmed tasks, one declined check-in and one unresolved item assigned to Sam. One reading is held from an earlier source state. The access task was acknowledged, but its result is not yet confirmed.” These illustrative counts are neither patient evidence nor acceptance results.

Morgan reviews burden and chooses whether to simplify tomorrow's routine. Corrections create immutable revisions and invalidate dependent estimates/summaries; a prior approval cannot authorize a changed proposal. A weekly review can examine task closure, acknowledgement latency, missingness, false-alert burden and reported usefulness. It cannot infer clinical improvement merely from more logged events.

## Candidate contract trace

| Step | Existing responsibility | Required durable evidence |
|---|---|---|
| Scope/data | HealthKit bridge, HealthKitVitalsMonitor, source mappings | Consent/source state, measurement provenance and freshness |
| Medication | MedicationAdherenceMonitor, medication access bus | Current instructions, authentic confirmation, unresolved gaps |
| Hydration/access | HydrationMonitor, food/activity/sleep producers, hydration bus | Native composition, lane choice, contextual evidence |
| Fall safety | Motion preaggregator, FallDetection, safety/care buses | Real producer, exact temporal native trace, independent alert acknowledgement |
| Daily review | DailyPatientCare, PatientWellness, WellnessAnalytics | Confirmed action/outcome distinction, correction lineage |

Responsibilities are candidate workflow coverage. The current audit's completion, projection and consumer integration gaps must be fixed and exercised before this becomes an operational guarantee.
