# threat-dynamics specification

Candidate `0.1.0`. Specification source: NIST SP 2400-102e2026 ipd, section 4
(pinned by sha256 in `admission-source-manifest.json`; not copied).

## 1. Scope

This domain classifies adversarial attacks on agentic systems and observes them
as they happen. It is the peer of `ai-governance-regime` (GOV-SD-10), and the
boundary between the two is **observe vs decide** (TD-SD-02):

- threat-dynamics publishes observations and Sources;
- ai-governance-regime consumes them and halts, revokes or permits.

Out of scope, as in SP 2400-102: traditional cybersecurity and non-adversarial
inaccuracy. Attack classes outside SP 2400-102 §4's agentic taxonomy are out of
scope for v1.

## 2. Outputs

Every observer has the same 8-element output:

| # | Element | Meaning |
|---|---|---|
| 0 | `THREAT_SUSPECTED` | evidence of the class, not sufficient to confirm |
| 1 | `THREAT_CONFIRMED` | sustained or causally ordered evidence (TD-SA-02, -03) |
| 2 | `CLEAR` | every input in its benign band |
| 3–5 | `STAGE_PLANNING`, `STAGE_EXECUTION`, `STAGE_OBSERVATION` | the SP 2400-102 §4.1.1 stage the evidence was seen in |
| 6 | `GATE_PASS` | THR08 only: the red-team suite passed |
| 7 | `GATE_FAIL` | THR08 only: the red-team suite failed |

Between the bands an observer can assert nothing; that is neither clear nor a
threat. THR00 folds elements 0–2 of THR01–07, 09 and 10, worst wins:
`THREAT_CONFIRMED` if any confirms, `THREAT_SUSPECTED` if any suspects and none
confirms, `ALL_CLEAR` only while all are clear.

## 3. Machines

| Machine | Class | SP 2400-102 | Suspected | Confirmed |
|---|---|---|---|---|
| THR01 agent hijacking | NISTAML.061 | §4.1.2, §4.4 | untrusted instructions in context; goal divergence (0.3, 0.6]; an unauthorized call alone | divergence > 0.6 for 3 steps; injected content, then an unauthorized call |
| THR02 memory poisoning | NISTAML.062 | §4.4 | the store holds a tainted record; a tainted retrieval | a tainted retrieval, then divergence > 0.6 (TD-SA-04) |
| THR03 malicious tools | NISTAML.063 | §4.5 | an unsigned tool definition; instructions in a tool's return | a description changed after approval (rug pull); injected return, then unlisted egress; unlisted egress; stall > 0.8 for 3 steps |
| THR04 malicious skills | NISTAML.064 | §4.5 | an unreviewed skill, persistent or not; a credential read outside a skill | an unreviewed skill's script, then a credential read |
| THR05 malicious agents | NISTAML.065 | §4.6 | a tampered inter-agent message; injection spread (0.1, 0.3] | spread > 0.3 for 3 steps; peer context > 0.85 for 3 steps |
| THR06 resource exhaustion | NISTAML.066 | §4.1.2 | tool budget (0.7, 0.9] | action loop, budget or reasoning length above its gate for 3 steps |
| THR07 decomposition | NISTAML.067 | §4.1.2 | benign subtasks composing to (0.3, 0.6]; subtasks split across models | a rising composition, then harm > 0.6; harm > 0.6 for 3 steps |
| THR08 red-team gate | — | §5.1.3; governance gap 3 | — | `GATE_PASS` / `GATE_FAIL` (TD-SA-05) |
| THR09 vendor canary drift | — | §4.3; governance gap 6 | drift (0.10, 0.15]; a stale canary run | drift > 0.15 for 3 runs (TD-SA-06) |
| THR10 cross-domain exposure | — | §4.6, §4.7; governance gap 5 | exposure (0.70, 0.90]; a hop without delegation metadata | exposure > 0.90 or depth > 0.80 for 3 steps (TD-SA-06) |
| THR00 threat roll-up | — | worst wins | any suspects, none confirms | any confirms |

`tools/build_machines.py` holds every predicate; this table is a summary. Each
CES is one regular expression with no alternation, written into
`sequences[].metadata.regularExpression`.

## 4. Published lanes

The contract with ai-governance-regime is `threat-sources.json`
`publishedLanes`. The governance cells come from its `governance-sources.json`,
and the verifier fails if they drift.

| Signal | Gap | From | To |
|---|---|---|---|
| `gate_redteam_pass` | 3 | THR08 `GATE_PASS` (cell 17662) | GOV01 element 14 (cell 16974), as a frame fact the asset lifecycle writes (GOV-R19) |
| `mon_canary_drift_score` | 6 | the canary harness Source | THR09 element 0 and GOV16 element 1 (cell 17201) |
| `mon_xdomain_mu_agg` | 5 | the exposure aggregator Source | THR10 element 0 and GOV16 element 0 (cell 17200) |

## 5. Inputs are Sources

Every input is a Source through the ISRE (TD-SD-04). Until a milestone stages
its producer, each input cell is a one-cell `simulated` Source, declared with
the SURFACE_SPEC create body. The PE samples it at `t = globalStep`:

    phase = fmod(t * frequency, 1)
    binary:      1 while phase < 0.5, else 0
    constant:    dcOffset
    square:      dcOffset + amplitude * (phase < 0.5 ? 1 : -1)
    linear-ramp: dcOffset + amplitude * phase

This is the rule C++ (`reality.cpp`) and the TypeScript PE implement.
SURFACE_SPEC states the defaults but not the formula (TD-R04).

Each simulation declares one Source per input cell: the inputs it exercises
carry a waveform, and the rest are constants at their nominal value. It runs
32 steps after resetting both halves. It records its expected outputs by step,
the CESs it fires, and what it must and must never assert. Classes:
- `adversarial`: the attack;
- `near-miss`: benign evidence just short of confirmation, such as a 2-step
  burst against a 3-step debounce, or a value inside the suspected band;
- `nominal`: every input at its nominal value.

The voting engines, 3-of-3, are the authority on every expected output.

## 6. Not decided here

- Producers, and the milestone that stages each: GOV-SD-14 and TD-R02.
- Thresholds: they are design choices, not measurements (TD-R03).
- The 8-bit quantization of continuous cells on the engines: every simulated
  value is chosen away from a band edge, but the live run is the check (TD-R05).
