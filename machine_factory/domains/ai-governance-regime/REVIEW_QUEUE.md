# AI governance regime intake review queue

These findings come from the intake review of the received package (2026-11-20).
Each one stays open until its disposition is recorded here and the affected
step in [PACKAGE_STATUS.md](PACKAGE_STATUS.md) is redone. Findings marked
**owner** need an owner decision; the rest are mechanical.

| Finding | Subject | Blocks | Needs |
|---|---|---|---|
| GOV-R01 | Neither corpus is in the canonical machine form | conversion | **closed 2026-11-21**: built from the spec (GOV-SD-06) |
| GOV-R02 | Machine identity: base templates against corpus ids | conversion | **closed 2026-11-21**: 17 base machines (GOV-SD-04) |
| GOV-R03 | Machine and corpus counts disagree across documents | documents | **closed 2026-11-25**: the count is 18 (GOV-SD-09); received documents keep their counts as received, mapped in PACKAGE_STATUS.md |
| GOV-R04 | The region-allocation patch does not apply | allocation | layout decided (GOV-SD-05); allocation through the admission workflow |
| GOV-R05 | Corpus-315 declares itself `accepted` | admission | **closed 2026-11-21**: candidates are `candidate-not-admitted` |
| GOV-R06 | Two meanings of "quorum" | specification | **closed 2026-11-25**: approval quorum vs engine quorum (GOV-SD-13) |
| GOV-R07 | Framework alignment has no pinned sources | every alignment claim | **decided 2026-11-25**: ifrs pattern, scope per milestone (GOV-SD-14); `source-requirements.json` is step 3 work |
| GOV-R08 | The authoritative baseline (V0.18) is not in the workspace | every citation | **closed 2026-11-25**: pinned at `intake/BASELINE-V0.18-NIST.md` (GOV-SD-15) |
| GOV-R09 | Designed mechanisms are described as if they exist | workplan, specification | **decided 2026-11-25**: simulated Sources until producers exist, producers staged by milestone (GOV-SD-16) |
| GOV-R10 | Generated-text residue and stale cross-references | documents | mechanical |
| GOV-R11 | Continuous-input watchdogs are multi-valued machines | regression reach | **decided 2026-11-25**: shared extension corpus (GOV-SD-12); open until that corpus exists in RealityEngine_CI |
| GOV-R12 | Latch feedback and verdict composition need live confirmation | engine/PE behavior | live 3-of-3 run |
| GOV-R13 | GOV10 permits on every quiet step | specification | **closed 2026-11-21**: GOV10 runs per message on `req_egress` (GOV-SA-08) |
| GOV-R14 | The semantic amendments need owner review | specification | **closed 2026-11-25**: all 22 approved as proposed (GOV-SD-17) |
| GOV-R15 | 91% of CESs are single events; the obligations are temporal | machines | **rebuilt 2026-11-21 (0.2.0)**: chains for every order in §1.4; 62 of 141 CESs are chains |
| GOV-R16 | Templates reserve no lifecycle lanes (cells 2–7) | frames | **rebuilt**: every template reserves 2–7; the missing observations are GOV-R19 |
| GOV-R17 | Templates publish verdicts by bus, which clones may not | clone contract | **rebuilt**: only fixtures publish; templates report by continuation and completion |
| GOV-R18 | No agent triggers or response Sources | agentic workflows | **rebuilt**: 16 agents, each a neutral behavior with a completion Source; all in v1 (GOV-SD-07) |
| GOV-R19 | A clone's non-lane inputs need a writer | lifecycle | localAssetStorageStack: frame facts and the step agent's completion into the clone's block |
| GOV-R20 | 31 of the 38 Sources are partial or new | Sources | build per governance-sources.json; issues in each producing repository |
| GOV-R21 | The agent-runtime side of the split: A2A, not ACP, in v0.0.3 | agent runtime, GOV10 egress | Manager A2A AgentDriver (localLangChainStack), the MCP servers behind the capabilities; GOV10's egress Sources at the A2A/MCP boundary |
| GOV-R22 | The received wrapper-machine document diverges from the package | documents | full review 2026-11-25 (below); settled in the new baseline (GOV-R29); intake copy stays as received |
| GOV-R23 | Three Sources move to the peer domain threat-dynamics | Sources, admission order | threat-dynamics package and its published-lane contract (GOV-SD-10, GOV-SD-11) |
| GOV-R24 | GOV-SA-10 names `lane_quorum_met`; the build reads `quorum_valid` | amendments | **closed 2026-11-25**: erratum recorded on the amendment |
| GOV-R25 | GOV12 containment drives engines to a domain fail-safe vector | engine/arbiter, Phase 2 | confirm s_safe in the implementation; if absent, an engine feature on the three voters |
| GOV-R26 | GOV13's evidence pack reads the lifecycle's hash-chained log; the engine's own record is Design | lifecycle, engines | GOV13's producer reads the lifecycle log (implemented); the engine-side hash chain is staged with GOV13 |
| GOV-R27 | An agent must never resume an approval continuation (T15) | agent runtime | an explicit check in the A2A work: agents hold task-scoped capabilities only |
| GOV-R28 | The ISO 42001 / EU AI Act crosswalk needs re-deriving | alignment | step 3 `source-requirements.json`, per milestone (GOV-SD-14) |
| GOV-R30 | An output region keeps its last vector when nothing asserts (threat-dynamics TD-R08) | machines, fixtures | **resolved 2026-11-27**: outputs are latched (GOV-SD-19); the evaluator models it; GOV-SA-23 clears a decision when its condition ends |
| GOV-R31 | GOV-SA-23 needs owner review | specification | **owner** |
| GOV-R32 | Simulated continuous values sit 0.0001 inside a band edge (GOV-SA-01) | live run | confirm on the engines that no value leaves its band (cf. threat-dynamics TD-R05); move such values to mid-band if any does |
| GOV-R29 | The V0.18 baseline lags the v0.0.3 implementation | every citation | **owner 2026-11-25**: a new baseline from v0.0.3 progress. **provisionally closed 2026-11-25**: V0.19 (heads of 25 November 2026) is provisionally accepted and pinned at `intake/BASELINE-V0.19-NIST.md` (GOV-SD-18); final acceptance pending |

## GOV-R01: neither corpus is in the canonical machine form

- `intake/corpus-312.json` holds 312 machines with full automaton specs
  (`automatonSpec`: states, transitions, interval-predicate guards).
- `intake/corpus-315.json` holds those 312 ids plus `M-GOV-HRD-313`–`315`. It
  is in a compact form (`intervalPredicates`, `osreOutputs`) with no states or
  transitions, so for 312 of its machines the behavior exists only in the
  312-machine file.
- Neither file follows `schemas/machine.schema.json`. Neither has CES patterns,
  regions or arbitration in the corpus's terms, and neither is one file per
  machine.

Conversion has to merge the two: the 312 automata, plus the three hardening
machines written out in full from
[HARDENING_TRANSITION_RULES.md](HARDENING_TRANSITION_RULES.md). Then each machine
becomes a canonical file under `machines/domains/ai-governance-regime/`, with a
globally unique filename and one regular expression per CES.

## GOV-R02: machine identity (owner)

- The documents name 17 base governance templates, `M-GOV-01`–`17`. Only 15–17
  have formal rules here; 01–14 appear only as prose in SPECIFICATION.md.
- The corpora instead hold per-target-domain instances: 6 families × 13
  operational domains × 4 = 312, plus 3 global hardening machines.
- The hardening machines are `M-GOV-15`–`17` in the documents and
  `M-GOV-HRD-313`–`315` in the corpus (`baseGovernanceTemplate` links them).

Decide what a canonical machine is: a base template that the clone route
instantiates per target domain at run time (the cloneable-template model,
lass#8), or each of the 315 pre-expanded instances. 262 of the 315 are already
marked cloneable, which points to the template model and far fewer canonical
files.

## GOV-R03: counts disagree

| Source | Machines | Corpus total |
|---|---|---|
| `intake/README.v1.md`, the SoA template, `amendments/region-allocation.md` | 312 (260 + 52) | 1,864 |
| `intake/README.v2.md`, RESOLUTION_WORKPLAN.md, `amendments/region-allocation.patch.json` | 315 (262 + 53) | 1,867 |
| `machines/` today | — | 1,552 across 13 domains |

The documents need to state one count, taken from whatever R02 decides.

## GOV-R04: the region-allocation patch does not apply

All three of its `test` operations, and all four `replace` operations, name
paths that do not exist in `domains/region-allocation.json` or
`domains/domain-manifest.json`: `/corpusFootprint/endCell`,
`/cloneSpace/startCell`, `/summary/totalMachines`, `/summary/totalDomains`, and
`/neuraleseBand/minAllowedStartCell`. The real fields are
`vectorBudget.maxCellExclusive` (16944) and the `engine-clone-space` reserved
band (offset 20480, length 65536).

The admission workflow also regenerates region allocation from the canonical
machines, so it is not hand-patched (docs/DOMAIN_APPROVAL_WORKFLOW.md). The
proposed band `[16960:17087]` sits above the current footprint and below the
clone space, and overlaps no reserved band. Whether governance gets a fixed
band or follows the normal allocation is an owner decision. Cell numbers in
every document follow from it.

## GOV-R05: corpus-315 declares itself `accepted`

`intake/corpus-315.json` has `"status": "accepted"`, and the patch writes
`accepted` into the domain manifest. A new domain enters as experimental and
becomes accepted only through the admission workflow's gates.

## GOV-R06: two meanings of "quorum" (owner)

The documents use quorum for human signers: q-of-n signature bundles with
Byzantine bounds (n ≥ 3f + 1, q ≥ 2f + 1) and signer diversity across org
units. They also cite "3-of-3" engine parity. In this workspace, quorum is the
engine rule of `RealityEngine_CI/docs/QUORUM_CONTRACT.md`: unanimous among C++,
LSP and Scala, no majority, followers never vote. The specification needs
distinct terms for these, for example "approval quorum" against "engine
quorum". It also needs to say that an approval quorum never substitutes for
3-of-3 engine agreement. RESOLUTION_WORKPLAN.md 1.3 proposes changing
QUORUM_CONTRACT.md itself, which is a contract change.

## GOV-R07: framework alignment has no pinned sources (owner)

The domain's purpose is alignment with the frameworks the documents track, but
only ISO/IEC 42001 Annex A has a control-by-control mapping (the SoA
template). IFRS has `source-requirements.json`: every control, with its
obligation, required evidence and source span, against a pinned edition. This
domain needs the same for each framework it claims. The owner decides which
frameworks and editions are in scope for the first version; the rest are
recorded as out of scope, not as aligned.

## GOV-R08: the authoritative baseline is not in the workspace (owner)

Every received document defers to *RealityEngine: Deterministic Pre-Execution
Governance for Agentic AI with Temporally Bounded Incompleteness*, V0.18
(Working Draft, 19 November 2026). Its threat ids (`T1`–`T22`), timing
objectives (`TO-1`–`TO-18`), solutions (`S1`–`S6`) and propositions are used
throughout, but the document is not here. It needs to be pinned (path and
sha256) as a package source, or the citations are unresolvable.

## GOV-R09: designed mechanisms described as if they exist (owner)

The machines' input cells assume sources that do not exist in any repository
today:

- SPIFFE/TPM and in-toto/SLSA attestation;
- offline YubiHSM/TPM root tokens;
- CRL/OCSP quorum-keyring polling;
- AgentDojo red-team gating;
- behavioral canary probes;
- C2PA egress tagging;
- `kperf` latency gates;
- a "neuralese" band at ≥ 86016.

SPECIFICATION.md §1 itself says several are Design. RESOLUTION_WORKPLAN.md
assigns work to CPP, Scala, LSP, CI and localAssetStorageStack. Each item
needs an issue in its repository and an owner decision on the release it
belongs to. Until a source exists, a machine reading its cell can only be
tested against interned test sequences.

## GOV-R10: generated-text residue and stale cross-references

- `intake/ISO42001-SOA-RELEASE-NOTE.md` and `amendments/region-allocation.md`
  begin "Here is your file:".
- `schemas/governance-asset-shapes.md` names
  `AIGovernanceRegime_Asset_Shapes.shacl.ttl`, but the received file was the
  `-v2` edition.
- The SoA template's evidence container is a placeholder
  (`https://pod.enterprise.org/...`).
- The received READMEs give target locations (`docs/architecture/`,
  `audit-binder/iso42001/`, `localAssetStorageStack/schemas/`) that this
  package does not use.
- The documents refer to each other by their received names.

These are fixed when the documents are next revised. The intake copies stay as
received.

## GOV-R11: continuous-input watchdogs are multi-valued machines (owner)

GOV07, GOV08, GOV09, GOV12, GOV14 and GOV16 read continuous signals
(exposure rate, latency drift, backlog, harm count, TTL, canary drift), so they
declare `bitsPerElement: 8`. MACHINE_CONCEPT.md §9.3 says the engines do not yet
claim to agree about multi-valued machines and the corpus parity sweep sets
them aside. These machines therefore need a named extension corpus, or a
binarized source per signal (one bit per threshold the rules use), before the
parity gate can reach them.

## GOV-R12: latch feedback and verdict composition need live confirmation

Six machines read their previous `LATCH` output through `latch_q_prev`, and
GOV00 reads every machine's verdicts. Both are declared PE compositions
(`metadata.latchFeedback`, the `ai-governance-regime.verdicts` bus). The
fixtures were replayed only by the package's authoring evaluator, which
implements SURFACE_SPEC's transition rule. The engines and the PE have to show
the same trajectories 3-of-3 before any of this counts. For a clone, the
feedback cell belongs in the block's bus quarter; whether the engines
already support intra-machine bus cells there has to be checked.

## GOV-R13: GOV10 permits on every quiet step (owner)

The specification's `S_0 → S_1` for M-GOV-10 needs only
`egress_external_comm = 0`, so GOV10 asserts `PERMIT_DEPLOY` whenever no
external egress is in flight, with no request signal (GOV-SA-08). Under GOV00's
fold, that permit is enough to make the domain permit while nothing halts.
Decide whether egress gets a request signal, or whether GOV00 counts only
permits that answer a request.

## GOV-R14: the semantic amendments need owner review (closed)

Closed 2026-11-25: the owner approved all 22 as proposed (GOV-SD-17). Each
amendment now carries `status: approved`.


`semantic-amendments.json` lists 22 places (GOV-SA-01 to GOV-SA-22; it was 12
at 0.1.0, and the 0.2.0 rebuild added ten) where the
machines resolve a choice or a nondeterminism the specification leaves open.
Each CES cites the amendments it carries.

## GOV-R15 to GOV-R18: interconnectivity and agentic workflows

The review is in [CONNECTED_WORKFLOW.md](CONNECTED_WORKFLOW.md):
- **GOV-R15:** 130 of 143 CESs are one event, so they recognize no order.
- **GOV-R16:** no template reserves the lifecycle's lanes, so a frame cannot
  drive any of them.
- **GOV-R17:** the templates' verdict bus contradicts the rule that a clone
  leaves only by continuation or termination.
- **GOV-R18:** no machine dispatches an agent or reads an agent's result.

The document lists every machine-to-machine edge, the external Sources and
whether each exists today, the order each obligation needs, and seven agentic
workflows (W1–W7).

## GOV-R19: a clone's non-lane inputs need a writer

Today the lifecycle writes cells 2–7 of a clone, and nothing else writes the
clone's block. The templates' other inputs are frame facts (the request,
gates, signatures, the GOV11 diff, GOV06's quorum) and the step agent's
completion. They need one frame-scoped writer, and the lifecycle is the
natural one: it already holds the frame, and the agent writes its result to
the frame's `return`. The design is the lifecycle mapping the return through
the behavior's `responseMapping` into the completion cells, and the frame's
facts into the cells the template names. That keeps agents away from vectors
and keeps one writer per block. It is localAssetStorageStack work.

## GOV-R20: Sources to build

`governance-sources.json` lists 38 input signals:
- **7 exist:** the lifecycle lanes and the recertification TTL;
- **16 are partial:** something close exists, such as CI parity reports, the
  re_pki CRL, localAI drift, or the approval requests;
- **15 are new:** for example the exposure budget, egress classification, the
  lifecycle's principal-distinct observation and the operator console.

The 16 agents' completion Sources are new as well. Each needs an issue in the
repository that produces it.

## GOV-R21: the agent-runtime side of the split

Widened 2026-11-25. localLangChainStack (LangGraph agents over A2A) replaces
localOpenClawStack in v0.0.3, so the runtime is A2A, not ACP. The same holds
for GOV10: its egress Sources (`req_egress`, `egress_external_comm`,
`egress_art50_marked`) are read at the A2A/MCP boundary, and the builder now
says so.

The agents are runtime-neutral behaviors (GOV-SD-08), rendered by
localOpenClawStack `machine-behaviors/runtimes/` for OpenClaw and for ACP.
To run them on ACP (now A2A), three things are still needed:
- an ACP `AgentDriver` in RealityEngine_Manager's instantiation component;
- the MCP servers behind the capabilities marked `implemented: false`, with
  the frame-scoped lifecycle server first (#714);
- a choice of runtime, with its protocol version pinned.

## GOV-R22: the received wrapper-machine document diverges from the package

`intake/ORGANIZATIONAL-WRAPPER-MACHINE.md` (received as
`organizational-wrapper-governance-machine.md`, intaken 2026-11-25) restates
SPECIFICATION.md §3–4 and differs from the package in four places:
- it names **14** machines (M-GOV-01–14) where the package has 18 (GOV00–17,
  GOV-SD-04, GOV-SD-09);
- it gives the band as `[16960:17087]` and fixed shared cells, where each
  machine has its own regions in `[16960:17429]` (GOV-SD-05);
- its outputs `HALT_PROMOTION`, `REVOKE_EPOCH`, `PERMIT_DEPLOY` and
  `TRIGGER_INCIDENT` sit at cells 17056–17059, which are GOV07's input region
  here; the package's domain verdicts are GOV00's output;
- it names the voting runtimes "C++, Scala/Akka, and Common Lisp" and uses
  "quorum" both for them and for the human q-of-n signers (GOV-R06). The
  quorum contract names C++, LSP and Scala, unanimous.

These are fixed when the documents are next revised, as with GOV-R10.

### Full review (2026-11-25)

The owner re-submitted the document (byte-identical, sha256 `4c35a365…`). A
full read against the package, the approved amendments (GOV-SD-17) and the
V0.18 baseline adds these. The baseline lags the implementation (GOV-R29), so
the "status" findings are to be confirmed against v0.0.3, not taken from V0.18.

**Corrections**
- **C1–C2:** the four points above (14 machines, the band, verdict cells,
  runtime names).
- **C3:** frame lanes at cells 16960–16966. The lifecycle writes reserved cells
  2–7 of each clone (GOV-R16).
- **C4:** `lane_quorum_met`, `gate_kline_replay` and `gate_task_sufficiency`
  are not Sources here. The quorum is `quorum_valid`, GOV06's verdict carried
  by the frame. K-line replay and task sufficiency are agent completions:
  GOV04's replay analyst and GOV02's hazard-sufficiency analyst.
- **C5:** the document ties the rule-update quorum to the engines' parity. The
  rule-update quorum is a q-of-n of governance signers (V0.18 §7, where n ≥ 3f+1
  under Byzantine faults). The engine quorum is 3-of-3 unanimous and compares
  runtimes in regression (GOV-SD-13). Rust and Go are non-voting followers.
- **C6:** the signers (CRO, Lead AI Architect, General Counsel, CISO). GOV-SA-18
  requires Risk, Engineering and Legal, with no preparer among the signers.
- **C7:** "sub-microsecond cycles". In V0.18 this is objective TO-1 (p99 ≤ 820
  ns), unmeasured (GOV-R09).
- **C8:** Proposition 1 is paraphrased as "a projection tangent to the
  boundary makes enforcement complete". The proposition gives ker π ⊆ T_cΣ as
  a consequence of task sufficiency, not a test for it. Corollary 1 reads
  "RealityEngine is not complete".
- **C9:** GOV10 inspects "ACP or MCP". In v0.0.3 it is A2A/MCP (GOV-R21).
- **C10:** Art. 50 requires machine-readable marking. C2PA is one technique,
  not the requirement.

**Status claims to confirm against v0.0.3**
- The domain fail-safe vector s_safe (GOV-R25). V0.18 says it exists in no
  domain.
- In-bounds harm, T13. V0.18 lists it as open. Gap 3, the red-team gate, now
  comes from threat-dynamics.
- T4, T20 and T21. V0.18 lists them as Design.
- Verified Source channels, which is Gap 2 (SLSA attestation).
- "Every state progression emits a signed log record". The lifecycle's log is
  implemented: append-only, fsynced, hash-chained, with Ed25519 receipts and
  LDN annotations (V0.18 §6). The engine's own hash-chained record is Design
  (V0.18 Table 7). ActivityStreams is not cited in V0.18 (GOV-R26).
- Clones deallocated while parked.
- Agents without WebIDs, holding EdDSA capabilities only (GOV-R27).

**Omissions**
- GOV00, GOV15, GOV16 and GOV17.
- The seven wrapper gaps.
- The threat-dynamics peer domain and its three Sources (GOV-R23).
- 14 of the 38 signals.
- The approved amendments: dwell and debounce (SA-14, SA-19), feedback-cell
  latches (SA-06) and the Art. 73 overdue rule (SA-21).
- Simulated Sources as the test path (GOV-SD-16).
- Per-milestone framework scope (GOV-SD-14), and NIST AI 600-1.
- Per-source TLS.
- The crosswalk files separation of duties and human review under ISO 42001
  A.6. Roles are A.3.2 and use and oversight are A.9; A.6.2.8 is event logs
  (GOV-R28).

## GOV-R23: three Sources move to the peer domain threat-dynamics

Under GOV-SD-10 and GOV-SD-11, threat classification and observation are a
separate domain, and this domain only consumes its results. Three Sources in
`governance-sources.json` now name threat-dynamics as their producer
(`producerDomain`):

| Signal | Consumer | Gap |
|---|---|---|
| `gate_redteam_pass` | GOV01, input element 14 | 3, domain blind spots |
| `mon_canary_drift_score` | GOV16, input element 1 | 6, closed-API vendor drift |
| `mon_xdomain_mu_agg` | GOV16, input element 0 | 5, cascading delegation |

This finding closes when threat-dynamics declares the same three lanes in its
published-lane contract, and its machines produce them. Because this domain
consumes them, threat-dynamics is admitted first.
