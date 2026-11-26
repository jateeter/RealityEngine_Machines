# RealityEngine: Deterministic Pre-Execution Governance for Agentic AI with Temporally Bounded Incompleteness

John Teeter, Open Commons (OpenCommons.org), DeepKernel Lab, research@opencommons.org

Version 0.19, v0.0.3 progress revision (working draft), 25 November 2026

**Status of this draft.** V0.19 brings the implementation record up to the repository heads of 25 November 2026: release v0.0.2 (closed 21 November) and the release v0.0.3 work merged since V0.18. The results, proofs, hypotheses and objectives are V0.18's; only statuses, counts and locations change, each with its source in Appendix E. Where V0.18 contradicted itself (TO-3 against Table 7 on $\mathbf{s}_{\mathrm{safe}}$) the code decides. The draft contains no new measurements beyond the release v0.0.2 certification record (Section 9.1). The V0.18 status paragraph follows unchanged.

*V0.18:* V0.18 is the academic-paper edition of the consolidated manuscript. It keeps V0.16 as the factual baseline (repository heads of 14 and 18 November 2026), takes from V0.17 the extensions that survive review, and states each of them as a result with its hypotheses and a complete proof (Sections 3 and 5, Appendix 15). V0.17’s “certified 10/10” results that depend on unmeasured numbers or misapplied theorems are restated as hypotheses (Section 12), and its benchmark figures are withdrawn because no runs produced them. Appendix 17 records how every V0.17 claim was treated. Statements carry one status label: *Implemented*, *Partial*, *Specified*, *Design*, *Objective* or *Hypothesis* (Section 1.1). Results that need runs not yet performed are marked **\[PENDING: …\]**; decisions only the author can make are marked **\[AUTHOR: …\]**. The draft contains no new measurements. This revision aligns vocabulary with NIST SP 2400-102e2026 \[6\] where the meanings coincide (Section 2.1); no result, status or claim has changed.

## Abstract

Agents built on large language models (LLMs) now call tools, change records and actuate physical systems. Their behavior is learned rather than specified, so a non-zero probability of a harmful action remains, and guardrails that inspect a projection of the agent’s context inherit a structural limit: a verifier cannot separate contexts that its projection maps to the same value. We present RealityEngine, a governance layer that evaluates an agent’s actions against domain-declared Critical Event Sequences, using deterministic finite automata over interval predicates on a bounded vector encoding of the action and its context. We make three contributions. First, we sharpen the limit: for any linear observation of lower dimension, a safe and a hazardous context collide wherever the unobserved directions cross the hazard boundary, and the colliding observations form a set of positive measure; a governor is complete for a declared hazard exactly when the hazard set is a union of its fibers. RealityEngine’s own encoding is such a projection, so RealityEngine is not complete. Second, we show that the incompleteness can be bounded in time. Agent responses and tool results return through *Sources*, are verified asynchronously, and are folded into the next state only after verification. With a consequence margin and an exposure budget that is conserved when it is split across messages, at most $\bar\mu$ consequential actions are admitted across an entire distributed causal cone before a hazard’s verdict arrives or a domain fail-safe output takes over, and verdict-gated staging commits no effect of a detected hazard. Third, we describe an implementation in three voting runtimes (C++, Scala/Akka, Common Lisp) and three conformance followers (Rust, Go and a TypeScript perception engine) over a shared corpus of 1,552 machines in 13 domains, with parity proven in regression and certified in a tagged release; a governed asset workflow in which each dispatch is a procedure call over a Solid-backed frame; eighteen timing objectives with gates on stated hardware; and a learning path from near misses to readable rules. We state which components are implemented and which are designed, and give an evaluation plan whose results are pending.

# 1 Introduction

Agentic systems orchestrate multi-step tool calls, run code, query private data and issue operational transactions through protocols such as the Model Context Protocol (MCP) \[46\] and the Agent Client Protocol (ACP) \[2\]. A model trained by maximum likelihood keeps a non-zero probability $\epsilon$ of producing a harmful action at each step. If the steps were independent, the probability of at least one such action over $H$ steps would be $1-(1-\epsilon)^H$, which tends to one as $H$ grows. Independence is an idealization, but the point survives it: when the agent holds actuation capability, a small per-step error rate becomes operational risk. Most deployed guardrails are what NIST SP 2400-102 \[6\] calls *input and output guardrails*: probabilistic classifiers, dialogue rails or post-hoc output validators (Section 2). They reduce empirical failure rates without bounding them. RealityEngine belongs to NIST’s category of *action-level policy enforcement*, in a deterministic form.

RealityEngine takes the position, shared with recent work on deterministic architectural boundaries \[16, 40, 42\], that the decision to release an action should be made by a deterministic component between the agent and the world, before the action takes effect, and that this component’s behavior should be specifiable, testable and replayable.

#### The question this paper answers.

A deterministic gate is still a function of what it observes. Radenković et al. \[51\] show that a verifier working on a projection of the execution context cannot separate contexts that share that projection; NIST reaches the same conclusion for guardrails in general, that no finite set is universally robust against adversarial prompts \[6, Sec. 5.1.1.1\]. RealityEngine is subject to the same limit, because its input encoding is a projection. We therefore ask what a deterministic governor *can* guarantee once completeness is out of reach. Our answer is *temporally bounded incompleteness*: a hazard that the admission check cannot see is caught when its effects return through a verified channel, and until then the number of consequential steps that may proceed on the hazardous state is bounded by a declared budget, across every node the action’s consequences reach.

#### Contributions.

1.  **A sharpened limit** (Section 3). For a linear observation map of lower dimension, same-fiber collisions between safe and hazardous contexts occur wherever an unobserved direction crosses the hazard boundary, and they occupy a set of observations of positive measure (Theorem 2). Completeness for a declared hazard holds exactly when the hazard set is saturated by fibers (Proposition 1). This gives task-sufficiency a precise, checkable meaning.

2.  **Bounded exposure** (Section 5). Definitions of the exposure margin, the operational separatrix with an $L_\infty$ distance, consequential steps and cones of awareness, and five results: the per-instance bound, coverage, the per-path bound, a whole-cone bound under conserved split budgets (Proposition 5), and commit safety under verdict-gated staging (Proposition 6), with a corrected escape bound for repeated verification (Proposition 7).

3.  **An architecture and its implementation** (Sections 4–9): actions and context encoded as Input State Reality Events (ISRE) and recognized by asynchronous deterministic finite automata (aDFA) over interval predicates; a return path through Sources and semantic evaluation; three voting runtimes and two followers over one machine corpus with parity proven in regression; and a governed asset workflow with cloneable template machines and one-shot, capability-gated continuations.

4.  **Timing as objectives** (Section 10): eighteen timing objectives, each with a clock, a gate and a recursive design–implementation loop, on declared reference hardware.

5.  **A learning path and research agenda** (Section 12): K-lines as replayable episodes, neuralese Reality Events, TopK node selection and a TopK sparse-autoencoder prism that turns near misses into readable rules; a provable error bound for coarse-grained hazard prediction (Proposition 8); and the open hypotheses about residual-stream dynamics stated as hypotheses.

#### What this paper does not claim.

It does not claim completeness over undeclared hazards; detection of an action whose encoded signals lie within declared bounds but whose effect is harmful; any latency, interception or false-positive figure (none has been measured); bit-identical cross-engine execution (parity today is pass-set equality, Section 9.1); or that the admit/reject/replace decision on agent-initiated actions is implemented (it is design, Section 4.7).

## 1.1 Status labels

*Implemented*: in the public repositories at the stated heads. *Partial*: some of the defining function is there. *Specified*: written in a repository contract, not implemented. *Design*: described here only. *Objective*: a measurable target with a gate, never reported as met until its gate passes at a tagged commit on stated hardware. *Hypothesis*: an empirical claim about models or dynamics, to be tested.

# 2 Background and Related Work

#### Probabilistic and dialogue-level guardrails.

NeMo Guardrails \[52\] expresses dialogue rails in Colang and typically adds model calls per turn. Llama Guard \[39\] is a fine-tuned safety classifier. Guardrails AI \[35\] validates structured outputs after generation. Amazon Bedrock Guardrails \[15\] offers managed content filters, grounding checks and Automated Reasoning checks. These reduce failure rates; none is designed to give a deterministic, replayable release decision for an outbound tool call.

#### Reference monitors and capabilities.

A reference monitor must mediate every access, resist tampering and be small enough to verify \[12, 57\]. Capability systems such as KeyKOS \[37\] and the confused-deputy analysis \[38\] motivate binding authority to the request; CapChain \[17\] defines attenuating capability tokens.

#### Agent-specific architectures.

Bhattarai and Vu \[16\] argue that trustworthy agentic AI requires deterministic architectural boundaries (the Trinity Defense Architecture). AgentBound \[40\] composes delegated authorization, signed behavioral constitutions and site action contracts into a permit/review/deny decision with verifiable receipts, and is the closest prior work. ARES \[42\] mediates computer-use agents at the endpoint resource layer. CaMeL \[25\] separates control flow from untrusted data, an *information-flow control* approach in NIST’s terms; Progent \[60\] checks tool calls against symbolic least-privilege policies. AgentDojo \[26\] benchmarks indirect prompt injection against tool-using agents.

#### The OEE execution calculus.

Radenković et al. \[51\] separate an admissibility criterion $\tau$, a domain specification $\omega_\tau$ and an execution context $C$, prove that external guardrails working on a projection of $C$ are incomplete, and require execution, verification and recording to form one act. We adopt their three levels and their incompleteness result (Theorem 1), sharpen the latter, and replace atomic execution with verify-then-commit plus a bounded return path, because atomic commit with the outside world is not generally achievable.

#### Runtime assurance.

Simplex architectures \[58\] and shielding \[11\] place a verified monitor between an unverified controller and the plant and switch to a safe controller on violation. RealityEngine’s domain fail-safe vectors follow this pattern, and its return path adds a bounded window in which a violation that the monitor could not see at admission is detected.

#### Explicit organizational descriptions.

Barber and Hewitt \[13\] treated office work as problem solving over explicit, machine-held descriptions of an organization, and OMEGA \[14\] supported that work with descriptions that workers consult and extend. RealityEngine inherits the stance that the rules governing actions should be explicit, inspectable descriptions held by the system; its domain specification plays that role, and its approval chains are descendants of the office procedures they described.

#### Memory, near misses and interpretability.

Minsky’s K-lines \[47\] and reflective hierarchy \[48\] and Winston’s near-miss learning \[64\] shape the learning path. Superposition \[29\] explains why single neurons are polysemantic; sparse dictionary learning \[20\] and TopK autoencoders \[45, 33\] recover sparser features, which RealityEngine uses only off the operational path.

#### Positioning.

RealityEngine is closest to AgentBound and Trinity. It differs in (i) deciding by finite-automaton recognition over a domain-declared vector encoding; (ii) executing one shared machine corpus on three independent runtimes; (iii) emitting domain-specific fail-safe outputs rather than deny-only decisions; (iv) bounding, in logical steps, the exposure left by its own incompleteness; and (v) giving each dispatch a governed asset context whose continuation log is the approval evidence.

**Table 1.** Positioning against related systems. \[AUTHOR: verify each cell against the cited papers before release\]

| System             | Decision mechanism                                      | Deterministic before effect              | Main limitation                 |
|:-------------------|:--------------------------------------------------------|:-----------------------------------------|:--------------------------------|
| NeMo Guardrails    | Colang rails, LLM calls                                 | No                                       | Rails themselves use LLMs       |
| Llama Guard        | Fine-tuned classifier                                   | No                                       | Probabilistic; evadable         |
| Guardrails AI      | Output validators                                       | Partly (after generation)                | Validates output, not actuation |
| Bedrock Guardrails | Managed filters, grounding, AR checks                   | Partly                                   | Content-focused                 |
| AgentBound         | Three-authority composition, receipts                   | Yes                                      | Policy authoring burden         |
| ARES               | Endpoint resource mediation                             | Yes                                      | Requires endpoint hooks         |
| Trinity            | Reference monitor, IFC labels, privilege separation     | Yes                                      | Position paper                  |
| RealityEngine      | aDFA over ISRE interval predicates; bounded return path | Yes (core); admission decision is design | Domain modeling; in-bounds harm |

## 2.1 Terminology alignment with NIST SP 2400-102

Where a concept in this paper has the same meaning as a term in the agentic taxonomy of NIST SP 2400-102e2026 (Initial Public Draft) \[6\], we use NIST’s term. Terms with no NIST counterpart keep their definitions here. NIST’s draft writes “Super Intelligence (SI)” for what this paper, like the NIST AI RMF and AI 100-2 E2025, calls AI; we keep “AI”. The draft is under public comment and its terms may change.

**Table 2.** Terms in this paper and their NIST SP 2400-102e2026 counterparts.

| This paper                                                                                                       | NIST SP 2400-102e2026                                                | Relation                                                                                                   |
|:-----------------------------------------------------------------------------------------------------------------|:---------------------------------------------------------------------|:-----------------------------------------------------------------------------------------------------------|
| Agent, tool, memory, multi-agent system                                                                          | Same terms (Sec. 4)                                                  | Same meaning                                                                                               |
| Task instructions, planning, execution, observation                                                              | Stages in agentic workflows (Sec. 4.1.1)                             | Admission acts on each proposed action between planning and execution; the return path acts at observation |
| Probabilistic and dialogue-level guardrails                                                                      | Input and output guardrails (Sec. 4.2)                               | Same meaning                                                                                               |
| Deterministic pre-execution governance; admission decision                                                       | Action-level policy enforcement (Sec. 4.2)                           | RealityEngine is a deterministic form                                                                      |
| aDFA recognition of declared hazard sequences                                                                    | Trajectory-level monitoring (Sec. 4.2)                               | Deterministic, evaluated before execution                                                                  |
| Poisoned tool result (T14)                                                                                       | Indirect prompt injection, NISTAML.015; malicious tools, NISTAML.063 | Same meaning                                                                                               |
| Agent redirected to an attacker’s task                                                                           | Agent hijacking, NISTAML.061                                         | Same meaning                                                                                               |
| Record poisoning (T10)                                                                                           | Memory poisoning, NISTAML.062                                        | Overlaps where the record (K-lines) informs later decisions                                                |
| Denial of service (T6)                                                                                           | Resource exhaustion, NISTAML.066                                     | T6 is broader                                                                                              |
| Software supply chain (T8)                                                                                       | Supply chain attacks, NISTAML.05                                     | Different scope: NIST covers models, tools and skills; T8 covers the engines’ own builds                   |
| Adversary who controls what the agent reads or outputs                                                           | Query access; resource control; model control (Sec. 4.1.3)           | Same meaning                                                                                               |
| Sandboxing; least privilege; information-flow control                                                            | Same terms (Secs. 4.4–4.6)                                           | Same meaning                                                                                               |
| ISRE, OSRE, aDFA, exposure margin, consequential step, cone of awareness, fail-safe vector, Source, split budget | No counterpart                                                       | Defined in this paper                                                                                      |

# 3 Model and the Limits of Projection

## 3.1 Execution model

Following \[51\], a governed system is described by a triple $\langle\tau,\omega_\tau,C\rangle$. In RealityEngine, $\tau$ is the set of Critical Event Sequences (CES), each a regular language over interval predicates; $\omega_\tau$ is the domain manifest (`RealityEngine_Machines/domains/domain-manifest.json`) with its machine definitions, and, as the design adds them, its declared hazards $H(\omega_\tau)$, fail-safe vectors $\mathbf{s}_{\mathrm{safe}}$, consequence margin $\delta$ and exposure budget $\bar\mu$; and $\mathcal C$ is the space of execution contexts (the agent’s prompt and state, tool arguments, records, and physical telemetry). A hazard $h$ defines a set $\mathcal C_h\subseteq\mathcal C$ of contexts in which the proposed action is harmful; $\mathcal C_{\mathrm{safe}}$ is its complement among contexts the domain admits.

A *governor* observes a context through a map $\pi:\mathcal C\to V$ and decides with a function $g:V\to\{\mathrm{admit},\mathrm{reject}\}$. For a fixed $\pi$, the *fiber* over $v\in V$ is $\pi^{-1}(v)=\{c\in\mathcal C:\pi(c)=v\}$.

**Theorem 1** (Same-fiber indistinguishability \[51\]). *If $c_1\in\mathcal C_{\mathrm{safe}}$ and $c_2\in\mathcal C_h$ satisfy $\pi(c_1)=\pi(c_2)$, then every governor $g\circ\pi$ admits $c_2$ whenever it admits $c_1$.*

*Proof.* $g(\pi(c_1))=g(\pi(c_2))$ because the arguments are equal. ◻

Theorem 1 is conditional on the existence of a colliding pair. The next result says when such pairs exist, and how many there are, for the case that matters in practice: a governor that observes fewer independent quantities than the context has.

**Theorem 2** (Collisions are generic). *Let $\mathcal C$ be an open subset of $\mathbb R^D$, let $\mathcal C_{\mathrm{safe}}$ and $\mathcal C_h$ be disjoint open subsets of $\mathcal C$, and let $c_0\in\mathcal C$ be a point near which the two sets are separated by a $C^1$ hypersurface $\Sigma$: there is a neighborhood $U$ of $c_0$ and a $C^1$ function $\phi$ with $\nabla\phi(c_0)\neq0$ such that $U\cap\mathcal C_{\mathrm{safe}}=\{\phi<0\}\cap U$ and $U\cap\mathcal C_h=\{\phi>0\}\cap U$. Let $\pi:\mathbb R^D\to V=\mathbb R^d$ be linear and surjective with $d<D$, and let $\mathbf{n}_0=\nabla\phi(c_0)$.*

1.  *If $\ker\pi\not\subseteq T_{c_0}\Sigma$, that is, if some $\mathbf{u}\in\ker\pi$ has $\langle\mathbf{u},\mathbf{n}_0\rangle\neq0$, then there exist $c_1\in\mathcal C_{\mathrm{safe}}$ and $c_2\in\mathcal C_h$ with $\pi(c_1)=\pi(c_2)$.*

2.  *Under the same condition, the set of observations $v\in V$ whose fiber meets both $\mathcal C_{\mathrm{safe}}$ and $\mathcal C_h$ contains a non-empty open set, and so has positive Lebesgue measure in $V$.*

The proof is in Appendix 15. The condition fails only when every unobserved direction is tangent to the hazard boundary at $c_0$, that is, when the boundary does not depend, to first order, on anything the governor cannot see. Collisions are therefore not isolated coincidences: wherever the hazard depends on an unobserved direction, they fill an open set of observations. (V0.17 justified the condition by an appeal to Sard’s theorem; the condition is in fact a statement about the hazard’s geometry, not a measure-zero accident.) The same argument holds for a smooth map $\pi$ that is a submersion near $c_0$, with $\ker d\pi(c_0)$ in place of $\ker\pi$.

**Definition 1** (Task-sufficient observation). An observation $\pi$ is *task-sufficient* for a hazard $h$ if, for all $c_1,c_2\in\mathcal C$ with $\pi(c_1)=\pi(c_2)$, either both or neither lie in $\mathcal C_h$. It is task-sufficient for $\omega_\tau$ if it is task-sufficient for every $h\in H(\omega_\tau)$.

**Proposition 1** (Completeness is saturation). *The following are equivalent: (a) some governor $g\circ\pi$ rejects exactly the contexts in $\mathcal C_h$; (b) $\pi$ is task-sufficient for $h$; (c) $\mathcal C_h=\pi^{-1}(\pi(\mathcal C_h))$, so $\mathcal C_h$ is a union of fibers. If $\pi$ is linear and $\mathcal C_h$ has a $C^1$ boundary as in Theorem 2, then (a)–(c) imply $\ker\pi\subseteq T_c\Sigma$ at every boundary point $c$.*

The proof is in Appendix 15. For a coordinate projection, the last condition says that the hazard’s boundary is a cylinder along the unobserved coordinates: the hazard depends only on what the governor reads. This is the precise form of V0.17’s statement that completeness holds when the hazard’s variables are spanned by the declared coordinates, with “if and only if” replaced by the equivalence that can actually be proved.

**Corollary 1** (RealityEngine is not complete). *The ISRE encoding $\pi_{\mathrm{ISRE}}$ is an observation map. For any hazard whose boundary depends on a quantity that $\omega_\tau$ does not encode, Theorem 2 applies to $\pi_{\mathrm{ISRE}}$, and no corpus of machines over the ISRE separates the colliding contexts at admission.*

#### Worked example: potassium infusion.

An agent proposes `set_infusion_rate(dose=15, unit=mEq/h)` for intravenous potassium chloride. In $c_1$ the patient is hypokalemic with normal urine output; in $c_2$ the patient is anuric with end-stage renal disease, for whom the same rate risks hyperkalemic cardiotoxicity. A guardrail that reads the tool call sees the same string in both contexts, so by Theorem 1 it admits both or neither. The hazard boundary depends on renal clearance, a direction the call does not observe, so Theorem 2 says this is not a corner case: a whole open set of call observations has hazardous preimages. Encoding urine output as an ISRE cell, from a Source such as the HealthKit bridge, removes that direction from the kernel and makes the observation task-sufficient for this hazard, if renal clearance is the only unobserved factor the hazard depends on. Whether it is must be argued clinically, per domain; this paper does not argue it. The example is illustrative: no clinical machine of this kind is in the corpus. **\[AUTHOR: keep, replace with a corpus example, or move to a clinical companion paper\]**

#### Admission semantics.

Atomic execution, verification and recording \[51\] cannot generally be achieved against an external system. RealityEngine specifies *verify-then-commit*: (1) evaluate $\tau$ on the ISRE of the proposed action; (2) append the decision to the write-ahead record; (3) release the action, or $\mathbf{s}_{\mathrm{safe}}$, only after (2) is durable; (4) where the domain allows, register a compensating action. Steps (1) and (2) exist for engine-initiated dispatch; the release decision on agent-initiated actions is design (Section 4.7).

# 4 Architecture

## 4.1 Three planes

The system is read as three planes. *Plane 1, neural observation and dynamical state*: the LLM agent, Sources, neuralese Reality Events, node selection and the TopK prism. *Plane 2, symbolic deterministic execution*: the admission boundary, the ISRE, the aDFA bank, decision and Output State Reality Event (OSRE) arbitration, the tool path, the write-ahead record, the manifest $\omega_\tau$ and semantic evaluation. *Plane 3, distributed and evolutionary mesh*: logical clocks, rule epochs, quorum-approved rule updates, K-lines, the sandbox replica and rule learning. A plane is a grouping for reading, not a process boundary. One invariant holds across them: plane 1 produces recorded values, plane 2 decides deterministically over them, and plane 3 changes plane 2 only through an approved corpus change.

*Figure 1. RealityEngine architecture with each component’s status and audit score (Table 3). Solid: the admission path as designed. Dashed: configuration and governance. Dotted: the asynchronous return path. \[Diagram in the PDF edition.\]*

## 4.2 ISRE encoding

A proposed action and the context relevant to it are encoded as a vector $\mathbf{v}\in[0,1]^N$, one cell per domain-declared signal; unbounded signals are mapped into $[0,1]$ by a declared normalization (for example clipped min–max over a calibrated range). The perceptual space is allocated in `domains/region-allocation.json`: the corpus footprint ends at cell 16,944, and the band $[20480{:}86015]$ is reserved as the clone space (Section 6). For closed API models only the action and its arguments are observable. For open-weight models the ISRE may also carry a neuralese band, one cell per neural node, whose values are raw activations and are not confined to $[0,1]$ (Section 12).

## 4.3 Automata over interval predicates

Each CES is a regular (Type-3 \[21\]) language over a finite alphabet $\Sigma$ whose letters are conjunctions of interval predicates, $$\mathbf{v}\in P_\epsilon \iff \bigwedge_{j\in\mathrm{cells}(\epsilon)} \alpha_j\le v_j\le\beta_j ,$$ an axis-aligned box. The alphabet is finite because the predicates are finitely many, while the input domain is continuous; this is a symbolic automaton in the sense of D’Antoni and Veanes \[24\]. Membership of a word $w$ is decided in $O(|w|)$ transitions, with no backtracking and no allocation on the evaluation path, because each automaton is deterministic. The corpus also uses comparators beyond the interval form (`gte`, which binarizes both sides at a threshold, `equals` and `pattern`); an interval $|v-x|\le t$ is the `threshold` comparator.

#### Asynchrony.

Each automaton advances when a letter arrives for it, with no global clock, barrier or lock-step across instances. Within one instance a step joins: the OSRE resolves only after every machine’s composition finishes. Determinism therefore holds per automaton over the letter sequence it actually received, which the write-ahead record captures and replay reproduces.

#### Single-Transition-Time (STT) evaluation.

In one step each automaton reads its letter, makes one transition and asserts its output. Per step the cost is $O(m)$ for $m$ automata and independent of history length. State that must persist, such as a set–reset latch, is read from the previous step’s committed output and written to the next step’s, $Q_k = S_k\lor(\lnot R_k\land Q_{k-1})$, so evaluation within a step is feed-forward and cannot oscillate. The latency of a step is objective TO-1 (Section 10); it is unmeasured.

## 4.4 Decision and output arbitration

When several machines write the same OSRE cell in one step, the arbiter combines their writes with a rule declared per cell (`RealityEngine_CI/docs/ARBITER_CONTRACT.md`). Rules are commutative monoids (for example maximum, minimum, a severity order, or provider precedence ranked deterministic $>$ measured $>$ generated), so the resolved value does not depend on the order in which machines finish. A failed agent transform contributes nothing and is diverted to an analysis stream. The domain fail-safe vector $\mathbf{s}_{\mathrm{safe}}$ replaces a rejected action’s output with a declared safe value (for example minimum cooling flow, never zero flow); it exists in no domain today.

## 4.5 Protocol planes

Action dispatches cross the admission boundary (C++ runtime, port 5301). “ACP” is the Agent Client Protocol \[2\] as OpenClaw provides it \[3\], not IBM’s Agent Communication Protocol \[1\], which merged into A2A \[9\]. Agent-to-agent messaging uses A2A \[4\], an Agentic AI Foundation project \[5\]. An MCP server (`RealityEngine_CI/mcp/src/server.js`) exposes 21 tools, 11 read-only and 10 that can change state and are disabled unless policy enables them. Governance follows the OWASP Agent Control Standard \[7\] and, in later phases, Microsoft’s Agent Governance Toolkit \[8\]. **\[AUTHOR: phase in which each attaches\]**

In release v0.0.3 the suite adopts A2A as its agent gateway (RealityEngine_CI#841) and replaces OpenClaw with `localLangChainStack`: LangGraph agents served over A2A. Its first agent persists tasks and checkpoints, keys threads by the frame’s continuation, and dispatches once only (localLangChainStack#1, \#12). The RealityEngine A2A framework is drafted (RealityEngine_CI#848), and inbound MCP and ACP admission proxies are planned (RealityEngine_CI#850, \#851). *Status: Partial.*

## 4.6 The return path: Sources and semantic evaluation

Admission governs what the agent may do; the return path governs what the engines may come to believe. Agent responses, tool results and other stimuli re-enter through *Sources*; this is the *observation* stage of the NIST agentic workflow \[6, Sec. 4.1.1\], while admission acts between *planning* and *execution*. Each is evaluated asynchronously for semantic validity against $\omega_\tau$, and only a stimulus that passes is folded into the next ISRE; one that fails contributes nothing and is recorded. Three properties follow. The evaluation adds nothing to the STT step, and its cost appears as staleness of the next ISRE, which Section 5 bounds. The evaluator may be non-deterministic, but the engines consume only its recorded verdict, so decisions remain replayable. And a poisoned tool result, including one that carries an indirect prompt injection, is stopped before it can shift the automata’s future transitions.

Semantic evaluation is implemented in the transformation of an agent response into the next ISRE (`localOpenClawStack/machine-behaviors/openclaw_side.py`, `apply_response_mapping`, with a gate in each PE model adapter). It is deterministic and rule-based. The asset lifecycle service is also a Source (Section 6). Open gaps: unresolved cells are not masked, the analysis stream is not wired, guardrail compilation is absent, and the path has not been exercised in live use. Its counterpart on the A2A path is to be built with the framework (RealityEngine_CI#848).

The simulated Source, the PE’s third kind beside test and sensor sources, is a pure function of the step: cell $i$ at step $n$ is sampled at $t=n+0.1\,i$ with phase $\mathrm{fmod}(t\,f,1)$, and six of its eight patterns are deterministic and therefore parity terms. The formula is written into `SURFACE_SPEC.md` (RealityEngine_CI#866, in review). Writing it down found that the Lisp PE served the DC offset for every pattern (RealityEngine_LSP#200, fix in review).

## 4.7 Component status

Table 3 gives each component’s status and a percent implemented from an audit of the repositories at their 14 November 2026 heads. Each requirement placed on a component scored 1 when code exists, $\tfrac12$ when it exists in some engines only, as a stub, or with a recorded deficiency, and 0 when it is specified or design only; the percent is the mean. It is a checklist score, not test coverage, and it counts code that exists, not results measured.

**Table 3.** Component status and audit score (audit of 16 November 2026, heads of 14 November 2026).

| Component                 | Status      | Items |   % | Principal gaps                                               |
|:--------------------------|:------------|------:|----:|:-------------------------------------------------------------|
| LLM agent                 | Implemented |    17 |  74 | Hidden-state tap; frame-scoped tools; OpenClaw successor     |
| Admission boundary        | Partial     |    17 |  44 | Admit/reject/replace on agent-initiated actions; locks       |
| ISRE encoder              | Implemented |    11 |  68 | Encoding of proposed actions; neuralese band                 |
| aDFA bank                 | Implemented |    15 |  67 | Parity record; latency harness; replay                       |
| Decision / OSRE           | Partial     |    15 |  53 | $\mathbf{s}_{\mathrm{safe}}$; admit or replace; egress gates |
| Tool / actuator           | Implemented |    13 |  81 | Lock verification; frame-scoped tools                        |
| Write-ahead record        | Partial     |    17 |  53 | Durable journal; K-lines; RE-Clock; hash chain               |
| Domain spec $\omega_\tau$ | Implemented |    14 |  61 | Hazards, $\mathbf{s}_{\mathrm{safe}}$, $\delta$, sufficiency |
| Rule-update quorum        | Design      |    11 |   0 | Epochs, pointer swap, $q$-of-$n$ signatures                  |
| Sources                   | Implemented |    15 |  80 | Source-kind taxonomy; neuralese Source                       |
| Semantic evaluation       | Implemented |    11 |  64 | Analysis stream; unresolved masking; guardrail compile       |

The audit’s central finding concerns direction. In the repositories, traffic to agents begins at the engine: a CES fires, its output carries governance, the PE turns it into a dispatch envelope and record, an agent is called, and its completion returns through a Source. No component yet intercepts an action an agent proposes on its own and admits, rejects or replaces it. Recognition, arbitration, dispatch and the return path are implemented; the pre-execution decision of Sections 3 and 5 is design at the boundary. **\[AUTHOR: confirm whether inbound admission of agent-initiated actions is in scope for this paper\]**

*Since the audit (heads of 25 November 2026).* Table 3 is not re-scored, but three of its named gaps have moved.
- **Write-ahead record:** the `RE-Clock` gap is closed. The full clock runs on every RE and PE (Section 7).
- **Sources:** the source-kind taxonomy is specified as the versioned vocabulary `re-source-kinds/1`, the PE half of a K-line (RealityEngine_Machines#290).
- **LLM agent:** the OpenClaw successor is Partial (Section 4.5).

Inbound admission is now tracked as release v0.0.3 work (RealityEngine_CI#850, \#851).

# 5 Temporally Bounded Incompleteness

Corollary 1 says RealityEngine is not complete. The return path means the incompleteness need not be permanent: an action admitted from a colliding context can be exposed once its effects come back through a Source and are verified. This section makes the size of that exposure an explicit quantity and bounds it. Time here is *logical*: a step is a per-instance committed step (Section 7), so every bound is stated without a global clock and without synchronization between instances. *Status: the window (B2) is to be implemented (owner decision, 16 November 2026; phase M1, Table 9). The split-budget rule of Proposition 5 and the staging rule of Proposition 6 are design.*

## 5.1 Definitions

**Definition 2** (Exposure margin). Let $\lambda_i$ be the committed-step counter of instance $i$. For an action $a$ admitted at $\lambda_i=k$, let $\lambda_i^{\mathrm{fold}}(a)$ be the first step at which a verified Source verdict covering an effect of $a$ is folded into the ISRE of instance $i$. The *exposure margin* of $a$ at $i$ is $\mu_i(a)=\lambda_i^{\mathrm{fold}}(a)-k$, or $\infty$ if no such verdict is ever folded.

**Definition 3** (Temporally bounded incompleteness). RealityEngine is *$\bar\mu$-bounded* for $\omega_\tau$ at instance $i$ if, for every $h\in H(\omega_\tau)$ and every action $a$ admitted from a context in $\mathcal C_h$ that shares its ISRE fiber with a safe context, either $\mu_i(a)\le\bar\mu$ and $h$ is recognized by step $k+\mu_i(a)$, or at most $\bar\mu$ consequential steps (Definition 5) are admitted at $i$ after $a$ before $\mathbf{s}_{\mathrm{safe}}$ holds.

**Definition 4** (Operational separatrix and distance). For a CES element $\epsilon$ of a hazard sequence, let $A_\epsilon\subseteq[0,1]^N$ be the set of frames on which $\epsilon$ matches. Its *operational separatrix* is the boundary $\partial A_\epsilon$. For an interval element, $A_\epsilon=P_\epsilon$ is a box, and the distance of a frame $\mathbf{x}$ from it is the $L_\infty$ distance over the cells $\epsilon$ reads, $$d_\epsilon(\mathbf{x})=\max_{j\in\mathrm{cells}(\epsilon)}\ \max\bigl(0,\ \alpha_j-x_j,\ x_j-\beta_j\bigr),$$ which is zero exactly when $\epsilon$ matches. For a binarized element (`gte`, `equals`, `pattern`) it is the number of cells that must flip for $\epsilon$ to match.

The $L_\infty$ form is the least uniform change to the cells that makes $\epsilon$ match, and it is computed with one subtraction pair and two maxima per cell, which is why its evaluation can share the interval kernel (objective TO-2). It is meaningful only because Source cells are normalized to a common scale; neuralese cells are not, and an element over them needs a declared per-cell scale before distances over its cells can be compared. **\[AUTHOR: scale rule for neuralese elements\]**

**Definition 5** (Consequential step). Let $E_i(k)$ be the hazard elements expected next at instance $i$ after step $k$: the active element of every open hazard K-line and the initial element of every hazard sequence. An action admitted at step $k$ with frame $\mathbf{x}_k$ is *consequential* when $\min_{\epsilon\in E_i(k)} d_\epsilon(\mathbf{x}_k)\le\delta$, where $\delta=(\delta_c,\delta_b)$ is declared per domain, $\delta_c\in[0,1]$ for continuous and $\delta_b\in\mathbb N$ for binarized elements. Entering the $\delta$-band is an *approach*.

The operational separatrix is a declared boundary. It is not the dynamical separatrix of Hypotheses H2 and H3 (Section 12); the two coincide only so far as the corpus captures the model’s basins.

**Definition 6** (Cone of awareness). For an event $e$ at instance $i$, its *cone of awareness* is its causal past $C(e)=\{e':e'\rightarrow e\}$ under happened-before \[43\]. A verdict is *known* at $e$ when the event that folds it lies in $C(e)$. An action $a$ is *outstanding* at $e$ when $a\in C(e)$, $a$ is consequential, and its verdict is not known at $e$.

## 5.2 Assumptions

**Assumption 1** (A1, complete mediation). Every effect of an agent action leaves the agent only through the admission boundary and, where staging is declared, only through the stager of Proposition 6. This is a deployment property: network namespaces with no egress except the boundary socket, and tool proxies that refuse calls without a valid release envelope (Section 7). It is not implemented today (threat T1, Section 8).

**Assumption 2** (A2, correct recognition). The automata recognize each declared hazard language $L_h$ exactly: an ISRE word is accepted by the machine for $h$ if and only if it lies in $L_h$, and concurrent writes are resolved by the arbiter’s monoids. Parity across the voting runtimes (Section 9.1) is the regression evidence for this assumption; it is not a proof of it.

**Assumption 3** (B1, observability). Every declared hazard has an effect that produces a Source stimulus, the semantic evaluator classifies that stimulus correctly, and once folded the resulting ISRE places the trajectory in $L_h$.

**Assumption 4** (B2, margin window). At each instance, a consequential action opens an obligation with budget $\bar\mu$. While it is outstanding, each further consequential admission at that instance consumes one unit of the budget, and a consequential action that finds no unit left is replaced by $\mathbf{s}_{\mathrm{safe}}$. A message sent while an obligation is outstanding carries the obligation’s identifier, its `RE-Clock` stamp and a share of the remaining budget; the receiver applies the Lamport receive rule, adds the obligation with that share, and treats it as discharged only when the verdict is known there.

The window counts committed steps, not Lamport timestamps: the receive rule $L_j\leftarrow\max(L_j,T_m)+1$ can advance a clock arbitrarily on one message, so a window counted in Lamport time could be closed by a remote message with no local step. Lamport time decides what lies in the cone; the step counter decides how far a step lies beyond it.

## 5.3 Results

**Proposition 2** (Per-instance bound). *Under (A1), (A2), (B1) and (B2), RealityEngine is $\bar\mu$-bounded for $\omega_\tau$ at each instance for every hazardous action that is consequential when admitted.*

*Proof.* Let $a$ be consequential, admitted at step $k$ from a hazardous colliding context. By (A1) its effects pass the boundary, and by (B1) a stimulus covering one of them is produced and classified correctly. By (B2), at most $\bar\mu$ consequential actions follow at $i$ while $a$ is outstanding, and any beyond them are replaced by $\mathbf{s}_{\mathrm{safe}}$. If the verdict is folded at step $k+\mu_i(a)$, then by (B1) and (A2) the automata recognize $L_h$ at that step; if it is not folded while budget remains, the budget is exhausted after $\bar\mu$ consequential steps and $\mathbf{s}_{\mathrm{safe}}$ holds thereafter. ◻

**Proposition 3** (Coverage). *Suppose the verdict that places the trajectory in $L_h$ writes at most $r$ cells read by the element $\epsilon$ it completes, and no other step changes those cells between the admission of $a$ and the fold. If $\delta_b\ge r$ (binarized $\epsilon$), or $\delta_c$ is at least the largest change the verdict makes to any cell of $\epsilon$ (continuous $\epsilon$), then $a$ is consequential, and Proposition 2 applies to it.*

*Proof.* After the fold, $\epsilon$ matches. Before it, the frame differs from a matching frame only in the verdict’s writes, so $d_\epsilon(\mathbf{x}_k)$ is at most $r$ (binarized) or at most the largest write (continuous, by the $L_\infty$ form of Definition 4), which is within $\delta$. ◻

**Proposition 4** (Per-path bound). *Under (B2), along any happened-before path that starts at an outstanding action $a$, at most $\bar\mu$ consequential actions are admitted, summed over all instances on the path, before $a$’s verdict is known.*

*Proof.* Each consequential admission on the path spends one unit; a message hands on at most what is left; nothing adds to it; the budget starts at $\bar\mu$. ◻

V0.16 noted that the per-path bound does not bound a cone that forks: $b$ concurrent branches that each inherit the remaining budget can admit up to $b\bar\mu$ consequential actions in total (threat T9). The remedy is to make the budget a conserved quantity, split rather than copied at each send. V0.17 proposed this and proved it by induction on the depth of the dispatch tree. The invariant argument below is shorter and covers what the induction does not: arbitrary interleavings, lost messages and, with one added rule, retransmission.

**Proposition 5** (Whole-cone bound under conserved budgets). *Let obligation $O_a$ open with budget $\bar\mu$. Suppose every instance holds a non-negative integer share of $O_a$, and the only operations on shares are: (i) a consequential admission at an instance where $O_a$ is outstanding, which requires a share of at least one and decrements it by one, otherwise it emits $\mathbf{s}_{\mathrm{safe}}$; (ii) a send, which moves $s\le r$ units from the sender’s share $r$ into the message; (iii) a receive, which adds the message’s units to the receiver’s share at most once per message identifier. Then the total number of consequential actions admitted under $O_a$, over all instances and all interleavings, never exceeds $\bar\mu$.*

The proof (Appendix 15) is a conservation invariant: held shares, plus units in transit, plus admissions made always sum to at most $\bar\mu$. Three consequences matter for the design. The receive-once rule is necessary: without deduplication, a retransmitted message mints budget, which the depth induction does not see. Decrements at one instance must be atomic, which the per-instance committed step already serializes (an atomic compare-and-swap suffices where steps run on several threads). And the bound is bought with liveness: a branch that receives no share must hold its consequential steps until the verdict arrives. How shares are split (evenly, by declared weight, or on demand) is a policy choice. **\[AUTHOR: adopt split budgets for (B2)? if so, the split policy\]**

**Proposition 6** (Verdict-gated staging). *Suppose a domain declares an action class as *stageable*, (A1) holds for it, and its stager commits a staged effect only on a recorded *safe* verdict covering it, discarding it on a hazard verdict or on lease expiry without a verdict. Then, under (B1), no effect of a hazardous action in that class is committed.*

*Proof.* By (A1) the effect reaches the world only through the stager. The stager commits it only on a safe verdict. By (B1) the verdict on a hazardous action is a hazard verdict, so the effect is discarded, either on that verdict or at expiry. ◻

This is the corrected form of V0.17’s two-phase actuation quarantine, which claimed zero irreversible effects from a lease length alone. A lease length cannot guarantee that a verdict arrives in time in an asynchronous system \[30\]; what guarantees safety is that expiry *discards*. The lease length then decides only liveness: how many safe actions are lost to expiry. Staging suits effects that can wait (a database write, a funds transfer, a document publication). It does not suit effects that must act within a control period, such as a valve that must close now, which keep the protection of Proposition 2 and $\mathbf{s}_{\mathrm{safe}}$ only.

## 5.4 Imperfect verification

(B1) assumes a correct verdict. The return path may instead offer several detection opportunities for one hazard within the window: successive Source stimuli, each verified. V0.17 bounded the probability that all of them miss by $\beta^{\bar\mu}$ through a supermartingale and Doob’s optional stopping theorem, and concluded that $\bar\mu\ge2$ meets DO-178C Level A. The bound holds only under a hypothesis V0.17 did not state, and the certification claim does not follow from any bound of this kind. The correct statement is short.

**Proposition 7** (Escape under repeated verification). *Let $M_1,\dots,M_m$ be the events that verification opportunities $1,\dots,m$ miss a hazard. If $\Pr(M_j\mid M_1\cap\dots\cap M_{j-1})\le\beta$ for every $j$, then $\Pr(M_1\cap\dots\cap M_m)\le\beta^m$. Without that hypothesis, only $\Pr(M_1\cap\dots\cap M_m)\le\min_j\Pr(M_j)\le\beta$ holds.*

*Proof.* By the chain rule, $\Pr(\bigcap_j M_j)=\prod_j\Pr(M_j\mid M_1\cap\dots\cap M_{j-1})\le\beta^m$. The second bound holds because the intersection is contained in each $M_j$. ◻

The hypothesis fails exactly where it matters. The same evaluator applied to stimuli generated by the same underlying fault tends to fail the same way, so conditional miss rates rise after a miss. Repetition buys a factor $\beta$ per opportunity only for opportunities that are independent in their failure modes: different sensors, different evaluators, or a deterministic check paired with a model-based one. The miss rate $\beta$ itself is unmeasured; the evaluator in the repositories is rule-based, and the three-model voting tier V0.17 describes is not in them.

## 5.5 Remarks

(i) All bounds are in causal steps. A wall-clock bound follows only by multiplying $\bar\mu$ by a measured per-step latency under a partial-synchrony assumption \[30\]. (ii) $\delta$ trades coverage for throughput: when it covers the whole cube, every action is consequential; when it is zero, nothing is held. Proposition 3 gives the smallest $\delta$ that keeps the bound for single-verdict hazards; hazards whose frames lie farther than $\delta$ from the separatrix are not bounded by this mechanism. (iii) Effects that are irreversible within the margin are not undone by detection; they are addressed by staging where it applies and by compensating actions where the domain allows one. (iv) A verifier with no verified return path has $\mu=\infty$ for every colliding hazard; the margin is what distinguishes bounded from unbounded incompleteness. (v) Verdicts must reach every instance in an obligation’s causal future; the design forwards each verdict along the sends that carried the obligation, and until it arrives the receiver holds its own consequential steps, which is safe but can stall. The stall is measured in Section 11.

#### Approach as a learning trigger.

Every approach is recorded on each open K-line whose expected element is within $\delta$. A K-line that records an approach and then completes nominally or is abandoned without its hazard element matching is a *near miss* in Winston’s sense \[64\]; each is paired with a completed nominal K-line of the same sequence and passed to the learning path (Section 12). A K-line whose hazard element matches is a *hit*, kept as the positive example.

# 6 Governed Dispatch: Asset Workflow Management

*Status: implemented across the repositories of Table 4, with the open items it names. Specifications: `RealityEngine_CI/SURFACE_SPEC.md` (“Cloneable machines”), `RealityEngine_CI/docs/CONTINUATIONS_APPROVAL_CHAIN.md` (v1.1.0), `localAssetStorageStack/ROADMAP.md` (decisions D1–D12).*

Sections 3–5 govern single actions. Real work is a process: a disclosure note is drafted, reviewed, approved and recorded over days, by agents and people, against documents that may change. RealityEngine gives each dispatch a governed context and runs a multi-step process through the engines without any engine holding state while a person decides. IFRS accounting documents are the first workflow.

#### Dispatch as a procedure call.

A dispatch follows the calling convention of a compiled language. The *assetID* is the stack frame: a record, held by the lifecycle service, of the documents the step acts on (tagged URIs with pinned revisions, permissions and authorities), its action and arguments, its return values and an append-only continuation log. A prologue builds the frame and dispatches, the domain-specific agent behavior is the body, and an epilogue writes the results into the same frame. Agents never write a pod directly: every read and write goes through the lifecycle service with a frame-scoped capability.

#### Cloneable templates and the clone space.

A *cloneable* machine is an ordinary corpus machine that an engine can instantiate once per agentic action. Each engine decides cloneability at corpus load by nine rules (it dispatches an agentic action, has fanout, is not the target of a shared bus, is not life-safety, is not a fixture, has not opted out, and its regions each fit in 16 cells), and the voting engines must return the verdict list byte-identical in regression. Each instance reserves the band $[20480{:}86015]$ as 1,024 blocks of 64 cells, each with four 16-cell quarters (input, output, private fanout copy, intra-machine bus). Blocks are allocated lowest-free first, so identical engines driven identically place identical clones. A clone starts at its template’s initial state, is bound to one dispatch envelope (so a retried dispatch is idempotent) and one assetID, and is recycled with a generation check, so a delayed or replayed recycle can never free a block a later clone holds. A per-template `clone.maxActive` (default 8) bounds clones; exhaustion is refused with `409`. A clone affects shared state through exactly two declared, recorded exits: advancing the frame’s continuation, or the completion its template declares.

#### Continuations through an approval chain.

A clone is recycled when its action finishes, but an approval can wait days. The process therefore waits as a *continuation* \[28, 22\] stored in the frame, not as a running clone, and a human wait holds no engine block. The IFRS chain is prepare $\rightarrow$ request review $\rightarrow$ review (human) $\rightarrow$ approve $\rightarrow$ record. Seven rules make it safe: a continuation names a template and an engine, never a clone; it is one-shot \[18\], with a generation, so a replay is refused; it names who may resume it, no agent holds the capability to resume approve, record or publish, and the approver must differ from the preparer; it is pinned to a content hash, so a changed document takes the escape path to rework; it is delimited by one assetID’s process; every capture, resume, supersession and abandonment is a receipt in the append-only log, so the approval trail is produced by running the process; and a missing engine takes the escape path rather than another engine.

#### The lifecycle service.

Documents live in Solid pods \[61\], authored in dokieli \[19\]. The lifecycle service is a store and gatekeeper only: it decides no workflow transition. People sign in with Solid-OIDC; the service authenticates with DPoP-bound tokens \[56\] and takes the principal from the token, never from the request body. It reads each document from the pod itself, pins its ETag and SHA-256, and writes with `If-Match`. Its event log is append-only, fsynced and hash-chained, with Ed25519 \[53\] receipts over the RFC 8785 canonical form \[55\]. Review annotations arrive as Linked Data Notifications \[44\] and become findings, but a finding never approves, because an inbox has no authenticated sender. The service is also a Source: while a clone runs a frame’s step, it writes the frame’s lanes (in workflow, re-pinned, approved, rework, step running, stale) into the clone’s input cells, so a lifecycle change reaches the engines as every stimulus does.

**Table 4.** Asset-workflow status (repository records, 14 November 2026).

| Component                                      | Where                                 | Status (repository records)                                                |
|:-----------------------------------------------|:--------------------------------------|:---------------------------------------------------------------------------|
| Clone/recycle routes, recognition, clone space | CPP#191, LSP#184, Scala#209           | Implemented on three voting engines; 3-of-3 regression spec (Machines#248) |
| Clone/recycle (follower)                       | Rust#71                               | Implemented; non-voting                                                    |
| Frame, continuations, review gate              | localAssetStorageStack#13, \#19       | Implemented; unit tests per rule                                           |
| Identity, integrity, receipts                  | localAssetStorageStack#17, \#18       | Implemented; verified live                                                 |
| Lifecycle as PE Source                         | localAssetStorageStack#20             | Implemented; same lanes on three engines                                   |
| Instantiation component                        | Manager#323, \#336, \#346             | Implemented; one-engine chain verified live                                |
| Frame-scoped `re-mcp` tools                    | CI#714                                | Open; owner-accepted deficiency                                            |
| IFRS chain on three engines                    | CI#715; `scripts/chain-regression.js` | Chain run 3-of-3 recorded; certified in release v0.0.2 (22/22); issue open |
| Asset workflow on the release install          | CI#814                                | Implemented; smoke 10/10 in the release v0.0.2 certification               |
| Failed step parks for its author               | localAssetStorageStack#32, CI#788, Manager#347 | Implemented: an agent turn retries, then parks with its reason             |

Three qualifications apply. The IFRS template machines do not yet recognize the lifecycle lanes, so a lane change alone does not yet produce a dispatch. Clone agents carry no MCP tools, because OpenClaw’s MCP servers are gateway-wide; release v0.0.3 replaces OpenClaw with A2A agents (Section 4.5). And the IFRS domain is experimental: admission of its version 1.4.0 is *failed, not approved*, stopping on 53 accounting-readiness findings. Two further domains are in the machine factory as candidates, not admitted: `ai-governance-regime`, the organizational wrapper as 18 machines (RealityEngine_Machines#256, \#297), and its peer `threat-dynamics`, 11 observer machines after NIST SP 2400-102 §4 (RealityEngine_Machines#301, in review). Every input of both is driven by a simulated Source until its producer exists.

# 7 Distributed Operation and Rule Governance

#### No enforced synchronization.

Each instance evaluates the dispatches and stimuli that reach it, against the rule epoch it enforces, without waiting on any other instance. Determinism is per instance over the recorded input sequence; replicas need not agree on a total order. Coordination is required only for rule updates and, where a domain needs cross-node causality, for logical clocks.

#### Parity in regression, specialization in deployment.

In regression, every voting engine runs the same corpus and must agree. In deployment, instances commonly carry different corpora, so a difference between them is expected, not a defect (owner decision, 4 November 2026). A component acts on the instance whose corpus carries what it needs and never rolls back healthy work because another lacks a machine.

#### Logical time.

Every runtime implements a per-instance logical clock: each committed step carries an instance UUID, a counter that never resets, and the step, so (instance, counter) is unique. The Lamport receive rule \[43\] in its four-field `RE-Clock` form {instance, lamport, commit, step} is implemented on the RE and the PE of the three voters (RealityEngine_CPP#207, RealityEngine_LSP#199, RealityEngine_Scala#223), with conformance on all three (RealityEngine_CI#861). The followers implement it too (RealityEngine_Rust#82, RealityEngine_GO#38, RealityEngine_Manager#367; the TypeScript PE’s clock is not persisted, an accepted deviation, RealityEngine_CI#863). Dispatch records carry the clock and completions their `causedBy` (RealityEngine_Machines#296). RealityEngine_CI#600 stays open for its remaining slices. (B2) depends on the clock: an obligation’s cone is computed from it.

#### Rule epochs.

The distributed hazard is not simultaneity but nodes enforcing different rule versions. Each rule bundle carries a monotone epoch. A node enforces one epoch at a time and switches by a single atomic release-store of the active-table pointer; readers acquire it, and the old bundle is reclaimed only after its last reader finishes (epoch-based reclamation). Release envelopes carry the epoch, and proxies accept a declared window of recent epochs. During a partition a node keeps enforcing its current epoch. *Status: design.*

#### Quorum-approved rule updates.

A candidate bundle $\tau'$ is deployed only if $q$ of $n$ governance nodes sign it after each independently replays it against recorded K-lines: $\mathrm{Deploy}(\tau')\iff|\{j:\tau'\text{ passes replay at }j\text{ and }j\text{ signs}\}|\ge q$. For crash faults $q=\lfloor n/2\rfloor+1$; for Byzantine faults $n\ge3f+1$ and $q=2f+1$. Consensus cannot be both safe and live in a fully asynchronous system with one crash fault \[30\], and a partitioned system must choose between consistency and availability \[34\]; RealityEngine chooses consistency for rule updates and availability for enforcement. This governance quorum is distinct from the 3-of-3 rule that compares runtimes in regression (`RealityEngine_CI/docs/QUORUM_CONTRACT.md`). A quorum relocates trust to its members; the root of authority must still be named. *Status: design (0%).* **\[AUTHOR: fault model, $n$, $q$, protocol, key custody, root of authority\]**

#### Release envelopes (authorization locks).

An admitted action is released as a signed envelope that the tool-side proxy verifies before execution: action identifier, tool and SHA-256 of the canonical arguments, decision with output hash, rule epoch, logical timestamp, a single-use nonce with expiry of at most 30 s, the requesting workload’s identity (SPIFFE \[62\], design) and a signature. The proxy refuses an envelope whose signature fails, whose expiry has passed, whose nonce has been seen, whose arguments do not hash to the recorded value, or whose epoch is outside its window. The boundary may return `202 Accepted` without blocking the engine step, but only after the decision is recorded. *Status: design.*

# 8 Threat Model

In the capability terms of NIST SP 2400-102 \[6, Sec. 4.1.3\], the adversary has *query access* and *resource control* (untrusted data, malicious tools and skills, malicious agents) over content the agent reads; may, through *model control*, control the agent’s outputs; and may compromise individual hosts. Where a threat matches a NIST attack class, its NISTAML index identifier is given. Table 5 lists each threat with its mitigation, the mitigation’s status at the repository heads of 25 November 2026, and the behavior when it fails. T1–T19 follow V0.16; T20–T22 come from V0.17. V0.17 marked seventeen of nineteen mitigations implemented; the statuses below are those the repositories support.

**Table 5.** Threats, mitigations and status. “Closed” = action blocked; “Fail-safe” = \mathbf{s}\_{\mathrm{safe}} emitted; “Escape” = the continuation re-enters at rework.

| ID  | Threat                                                                | Mitigation                                                                                    | Status                                          | On failure   |
|:----|:----------------------------------------------------------------------|:----------------------------------------------------------------------------------------------|:------------------------------------------------|:-------------|
| T1  | Unmediated bypass                                                     | Network namespaces; egress only via the boundary; proxies require envelopes                   | Design (deployment)                             | Closed       |
| T2  | Token replay                                                          | Nonce, expiry, argument hash, signed envelope; one-shot continuations and block generations   | Envelope: design; continuations, recycle: impl. | Closed       |
| T3  | Confused deputy \[38\]                                                | Per-call argument checks; attenuating capabilities \[17\]                                     | Checks: impl.; capabilities: design             | Fail-safe    |
| T4  | Rule tampering                                                        | Read-only rule pages; quorum-signed bundles                                                   | Design                                          | Closed       |
| T5  | Unsafe shutdown                                                       | Domain $\mathbf{s}_{\mathrm{safe}}$ instead of zero output                                    | Design (no domain declares one)                 | Fail-safe    |
| T6  | Denial of service; resource exhaustion (NISTAML.066)                  | Rate limits, bounded queues, bounded per-step work                                            | Planned                                         | Closed       |
| T7  | Insider abuse                                                         | Rule quorum; signed record; approver $\neq$ preparer                                          | Rules: design; approvals: impl.                 | —            |
| T8  | Software supply chain (engine builds)                                 | Pinned builds, reproducible releases, runtime parity                                          | Partly (parity)                                 | —            |
| T9  | Key compromise                                                        | Per-install CA, short-lived leaves, rotation, revocation; SPIFFE \[62\]                       | PKI: impl.; SPIFFE: design                      | Closed       |
| T10 | Record poisoning (cf. memory poisoning, NISTAML.062)                  | Append-only, hash-chained record                                                              | K-line: design; lifecycle log: impl.            | Closed       |
| T11 | Side channels                                                         | Out of scope                                                                                  | —                                               | —            |
| T12 | $\omega_\tau$ specification error                                     | Review, tests, replay on recorded traffic                                                     | Partly                                          | —            |
| T13 | In-bounds harmful action                                              | Not mitigated by interval checks                                                              | —                                               | Open         |
| T14 | Indirect prompt injection or poisoned tool result (NISTAML.015, .063) | Semantic evaluation before ISRE fold                                                          | Implemented; gaps open                          | Excluded     |
| T15 | Self-approval                                                         | Capability-gated resume; no agent holds approve/record/publish                                | Implemented                                     | Closed       |
| T16 | Approval of a changed document                                        | Pinned ETag and SHA-256; `If-Match`; escape to stale                                          | Implemented                                     | Escape       |
| T17 | Cross-frame access                                                    | Frame-scoped capability on the lifecycle proxy                                                | Impl.; MCP tools open (#714)                    | Closed       |
| T18 | Link interception                                                     | TLS 1.3 \[54\], mTLS, hybrid key exchange; release gate                                       | Impl.; certified in v0.0.2; deficiencies recorded | Refused    |
| T19 | Activations steered past learned rules; mislabeled feature            | Rules proven on near misses and counterparts; versioned dictionary; label review              | Design                                          | Open         |
| T20 | Budget multiplication across forks or retransmission                  | Conserved split budgets with receive-once (Prop. 5)                                           | Design                                          | Fail-safe    |
| T21 | Evaluator stall or severed return path                                | Expiry discards staged effects (Prop. 6); exhausted budget emits $\mathbf{s}_{\mathrm{safe}}$ | Design                                          | Fail-safe    |
| T22 | Numeric divergence across runtimes                                    | Each computed cell computed once by its Source and recorded; ordered comparisons              | Partly (recorded Sources)                       | Disagreement |

**Notes.** T18: every link is held to one transport profile and listed in a checked inventory; the release gate fails any link short of it, and owner-accepted deficiencies are recorded per link. T22 (V0.17 listed it as mitigated by ordered comparisons alone): ordered IEEE-754 comparisons make a comparison of two given floats identical on every conforming machine, but they do not make the *values* identical when engines compute them differently, for example a normalization summed in a different order. Parity therefore requires that every computed cell be computed once, by its Source, and recorded. SPIFFE identities are not hardware-attested by themselves; that needs a node attestor such as a TPM. **\[AUTHOR: attestor; SPIFFE trust domain\]** T18 since V0.18: each device source on the PE presents its own client certificate (RealityEngine_CI#774), and release v0.0.2 was certified on transport profile `re-transport-2026.11`. T13, T6 and the agentic classes NISTAML.061–.067: candidate detectors and a red-team gate exist in the `threat-dynamics` factory package (Section 6). No status changes until that domain is admitted.

# 9 Implementation

#### Runtimes.

Three voting runtimes implement the engine: C++ (`RealityEngine_CPP`, RE on port 5301, PE on 5300), Scala/Akka (`RealityEngine_Scala`, 5001 and 5000) and Common Lisp on SBCL (`RealityEngine_LSP`, 5601 and 5600). These are the defaults; a universe started with free ports takes OS-assigned ones and publishes them in its instance registry. Three conformance followers are measured against what the voters agree on, never as votes (`RealityEngine_CI/docs/QUORUM_CONTRACT.md`):
- the Rust RE/PE (`RealityEngine_Rust`, 5801 and 5800), shipped in release v0.0.2;
- the Go RE/PE (`RealityEngine_GO`, 5851 and 5850), which implements the full RE/PE surface for release v0.0.3 (RealityEngine_GO#15–#38) and is in the regression follower lane (RealityEngine_CI#849, \#853);
- the TypeScript perception engine in `RealityEngine_Manager`, bound to Manager.

From release v0.0.3 a Rust or Go follower that differs from the voters, or is unsupported or unavailable, blocks the release (RealityEngine_CI#842, \#843).

#### Corpus.

The shared corpus (`RealityEngine_Machines`, head of 25 November 2026) declares 13 domains and 1,552 machines (Table 6), unchanged since V0.18. Packages in the machine factory are not counted until admitted: `ai-governance-regime`, `threat-dynamics` and the energy-infrastructure work (RealityEngine_Machines#289–#305). Measured on 24 October 2026, the corpus held 5,075 sequences, 3,181 of them one-event sequences, with a longest initial-to-final path of 7 events, and its elements used the binarizing `gte` comparator for 39,737 elements and `threshold` for 4.

**Table 6.** Domains in domains/domain-manifest.json (field currentMachineCount), read 19 November 2026 and unchanged on 25 November 2026. V0.17’s domain table, whose counts summed to 1,652 and whose names and autonomy levels do not match the manifest, is replaced by this one.

| Domain             | Machines | Default autonomy | Status       |
|:-------------------|---------:|:-----------------|:-------------|
| health-services    |      220 | supervised-act   | accepted     |
| health-personal    |       43 | supervised-act   | accepted     |
| life-balance       |      110 | supervised-act   | accepted     |
| agriculture        |       71 | advise           | accepted     |
| built-space        |      165 | advise           | accepted     |
| transportation     |      165 | advise           | accepted     |
| community-services |      113 | supervised-act   | accepted     |
| legal-services     |      110 | supervised-act   | accepted     |
| data-center        |       65 | advise           | accepted     |
| digital-logic      |       69 | observe          | accepted     |
| ai-services        |        9 | advise           | accepted     |
| energy             |      187 | advise           | accepted     |
| ifrs-accounting    |      225 | observe          | experimental |
| Total              |    1,552 |                  |              |

**Table 7.** Implementation status. Several components V0.17 described with code listings and file paths are absent: no SIMD intrinsics, fail-safe vector, CapChain or SPIFFE code, or seccomp profile exists in the engine and CI repositories at their heads of 18–19 November 2026, and the files src/core/output_arbiter.cpp, src/core/adfa_engine.cpp, src/core/tri_modal_evaluator.hpp (C++), src/k-line-replay.lisp (Lisp) and deploy/sandbox_profile.json (CI) do not exist.

| Capability                                                          | Location                                                             | Status                                                 |
|:--------------------------------------------------------------------|:---------------------------------------------------------------------|:-------------------------------------------------------|
| aDFA core, admission server (C++)                                   | `RealityEngine_CPP/src/reality_engine_server.cpp`                    | Implemented                                            |
| Scala/Akka and Common Lisp runtimes                                 | `RealityEngine_Scala`, `RealityEngine_LSP`                           | Implemented (voting)                                   |
| Rust and Go RE/PE; TypeScript PE                                    | `RealityEngine_Rust`, `RealityEngine_GO`, `RealityEngine_Manager`    | Implemented (followers); Go for v0.0.3                 |
| Domain manifest and corpus                                          | `RealityEngine_Machines`                                             | Implemented                                            |
| Cross-engine parity                                                 | per-repository parity suites; release gate                           | Proven in regression; certified in release v0.0.2      |
| Asset workflow                                                      | Table 4                                                              | Implemented, open items                                |
| TLS 1.3 with mTLS on every link                                     | `RealityEngine_CI/docs/TRANSPORT_SECURITY.md`                        | Implemented; certified in v0.0.2; deficiencies recorded |
| MCP gateway (11 read-only, 10 gated)                                | `RealityEngine_CI/mcp/src/server.js`                                 | Implemented                                            |
| Per-instance logical clock                                          | all six runtimes                                                     | Implemented                                            |
| Semantic evaluation                                                 | `localOpenClawStack/machine-behaviors/openclaw_side.py`; PE adapters | Implemented; gaps                                      |
| Lamport receive rule (`RE-Clock`)                                   | CI#600; CI#861 (conformance)                                         | Implemented on RE and PE; issue open for later slices  |
| Source-kind taxonomy `re-source-kinds/1`                            | `RealityEngine_Machines` (#290)                                      | Specified                                              |
| A2A agent gateway (LangGraph)                                       | `localLangChainStack`; CI#841, \#848                                 | Partial                                                |
| Margin window (B2); split budgets; staging                          | Section 5                                                            | To be implemented (M1); design                         |
| Admit/reject/replace on agent actions; $\mathbf{s}_{\mathrm{safe}}$ | —                                                                    | Design                                                 |
| Release envelopes; SPIFFE; CapChain; hash-chained engine record     | —                                                                    | Design                                                 |
| Rule epochs, pointer swap, quorum updates                           | —                                                                    | Design                                                 |
| Interval SIMD kernel (NEON)                                         | —                                                                    | Objective (TO-2); not written                          |
| K-lines, export, sandbox replica                                    | `RealityEngine_CI/SURFACE_SPEC.md` (CI#287, \#603, \#857)            | Specified; readiness decided 24 November 2026          |
| Neuralese Reality Events                                            | owner specification, 31 Oct 2026                                     | Specified (owner)                                      |
| TopK prism, node selection, predictors, rule compilation            | Section 12                                                           | Design                                                 |
| Timing harness                                                      | Section 10                                                           | Absent                                                 |

## 9.1 Cross-engine parity

The voting engines are held to parity in regression: on the shared CES oracles over the shared corpus, each produces the same pass-set. The suites are `RealityEngine_CPP/tests/cesgen_oracles_parity.cpp`, `RealityEngine_Scala/.../CesgenOraclesParitySpec.scala` and `RealityEngine_LSP/tests/oracle-parity-tests.lisp`. Parity is equality of pass-sets: the engines agree on every oracle verdict. It does not compare traces transition by transition, and it makes no claim about timing or interleaving. Bit-identical OSRE bytes on edge-case transitions (gate TC-PAR-02) is a stronger target, not yet met. Clone surfaces are compared the same way: the cloneable verdict list byte-identical, each clone response except its instance name, and each clone’s steps. The first per-release record is release v0.0.2, closed on 21 November 2026 (`RealityEngine_CI/releases/release-v0.0.2.md` and its manifest). Twelve repositories are tagged at stated commits, and sixteen images are pinned by digest. Two lanes certified it, both running `cpp:1,lsp:1,scala:1` on the regression corpus with TLS on:
- the native run `rc5-native-20261120`;
- the containerized run `e1-rc5-cert-20261120b` on the published images.

Every required stage passed on both lanes, among them ISRE/OSRE trajectory parity, machine-set, export and engine-process parity, universal vectors, the reset contract, arbiter conformance and the asset workflow. 53 of 62 reports were identical across the lanes, and the nine that differ are explained in the record; none is an engine difference. Two stages were omitted with owner acceptance: the arbiter sweep ran on the native lane only, and the deployment suite ran on neither. The record does not state the oracle count or per-engine pass counts **\[PENDING: oracle and pass counts in the next release record\]**. The Rust follower ran on the native lane, shown and not counted. The followers are not part of the pass-set equality; V0.17’s equation equating four pass-sets is withdrawn. From v0.0.3, followers gate the release without voting (Section 9).

#### Code and data availability.

Repositories are public under <https://github.com/jateeter>: RealityEngine_CPP, localAIStack and localAssetStorageStack under Apache-2.0; RealityEngine_CI, \_LSP, \_Machines, \_Manager, \_Rust and \_Scala, localHealthkitBridge and localOpenClawStack under MIT. Release v0.0.2 is tagged across its twelve repositories. RealityEngine_GO and localLangChainStack have joined since **\[AUTHOR: their licenses\]**. **\[PENDING: DOI; CITATION.cff\]**

# 10 Timing Objectives

*Status: every row of Table 8 is an Objective. None has been measured to its gate. The only timing the engines report today is summed seconds per phase on `/api/metrics`, which yields no percentile.*

The owner’s V0.0.3 specification states timing figures as properties: sub-microsecond evaluation with a p99 below 0.82 $\mu$s, a one-cycle pointer swap, a small-cycle interval check, interception before a given layer. We keep each figure as a goal. An *objective* is a quantity with a unit, a percentile, stated conditions, a harness, a gate and a status, pursued by a recursive design–implementation loop in which every iteration leaves a recorded measurement. V0.17 marked all eighteen objectives “Gated / Passing”; no harness exists, so that status is withdrawn.

## 10.1 Five clocks

An objective is stated in exactly one clock, and converting between clocks requires a stated assumption.

1.  **Wall-clock latency** (ns, $\mu$s, ms) on stated hardware, ISA, compiler and load. This is the clock for STT evaluation, kernels, epoch switches and write-ahead durability.

2.  **Logical steps**: committed steps and the RE-Clock counters (Section 7). This is the clock for the exposure budget $\bar\mu$, the margin $\delta$ and K-line bounds. A logical bound becomes a wall-clock bound only under partial synchrony, by multiplying by a measured per-step latency.

3.  **Model clocks**: the presentation index $t$ of a Source and the layer depth $\ell$ within one forward pass. This is the clock for interception lead, adaptive taps and predictor horizons $H_p$.

4.  **Agent and remote time** (seconds): dispatch acknowledgements, leases, envelope expiry, human waits. The engine never waits on this clock (Section 6).

5.  **Physical propagation** $d/c$: a lower bound for any remote effect, never an objective. At $d\approx10^{-2}$ m and $2\times10^{8}$ m/s it is 50 ps, which is why only remote dispatch, not local evaluation, is constrained by it.

## 10.2 The recursive loop

Each objective $O$ is pursued by one loop, and a loop may spawn child loops.

1.  **Specify.** State $O$: quantity, unit, percentile (p50, p99 and p999 are always reported; the target names one), conditions (hardware, ISA, compiler and flags, corpus fingerprint, load), harness, gate and the clock of Section 10.1.

2.  **Design.** Give an analytic bound from operation counts (comparisons, cache lines, branches) showing that $O$ is reachable in principle. A design with no such bound does not proceed.

3.  **Implement** on the reference runtime named by $O$. Correctness parity comes first: no change that breaks 3-of-3 regression is measured.

4.  **Measure** with the harness under the stated conditions, with warm-up, at least 30 runs, and the full distribution recorded.

5.  **Decide.** If the gate passes, $O$ becomes a regression guard: a later SHA that worsens the gated percentile by more than a declared tolerance fails CI. If it fails, profile. Then *decompose* $O$ into child objectives whose budgets sum to at most $O$’s, and recurse on the child that misses; or revise the design and return to R1. A target is changed only by a recorded owner decision with its reason, never silently.

6.  **Record** the measurement, the SHA, the conditions and the decision in the per-release evidence (Section 11).

The recursion terminates. Every iteration either passes a gate, splits a budget into strictly smaller parts that bottom out in kernels with analytic bounds, changes the design, or records a decision to change the target. Because budgets compose additively along the admission path, a parent passes once its children pass, provided the sum of the children’s measured percentiles is checked against the parent (percentiles do not add exactly, so the parent is always re-measured).

*Figure 2. The recursive design–implementation loop for one objective. A miss either revises the design or splits the budget into child objectives, each run through the same loop. \[Diagram in the PDF edition.\]*

## 10.3 The admission budget

The root wall-clock objective is the admission path from an ISRE letter arriving at an engine to the action, or the fail-safe output, being releasable: $$T_{\mathrm{adm}}=t_{\mathrm{fold}}+t_{\mathrm{eval}}+t_{\mathrm{arb}}+t_{\mathrm{wal}}+t_{\mathrm{rel}} .$$ Here $t_{\mathrm{fold}}$ is the merge into the ISRE (Sources already recorded), $t_{\mathrm{eval}}$ the aDFA step over all machines the letter reaches (TO-1), $t_{\mathrm{arb}}$ the OSRE arbitration, $t_{\mathrm{wal}}$ the durable write-ahead append (TO-12), and $t_{\mathrm{rel}}$ the signed release (Section 7). The specification’s 0.82 $\mu$s figure bounds only $t_{\mathrm{eval}}$. $t_{\mathrm{wal}}$, when durable, will normally dominate, and the specification gives no figure for it. $t_{\mathrm{eval}}$ decomposes further, per machine and then per element block, down to the interval kernel (TO-2). Source acquisition (model forward passes, sensor reads) lies outside $T_{\mathrm{adm}}$ and has its own objectives (TO-9, TO-10), because the engine consumes recorded values.

## 10.4 Objectives

**Table 8.** Timing objectives. “To set” marks a target the owner must declare in R0. A status changes only by a recorded gate result.

| ID    | Objective (target and conditions)                                                                                                                                                                                                                                                       | Clock                | Source; gate                                  | Status                                           |
|:------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:---------------------|:----------------------------------------------|:-------------------------------------------------|
| TO-1  | STT step evaluation on the C++ runtime: p99 $\le 820$ ns per presented ISRE vector on the reference machine (Apple silicon, Section 10.5), over $10^6$ randomized vectors; corpus size and per-machine versus per-step scope to be stated                                               | Wall                 | V0.0.3, TC-STT-01                             | Unmeasured; harness absent                       |
| TO-2  | Interval kernel on the reference ISA (Apple silicon, 128-bit NEON, 4 fp32 lanes): a 32-interval block check in $\le 8$ cycles reciprocal throughput (R1 bound, Section 10.5); the specification’s $\le 4$ cycles on 16-lane AVX-512 is kept as a non-reference comparison               | Wall                 | V0.0.3, Narr. 3; microbench                   | Unmeasured; kernel not written                   |
| TO-3  | Single-step fail-safe: when the ISRE satisfies a hazard element, or a (B2) budget is exhausted, $\mathbf{s}_{\mathrm{safe}}$ is in the OSRE of the *same* committed step; wall-clock $\le$ TO-1 + $t_{\mathrm{arb}}$                                                                    | Logical, Wall        | V0.0.3, Sec. 3; replay                        | Design: no domain declares $\mathbf{s}_{\mathrm{safe}}$ (Table 7); (B2) Design |
| TO-4  | Rule-epoch switch: one atomic release-store; the next step evaluates the new epoch; p99 from commit of a compiled bundle to its first evaluated step $\le 1\,\mu$s; old-bundle reclamation bounded; compile time measured, not budgeted                                                 | Wall, Logical        | V0.0.3 “1 cycle”, “$<1\,\mu$s”; epoch test    | Design                                           |
| TO-5  | Estate-wide adoption: an approved epoch is enforced at every reachable node within $T_{\mathrm{prop}}$ (to set); proxies accept epochs in $[e_{\max}-k_e,e_{\max}]$. “Single tick estate-wide” is unattainable under asynchrony \[30\] and is not an objective                          | Wall                 | V0.0.3, Q4; partition test                    | Design                                           |
| TO-6  | Exposure: per domain, at most $\bar\mu$ consequential steps after a hazardous action before its verdict is folded or the fail-safe holds; wall-clock equivalent $\bar\mu\times$ measured per-step p99                                                                                   | Logical              | (B2), Sec. 5; replay                          | Design (M1)                                      |
| TO-7  | Clone activation (dynamic instantiation): a leased clone’s first evaluated step within one step of allocation; allocation p99 $\le 1\,\mu$s; release zeroes lanes within the same step                                                                                                  | Logical, Wall        | V0.0.3, Sec. 2C; asset tests                  | Partial: clones implemented, unmeasured          |
| TO-8  | Interception lead in depth: on a recorded bifurcation at layer $\ell_b$ that commits by $\ell_c$, the censor fires at layer $<\ell_b+\tfrac12(\ell_c-\ell_b)$; for the specification’s case ($\ell_b=11$, $\ell_c=22$) before layer 16. Restated for the 42-layer hybrid universe model | Model ($\ell$)       | V0.0.3, TC-DYN-01                             | Hypothesis-dependent (H3); needs multi-layer tap |
| TO-9  | Adaptive tap: when inter-layer acceleration $\|\Delta\mathbf{h}_{\ell+1}-\Delta\mathbf{h}_\ell\|>\theta_{\mathrm{accel}}$, capture $[\ell^*-2,\ell^*+3]$ within the same forward pass; added cost $\le$ a declared share of token latency                                               | Model, Wall          | V0.0.3, Narr. 2                               | Design                                           |
| TO-10 | Neuralese Source: write of $k$ selected nodes plus momental and projection cells per presentation p99 $\le t_{\mathrm{src}}$ (to set); model throughput loss $\le$ a declared share                                                                                                     | Wall                 | This paper, Sec. 12.4                         | Design                                           |
| TO-11 | K-line memory: flat over a 24-hour run; ring never exceeds $W=L(\mathtt{klineFeedbackHops}+1)$ committed steps; store never evicts an unexported segment                                                                                                                                | Wall (24 h), Logical | V0.0.3, TC-DYN-02; Sec. 12.1                  | Specified; not implemented                       |
| TO-12 | Write-ahead durability: each decision durable before release; p99 append-plus-sync $\le t_{\mathrm{wal}}$ (to set per storage class)                                                                                                                                                    | Wall                 | Sec. 4.7                                      | Partial: in memory only                          |
| TO-13 | Recall during revision: the recalled settlement is written in the presentation that detects the revision; p99 $\le$ the inter-presentation interval                                                                                                                                     | Model, Wall          | This paper; V0.0.3 “single tick” reactivation | Design                                           |
| TO-14 | Dispatch non-blocking: the dispatch call (ACP in v0.0.2, A2A from v0.0.3) returns (acknowledgement or local enqueue) at p99 $\le t_{\mathrm{ack}}$, and TO-1 is unchanged while agent latency is swept from 0 to 60 s                                                                                                | Wall, Agent          | V0.0.3, “202 Accepted”                        | Partial: path exists, unmeasured                 |
| TO-15 | Lease and expiry: a missed completion asserts its timeout cell within one step after the lease TTL; signed envelopes expire at TTL $\le 30$ s                                                                                                                                           | Agent, Logical       | V0.0.3, watchdog; Sec. 7                      | Design                                           |
| TO-16 | Return-path staleness: a verified completion is folded within $\bar\mu$ steps of its dispatch, or the fail-safe holds                                                                                                                                                                   | Logical              | Sec. 4.6                                      | Partial                                          |
| TO-17 | Predictor lead: a departure predictor fires $\ge H_p$ presentations before the comparator crossing on recorded near misses, at a declared precision                                                                                                                                     | Model                | This paper, Sec. 12.4                         | Design                                           |
| TO-18 | Wall-clock windows in CES (for example a 3-second pattern): stated in steps with a declared sample rate; jitter measured                                                                                                                                                                | Logical, Wall        | V0.0.3, Q3                                    | Design                                           |

#### Figures not adopted as objectives.

Three figures in the V0.0.3 specification are not objectives. “STT evaluation $\le 1$ ns for $N$ grammars” contradicts both TO-1 and the $O(m)$ cost of evaluating $m$ automata, so it is replaced by TO-1 and TO-2. “Separatrix crossing between layers 10 and 14” and “an 87.5% single-step trapping rate” are empirical claims about models. They are Hypotheses H2 and H3, to be measured on the universe model. The 87.5% figure is Akarlar’s patching result on a different model, not a trapping rate \[10\]. The “$>50$ ms” cost of dense half-space checks is a motivation, and it becomes a decision rule: option C of Section 12.5 (a linear comparator) is admissible only if it meets TO-1.

#### Non-timing gates adopted with them.

The same specification states three acceptance tests that are not about time, and V0.16 adopts them as gates. TC-NEU-01: every prism record has exactly $k_f$ non-zero features, at every tap depth. TC-NEU-02: at most 20% dead dictionary features over a 100,000-token sweep. TC-PAR-02: bit-identical OSRE bytes across the voting runtimes on 500 edge-case transitions. TC-PAR-02 is stronger than the pass-set equality proven today (Section 9.1).

#### Candidate targets from V0.17.

V0.17 proposed concrete values for several quantities. They are recorded here as candidates for the owner’s R0 decisions, not as results: separatrix distance $d_\epsilon$ in $<4$ ns (a child of TO-2 and TO-3), OSRE arbitration in $<45$ ns (the $t_{\mathrm{arb}}$ term of $T_{\mathrm{adm}}$), ISRE fold in $<120$ ns ($t_{\mathrm{fold}}$), dispatch acknowledgement $t_{\mathrm{ack}}<2.5$ ms (TO-14), a watchdog of 150 ms (TO-15), clone allocation in $<10\,\mu$s (TO-7 currently states $1\,\mu$s), K-line commit in $<80\,\mu$s (TO-11), prism encoding in $<250\,\mu$s (TO-10), and a 3-of-5 signature check in $<450\,\mu$s (rule updates). **\[AUTHOR: adopt, change or reject each candidate\]**

## 10.5 Reference hardware

*Decided 19 Nov 2026 by the owner:* the reference machine for every wall-clock objective is Apple silicon (AArch64, 128-bit NEON). Each recorded distribution names the chip, core type (performance or efficiency), macOS version, compiler and flags. Measurements are pinned to performance cores, because the scheduler may otherwise move the harness thread to an efficiency core.

#### R1 bound for TO-2.

A 32-interval block holds 32 lower and 32 upper bounds in fp32. On 4-lane NEON this is 16 vector compares (8 `FCMGE`, 8 `FCMLE`), 8 `AND`s combining each pair, and a reduction of 3 to 4 operations (an `AND` tree with one across-lane `UMINV`): about 28 vector operations. With four 128-bit SIMD pipes on a performance core, that gives a reciprocal throughput of about 7 cycles. The objective is therefore $\le 8$ cycles per block in steady state. The specification’s 4-cycle figure assumes 16 lanes and does not carry over. Two routes to a lower figure are child objectives, not assumptions: bounds stored as fp16 (8 lanes, halving the compare count, valid only if the 16-bit quantization error stays inside the margin $\delta$), and SME streaming mode on chips that implement it, used only after its mode-switch cost has been measured.

#### Timing on this machine.

There is no `rdtsc`. The architectural counter `CNTVCT_EL0` runs at 24 MHz on Apple silicon, so one tick is about 41.7 ns, about 5% of the TO-1 budget. The harness therefore (a) times batches of at least $10^3$ evaluations with `mach_absolute_time` for throughput, and (b) reads the per-evaluation distribution behind the p99 from the core cycle counter through the kperf performance-monitoring interface, which needs elevated privileges on macOS. If (b) is unavailable, TO-1 is reported as a batch mean with a stated tick resolution, and its p99 gate stays open, not passed.

#### Order of work.

The first loop to run is TO-1 with TO-2 as its child. The harness it requires is also the evaluation plan’s latency item, and every other wall-clock objective is stated relative to the per-step latency it produces. Phase T0 (Table 9) delivers the harness and the first recorded distribution.

# 11 Evaluation Plan

*No result in this section exists yet.* V0.17 reported an AgentDojo and “CyberSecAgent” campaign of 5,000 attacks with 100% interception, a 0.08% false-positive rate, a 740 ns p99, and bypass rates for three other guardrails. No such runs were performed, so those figures are withdrawn. The plan is:

1.  **Parity record** at one tagged commit set over the full corpus. **\[PENDING: release record\]**

2.  **Latency**: TO-1 with TO-2 as its child, then $T_{\mathrm{adm}}$ with each part measured under increasing load, on the reference machine. **\[PENDING: result\]**

3.  **Security effectiveness**: an AgentDojo-style \[26\] corpus of indirect prompt injection, agent hijacking and malicious-tool attacks (NISTAML.015, .061, .063) over the action plane, with closed-API and open-weight agents, reporting block rate, false-positive rate on benign tasks, task completion, and at least two baselines (a schema validator and an input/output classifier guardrail). This requires the admission decision on agent-initiated actions. **\[PENDING: result\]**

4.  **Exposure margin**: the distribution of $\mu_i(a)$ per domain with and without (B2), the share of steps that are consequential, and stall time while verdicts propagate, as $\delta$ is swept; with split budgets, the conservation check of Proposition 5 on recorded multi-instance runs, including retransmission. **\[PENDING: result\]**

5.  **Staging**: actions discarded at expiry and added latency, as the lease is swept. **\[PENDING: result\]**

6.  **Semantic return path**: exclusion rate of poisoned or fabricated responses, false-exclusion rate, and the miss rate $\beta$ with its conditional dependence across repeated opportunities (Proposition 7). **\[PENDING: result\]**

7.  **Replay**: determinism of re-evaluating recorded traffic against a candidate bundle. **\[PENDING: result\]**

8.  **Asset workflow**: the IFRS chain on the three voting engines, compared 3-of-3, with zero blocks held while parked, approver $\neq$ preparer, a refused replay, escape on a stale upstream, the pool limit at $\texttt{maxActive}+1$, and receipts verified offline (CI#715). **\[PENDING: result\]**

9.  **Learning path**: neuralese parity on a recorded corpus; dictionary reconstruction and sparsity; held-out separation of node selections; and the share of near misses whose markers yield a rule that fires on them and not on their counterparts. **\[PENDING: result\]**

# 12 Learning Path and Research Agenda

*Status: K-lines are specified (`RealityEngine_CI/SURFACE_SPEC.md`, CI#287 and \#603) and not implemented; neuralese Reality Events are an owner specification (31 October 2026) not yet in the repositories; everything else in this section is design or hypothesis. Under the engineering contract, none of it is reported as working until all three voting engines implement it and regression proves it on identical corpora.*

The admission path cannot see what $\omega_\tau$ does not encode (Corollary 1). The learning path is how the encoding grows: it keeps every episode, reads close calls from inside the model, and proposes new rules that a person can read, which reach operation only as approved corpus changes (Figure 3).

*Figure 3. The learning loop. The top row is the operational path; the lower row is B- and C-level work beside it, which changes nothing in operation. All components are specified or designed. \[Diagram in the PDF edition.\]*

## 12.1 K-lines

After Minsky \[47, 48\], a K-line is the composition of the active Reality Events of a machine set $M$ and the ordered step pairs they went through, $$\mathrm{Kline}(M,m..n)=\bigl(\mathrm{active}(M,\text{before }m),\ [(\mathrm{ISRE}_k|_M,\mathrm{OSRE}_k|_M)]_{k=m}^{n},\ \mathrm{active}(M,\text{after }n)\bigr).$$ The start state makes it self-verifying (re-establish it, present the recorded ISREs, and every OSRE must reproduce, Appendix 16); the end state makes it resumable. Boundaries come from the corpus: a K-line opens when a sequence’s initial event matches and closes *completed*, *abandoned*, *subsumed* or *interrupted*. Abandoned K-lines are kept; they are the near misses. Scope is the focal machine plus every machine that fed the path through arbitration feedback, for at most `klineFeedbackHops` hops (default 3), so a start-state ring of $W=L(\mathtt{klineFeedbackHops}+1)$ committed steps resolves any contributor. Each instance keeps its K-lines in append-only segments, bounded by `klineStoreMaxBytes` (default 2 GiB), never silently evicting an unexported segment; export bundles seed a sandboxed learning replica from which nothing flows back.

## 12.2 Neuralese Reality Events

A model-bound Reality Event carries members $[0..n)$, where $n$ is the model’s hidden dimension, so its neural nodes are exactly the event’s members (owner, 31 October 2026). For the universe model, `nemotron-3-nano:4b`, $n=3{,}136$ over 42 layers: 21 Mamba-2, 4 attention and 17 MLP \[49, 50\]. A neuralese Source reads the residual stream at a declared tap and writes node $j$ to cell $b+j$ of a reserved band. The band cannot sit at $[1024..4159]$ as the source notes and V0.17 place it, because those cells hold corpus regions; a first band could start at 86,016, after the clone space. Five declarations make the fold deterministic: the band, the model identity (tag, digest, quantization; the GGUF and MLX builds produce different activations), the tap (layer, position, cadence), the value rule (raw activations are unbounded, so elements over them use `threshold` or `equals`, or a declared affine calibration), and the acquisition runtime. The model need not be deterministic: the engines consume the recorded vector, so decisions are deterministic over it, and in regression a recorded neuralese corpus is replayed into all three voting engines. One tap is 12,544 bytes per vector at float32. **\[AUTHOR: band offset, tap, value rule, runtime\]**

## 12.3 The TopK prism and difference markers

Superposition \[29\] makes the raw difference between a near miss and its counterpart dense and unreadable. A TopK sparse autoencoder \[45, 33\] keeps exactly $k_f$ features per input, $\mathbf{z}=\mathrm{TopK}\bigl(W_{\mathrm{enc}}(\mathbf{h}-\mathbf{b}_{\mathrm{dec}})+\mathbf{b}_{\mathrm{enc}}\bigr)\in\mathbb R^m$, $m\gg n$. For a near miss and a completed K-line of the same sequence, the B-level encodes each recorded vector separately and compares supports: features that appeared, vanished or changed by more than a declared margin. These are Winston’s difference markers \[64\], read from inside the model. Because the deciding feature may rank just below the cut, candidates at ranks 33–48 are scored by their residual gain, following Joung and Bae \[31\], whose TopK128$\to$<!-- -->64$\to$<!-- -->32 schedule with FISTA refinement reduced dead features from 63.12% to 17.84% on GPT-2 Small; those figures are a training recipe, not expected results for the universe model. A dictionary is valid for one model build, quantization and tap, and its identity is recorded on every marker and every rule derived from it. V0.17’s example of a named feature (“Feature 4182: unauthorized shell redirection”) and its thresholds are illustrative: no dictionary exists yet for the universe model. **\[AUTHOR: train or adopt a dictionary\]**

## 12.4 TopK node selection

*Status: design (owner direction, 18 November 2026).* TopK is applied a second time, to the model’s own nodes, to decide which are ingested at all. A *settled span* is at least $w$ consecutive presentations with relative speed $v(t)=\|\Delta\mathbf{h}(t)\|/\|\mathbf{h}(t)\|<\varepsilon$; a *revision* is a span with $v>\varepsilon_{\mathrm{hi}}$ that moves between settled states more than $\rho$ apart. For node $j$ over a K-line, the momental vector $\mathbf{\mu}_j=(\bar h_j^{\,\mathrm{commit}},\ \bar h_{B,j}-\bar h_{A,j},\ \overline{|\Delta^2 h_j|}_{\mathrm{rev}})$ records its committed level, its displacement across the preceding revision and its turbulence during it. Nodes are scored by the largest standardized class-mean gap between completed and abandoned K-lines, and the top $k$ form a versioned selection $\sigma$, as in sparse probing \[32\]. Over the selected nodes, a completed K-line doubles as a predictor: *transition predictors* test whether the projected state lies in the next event’s interval, and *departure predictors* test whether the trajectory has left the envelope of stored successes. A departure predictor can open an approach before the comparator crossing; prediction never relaxes (B2), it can only bring the window forward. Errors drive reselection, new rules and a small share of full-band shadow capture, since a selection cannot detect what it never ingests. With $k=64$ the band is 384 cells, about one eighth of the full tap. **\[AUTHOR: momental thresholds; $k$ per family; $H_p$; shadow share\]**

## 12.5 From markers to rules

The C-level compiles markers into a candidate machine that acts as a Minskyan censor (refuse) or suppressor (redirect to $\mathbf{s}_{\mathrm{safe}}$). One geometric fact decides how such a rule runs. A conjunction of per-member intervals is an axis-aligned box, while “feature $i$ is active” is approximately a half-space $\mathbf{w}_i^{\top}(\mathbf{h}-\mathbf{b}_{\mathrm{dec}})+b_i\ge\theta$, which no box expresses. The options are: (A) the Source also writes the pre-activations of the features rules use, as cells, so rules stay readable and engines unchanged; (B) a box approximation over raw members, which loses fidelity (but is exact over selected nodes, where a rule is a box in node coordinates); and (C) a linear comparator in the engines, which is exact but requires three engines to compute a 3,136-term dot product identically, with summation order and precision specified and proven at parity. **\[AUTHOR: choose; A is recommended\]** A candidate is accepted for review when, in the sandbox replica, it fires on the near misses it came from and stays silent on their counterparts; it then enters the corpus like any machine, through 3-of-3 regression and the governance of Section 7.

**Table 9.** Phased plan. Followers adopt each phase on their own cadence and never vote.

| Phase  | Delivers                                                                      | Proven by                                                          | Depends on             |
|:-------|:------------------------------------------------------------------------------|:-------------------------------------------------------------------|:-----------------------|
| T0     | Timing harness; first TO-1/TO-2 distributions                                 | Recorded distribution at a tagged commit                           | None                   |
| K1     | K-line capture, store, routes on C++, LSP, Scala                              | 3-of-3 regression; self-verification                               | RE-Clock (CI#600)      |
| M1     | Margin window (B2): $\delta$, approach records, budgets (split, receive-once) | Fail-safe after $\bar\mu$ in replay; conservation on recorded runs | K1; RE-Clock           |
| K2     | Export bundles; sandbox replica                                               | Replica replays every imported near miss                           | K1                     |
| N1     | Neuralese Source; full-band capture to sandbox                                | Recorded corpus replayed 3-of-3                                    | Tap, runtime decisions |
| S1, N2 | Node selection $\sigma$; operational band over $S$                            | Reproducible selection; held-out separation; 3-of-3                | K2, N1                 |
| Q1     | Projection cells; predictors; prediction-error records                        | Predictions scored at K-line close                                 | N2, M1                 |
| P1, P2 | Dictionary; difference markers                                                | Reconstruction, sparsity; markers with dictionary identity         | N1, K2                 |
| R1, R2 | Rule compilation; approval and deployment                                     | Sandbox acceptance; 3-of-3; governance record                      | P2; quorum             |

## 12.6 Coarse-grained hazard prediction

Predictors over K-line partitions raise a quantitative question: how far ahead can a coarse-grained chain predict hazard occupancy, and with what error? V0.17 stated a “Mori–Zwanzig” theorem whose bound mixed a memory-kernel constant with a Dobrushin coefficient it gave as $0.812$, a value no run produced. The following statement separates what can be proved from what must be measured. Let the state at a declared tap be labeled by a partition $\{K_1,\dots,K_M\}$ (for example by clustered TopK supports), and let $\mathbf{p}_t\in\Delta_M$ be the distribution of the label at presentation $t$.

**Proposition 8** (Prediction error of a coarse-grained chain). *Suppose there are a stochastic matrix $P$ and zero-sum vectors $\mathbf{e}_t$ with $\mathbf{p}_{t+1}=\mathbf{p}_tP+\mathbf{e}_t$ and $\|\mathbf{e}_t\|_{\mathrm{TV}}\le\varepsilon_{\mathrm{mem}}$ for all $t$, and let $\hat P$ be an estimate with $\max_i\|\hat P_{i\cdot}-P_{i\cdot}\|_{\mathrm{TV}}\le\varepsilon_{\mathrm{stat}}$ and Dobrushin coefficient $\eta=\eta(\hat P)$ \[27\]. Then for every $k\ge1$, $$\bigl\|\mathbf{p}_{t+k}-\mathbf{p}_t\hat P^{\,k}\bigr\|_{\mathrm{TV}}\ \le\ E(k)\ :=\ (\varepsilon_{\mathrm{mem}}+\varepsilon_{\mathrm{stat}})\sum_{j=0}^{k-1}\eta^{\,j}\ \le\ \frac{\varepsilon_{\mathrm{mem}}+\varepsilon_{\mathrm{stat}}}{1-\eta}\quad(\eta<1).$$ Consequently, for any set of hazard cells $\mathcal H$, if $[\mathbf{p}_t\hat P^{\,k}](\mathcal H)>\theta+E(k)$ then the true probability of $\mathcal H$ at $t+k$ exceeds $\theta$.*

The proof is in Appendix 15. The two error terms have different sources. $\varepsilon_{\mathrm{mem}}$ is the per-step failure of the label process to be Markov on this partition: it is zero when the chain is lumpable with respect to the partition \[41\], and the Mori–Zwanzig formalism \[66, 69\] expresses it as a memory term whose decay would make it small; neither its size nor its decay is known for any model, so it must be estimated from held-out K-lines. $\varepsilon_{\mathrm{stat}}$ is estimation error: if row $i$ is estimated from $n_i$ transitions that are independent given the current label, then by the $L_1$ deviation inequality of Weissman et al. \[68\] and a union bound over rows, with probability at least $1-\delta_c$, $\varepsilon_{\mathrm{stat}}\le\tfrac12\max_i\sqrt{2\,(M\ln2+\ln(M/\delta_c))/n_i}$. Transitions counted along K-lines are independent given the label only if the chain is Markov, so this bound is itself conditional on $\varepsilon_{\mathrm{mem}}$ being small. Across layers the kernels differ, and the product $\prod_i\hat P_{\ell+i}$ replaces $\hat P^{\,k}$, with $\eta$ taken as the largest coefficient in the product; the same proof applies. **\[AUTHOR: layer time, token time, or both\]**

## 12.7 Hypotheses about residual-stream dynamics

V0.17 promoted four hypotheses to theorems: a Whitney–Takens observability theorem, a tri-modal spectral theorem for attention, Mamba-2 and MLP layers, and two attractor theorems. Each proof rested on numbers no run produced or on a theorem that does not apply, so each returns to hypothesis here, with the one structural fact that can be proved.

**Lemma 1** (State contraction in a Mamba-2 recurrence). *In a Mamba-2 layer the recurrent state evolves as $\mathbf{s}_t=a_t\mathbf{s}_{t-1}+B_t\mathbf{x}_t$ with scalar $a_t=\exp(\Delta_tA)$, $A<0$ and $\Delta_t>0$ \[23\]. For two state sequences driven by the same inputs, $\|\mathbf{s}_t-\mathbf{s}'_t\|=a_t\|\mathbf{s}_{t-1}-\mathbf{s}'_{t-1}\|$ with $0<a_t<1$, so the state forgets its initial condition geometrically, at rate $\prod_t a_t$.*

*Proof.* Subtract the two recurrences: the input terms cancel, leaving $\mathbf{s}_t-\mathbf{s}'_t=a_t(\mathbf{s}_{t-1}-\mathbf{s}'_{t-1})$, and $a_t=\exp(\Delta_tA)\in(0,1)$ because $\Delta_tA<0$. ◻

The lemma is about the recurrent state over token time with fixed inputs. It does not imply that the residual stream contracts across a Mamba-2 layer, because the layer adds its output to the residual (an identity term), and $\Delta_t$, $B_t$ and the output projection depend on the input. It is the only part of V0.17’s Theorem 4 that survives; its layer exponents ($|\Lambda_{\mathrm{Attn}}|\le0.048$, $\Lambda_{\mathrm{SSM}}\le-0.084$, $\Lambda_{\mathrm{MLP}}\ge0.312$) were not measured, and its MLP bound does not follow from Cauchy interlacing.

**Hypothesis 1** (H1, layer-type dynamics). *Treating depth as discrete time, finite-time Lyapunov exponents \[59\] of the residual stream differ systematically by layer type in the universe model: near zero for attention layers, negative for Mamba-2 layers and positive for MLP layers.*

**Hypothesis 2** (H2, separable basins). *Factual and hallucinated generations occupy distinct regions of a state space reconstructed from recorded taps, and a declared observation map built from layer statistics is injective on the union of those regions, so the regions’ images are disjoint.*

Generic embedding results \[63, 67\] say that *almost every* smooth map into enough dimensions is injective on a set of given box-counting dimension. They say nothing about a particular engineered map, and V0.17’s attractor dimension ($d_A\le14.2$) was not measured. H2 is therefore an empirical claim to test, not a consequence of those theorems; delay embedding also presumes autonomous dynamics, which layer-to-layer maps are not.

**Hypothesis 3** (H3, asymmetric capture). *Unperturbed transitions from a factual into a hallucination regime are much more probable than the reverse, so intervention must precede the crossing.*

Akarlar \[10\], on Qwen2.5-1.5B, found that injecting a hallucinated activation into a correct trajectory corrupted output in 87.5% of trials (layer 20), while the reverse recovered only 33.3% (layer 24). These are intervention success rates on a different model. V0.17 divided them to obtain a Kramers rate ratio of 2.627 \[65\]. That step is invalid: a Kramers ratio of escape rates depends on barrier heights and a noise intensity, none of which the patching experiment measures, and a ratio of intervention success rates is not a ratio of rates. H3 is consistent with the asymmetry but not established by it. Gurnee et al. \[36\] identify a small set of verbalizable representations with workspace-like properties, a candidate low-dimensional signal for testing H2 and H3.

#### Reflection hierarchy.

In Minsky’s terms \[48\], the A-level executes, the B-level observes near misses, and the C-level proposes rule changes that are replayed against recorded K-lines and deployed only through the quorum of Section 7.

# 13 Limitations

- **Incomplete by construction.** Corollary 1 applies to RealityEngine: hazards that depend on unencoded quantities collide at admission.

- **Bounded, not closed.** The exposure bounds hold only for hazards observable through Sources (B1), only with the window (B2), which is to be implemented, and only for actions within $\delta$ of a separatrix. The whole-cone bound needs split budgets with receive-once; without them the bound is per path.

- **In-bounds harm.** Interval predicates cannot detect an action whose encoded signals are in bounds but whose effect is harmful, such as a well-formed transfer to an attacker when the recipient is not a declared signal.

- **Admission decision not built.** The admit/reject/replace decision on agent-initiated actions and $\mathbf{s}_{\mathrm{safe}}$ are design; complete mediation (A1) is a deployment property not yet provided.

- **Evaluator trust.** The return path is only as good as its evaluator; its miss rate, and how misses correlate, must be measured.

- **No measurements.** Latency and effectiveness results are pending. Release v0.0.2’s parity record states which stages passed, not the oracle and pass counts.

- **Domain modeling cost.** Protection extends only to declared hazards; task-sufficiency must be argued per domain.

- **Asset workflow, one domain.** IFRS is the only admitted workflow. Its domain is experimental, and its templates do not yet recognize the lifecycle lanes. The governance and threat-dynamics machines are candidates, tested only through simulated Sources.

- **Learning path unbuilt; open-weight models only.** No dictionary or selection exists for the universe model, and neuralese folding needs hidden states that closed APIs do not expose.

- **Single author, no external review.** **\[AUTHOR: note invited reviewers once engaged\]**

# 14 Conclusion

A deterministic governor between an agent and the world cannot escape the limit of its own observation: wherever a hazard depends on something it does not encode, safe and hazardous contexts collide on a set of positive measure, and only an encoding whose fibers saturate the hazard is complete. RealityEngine accepts that limit and bounds its consequence instead. Responses return through verified Sources; consequential steps are counted against a budget that is conserved across every node an action’s effects reach; staged effects commit only on a safe verdict; and the domain’s fail-safe output takes over when the budget runs out. The engine that enforces this is implemented in three voting runtimes over a shared corpus, with parity proven in regression and a governed asset workflow on top. The window, the admission decision, the fail-safe vectors and every timing figure remain to be built or measured, and the evaluation plan says how each will be shown.

# A Proofs

#### Proof of Theorem 2.

\(i\) Choose $\mathbf{u}\in\ker\pi$ with $\langle\mathbf{u},\mathbf{n}_0\rangle\neq0$ and set $\gamma(s)=c_0+s\mathbf{u}$. Then $\phi(\gamma(s))=\phi(c_0)+s\langle\nabla\phi(c_0),\mathbf{u}\rangle+o(s)=s\langle\mathbf{n}_0,\mathbf{u}\rangle+o(s)$, since $\phi(c_0)=0$. Hence for all sufficiently small $\varepsilon>0$, $\gamma(-\varepsilon)$ and $\gamma(\varepsilon)$ lie in $U$ and $\phi$ takes opposite non-zero signs at them. One of them, call it $c_1$, lies in $\{\phi<0\}\cap U\subseteq
\mathcal C_{\mathrm{safe}}$ and the other, $c_2$, in $\{\phi>0\}\cap U\subseteq\mathcal C_h$. By linearity, $\pi(\gamma(\pm\varepsilon))=\pi(c_0)\pm\varepsilon\pi(\mathbf{u})=\pi(c_0)$, so $\pi(c_1)=\pi(c_2)$.

\(ii\) The condition $\ker\pi\not\subseteq T_{c_0}\Sigma$ is open in $c_0$ along $\Sigma$, because $\nabla\phi$ is continuous: it holds at every point of $\Sigma\cap U'$ for some neighborhood $U'\subseteq U$ of $c_0$, and the argument of (i) applies at each such point, so every $v\in\pi(\Sigma\cap U')$ is the observation of a colliding pair. It remains to show that $\pi(\Sigma\cap U')$ contains an open set. Since $T_{c_0}\Sigma$ has dimension $D-1$ and $\ker\pi$ contains a vector outside it, $T_{c_0}\Sigma+\ker\pi=\mathbb R^D$, so $\pi(T_{c_0}\Sigma)=\pi(\mathbb R^D)=V$. The restriction $\pi|_\Sigma$ therefore has differential of full rank $d$ at $c_0$, hence near $c_0$, and by the constant-rank (submersion) theorem it maps a neighborhood of $c_0$ in $\Sigma$ onto an open subset of $V$. An open non-empty subset of $\mathbb R^d$ has positive Lebesgue measure. $\square$

#### Proof of Proposition 1.

(a)$\Rightarrow$(b): if $g\circ\pi$ rejects exactly $\mathcal C_h$ and $\pi(c_1)=\pi(c_2)$, the two receive the same decision, so both or neither lie in $\mathcal C_h$. (b)$\Rightarrow$(c): $\mathcal C_h\subseteq\pi^{-1}(\pi(\mathcal C_h))$ always; if $\pi(c)=\pi(c')$ with $c'\in\mathcal C_h$, then $c\in\mathcal C_h$ by (b). (c)$\Rightarrow$(a): let $g(v)=\mathrm{reject}$ exactly when $v\in\pi(\mathcal C_h)$; then $g(\pi(c))=\mathrm{reject}$ iff $c\in\pi^{-1}(\pi(\mathcal C_h))=\mathcal C_h$. For the last claim, if some boundary point $c$ had $\ker\pi\not\subseteq T_c\Sigma$, Theorem 2(i) would give a colliding safe–hazardous pair, contradicting (b). $\square$

#### Proof of Proposition 5.

Write $R$ for the sum of shares held by all instances, $T$ for the units carried by messages sent and not yet received, and $A$ for the number of consequential admissions made under $O_a$. Initially $R=\bar\mu$ and $T=A=0$. We show that $R+T+A\le\bar\mu$ is preserved by every operation. An admission moves one unit from $R$ to $A$ and is allowed only when the acting instance’s share is at least one, so all shares stay non-negative. A send moves $s\le r$ units from $R$ to $T$. A first receive of a message moves its units from $T$ to $R$; a later receive of the same identifier is ignored. A lost message leaves its units in $T$ forever, which can only lower what remains available. No operation increases $R+T+A$. Since $R,T\ge0$, $A\le\bar\mu$ at every point of every execution. Without the receive-once rule, a duplicated message adds its units to $R$ twice while $T$ falls once, so $R+T+A$ can exceed $\bar\mu$; this is why the rule is necessary. $\square$

#### Proof of Proposition 8.

Write the error as a telescoping sum, $$\mathbf{p}_{t+k}-\mathbf{p}_t\hat P^{\,k}=\sum_{j=0}^{k-1}\bigl(\mathbf{p}_{t+j+1}-\mathbf{p}_{t+j}\hat P\bigr)\hat P^{\,k-1-j}.$$ Each bracket equals $\mathbf{p}_{t+j}(P-\hat P)+\mathbf{e}_{t+j}$, a zero-sum vector. Its total-variation norm is at most $\sum_i p_{t+j,i}\|P_{i\cdot}-\hat P_{i\cdot}\|_{\mathrm{TV}}+\|\mathbf{e}_{t+j}\|_{\mathrm{TV}}\le\varepsilon_{\mathrm{stat}}+\varepsilon_{\mathrm{mem}}$. For a zero-sum vector $\mathbf{x}$ and stochastic $Q$, $\|\mathbf{x}Q\|_{\mathrm{TV}}\le\eta(Q)\|\mathbf{x}\|_{\mathrm{TV}}$, and $\eta$ is submultiplicative, so $\|\mathbf{x}\hat P^{\,r}\|_{\mathrm{TV}}\le\eta^r\|\mathbf{x}\|_{\mathrm{TV}}$. Summing gives $E(k)$. The last claim follows because $|\mathbf{p}(\mathcal H)-\mathbf{q}(\mathcal H)|\le\|\mathbf{p}-\mathbf{q}\|_{\mathrm{TV}}$ for any set $\mathcal H$. $\square$

# B Initial Condition for Replay

**Proposition 9** (Sufficiency). *Let a machine have transition $\delta:Q\times\Sigma\to Q\times O$. Given an initial configuration $S_0$ and recorded inputs $\mathbf{v}_1,\dots,\mathbf{v}_H$, the run $S_0,\dots,S_H$ and its outputs are uniquely determined.*

*Proof.* Induction on $H$: $(S_{k+1},o_{k+1})=\delta(S_k,\mathbf{v}_{k+1})$ is unique because $\delta$ is a function. ◻

**Proposition 10** (Necessity, conditional). *If two initial configurations produce different outputs on the recorded inputs, the inputs alone do not determine the execution, so $S_0$ must be recorded.*

Necessity is conditional: it fails when the input word is synchronizing or only one state is reachable. Recording $S_0$ is therefore a safe design rule, and the K-line start state implements it. The replay procedure is specified in the K-line contract as self-verification and is not yet implemented; no replay function exists in the Lisp repository. **\[AUTHOR: commit an implementation with a test\]**

# C Treatment of the V0.17 Claims

Each row records what V0.17 asserted and what V0.18 does with it. “Adopted” means kept with its hypotheses stated; “corrected” means kept in a different, provable form; “withdrawn” means removed because no evidence supports it.

| V0.17 claim                                                                                          | Treatment               | Reason and where it now lives                                                               |
|:-----------------------------------------------------------------------------------------------------|:------------------------|:--------------------------------------------------------------------------------------------|
| “Certified 10/10” proof completeness and realizability                                               | Withdrawn               | No certification exists; each result now carries its hypotheses                             |
| Theorem 1, transverse-slice collision proof                                                          | Corrected               | Theorem 2: condition is geometric, not “measure zero by Sard”; positive-measure part proved |
| Theorem 1(3), complete iff variables spanned                                                         | Corrected               | Proposition 1 (saturation equivalence)                                                      |
| Appendix A, Fubini positive-measure argument                                                         | Corrected               | Theorem 2(ii) via the submersion theorem                                                    |
| Proposition 1, induction over dispatch trees                                                         | Corrected               | Proposition 5: conservation invariant; adds the receive-once rule the induction missed      |
| Two-phase actuation quarantine, zero irreversible effects                                            | Corrected               | Proposition 6: safety from discard-on-expiry, not from lease length; stageable actions only |
| Supermartingale escape bound, DO-178C Level A                                                        | Corrected / withdrawn   | Proposition 7 with its dependence hypothesis; certification claim withdrawn                 |
| Chebyshev distance $d_\epsilon$                                                                      | Adopted                 | Definition 4                                                                                |
| Theorem 2, Mori–Zwanzig predictability, $\eta=0.812$                                                 | Corrected               | Proposition 8; $\varepsilon_{\mathrm{mem}}$ and $\eta$ to be measured                       |
| Theorem 3, Whitney–Takens observability, $d_A\le14.2$                                                | Withdrawn to hypothesis | H2; generic theorems do not apply to a fixed map; dimension unmeasured                      |
| Theorem 4, tri-modal spectral exponents                                                              | Withdrawn to hypothesis | H1; Lemma 1 keeps the provable Mamba-2 fact                                                 |
| Theorems 5–6, basins and Kramers ratio 2.627                                                         | Withdrawn to hypothesis | H2, H3; ratio of intervention rates is not a rate ratio                                     |
| A1 as an “iff” with seccomp profile                                                                  | Corrected               | Assumption 1; profile file does not exist                                                   |
| A2 with STT $\le0.82\,\mu$s across 1,552 machines                                                    | Corrected               | Assumption 2; latency is objective TO-1                                                     |
| B1 dual-tier PAC ensemble, $\beta\le10^{-3}$                                                         | Withdrawn               | Evaluator is rule-based; $\beta$ unmeasured                                                 |
| B2 fractional affine tokens                                                                          | Corrected               | Integer shares, Proposition 5                                                               |
| Code listings (SIMD recognizer, budget manager, HealthKit transducer, tri-modal kernel, Lisp replay) | Withdrawn               | Files absent from the repositories (Table 7)                                                |
| 13-domain table, 1,552 machines                                                                      | Corrected               | Table 6; V0.17’s counts summed to 1,652                                                     |
| 8,192-slot ISRE; neuralese at 1024–4159                                                              | Withdrawn               | Superseded by `region-allocation.json`                                                      |
| Coverage percentages as “verified code coverage”                                                     | Corrected               | Audit checklist scores (Section 4.7)                                                        |
| Threat statuses, 17 of 19 implemented                                                                | Corrected               | Table 5; T20–T22 added from V0.17                                                           |
| TO-1 to TO-18 “Gated / Passing”                                                                      | Withdrawn               | No harness; candidate targets kept for R0 (Section 10.4)                                    |
| AVX-512 reference kernel                                                                             | Corrected               | Apple silicon NEON is the reference (owner, 19 Nov 2026)                                    |
| AgentDojo/CyberSecAgent results; comparison table                                                    | Withdrawn               | No runs performed (Section 11)                                                              |
| Four-way pass-set equality including Rust; bit-identical traces                                      | Corrected               | Three voters, pass-set equality (Section 9.1)                                               |
| Radenković “relativistic” proofs; OEE calculus implemented by RealityEngine                          | Corrected               | RealityEngine adopts the three levels and the incompleteness theorem, not atomic execution  |
| All 34 author items resolved                                                                         | Withdrawn               | Appendix 18 lists the items still open                                                      |

# D Open Author Items

1.  Scope: is admission of agent-initiated actions in this paper, or the next release?

2.  (B2): adopt split budgets with receive-once? Split policy; $\delta$ per domain; $\bar\mu$.

3.  Staging: which action classes are stageable; lease lengths.

4.  Fail-safe vectors $\mathbf{s}_{\mathrm{safe}}$ per domain; hazard tags in $\omega_\tau$.

5.  Rule-update governance: fault model, $n$, $q$, protocol, key custody, root of authority.

6.  SPIFFE trust domain and node attestor.

7.  Timing: the “to set” targets, the V0.17 candidate values, TO-1 per machine or per step and at what corpus size, the CI regression tolerance.

8.  Learning path: neuralese band offset, tap, value rule and runtime; dictionary; rule option (A recommended); momental thresholds; $k$ per family, $k_{\max}$, $H_p$, shadow share; layer time or token time.

9.  ~~Ports of the Scala and Lisp runtimes; the parity release record.~~ Resolved in V0.19 (Sections 9, 9.1). What remains is oracle and pass counts in the next release record.

10. The potassium example: keep, replace with a corpus example, or move to a clinical companion.

11. Related-work cells; Radenković et al. volume, issue and DOI; CapChain title.

12. Affiliation and contact address; AI-assistance disclosure details; invited reviewers.

# E Changes from V0.18

Each change, with its source at the repository heads of 25 November 2026.

| Section | Change | Source |
|:--|:--|:--|
| Header, Abstract | V0.19; three followers; parity certified in a tagged release | this appendix |
| 4.5 | A2A replaces OpenClaw in v0.0.3; LangGraph agents with persisted tasks and once-only dispatch; framework drafted; admission proxies planned | CI#841, \#844, \#846, \#848, \#850, \#851; localLangChainStack#1, \#12 |
| 4.6 | Simulated-Source sample formula; a Lisp PE defect it found | CI#866; LSP#200, \#201 (in review) |
| 4.7 | Gaps moved since the audit: `RE-Clock`, source-kind taxonomy, OpenClaw successor | CI#600, \#861; Machines#290 |
| 6, Table 4 | IFRS chain certified (22/22); asset workflow on the release install; a failed step parks for its author; two candidate domains | CI#788, \#814, \#818–\#824; localAssetStorageStack#32; Manager#347; Machines#256, \#297, \#301 |
| 7 | Full `RE-Clock` with the receive rule on every RE and PE | CPP#207, LSP#199, Scala#223, Rust#82, GO#38, Manager#367; CI#858, \#861–\#863; Machines#296, \#299 |
| 8 | Heads moved to 25 November; T18 per-source client certificates and v0.0.2 certification; threat-dynamics candidates noted, no status change | CI#774, \#818; Machines#301 |
| 9 | Ports stated; Go follower; follower release gate; corpus unchanged; factory packages named | start scripts; GO#15–\#38; CI#842, \#843, \#849, \#853; Machines#289–\#305 |
| 9, Table 7 | Followers, parity, TLS, clock, taxonomy, A2A, K-line readiness rows | as above; CI#857 |
| 9.1 | Release v0.0.2 parity record replaces the PENDING marker | `RealityEngine_CI/releases/release-v0.0.2.md` |
| 10.4 | TO-3: V0.18 said “fail-safe exists” while Table 7 and Section 4.4 say none does; no engine or domain has it, so Design. TO-14 names the dispatch protocol | code search of the three voters and the corpus; CI#841 |
| 13, D | Limitations and author item 9 updated | above |

Unchanged, and checked in code: the domain fail-safe vector, rule epochs and the pointer swap, release envelopes, split budgets and the margin window, K-line recording, and the timing harness. None exists in the engines or the corpus.

# AI-Assistance Disclosure

AI tools were used for code generation, typesetting, literature search and manuscript revision. **\[AUTHOR: list the exact tools and model versions used and what each did\]**. The author reviewed all content and is responsible for it.

# References

1.  IBM Research, BeeAI project. Agent Communication Protocol (ACP): Welcome. <https://agentcommunicationprotocol.dev/introduction/welcome>. Specification v1.0.3, 21 August 2025; repository archived, <https://github.com/i-am-bee/acp>.

2.  Agent Client Protocol. Introduction and Overview. <https://agentclientprotocol.com/protocol/overview>.

3.  OpenClaw Docs. ACP: run the Agent Client Protocol bridge that talks to an OpenClaw Gateway. <https://docs.openclaw.ai/cli/acp>.

4.  A2A Protocol. Specification. <https://a2a-protocol.org/latest/specification/>.

5.  Agentic AI Foundation. A2A joins AAIF’s open agentic stack. 17 August 2026; <https://aaif.io/blog/a2a-joins-aaif>.

6.  A. Vassilev, A. Oprea, A. Fordyce, X. Davies, M. Hamin. Adversarial Machine Learning: A Taxonomy and Terminology of Attacks and Mitigations. NIST SP 2400-102e2026 ipd (Initial Public Draft), November 2026. <https://doi.org/10.6028/NIST.SP.2400-102e2026.ipd>.

7.  OWASP GenAI Security Project. Agent Control Standard. <https://github.com/GenAI-Security-Project/agent-control-standard>.

8.  Microsoft. Agent Governance Toolkit. <https://github.com/microsoft/agent-governance-toolkit>.

9.  LF AI & Data. ACP Joins Forces with A2A Under the Linux Foundation’s LF AI & Data. 29 August 2025; <https://lfaidata.foundation/communityblog/2025/08/29/acp-joins-forces-with-a2a-under-the-linux-foundations-lf-ai-data/>.

10. G. A. Akarlar. Hallucination as Trajectory Commitment: Causal Evidence for Asymmetric Attractor Dynamics in Transformer Generation. arXiv:2604.15400, 2026.

11. M. Alshiekh, R. Bloem, R. Ehlers, B. Könighofer, S. Niekum, U. Topcu. Safe Reinforcement Learning via Shielding. *AAAI*, 2018.

12. J. P. Anderson. Computer Security Technology Planning Study. ESD-TR-73-51, 1972.

13. G. R. Barber, C. Hewitt. Foundations for Office Semantics. MIT LCS TM-225, July 1982.

14. G. Barber, P. de Jong, C. Hewitt. Semantic Support for Work in Organizations. MIT AI Memo 719, April 1983; also in *Information Processing 83* (IFIP), 1983.

15. Amazon Web Services. Amazon Bedrock Guardrails. User Guide, <https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html>.

16. M. Bhattarai, M. Vu. Trustworthy Agentic AI Requires Deterministic Architectural Boundaries. arXiv:2602.09947, 2026.

17. H. Choong, C. Hsieh, F. Leu. CapChain: A Capability-Token Access Control Architecture. *Applied Sciences* 16(15):7776, 2026. **\[AUTHOR: verify exact title\]**

18. C. Bruggeman, O. Waddell, R. K. Dybvig. Representing Control in the Presence of One-Shot Continuations. *PLDI*, pp. 99–107, 1996.

19. S. Capadisli, A. Guy, R. Verborgh, C. Lange, S. Auer, T. Berners-Lee. Decentralised Authoring, Annotations and Notifications for a Read-Write Web with dokieli. *ICWE 2017*, LNCS 10360, pp. 469–481, 2017.

20. T. Bricken et al. Towards Monosemanticity: Decomposing Language Models With Dictionary Learning. *Transformer Circuits Thread*, 2023.

21. N. Chomsky. Three Models for the Description of Language. *IRE Trans. Information Theory* 2(3):113–124, 1956.

22. O. Danvy, A. Filinski. Abstracting Control. *ACM Conference on LISP and Functional Programming*, pp. 151–160, 1990.

23. T. Dao, A. Gu. Transformers are SSMs: Generalized Models and Efficient Algorithms Through Structured State Space Duality. *ICML*, 2024; arXiv:2405.21060.

24. L. D’Antoni, M. Veanes. The Power of Symbolic Automata and Transducers. *CAV*, 2017.

25. E. Debenedetti et al. Defeating Prompt Injections by Design. arXiv:2503.18813, 2025.

26. E. Debenedetti, J. Zhang, M. Balunović, L. Beurer-Kellner, M. Fischer, F. Tramèr. AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents. *NeurIPS Datasets and Benchmarks*, 2024.

27. R. L. Dobrushin. Central Limit Theorem for Nonstationary Markov Chains I, II. *Theory of Probability and Its Applications* 1, 1956.

28. M. Felleisen. The Theory and Practice of First-Class Prompts. *POPL*, pp. 180–190, 1988.

29. N. Elhage et al. Toy Models of Superposition. *Transformer Circuits Thread*, 2022; arXiv:2209.10652.

30. M. J. Fischer, N. A. Lynch, M. S. Paterson. Impossibility of Distributed Consensus with One Faulty Process. *J. ACM* 32(2):374–382, 1985.

31. K.-I. Joung, J. P. Bae. FISTA-Refined Dictionary Learning with Learned TopK Initialization for Sparse Decomposition of Transformer Residual Streams. *Algorithms* 19(8):697, 2026; doi:10.3390/a19080697.

32. W. Gurnee, N. Nanda, M. Pauly, K. Harvey, D. Troitskii, D. Bertsimas. Finding Neurons in a Haystack: Case Studies with Sparse Probing. *TMLR*, 2023; arXiv:2305.01610.

33. L. Gao et al. Scaling and Evaluating Sparse Autoencoders. arXiv:2406.04093, 2024.

34. S. Gilbert, N. Lynch. Brewer’s Conjecture and the Feasibility of Consistent, Available, Partition-Tolerant Web Services. *SIGACT News* 33(2):51–59, 2002.

35. Guardrails AI. <https://github.com/guardrails-ai/guardrails>.

36. W. Gurnee, N. Sofroniew, et al., J. Lindsey. Verbalizable Representations Form a Global Workspace in Language Models. *Transformer Circuits Thread*, 2026; arXiv:2607.15495.

37. N. Hardy. KeyKOS Architecture. *ACM SIGOPS Operating Systems Review* 19(4):8–25, 1985.

38. N. Hardy. The Confused Deputy. *ACM SIGOPS Operating Systems Review* 22(4):36–38, 1988.

39. H. Inan et al. Llama Guard: LLM-based Input-Output Safeguard for Human-AI Conversations. arXiv:2312.06674, 2023.

40. A. Kaul, Q. Lan, P. Gupta. Behavioral Governance for Autonomous AI Agents: The AgentBound Framework. arXiv:2606.30970, 2026.

41. J. G. Kemeny, J. L. Snell. *Finite Markov Chains*. Van Nostrand, 1960.

42. C. Kim, S. Cho. ARES: Securing Agents for Computer Use Through Endpoint Resource Mediation. Preprints.org 202608.0594, 2026.

43. L. Lamport. Time, Clocks, and the Ordering of Events in a Distributed System. *Commun. ACM* 21(7):558–565, 1978.

44. S. Capadisli, A. Guy (eds.). Linked Data Notifications. W3C Recommendation, 2 May 2017.

45. A. Makhzani, B. Frey. k-Sparse Autoencoders. arXiv:1312.5663, 2013.

46. Model Context Protocol Specification. <https://modelcontextprotocol.io/specification>.

47. M. Minsky. K-Lines: A Theory of Memory. *Cognitive Science* 4(2):117–133, 1980.

48. M. Minsky. *The Society of Mind*. Simon & Schuster, 1986.

49. NVIDIA. Nemotron 3 Nano 4B model card and configuration (`hidden_size` 3136, 42 layers), 2026; <https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-FP8>.

50. NVIDIA. Nemotron-H: A Family of Accurate and Efficient Hybrid Mamba-Transformer Models. arXiv:2504.03624, 2025.

51. M. Radenković, N. Radosavljević, A. Labus, S. Prokhorov, B. Radenković. Evolutive Consensus for Agentic AI: OEE Incompleteness of External Guardrails and the Execution Calculus for Safe Evolutive Agents. *Facta Universitatis, Series: Electronics and Energetics*, pp. 723–765, 2026. **\[AUTHOR: confirm volume/issue and DOI\]**

52. T. Rebedea, R. Dinu, M. Sreedhar, C. Parisien, J. Cohen. NeMo Guardrails: A Toolkit for Controllable and Safe LLM Applications with Programmable Rails. *EMNLP System Demonstrations*, 2023.

53. S. Josefsson, I. Liusvaara. Edwards-Curve Digital Signature Algorithm (EdDSA). RFC 8032, 2017.

54. E. Rescorla. The Transport Layer Security (TLS) Protocol Version 1.3. RFC 8446, 2018.

55. A. Rundgren, B. Jordan, S. Erdtman. JSON Canonicalization Scheme (JCS). RFC 8785, 2020.

56. D. Fett, B. Campbell, J. Bradley, T. Lodderstedt, M. Jones, D. Waite. OAuth 2.0 Demonstrating Proof of Possession (DPoP). RFC 9449, 2023.

57. J. H. Saltzer, M. D. Schroeder. The Protection of Information in Computer Systems. *Proc. IEEE* 63(9):1278–1308, 1975.

58. L. Sha. Using Simplicity to Control Complexity. *IEEE Software* 18(4):20–28, 2001.

59. S. C. Shadden, F. Lekien, J. E. Marsden. Definition and Properties of Lagrangian Coherent Structures from Finite-Time Lyapunov Exponents. *Physica D* 212:271–304, 2005.

60. T. Shi et al. Progent: Securing AI Agents with Privilege Control. arXiv:2504.11703, 2025.

61. S. Capadisli, T. Berners-Lee, R. Verborgh, K. Kjernsmo (eds.). Solid Protocol. W3C Solid Community Group, <https://solidproject.org/TR/protocol>.

62. SPIFFE: Secure Production Identity Framework for Everyone. Specification, <https://spiffe.io/docs/latest/spiffe-about/overview/>.

63. F. Takens. Detecting Strange Attractors in Turbulence. In *Dynamical Systems and Turbulence*, LNM 898:366–381, Springer, 1981.

64. P. H. Winston. Learning Structural Descriptions from Examples. MIT AI TR-231, 1970.

65. H. A. Kramers. Brownian Motion in a Field of Force and the Diffusion Model of Chemical Reactions. *Physica* 7(4):284–304, 1940.

66. H. Mori. Transport, Collective Motion, and Brownian Motion. *Progress of Theoretical Physics* 33(3):423–455, 1965.

67. T. Sauer, J. A. Yorke, M. Casdagli. Embedology. *Journal of Statistical Physics* 65(3–4):579–616, 1991.

68. T. Weissman, E. Ordentlich, G. Seroussi, S. Verdú, M. J. Weinberger. Inequalities for the L1 Deviation of the Empirical Distribution. HP Laboratories Technical Report HPL-2003-97, 2003.

69. R. Zwanzig. Memory Effects in Irreversible Thermodynamics. *Physical Review* 124(4):983–992, 1961.
