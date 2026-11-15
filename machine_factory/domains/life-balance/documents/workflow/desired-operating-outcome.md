# Desired outcome of the LifeBalance operating environment

Status: desired full-featured behavior, not a statement of current implementation.

## A day that works for the individual

LifeBalance helps a person turn what matters to them into a feasible daily plan, act on that plan with appropriate support, and learn from what actually happened. The environment coordinates nutrition, sleep, movement, stress, care, family obligations and social connection without forcing the person to manage ten separate assistants. It shows what it knows, what remains uncertain, why it suggests an action and what authority is required to take it.

Success is a sustainable routine that the person finds useful and can change. It is measured against chosen goals, relevant observations and acceptable effort, not the volume of messages, model confidence, agent completions or machine activations. The user can pause tracking, correct an observation, decline a recommendation, inspect a citation or revoke access without losing control of their plan.

The operating environment supports four related outcomes: personal agency; grounded, understandable guidance; reliable execution of approved actions; and honest longitudinal feedback. A technically successful action need not improve wellbeing, and an observed improvement does not establish causation or clinical efficacy.

## One coherent workspace

The person has a daily view showing the current plan, a few priorities, optional reminders, completed actions, unresolved questions and follow-up requests. A weekly view shows coverage and trends with their uncertainty and provenance. A care-team or guardian view is available only within the granted scope; it does not inherit all private journal content.

The environment maintains a versioned goals/preferences profile, consent and delegation records, applicable approved plans, timestamped observations, source evidence receipts, proposed actions, approval records and outcomes. A canonical document head prevents parallel agents from creating competing plans. Changes create immutable revisions and invalidate affected approvals or summaries.

The agentic layer is proactive within configured triggers, quiet hours and burden limits. It notices an expiring plan or repeated practical barrier, requests the smallest missing input and offers a revision. It does not invent observations or silently expand its authority. Users choose the cadence; a missed check-in is missing information, not failure or proof of a healthy state.

## Grounded reasoning and controlled action

Each interaction resolves subject, purpose, time window, consent, applicable plan and current evidence before retrieval. RAG retrieves authorized, applicable passages and personal evidence from separate collections. The LLM explains options and drafts plans using that context; deterministic checks validate fields, calculations, scope and tools. The machine layer recognizes defined signal patterns; native scores are not personal records, clinical facts or approvals.

Input analysts assess observations. Planners propose actions. An independent reviewer handles review-required content. Tool workers execute only permitted actions against the exact approved revision. The outcome reviewer compares intent with observed completion and experience. These are distinct responsibilities even when one service hosts several roles.

An observation, retrieval receipt, proposal, approval, dispatch, tool receipt, writeback and later outcome share a correlation chain. The environment distinguishes proposed, awaiting approval, denied/expired, running, succeeded/failed/cancelled and outcome-not-yet-known. Retries and restarts do not create duplicate effects. Service outages surface as explicit unavailable states with a defined fallback.

## Nutrition as the reference daily loop

A person wants a more manageable meal routine and better visibility into their nutrition. Their preferences, allergies/restrictions, budget, food access, preparation time and existing professional instructions constrain planning. The environment helps the person agree a practical goal, review approved evidence, choose feasible options, prepare a plan, log actual intake with uncertainty and adjust when barriers arise.

Nutrient optimization means balancing adequate intake, preferences, tolerability, affordability, availability and tracking burden within applicable guidance. It is not automatic calorie minimization, maximum supplement intake or blind optimization of one sensor metric. Any numerical nutrient or energy target requires an applicable, reviewed basis; a language model does not invent one.

The nutrition journey connects meal patterns, food/mood observations, hydration, food context, adherence and executive review to sleep, stress and daily scheduling. Optional sensors enrich context only when consented and interpretable. Photos and incomplete portions remain estimates. No meal log proves absorption, nutrient deficiency or disease; no short trend proves the meal caused a mood change.

## Whole-domain outcomes

| Family | Desired contribution to a coherent day |
|---|---|
| Intake/goals | Maintain the person's priorities, constraints and chosen definitions of progress. |
| Nutrition/metabolic | Support a feasible, evidence-grounded food routine and transparent intake tracking. |
| Sleep/circadian | Coordinate an approved sleep routine with work, school and recovery needs. |
| Movement/physical | Offer feasible activity within approved limitations and record experience. |
| Stress/psychotherapy | Support agreed coping practices and follow-up with appropriate boundaries. |
| Medication/care | Support the existing authorized care plan and preparation for professional review. |
| Adolescent/family/school | Coordinate scoped routines and delegated support while preserving privacy. |
| Testing/personalization | Qualify data quality, source, units, consent and applicability before interpretation. |
| Connection/harm reduction | Support chosen relationships, community actions and approved follow-up. |
| Projection/outcomes | Reconcile cross-family priorities, track results and propose reviewed adjustments. |

## Release definition

Full-featured operation requires a complete, traceable daily loop in each family, including missing-data and failure paths, with cross-family conflicts resolved visibly. The accepted release has grounded guidance, enforced permissions, durable state, tested recovery, reviewed reference collections and user-visible outcomes. This package specifies that destination; issue #225 tracks the implementation gaps and live acceptance gates.
