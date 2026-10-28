# Daily outcome runbook

| Trigger | Behavior | Durable asset | Completion evidence |
|---|---|---|---|
| Onboarding/goal change | Agree goals, limits, consent, measures and review cadence | Profile and approved-plan revisions | User decision and scoped receipt |
| Morning/user-selected start | Reconcile sleep, schedule, preferences and unfinished tasks | Daily plan draft | Accepted exact revision or explicit decline |
| Scheduled/event check-in | Offer configured action or request missing observation | Observation/action record | Confirmed report or tool receipt, not inferred behavior |
| Practical barrier | Propose a feasible alternative within the same constraints | Barrier and plan revision | User choice; old tasks superseded |
| Concerning/conflicting input | Apply configured escalation criteria and scope | Escalation record | Acknowledged handoff or timed fallback |
| Evening/user-selected review | Compare plan, actual action, experience and burden | Outcome review | Coverage/missingness and agreed follow-up |
| Weekly/source/plan change | Review trends and invalidate affected artifacts | Revised goals/plan/evidence | Reviewed current revision and source references |

All triggers respect timezone/DST, quiet hours, pause, deduplication and burden budgets. Freshness windows and escalation rules must be configured and reviewed for the use case; this design does not invent clinical thresholds. No response, missing sensor data or declined tracking is not consent and not a zero-risk observation.

Cross-family examples: nutrition timing may conflict with work or sleep; exercise may conflict with a documented limitation; family coordination may conflict with private journaling. Preserve both constraints, route to the accountable owner and ask for a scoped decision.
