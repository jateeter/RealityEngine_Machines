# threat-dynamics review queue

| ID | Finding | Area | Owner / next step |
|---|---|---|---|
| TD-R01 | The specification is an initial public draft | sources | re-pin at the final edition; re-check every quoted NISTAML identifier and section |
| TD-R02 | 30 of 33 input signals have no producer yet (3 partial) | Sources | stage per milestone (GOV-SD-14); simulated Sources until then |
| TD-R03 | The semantic amendments TD-SA-01..06 need owner review, the thresholds above all | specification | **owner** |
| TD-R04 | SURFACE_SPEC states the simulated-source defaults but not the sample formula | contract | add the formula to SURFACE_SPEC (RealityEngine_CI); LSP and Scala to be confirmed against it |
| TD-R05 | Continuous cells are 8-bit on the engines | engines | confirm in the live extension-corpus run that no simulated value crosses a band edge |
| TD-R06 | No engine has loaded these machines | engines | live 3-of-3 on the shared extension corpus (roadmap Phase 3), followers included |
| TD-R07 | `gate_redteam_pass` reaches GOV01 only through the lifecycle's frame-fact writer | lifecycle | localAssetStorageStack, with GOV-R19 |

## TD-R03: amendments

`semantic-amendments.json` lists six. TD-SA-05 (THR08 passes at an attack
success rate of 0.05 or less) and TD-SA-02 (a 3-step debounce) are the design
choices most open to judgement. TD-SA-06 ties THR09 and THR10 to GOV16's bands,
so a change to GOV16 has to change both.
