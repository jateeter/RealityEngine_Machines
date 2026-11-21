# AI governance regime: interconnectivity and agentic workflows

Review of the candidate machines (`machines/`, package 0.1.0) against what the
organizational wrapper has to do, 2026-11-21. It answers two questions:
1. What does each machine need to be connected to?
2. Which agentic workflows does the wrapper need?

It was the design input for the 0.2.0 rebuild, and it opened findings GOV-R15
to GOV-R18 in [REVIEW_QUEUE.md](REVIEW_QUEUE.md). **Status:** rebuilt to it on
2026-11-21, with every workflow and Source in v1. Section 0 describes 0.1.0;
the 0.2.0 record is in PACKAGE_STATUS.md.

## 0. What the candidates are today

| Measure | Value |
|---|---|
| CESs | 143: 130 of one event, 6 of two, 7 of three |
| Machines with any chain | GOV01, GOV04, GOV13, GOV15 |
| Buses | one, every machine's verdicts into GOV00 |
| Agent triggers (`agentBinding`, `aiTrigger`) | none |
| Response Sources (`writeBack` completions) | none |
| Templates declaring reserved lanes (cells 2–7) | none |

Five consequences follow.

1. **Mostly combinational, so order is lost.** A one-event CES tests the
   current Reality Event and nothing before it, so 91% of the CESs recognize
   no order. Per-step cost isn't the issue: engine cost grows with loaded
   machines and active events, and short paths are cheap. Expressiveness is.
   The wrapper's obligations are temporal:
   - a diff is shown before approval;
   - a dossier is drafted, then reviewed, then approved;
   - a breach is sustained, not one sample;
   - an emergency is ratified within its lease;
   - a notice is filed within its statutory clock.

   None of that is in a one-event CES. The latches (GOV-SA-06) work around
   the missing order with a feedback cell. The rebuild should express each
   order as a chain (§1.4).
2. **Templates cannot be driven by an asset frame.** The lifecycle writes a
   frame's lanes into the reserved input cells 2–7 of the clone running the
   step. It finds them by asking the engine for the template's
   `inputSemantics` entries that begin `reserved`
   (`localAssetStorageStack/lifecycle/src/engines.js`). No GOV template
   declares any, so every allocation would be recorded `unwired`.
3. **The verdict bus breaks the clone contract.** A clone's only ways out are
   a continuation or the termination its template declares (`agentBinding`
   writeBack, or the close of a document workflow). Nothing a clone writes is
   composed into a shared region (`RealityEngine_CI/docs/CONTINUATIONS_APPROVAL_CHAIN.md`).
   The bus edges from the eleven templates to GOV00 are therefore valid only
   for the templates themselves at rest, never for their clones. Fixtures may
   publish verdicts by bus; templates have to report through their
   continuation or a writeBack.
4. **Signals are treated as external that are really other machines'
   verdicts.** The specification gives 32 input cells as if each came from an
   outside Source. At least seven are the verdicts of other governance
   machines:
   - `lane_quorum_met` is GOV06's;
   - `gate_aibom_pinned` is GOV05's;
   - `lane_diff_rendered` is GOV11's precondition;
   - the domain-admission verdict is GOV01 + 02 + 03 + 05;
   - `lane_quorum_integrity_ok` is GOV17's;
   - the budget breach GOV12 re-tests is GOV07's latch;
   - the renewal frame is GOV14's.

   Today each machine re-tests the raw signal on its own, so the domain has
   no composition.
5. **No agent is ever dispatched, and no agent result ever comes back.** The
   wrapper's work is mostly preparation: dossiers, AIBOMs, quorum bundles,
   incident archives, audit packs. That is agent work under human approval,
   and the corpus has a fixed shape for it:
   - `agentBinding` names the agent and its trigger;
   - its `writeBack` declares a `pe-sensor` completion Source (`ingest`
     `/api/integrations/completions`, a `ttlMs`, normalized semantics) into
     the machine's own input lane;
   - the next CES reads that response.

   None of the 18 machines has one.

## 1. Interconnectivity needs

### 1.1 Asset-frame lanes (localAssetStorageStack lifecycle), every template

Every cloneable template (GOV01–05, 10–13, 15, 17) reserves input cells 2–7
and names them in `inputSemantics` with a `reserved` prefix, in the
lifecycle's order:

| Cell | Lifecycle lane | Specification signal it replaces |
|---|---|---|
| 2 | asset in its workflow | `lane_in_workflow` (16960) |
| 3 | a frame document re-pinned | `lane_re_pinned` (16961) |
| 4 | approved | `lane_approved` (16962) |
| 5 | rework requested | `lane_rework` (16963) |
| 6 | a step is running | none; new, and needed to tell parked from running |
| 7 | head is STALE | `lane_stale` (16964) |

That leaves cells 0–1 and 8–15 per template for everything else.

Three specification signals are lifecycle observations the lifecycle does not
make today. They need lifecycle work (a localAssetStorageStack issue) or a
machine source:
- **`lane_principal_distinct` (T15):** the lifecycle already refuses an
  approver who is the preparer or an agent, so a refused approval never sets
  lane 4. If that refusal is guaranteed, the signal is implied by lane 4. If
  the machines must see attempted self-approval (GOV04's
  `rejected-self-approval`), the lifecycle needs a "refused approval" lane.
- **`lane_diff_rendered`:** Manager or dokieli has to report that the reviewer
  was shown the canonical diff for this revision. There is no such
  observation today.
- **`lane_quorum_met`:** this is GOV06's verdict (§1.2), not a lifecycle lane.

### 1.2 Machine-to-machine: buses and continuations

Edges are native buses (PE-composed, `published-domain-bus-producer`) only
from fixtures. A template's result travels by its continuation (the next step's
template reads it from the frame's lanes) or by its writeBack.

| Producer | Signal | Consumers | Edge |
|---|---|---|---|
| GOV06 QuorumConsensusMonitor (fixture) | approval quorum valid | GOV04 promote, GOV15 ratify | bus: GOV06 output → consumers' input cell; replaces `lane_quorum_met` |
| GOV05 AIBOMProvenancePin (template) | AIBOM pinned for this frame | GOV04, GOV13 | continuation: GOV05 is a step of the epoch-promotion and audit-pack frames; its writeBack sets the frame's `aibom` observation |
| GOV11 HumanReviewAntiBiasGate (template) | diff shown to a distinct principal | every approval step: GOV01, 04, 13, 15, 17 | continuation: GOV11 runs as the review step before each approval; the approval template reads its result |
| GOV01, 02, 03, 05 | domain-admission verdicts | admission decision | a new **admission aggregator** (fixture, AND over the four), separate from GOV00; GOV00 is OR/veto over everything, admission is all-of-four |
| GOV04, 05, 06, 08, 09 | epoch-promotion verdicts | promotion decision | a new **epoch-promotion aggregator** (fixture, AND); GOV08 latency and GOV09 backlog veto a promotion |
| GOV07 ExposureBudgetWatchdog (fixture) | breach latched | GOV12 contain | bus: replaces GOV12's own re-test of `mon_mu_exhaust_rate` |
| GOV16 CrossDomainDelegationCap (fixture) | cross-domain breach | GOV12 contain | bus |
| GOV17 QuorumKeyRevocationLifecycle (template) | keyring compromised or rotating | GOV06 (quorum invalid), GOV15 (`lane_quorum_integrity_ok`) | writeBack: a keyring-state Source the fixtures read; and a lifecycle action invalidating every parked continuation signed by the revoked principal (GOV01, 04, 12, 13, 15) |
| GOV14 PeriodicRecertificationTimer (fixture) | renewal window opened | GOV01 | agentic trigger (§2 W7): opens a renewal frame. A machine output cannot create a frame |
| GOV00 verdict aggregator (fixture) | TRIGGER_INCIDENT | GOV12 | agentic trigger (§2 W5): opens an incident frame |
| every fixture | four verdicts | GOV00 | bus, as built (keep for fixtures only) |

### 1.3 External Sources

Each needs a Source: an id, a region in the consuming machine's input, `ttlMs`,
normalization and an owner. Each also needs a decision whether it is in v1.
"Exists" means something in the workspace produces it today.

| Signal | Producer | Exists today? |
|---|---|---|
| `gate_3of3_parity` | CI regression run (`regression-test.sh`, the parity stages) for the candidate corpus | yes; needs a Source adapter from the run report |
| `gate_kline_replay` | candidate rules replayed on near-miss K-lines in a sandbox universe | partly: K-line histories exist (SURFACE_SPEC "K-lines"), the replay harness does not |
| `gate_kperf_to1`, `mon_latency_drift` | per-step latency measurement | partly: corpus-parity-loop `timings` measure steps; no TO-1 gate |
| `gate_aibom_pinned` | AIBOM verifier over the frame's AIBOM document | no; the release manifest pins images by digest, the closest existing evidence |
| `gate_task_sufficiency` | hazard-coverage analysis of a domain manifest | no |
| `comp_iso42005_signed`, `comp_eu_fria_signed`, `comp_bias_audit_signed` | the dossier's own approval: document-workflow close in the frame | yes, as a frame lane once each dossier is its own asset |
| `comp_high_risk_domain` | domain manifest classification | no field today; needs a `domain-manifest.json` attribute |
| `egress_external_comm`, `egress_art50_marked` | the ACP/MCP boundary | no; OpenClaw and MCP have no egress classifier |
| `mon_mu_exhaust_rate` | engines' exposure budget | no: the budget is Design in V0.18 |
| `mon_t13_incident_cnt` | confirmed in-bounds harm, from incident triage | no |
| `mon_nearmiss_backlog` | unresolved near-miss K-lines against ring capacity | partly: K-lines exist, no near-miss classification |
| `mon_recert_ttl_rem` | time since a domain's last approval | yes, derivable from `domains/approvals/<domain>/` and the approval tags |
| `req_domain_admit` | `scripts/approve-domain.sh prepare` for a domain | yes, as the admission run's state |
| `req_epoch_swap` | a corpus or rule deployment (`approve-domain.sh deploy`, `domains/deployments/`) | yes, as the deployment request |
| `req_audit_pack_seal` | a release (`cut-release.sh`) or an audit request | yes for releases |
| `gate_redteam_pass` | adversarial evaluation | no |
| `gate_source_slsa_attested` | provenance attestation of Sources and builds | partly: `verify-build-provenance.py` checks engine build currency; no SLSA/in-toto |
| `lane_quorum_integrity_ok` | signer keys on the CRL, org-unit diversity, dwell | partly: `re_pki.py` issues, revokes and publishes a CRL for service keys; signer keys are not in it |
| `mon_xdomain_mu_agg` | aggregate exposure across domains | no |
| `mon_canary_drift_score` | drift on fixed canary prompts | partly: localAI records LLM drift (`/observations/drift`), which is recorded and not evaluated |

### 1.4 Temporal structure the CESs have to carry

These are the orders the obligations require, written as the chains the
rebuild should use. `[…]` is one Reality Event; `·` is the next step; `{k}` is
k consecutive steps, as k chained events. In the agent-loop rows, `prep` is a
completion Source (§2).

| Machine | Required order | Chain |
|---|---|---|
| GOV01, 13 | the agent prepares, the human reviews a rendered diff, a distinct human approves | `[in-workflow ∧ running] · [prep-complete] · [parked ∧ diff-shown]{dwell} · [approved]` |
| GOV04 | replay and parity before AIBOM pin, before quorum | `[req ∧ parity ∧ replay] · [aibom] · [awaiting]{dwell} · [quorum-valid]` |
| GOV11 | the diff precedes the approval and is viewed for a minimum dwell (ASI09) | `[diff ∧ ¬approved]{dwell} · [approved ∧ distinct]`; a blind approval is `[¬diff ∧ ¬approved] · [approved ∧ ¬diff]` |
| GOV06 | one signature per required org unit (Risk, Engineering, Legal) before quorum | one chain per arrival order, or one lane per unit with a final `[all three]` symbol; quorum on a single external bit hides the order and the diversity |
| GOV07, 08, 09, 16 | a breach must be sustained (debounce), and release needs a sustained return | `[breach]{k}` to set, `[in-band ∧ approved]{k}` to release, replacing the single-sample trip |
| GOV12 | contain, park the notice, close within the statutory clock (Art. 73) | `[harm] · [contained ∧ in-workflow] · [parked]{≤ T} · [approved ∧ ¬harm]`, plus an overdue CES `[parked]{T+1}` |
| GOV14 | a renewal window comes before expiry; reaching expiry without a window is its own finding | `[window] · … · [expired]` and `[current] · [expired]` |
| GOV15 | ratification within the lease | `[emergency] · [ratified]` inside the lease, `[emergency] · [stale]` at expiry, with the stale lane carrying the 4-hour lease |
| GOV17 | revoke, park the rotation, approve the rotation | `[revoked] · [in-workflow] · [parked]{dwell} · [approved ∧ rotated ∧ attested]` |
| GOV02, 03, 05, 10 | request, the agent's evaluation, then the verdict | `[req ∧ ¬prep] · [req ∧ prep-complete ∧ result]` |

Every `{k}` and `{T}` is a step count. A step count is not a wall-clock
duration: where an obligation is in hours (the lease, the Art. 73 clock), the
lifecycle's stale lane or a timer Source has to carry it.

### 1.5 Arbitration

Each completion Source writes its own machine's input lane, so it contends
with nothing. Two kinds of cell do need declarations in the arbitration
registry:
- the verdict elements GOV00 and the two new aggregators write;
- any cell where a fixture's bus output and a live Source meet.

The specification's "max" and "min" monoids become declared rules on those
cells (`docs/ARBITER_CONTRACT.md` §5).

## 2. Agentic workflows

### Shared rules

- **Agents prepare; humans approve.** No agent resumes an approval
  continuation. The lifecycle refuses it (T15), and every binding below
  declares `requiresHumanApproval: true` on any action that stages or
  publishes.
- **Every agent is dispatched by a CES and answers through a completion
  Source.** The pieces:
  - `agentBinding.trigger` is the CES that dispatches the agent;
  - `writeBack` is a `pe-sensor` completion into the dispatching machine's
    input (normalized semantics, `ttlMs`);
  - the machine's next CES reads that completion.

  The agent's document work happens on the frame's documents, through the
  lifecycle, and never as vector values.
- **Runtime.** Today a template's step agent is a per-clone OpenClaw agent
  (Manager `INSTANTIATION_AGENT=openclaw`), or the simulated agent without
  `--openclaw`. Two constraints apply:
  - OpenClaw is retired in v0.0.3;
  - its MCP servers are gateway-wide, an accepted deficiency (#714).

  Agents that need frame-scoped tools (reading the frame's documents,
  writing its return) depend on the frame-scoped MCP tools #714 tracks, or
  on their replacement runtime.
- **Autonomy.** The domain defaults to `supervised-act` (SPECIFICATION.md
  4.1). Watchdog agents run at `advise`.

### The workflows

| # | Workflow (spec) | Frame and steps | Dispatching CES → agent | Agent's job | Response Source | Human step | Governs |
|---|---|---|---|---|---|---|---|
| W1 | Domain admission (A: GOV01, 02, 03, 05, 11) | one frame per domain admission: prepare dossier → hazard analysis → bias audit → AIBOM → review → approve | GOV01 `[in-workflow ∧ running]` → **dossier preparer** | draft ISO/IEC 42005 impact assessment and Art. 27 FRIA from the domain manifest, hazards and corpus | `prep-complete`, `sections-unresolved` | review (diff via GOV11), approve by a distinct human | `scripts/approve-domain.sh`: admission waits on the admission aggregator's permit |
| | | | GOV02 `[req ∧ ¬prep]` → **hazard-sufficiency analyst** | evidence that every declared hazard is fiber-saturated or exposure-bounded | `sufficient`, `gaps` | sign-off | |
| | | | GOV03 `[req ∧ high-risk ∧ ¬prep]` → **bias-audit preparer** | data lineage and bias audit draft | `audit-drafted` | auditor sign-off | |
| | | | GOV05 `[req ∧ ¬prep]` → **AIBOM assembler** | collect model, quantization, tap, dictionary and runtime digests into the AIBOM | `aibom-complete`, `unpinned-items` | none (verifier decides) | |
| W2 | Rule-epoch promotion (B: GOV04, 05, 06, 11) | one frame per epoch: replay → parity → AIBOM → quorum bundle → signatures → promote | GOV04 `[req]` → **replay analyst** | run the candidate rules on near-miss K-lines in a sandbox; report fires and silences | `replay-pass`, `replay-fail` | none | corpus and rule deployments (`approve-domain.sh deploy`, `domains/deployments/`) |
| | | | GOV04 `[aibom]` → **quorum bundle assembler** | canonicalize (JCS) the bundle, route it to signers, track arrivals by org unit | `bundle-ready`, one lane per org unit signed | each signer signs | |
| W3 | Runtime assurance (C: GOV07, 08, 09, 16) | no frame; watchdog fixtures | GOV07, 16 latch set → **incident triage agent** (advise) | summarize the breach from K-lines; propose containment | `triage-complete`, `confirmed-harm` (feeds `mon_t13_incident_cnt`) | operator decides containment | live engines' exposure budget |
| | | | GOV09 `[backlog ≥ 0.80]` → **near-miss triage agent** | classify and resolve near-miss K-lines; draft candidate rules for W2 | `resolved-count` (lowers `mon_nearmiss_backlog`) | review of candidate rules (W2) | |
| | | | GOV16 throttle → **delegation clamp agent** (supervised-act) | reduce delegation depth on the offending A2A chains | `clamped` | approval to clamp | cross-domain agent delegation |
| W4 | Egress transparency (D: GOV10, 11) | per outbound communication | GOV10 `[external ∧ ¬marked]` → **egress provenance tagger** | add Art. 50 machine-readable provenance, or hold the message | `marked`, `held` | release a held message | the ACP/MCP boundary |
| | | | GOV11 review step → **diff renderer** (deterministic tool, not an LLM) | render the canonical diff of the exact revision | `diff-shown` (the missing lifecycle observation, §1.1) | the review itself | every approval |
| W5 | Incident and audit (E: GOV12, 13) | incident frame: contain → archive → notice → close | GOV00 incident, or GOV07/16 bus → **incident responder** | export the K-line bundle, draft the Art. 73 notice, keep the clock | `bundle-exported`, `notice-drafted` | file the notice; close | serious-incident obligations |
| | | audit-pack frame: collect → assemble → seal | GOV13 `[req ∧ parity ∧ aibom ∧ impact]` → **control crosswalk assembler** | collect receipts (dossiers, AIBOM, parity certificate, WAL, egress log, incident archive) into the ISO 42001 SoA / NIST RMF / EU AI Act evidence pack | `pack-assembled`, `missing-receipts` | external auditor verifies; a distinct human seals | releases (`cut-release.sh`, `release-manifest.py`): the pack seals each release's evidence |
| W6 | Hardening (H: GOV15, 17) | emergency frame: activate → lease → ratify or revoke | GOV15 `[req ∧ attested ∧ clean keys]` → **break-glass coordinator** | open the emergency epoch, start the lease, queue the post-hoc ratification as a W2 frame | `emergency-open`, `ratification-queued` | two root-token holders activate; the quorum ratifies | emergency deployments |
| | | rotation frame: revoke → invalidate → rotate | GOV17 `[revoked]` → **key rotation coordinator** | invalidate every parked continuation signed by the revoked principal; prepare the rotated keyring | `invalidated-count`, `keyring-ready` | the quorum approves the rotation | approval-quorum keys |
| W7 | Recertification (A: GOV14) | renewal opens a W1 frame | GOV14 renewal window → **renewal scheduler** | open a renewal admission frame for the domain, carrying the last dossier as its base | `renewal-frame-open` | as W1 | every admitted domain's annual recertification |

### What each workflow needs from the rest of the workspace

- **W1, W2, W5** need the lifecycle to hold each governance document
  (dossier, AIBOM, quorum bundle, audit pack) as an asset with its own
  revisions and approvals. The SHACL shapes in `schemas/` are the documents'
  contracts, and step 4 (asset catalog) turns them into
  `document-asset-catalog.json`.
- **W1, W2, W5** are the integration points with the processes the wrapper
  governs: `approve-domain.sh` (admission and deployment) and `cut-release.sh`
  with `release-manifest.py` (releases). Each needs a hook that reads the
  governing permit. That is a CI/Machines change for the owner to approve.
- **W3, W6** need Sources that don't exist yet (§1.3): the exposure budget,
  near-miss classification, signer-key CRL, cross-domain exposure.
- **Every workflow** needs its agents defined (`agent-candidates/`, step 7)
  and its runbooks (`runbooks/`, step 6).

## 3. What the rebuild changes, in order

1. Reserve cells 2–7 for the lifecycle lanes in every template (§1.1).
2. Replace single-sample trips and the latch feedback with chains (§1.4).
   Keep the feedback element only where no order expresses the state.
3. Add an `agentBinding` and `writeBack` completion lane per dispatching CES
   (§2). Make the next CES read the completion.
4. Replace the templates' verdict bus edges with continuation and writeBack
   reporting. Keep buses for fixtures, and add the admission and
   epoch-promotion aggregators (§1.2).
5. Declare the external Sources in scope for v1 and their regions (§1.3).
   Mark the rest as not available, so their machines are tested only against
   interned sequences.
6. Declare arbitration for the aggregators' verdict cells (§1.5).

Steps 1–4 are mechanical once the owner settles which workflows and Sources
are in v1. Step 5 is that decision.
