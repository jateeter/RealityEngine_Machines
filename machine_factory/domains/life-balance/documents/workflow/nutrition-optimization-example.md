# Nutrition optimization and tracking: a worked desired-state journey

All people, records, decisions and counts below are synthetic. This is a reference workflow, not individualized nutritional advice or a performed live run.

## Situation and agreed outcome

Alex is an adult who wants a practical workday lunch routine and a clearer picture of meals and reported afternoon energy. Alex chooses a five-workday trial: prepare or select an acceptable lunch on four days, record what was actually eaten when comfortable doing so, and review feasibility and reported experience at week's end. These counts are user-selected behavior goals, not nutritional requirements or clinical thresholds. No weight-loss objective or calorie/macronutrient target is assumed.

The intake agent asks about preferences, food access, budget, preparation/storage facilities, relevant restrictions, desired tracking detail and existing professional instructions. Alex can decline optional information; unresolved restrictions prevent personalized menu selection until clarified. The profile records consent separately for meal logs, reminders and any sensor data. No wearable or CGM is required.

## 1. Establish context and a grounded basis

The environment retrieves the current profile and approved instructions, then applicable reviewed nutrition references. WHO's healthy-diet resource can supply general population context; the USDA DRI resource is a reference for professionally interpreted nutrient recommendations, not proof of Alex's exact needs; USDA FoodData Central documentation explains the provenance of food-composition data. These are candidate sources listed in `source-manifest.json`, not an included or clinically approved evidence corpus.

Before providing personalized advice, the deployed service must retrieve exact reviewed passages with document/chunk IDs, version, scope, source hash and index snapshot. If the evidence store is absent, it returns evidence-unavailable and can help organize Alex's stated routine without pretending to have evidence-backed personalized nutrient guidance. It never fabricates citations.

The input analyst classifies known observations and uncertainty. The machine adapter separately maps validated signals to the native binary/temporal contract. The analyst's prose and nutrient values are not written into native cells as if they were completion tokens.

## 2. Propose a feasible daily plan

The nutrition planner proposes two lunch options drawn from Alex's accepted options, with preparation steps and a backup that fits access and budget. Each recommendation has a rationale, relevant evidence references, uncertainties and an alternative. Ingredient/allergen suitability must be verified; unknown ingredients remain unresolved. An approved target, if later supplied, is stored with issuer, units, effective dates, calculation basis and review requirements.

Example user-facing proposal: “You chose a four-day lunch routine this week. Would you like to use one of your saved lunch options tomorrow and keep the other as a backup? I have not set a nutrient target. The ingredient details still need confirmation before I can compare nutritional coverage.” This respects the distinction between organizing preferences and making a personalized nutritional claim.

Alex approves a draft plan revision. Calendar/reminder actions require their own authorized scope. A grocery list remains a draft until accepted; purchases or messages to others need explicit authorization and a permitted tool. The drafting agent cannot approve its own review-required plan.

## 3. Execute and capture what happened

On each workday, reminders respect timezone, quiet hours and opt-out. Alex records an actual meal or declines. A meal record contains observed time, source, item/recipe, portion amount and unit if known, preparation state, estimation method, confidence/uncertainty and any correction history. Planned meals are never copied into actual intake without confirmation.

If food-composition calculation is permitted, a deterministic calculator links the selected food record ID, dataset version, nutrient unit, amount basis and edible portion. For each nutrient, estimated intake equals the source amount per basis multiplied by the amount eaten divided by that basis, with explicit unit conversions. Unknown portions or nutrients stay unknown. Avoid double-counting a recipe and its ingredients or conflating raw and prepared weights. Manufacturer-label and analytically derived data retain their distinct provenance. Human confirmation is required for ambiguous food matches.

A tool receipt confirms a reminder was created or a log stored; it does not assert that Alex ate a meal. Retries reuse the action idempotency key. Corrected meal data produces a new revision and marks dependent totals and summaries stale.

## 4. Adapt to a barrier

On day three, Alex reports no preparation time. The agent retrieves the current approved plan and preferences, proposes the accepted backup and asks whether reminders should change. It records time pressure as a barrier rather than labeling the person non-adherent. If the backup's ingredients or restrictions cannot be checked, the system asks for clarification instead of marking it safe.

The planner can propose schedule changes; it cannot autonomously change a clinical diet, prescribe supplements or adjust medication. Conflicting professional instructions or a concerning observation follow the approved escalation runbook, preserving scope and human acknowledgement.

## 5. Review the daily and weekly outcome

At evening review, the environment separates plan, confirmed actions, unknowns and reported experience. At week's end it might report: “You confirmed an acceptable lunch on four of five workdays. Intake details were recorded on three days; nutritional coverage cannot be concluded for the two incomplete days. You reported that the backup made one day easier. We have not established that lunch caused a change in afternoon energy.”

This is an illustrative result, not evidence from a real person. The user chooses whether to continue, simplify tracking, change options or seek professional review. No nutrient adequacy claim follows from completing the behavioral goal. User-reported burden and feasibility influence the next plan alongside relevant evidence.

## Machine and document trace

| Stage | Candidate machine responsibility | Documentary output |
|---|---|---|
| Context | LBL001–010 intake/goals | Versioned profile, purpose and consent scope |
| Meal routine | LBL011 meal-pattern stability; LBL018 family food context | Draft daily plan and practical constraints |
| Interpretation | LBL014 food/mood; LBL015 hydration; LBL071–080 monitoring where applicable | Qualified observations and retrieval/calculation receipts |
| Follow-through | LBL019 adherence; nutrition family interconnect | Barrier task and confirmed action status |
| Review | LBL020 executive review; LBL091–095 projection/actions | Reviewed summary and proposed revision |
| Cross-family journey | LBL096 metabolic/mood; LBL100 command center | Correlated acceptance trace and next-day feedback |

These are intended responsibilities, not proof that present template dispatchers implement the journey. Resolve issue #225 mapping, composition and execution defects before live acceptance.

## Acceptance evidence

A complete synthetic run must demonstrate real scoped retrieval and model execution, schema-valid proposals, authentic approval of the exact revision, authorized tool execution, persistent completion, correction/staleness propagation and next-day feedback. It must also demonstrate missing portions, unavailable evidence, conflicting restrictions, denied approval, duplicate callbacks, revoked consent and restart recovery. No fabricated approvals, source passages, sensor readings or outcome claims may fill a gap.

## Reference candidates

- [WHO healthy diet](https://www.who.int/news-room/fact-sheets/detail/healthy-diet)
- [USDA DRI calculator for healthcare professionals](https://www.nal.usda.gov/human-nutrition-and-food-safety/dri-calculator)
- [USDA FoodData Central data documentation](https://fdc.nal.usda.gov/data-documentation/)

Located 2026-10-28. URLs are navigation references; ingestion requires licensed/authorized snapshots, passage checks, applicability and qualified review. This example does not reproduce source text or adopt numerical dietary targets.
