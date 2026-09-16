#!/usr/bin/env python3
"""Static workflow provability — M3 of the Semantic OWL roadmap.

Proves the six authored-workflow rules M3 names, over a corpus profile, *before*
anything runs. Where M2 gave the integration paths a vocabulary, this decides
whether what the corpus actually says is admissible.

    scripts/prove-workflows.py --profile standard-deployment
    scripts/prove-workflows.py --profile standard-deployment --emit out.ttl
    scripts/prove-workflows.py --fixtures        # every bad fixture must fail

## Why this is deterministic rather than OWL

M2 established the dividing line the hard way: an OWL class defined over an
absence is inert, because the open world entails nothing from a missing
assertion. Five of M3's six rules are absence checks — "every X *has* a known Y"
— so OWL can state them and never fail them.

So the reasoner keeps the half it is good at (classification, and the RED
contradiction `re:EscalationDetermination` catches), and this script closes the
world over a named profile and asks the questions OWL cannot. The roadmap says
as much for each rule: "Deterministic profile check", "Deterministic mapping
check", "deterministic invariant check".

## What a violation is

Every finding is emitted as a `re:SemanticGuardrailViolation` individual — the
M2 class whose extension has been empty since it was declared. A violation is an
individual rather than a log line so that it joins to the policy breached and
can be counted, merged and reasoned over alongside everything else.

Exit status is 1 if any violation is found, 0 otherwise. `--fixtures` inverts
that for the negative cases: a fixture that does *not* produce its expected
violation fails the run, because a guard with no violating case to catch is a
guard nobody has seen work.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = REPO_ROOT.parent
ONTOLOGY = REPO_ROOT / "semantics" / "ontology" / "re-core.ttl"
ABOX_ROOT = REPO_ROOT / "semantics" / "abox"
MACHINES_ROOT = REPO_ROOT / "machines"
FIXTURE_ROOT = REPO_ROOT / "semantics" / "shapes" / "fixtures" / "bad-workflows"

CI_CONFIG = WORKSPACE / "RealityEngine_CI" / "config"
OPENCLAW_ROOT = WORKSPACE / "localOpenClawStack"

IRI_BASE = "https://realityengine.example.org/machines"


# ── Findings ─────────────────────────────────────────────────────────────────

class Violation:
    """One guardrail breach, in the shape re:SemanticGuardrailViolation names."""

    def __init__(self, rule: str, kind: str, severity: str, record: str, detail: str):
        self.rule = rule          # which M3 rule
        self.kind = kind          # re:violationType
        self.severity = severity  # re:severity
        self.record = record      # re:recordId — what exhibits it
        self.detail = detail

    def __str__(self) -> str:
        return f"[{self.severity}] {self.rule}: {self.kind} — {self.record}\n      {self.detail}"


class Result:
    def __init__(self) -> None:
        self.violations: list[Violation] = []
        self.checked: dict[str, int] = defaultdict(int)
        self.ungated: list[str] = []

    def add(self, *args) -> None:
        self.violations.append(Violation(*args))

    def gap(self, note: str) -> None:
        """A rule that cannot be checked, named rather than silently skipped."""
        self.ungated.append(note)


# ── Corpus reading ───────────────────────────────────────────────────────────

def read_profile(name: str) -> list[Path]:
    """Machine JSON paths named by a corpus manifest."""
    stem = name.removesuffix(".txt").removesuffix("-corpus")
    for root in (Path(name).parent, CI_CONFIG, WORKSPACE / "config"):
        cand = root / f"{stem}-corpus.txt" if root != Path(name).parent else Path(name)
        if cand.is_file():
            lines = [l.strip() for l in cand.read_text().splitlines()]
            return [MACHINES_ROOT / l for l in lines if l and not l.startswith("#")]
    sys.exit(f"prove-workflows: no corpus manifest for '{name}' (looked in {CI_CONFIG})")


def abox_for(machine_json: Path) -> Path:
    return ABOX_ROOT / machine_json.parent.name / f"{machine_json.stem}.ttl"


def parse_abox(text: str) -> dict[str, dict[str, list[str]]]:
    """Subject -> predicate -> objects, for the shape generate-owl.py emits."""
    out: dict[str, dict[str, list[str]]] = {}
    subject: str | None = None
    for raw in text.splitlines():
        if raw.lstrip().startswith("#"):
            continue
        line = raw.rstrip()
        if not line.strip():
            continue
        if not raw.startswith((" ", "\t")):
            m = re.match(r"^([A-Za-z][\w-]*:[\w.:@+-]+)\s*$", line.strip())
            subject = m.group(1) if m else None
            if subject:
                out.setdefault(subject, {})
            continue
        if subject is None:
            continue
        body = line.strip().rstrip(" ;.").strip()
        # Every prefixed predicate, not only re: — machine names arrive as
        # rdfs:label, and a reader that silently drops them reports a machine
        # with no name rather than failing.
        m = re.match(r"^(?:a\s+(.*)|([A-Za-z][\w-]*:[\w-]+)\s+(.*))$", body)
        if not m:
            continue
        pred = "a" if m.group(1) is not None else m.group(2).removeprefix("re:")
        objs_raw = m.group(1) if m.group(1) is not None else m.group(3)
        objs = [o.strip() for o in objs_raw.split(",") if o.strip()]
        out[subject].setdefault(pred, []).extend(objs)
        if line.rstrip().endswith("."):
            subject = None
    return out


def lit(values: list[str] | None) -> str | None:
    if not values:
        return None
    return values[0].strip().strip('"')


def num(values: list[str] | None) -> int | None:
    v = lit(values)
    if v is None:
        return None
    try:
        return int(v.split("^^")[0].strip('"').strip())
    except ValueError:
        return None


# ── Rule 1 — every dispatchable action has a known machine IRI ───────────────

def rule_dispatchable_actions(graphs, actions, result: Result) -> None:
    """ROBOT + manifest join, closed over the profile.

    Two ways to fail: a determination prescribes an action the ontology's
    controlled vocabulary does not declare, or it prescribes one while hanging
    off no machine at all — a dispatchable action with no machine IRI behind it
    is an action nothing can be held to.
    """
    for name, g in graphs.items():
        owned = [1 for props in g.values() if "re:Machine" in props.get("a", [])]
        if not owned:
            result.add("R1", "machine-iri-missing", "error", name,
                       "ABox declares no re:Machine individual")
            continue
        for subj, props in g.items():
            for act in props.get("prescribesAction", []):
                result.checked["R1 actions"] += 1
                if act.startswith("re:") and act not in actions:
                    result.add("R1", "unknown-action-code", "error", f"{name} {subj}",
                               f"prescribes {act}, which re-core.ttl does not declare")


# ── Rule 2 — MCP endpoints allowed for the workflow class ────────────────────

def rule_mcp_endpoints(integrations, result: Result) -> None:
    """Deterministic profile check plus OWL class membership.

    Only half of this rule is checkable today, and the missing half is named
    rather than quietly dropped. `integrations.json` declares 8 providers with
    base URLs, so "is this endpoint one the deployment declares" is answerable.
    **No integration entry carries an `allowedOperations` field**, so "is this
    operation allowed *for this workflow class*" has no data behind it — the
    workflow-class half of the rule cannot be proved and must not be reported as
    proved.
    """
    declared = {i.get("baseUrl") or i.get("endpoint") for i in integrations}
    declared.discard(None)
    result.checked["R2 declared endpoints"] = len(declared)

    if not any("allowedOperations" in i for i in integrations):
        result.gap(
            "R2 workflow-class half: no integrations.json entry declares "
            "`allowedOperations`, so operation-level permission has no source of "
            "truth. Endpoint membership is checked; per-workflow-class operation "
            "permission is NOT, and no fixture can currently exercise it.")


# ── Rule 3 — one machine binding per generated agent ─────────────────────────

def rule_agent_bindings(agents, profile_machines, result: Result) -> None:
    """Every OpenClaw generated agent has exactly one machine binding.

    Exactly one, not at least one: two agents claiming the same machine makes
    the dispatch target ambiguous, and an agent claiming a machine outside the
    active profile dispatches into a corpus the engines did not load.
    """
    by_machine: dict[str, list[str]] = defaultdict(list)
    for a in agents:
        key = norm(a.get("machineName") or a.get("machineId") or "")
        by_machine[key].append(a.get("agentId", "?"))

    for key, ids in sorted(by_machine.items()):
        if key in profile_machines and len(ids) > 1:
            result.add("R3", "ambiguous-agent-binding", "error", key,
                       f"{len(ids)} agents claim this machine: {', '.join(sorted(ids))}")
    result.checked["R3 agents"] = len(agents)
    result.checked["R3 profile machines with an agent"] = sum(
        1 for k in profile_machines if k in by_machine)


def norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


# ── Rule 4 — agent input axes map to authored regions ────────────────────────

def rule_agent_axes(agents, name_to_graph, result: Result) -> None:
    """Every agent input axis maps to an authored machine input axis or bus lane.

    The agent index states an `inputRegion`; the machine's own ABox states
    `re:inputOffset`/`re:inputLength` on its perceptual mapping. An agent reading
    a region the machine does not declare is reading somebody else's lane.
    """
    for a in agents:
        key = norm(a.get("machineName") or "")
        g = name_to_graph.get(key)
        if g is None:
            continue                       # outside the profile; R3's business
        region = a.get("inputRegion") or {}
        a_off, a_len = region.get("offset"), region.get("length")
        if a_off is None or a_len is None:
            result.add("R4", "agent-axis-unmapped", "error", a.get("agentId", "?"),
                       "agent declares no inputRegion")
            continue
        mapping = next((props for props in g.values()
                        if "re:PerceptualMapping" in props.get("a", [])), None)
        if mapping is None:
            result.add("R4", "agent-axis-unmapped", "error", a.get("agentId", "?"),
                       "machine ABox declares no re:PerceptualMapping")
            continue
        m_off, m_len = num(mapping.get("inputOffset")), num(mapping.get("inputLength"))
        result.checked["R4 axes"] += 1
        if m_off is None or m_len is None:
            continue
        if a_off != m_off or a_len != m_len:
            result.add("R4", "agent-axis-unmapped", "error", a.get("agentId", "?"),
                       f"agent reads [{a_off}:{a_off + a_len}] but the machine "
                       f"authors [{m_off}:{m_off + m_len}]")


# ── Rule 5 — completions write only through approved mappings ────────────────

def rule_completion_mappings(graphs, approved_ids, result: Result) -> None:
    """Deterministic mapping check.

    The closed-world half of the invariant M2 could not express in OWL. Every
    re:SourceMappingWrite must name a re:CompletionMapping, and every mapping
    named must be one `integrations.json` approves.
    """
    for name, g in graphs.items():
        for subj, props in g.items():
            if "re:SourceMappingWrite" not in props.get("a", []):
                continue
            result.checked["R5 writes"] += 1
            targets = props.get("writesThroughMapping") or []
            if not targets:
                result.add("R5", "unmapped-completion-write", "error", f"{name} {subj}",
                           "names no re:CompletionMapping — wrote by a route nothing approved")
                continue
            for t in targets:
                mapping = g.get(t, {})
                sensor = lit(mapping.get("sensorId"))
                if sensor is None:
                    result.add("R5", "completion-mapping-unnamed", "error", f"{name} {t}",
                               "completion mapping declares no re:sensorId")
                    continue
                if approved_ids and not approved_sensor(sensor, approved_ids):
                    result.add("R5", "unapproved-completion-mapping", "error",
                               f"{name} {t}",
                               f"sensor '{sensor}' matches no sourceMappings entry "
                               f"in integrations.json")


def approved_sensor(sensor: str, approved: list[str]) -> bool:
    """A sensor id matches an approved template, `{placeholder}` wildcards aside."""
    for template in approved:
        pattern = re.escape(template)
        pattern = re.sub(r"\\\{[^}]*\\\}", r"[^.]+", pattern)
        if re.fullmatch(pattern, sensor):
            return True
    return False


def determinations_of(g, sequences: set[str]) -> set[str]:
    """Every determination emitted by a step of the given sequences."""
    out: set[str] = set()
    for seq in sequences:
        for step in g.get(seq, {}).get("hasStep", []):
            out.update(g.get(step, {}).get("emitsDetermination", []))
    return out


def determinations_reading_red(g) -> set[str]:
    """Determinations this graph states are RED, and only those.

    An earlier version also walked `re:TriggerRule -> re:appliesToSequence` and
    treated every determination of that sequence as RED. That was wrong and the
    corpus says so plainly: `AICapacityThrottler`'s capacity-escalation sequence
    carries **seven** rules over **seven** determinations, two RED and five
    AMBER. Attributing the sequence's RED rules to all seven reported five
    nominal determinations — `out-available`, `out-busy` — as unactioned RED.

    The join does not exist in the ABox to be made. `re:matchesOutputPosition`
    indexes the machine's *output value vector*, not the sequence's list of
    determinations, so a rule cannot be resolved to the determination it governs
    from this graph alone. That is why `escalation_rag_test.py` works on the
    machine JSON rather than here.

    So this reads only what is asserted, and `trigger_rule_only_red()` counts
    what is therefore out of reach, rather than guessing it into scope.
    """
    return {s for s, props in g.items()
            if "re:Determination" in props.get("a", [])
            and "re:RED" in props.get("hasRagStatus", [])}


def trigger_rule_only_red(g) -> bool:
    """True when a graph states RED on a trigger rule but on no determination.

    Not a violation — the corpus is entitled to state a status on the rule. It
    is a *reach* limit: R6 cannot evaluate those determinations, and a rule that
    silently evaluates nothing is the failure this project keeps rediscovering.
    """
    rule_red = any("re:TriggerRule" in props.get("a", [])
                   and "re:RED" in props.get("hasRagStatus", [])
                   for props in g.values())
    return rule_red and not determinations_reading_red(g)


# ── Rule 6 — RED and life-safety cannot be downgraded ────────────────────────

# "Non-critical automation", in the roadmap's words: a consequence that reaches
# neither a person nor an escalation path. Read from the ontology's action
# individuals rather than listed here, because the controlled vocabulary is
# re-core.ttl's and a second list beside it would drift.
REACHES_SOMEONE = ("re:EscalationAction", "re:NotificationAction")


def action_classes(ontology: str) -> dict[str, str]:
    """re:ActionIndividual -> its consequence class."""
    return {m.group(1): m.group(2) for m in re.finditer(
        r"^(re:\w+) a owl:NamedIndividual , (re:\w+Action)", ontology, re.M)}


def rule_no_downgrade(graphs, classes, result: Result) -> None:
    """RED/life-safety actions cannot be downgraded to non-critical automation.

    OWL already forbids the other direction — an escalating action prescribed by
    a non-RED determination makes HermiT reject the graph
    (`re:EscalationDetermination`). This is the converse, which is an absence and
    therefore outside what OWL will conclude.

    The bar is the roadmap's wording, not a stricter one: "downgraded to
    non-critical **automation**". A `re:NotificationAction` is not a downgrade —
    routing a referral reaches a person. Requiring `re:EscalationAction` here
    reported all five RED determinations in the standard-deployment profile as
    violations, and all five were prescribing `re:RouteReferral` or
    `re:RouteReview`, which are notifications. The check is for a determination
    that reaches *nobody*: logging or automation only, or no action at all.
    """
    out_of_reach = 0
    for name, g in graphs.items():
        if trigger_rule_only_red(g):
            out_of_reach += 1
        red_determinations = determinations_reading_red(g)
        ls_determinations = determinations_of(g, {
            s for s, props in g.items()
            if "re:LifeSafetySequence" in props.get("a", [])})

        for subj, props in g.items():
            if "re:Determination" not in props.get("a", []):
                continue
            is_red = subj in red_determinations
            if not (is_red or subj in ls_determinations):
                continue
            result.checked["R6 critical determinations"] += 1
            prescribed = props.get("prescribesAction") or []
            if not prescribed:
                # A RED determination prescribing nothing is the downgrade in its
                # purest form: nothing happens, and nothing says nothing happened.
                result.add("R6", "critical-determination-no-action", "error",
                           f"{name} {subj}",
                           "RED or life-safety, and prescribes no action at all")
                continue
            reaching = [a for a in prescribed
                        if classes.get(a) in REACHES_SOMEONE]
            if not reaching:
                why = "RED" if is_red else "terminates a life-safety sequence"
                shown = ", ".join(f"{a} ({classes.get(a, 'unclassified')})" for a in prescribed)
                result.add("R6", "critical-action-downgraded", "error", f"{name} {subj}",
                           f"{why}, but prescribes only {shown} — nothing that "
                           f"reaches a person or an escalation path")

    if out_of_reach:
        result.gap(
            f"R6 reach: {out_of_reach} machine(s) state RED only on a "
            f"re:TriggerRule, never on a determination. The ABox carries no "
            f"rule->determination join (re:matchesOutputPosition indexes the "
            f"output vector, not the determination list), so R6 cannot evaluate "
            f"those. escalation_rag_test.py covers the corpus-JSON side; "
            f"joinability is M4's problem.")


# ── Emission ─────────────────────────────────────────────────────────────────

def emit_ttl(result: Result, path: Path, profile: str) -> None:
    """Violations as re:SemanticGuardrailViolation individuals."""
    lines = [
        f"# Generated by scripts/prove-workflows.py --profile {profile}.",
        "# Violations of the M3 static workflow rules, as individuals rather than",
        "# log lines, so they join to the graph they were found in.",
        "",
        "@prefix re:   <https://realityengine.example.org/ontology/re-core#> .",
        "@prefix owl:  <http://www.w3.org/2002/07/owl#> .",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix v:    <https://realityengine.example.org/guardrail-violations#> .",
        "",
    ]
    for i, v in enumerate(result.violations, 1):
        lines += [
            f"v:violation-{i:04d}",
            "    a owl:NamedIndividual , re:SemanticGuardrailViolation ;",
            f'    rdfs:label "{v.rule} {v.kind}" ;',
            f'    re:violationType "{v.kind}" ;',
            f'    re:severity "{v.severity}" ;',
            f'    re:recordId "{v.record}" .',
            "",
        ]
    path.write_text("\n".join(lines))


# ── Fixtures ─────────────────────────────────────────────────────────────────

def run_fixtures(result_cls, actions, classes, approved_ids) -> int:
    """Every bad fixture must produce its expected violation kind.

    This is M3's second acceptance criterion, and the reason it exists is the
    lesson from M2: a check that finds nothing and a check that cannot find
    anything are indistinguishable from outside.
    """
    if not FIXTURE_ROOT.is_dir():
        print(f"prove-workflows: no fixtures at {FIXTURE_ROOT}", file=sys.stderr)
        return 2
    manifest = json.loads((FIXTURE_ROOT / "cases.json").read_text())
    failures = 0
    for case in manifest["cases"]:
        ttl = (FIXTURE_ROOT / case["graph"]).read_text()
        graphs = {case["graph"]: parse_abox(ttl)}
        r = result_cls()
        rule_dispatchable_actions(graphs, actions, r)
        rule_completion_mappings(graphs, approved_ids, r)
        rule_no_downgrade(graphs, classes, r)
        kinds = {v.kind for v in r.violations}
        want = case["expect"]
        if want in kinds:
            print(f"  ok     {case['graph']:<44} -> {want}")
        else:
            print(f"  FAILED {case['graph']:<44} expected {want}, got {sorted(kinds) or 'nothing'}")
            failures += 1
    print()
    if failures:
        print(f"prove-workflows: {failures} fixture(s) did not produce the violation "
              f"they exist to produce — the guard is not proven to work")
    else:
        print(f"prove-workflows: all {len(manifest['cases'])} bad fixtures rejected as expected")
    return 1 if failures else 0


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--profile", default="standard-deployment",
                    help="corpus manifest name or path (default: standard-deployment)")
    ap.add_argument("--emit", type=Path, help="write violations as TTL individuals")
    ap.add_argument("--fixtures", action="store_true",
                    help="run the bad-workflow fixtures; each must fail")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    ontology = ONTOLOGY.read_text()
    actions = set(re.findall(r"^(re:\w+)\s+a owl:NamedIndividual", ontology, re.M))
    actions |= set(re.findall(r"^(re:\w+)\n?\s+a owl:NamedIndividual", ontology, re.M))
    classes = action_classes(ontology)

    integrations_path = CI_CONFIG / "integrations.json"
    integrations, approved_ids = [], []
    if integrations_path.is_file():
        cfg = json.loads(integrations_path.read_text())
        integrations = cfg.get("integrations", [])
        approved_ids = [m.get("sensorIdTemplate") for m in cfg.get("sourceMappings", [])
                        if m.get("sensorIdTemplate")]

    if args.fixtures:
        return run_fixtures(Result, actions, classes, approved_ids)

    machine_paths = read_profile(args.profile)
    graphs, name_to_graph, profile_machines = {}, {}, set()
    for mp in machine_paths:
        ab = abox_for(mp)
        if not ab.is_file():
            print(f"prove-workflows: no ABox for {mp.relative_to(MACHINES_ROOT)} "
                  f"(run generate-owl.py)", file=sys.stderr)
            return 2
        g = parse_abox(ab.read_text())
        graphs[mp.stem] = g
        label = next((lit(props.get("rdfs:label"))
                      for props in g.values()
                      if "re:Machine" in props.get("a", [])), None)
        key = norm(label or mp.stem)
        name_to_graph[key] = g
        profile_machines.add(key)

    agents = []
    index = OPENCLAW_ROOT / "machine-behaviors" / "agents" / "INDEX.json"
    if index.is_file():
        agents = json.loads(index.read_text()).get("agents", [])

    result = Result()
    rule_dispatchable_actions(graphs, actions, result)
    rule_mcp_endpoints(integrations, result)
    rule_agent_bindings(agents, profile_machines, result)
    rule_agent_axes(agents, name_to_graph, result)
    rule_completion_mappings(graphs, approved_ids, result)
    rule_no_downgrade(graphs, classes, result)

    if args.emit:
        emit_ttl(result, args.emit, args.profile)

    if not args.quiet:
        print(f"prove-workflows: profile '{args.profile}' — {len(graphs)} machines")
        for k in sorted(result.checked):
            print(f"  checked  {k}: {result.checked[k]}")
        for note in result.ungated:
            print(f"  UNGATED  {note}")
        print()
        for v in result.violations:
            print(f"  {v}")
        print()

    if result.violations:
        print(f"prove-workflows: FAIL — {len(result.violations)} violation(s)")
        return 1
    print(f"prove-workflows: OK — profile '{args.profile}' proves under all six M3 rules"
          + (f" ({len(result.ungated)} ungated, named above)" if result.ungated else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
