# threat-dynamics review queue

| ID | Finding | Area | Owner / next step |
|---|---|---|---|
| TD-R01 | The specification is an initial public draft | sources | re-pin at the final edition; re-check every quoted NISTAML identifier and section |
| TD-R02 | 30 of 33 input signals have no producer yet (3 partial) | Sources | stage per milestone (GOV-SD-14); simulated Sources until then |
| TD-R03 | The semantic amendments TD-SA-01..06 need owner review, the thresholds above all | specification | **closed 2026-11-25**: all six approved as proposed (TD-SD-07) |
| TD-R04 | SURFACE_SPEC states the simulated-source defaults but not the sample formula | contract | **closed 2026-11-26**: formula in SURFACE_SPEC (RealityEngine_CI#866); LSP fixed (RealityEngine_LSP#201); binary, square, linear-ramp and constant agree live on five engines (`acceptance/live-run-2026-11-26.json`) |
| TD-R05 | Continuous cells are 8-bit on the engines | engines | **confirmed for the 45 simulations 2026-11-26**: every continuous value landed in its band on five engines; re-check when values change |
| TD-R06 | No engine has loaded these machines | engines | **live run 2026-11-26**: 45 of 45 simulations agree 3-of-3; Rust and Go agree on 45 of 45 (`acceptance/live-run-2026-11-26.json`). Registered at run time on the regression corpus, plaintext lane. **Extension-corpus boot 2026-11-27**: RealityEngine_CI regression run `20261127T000353Z` (`--machine-corpus extension`, TLS lane) booted the 11 candidates with the regression corpus. Every voter stage passed 3-of-3, 57 machines resident on every instance, no new failures. Both followers differed on five stages only because the follower lane's localAI slice was refused by localAI's clock lock. Fixed in RealityEngine_CI#880: re-run on the extension corpus, Rust and Go agree on all 11 compared stages. Open: the CES contract shard for `corpus:extension`, and a TLS-lane follower re-run |
| TD-R08 | An output region keeps its last vector on a step where nothing asserts | evaluator, specification | **owner**: model persistence in the evaluator, or have each observer assert an explicit vector on every step; and SURFACE_SPEC to state the rule |
| TD-R07 | `gate_redteam_pass` reaches GOV01 only through the lifecycle's frame-fact writer | lifecycle | localAssetStorageStack, with GOV-R19 |

## TD-R08: output persistence (owner)

Found in the 2026-11-26 live run. On a step where no CES asserts, every engine
(C++, LSP, Scala, Rust, Go) leaves the machine's output region as it was, so it
keeps the last vector written. The package's evaluator models that step as
all-zero. 18 of the 45 simulations differ from the authored expectation for this
reason alone; with the last vector carried forward all 45 match.

The consequence is semantic. Example: THR01 `hijack-after-injection`. At steps
16–19 the untrusted-instruction signal is up but not yet debounced. No CES
asserts, so the observer still shows the CLEAR it wrote at step 15.

Options:
- Accept persistence and model it in the evaluator. A level then means "last
  observed", not "now".
- Give each observer a CES that asserts on every step. For example, an explicit
  "observing" or all-zero vector while a breach is being debounced, as
  ai-governance-regime does for incident close (GOV-SA-20).

Either way, SURFACE_SPEC should state the rule; today it does not. The same
question applies to ai-governance-regime's fixtures (GOV-R30).

## TD-R03: amendments (closed)

Closed 2026-11-25: the owner approved all six as proposed (TD-SD-07), the
thresholds below included.


`semantic-amendments.json` lists six. TD-SA-05 (THR08 passes at an attack
success rate of 0.05 or less) and TD-SA-02 (a 3-step debounce) are the design
choices most open to judgement. TD-SA-06 ties THR09 and THR10 to GOV16's bands,
so a change to GOV16 has to change both.
