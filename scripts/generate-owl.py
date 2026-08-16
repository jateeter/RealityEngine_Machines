#!/usr/bin/env python3
"""Generate OWL (Turtle) ABox files from canonical machine JSON.

Each machine JSON file is projected into a deterministic Turtle document under
semantics/abox/<domain>/<MachineFile>.ttl using the vocabulary declared in
semantics/ontology/re-core.ttl. The generated graphs are the semantic
representation of machine actions and critical event sequences consumed by
verification and auditing tooling in the RE and PE components.

The generator is intentionally stdlib-only (like the rest of scripts/) and
byte-deterministic: regenerating an unchanged machine must yield an identical
file, which is what --check enforces in CI.

Usage:
  python3 scripts/generate-owl.py --machine machines/domains/health-personal/FallDetection.json
  python3 scripts/generate-owl.py --domain health-personal --write
  python3 scripts/generate-owl.py --all --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re as regex
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
MACHINES_ROOT = REPO_ROOT / "machines"
ONTOLOGY_PATH = REPO_ROOT / "semantics" / "ontology" / "re-core.ttl"
ABOX_ROOT = REPO_ROOT / "semantics" / "abox"
MANIFEST_PATH = REPO_ROOT / "semantics" / "abox-manifest.json"

MACHINE_BASE = "https://realityengine.example.org/machines"

PREFIXES = """@prefix re:      <https://realityengine.example.org/ontology/re-core#> .
@prefix owl:     <http://www.w3.org/2002/07/owl#> .
@prefix rdf:     <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs:    <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:     <http://www.w3.org/2001/XMLSchema#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
"""

RAG_INDIVIDUALS = {"GREEN": "re:GREEN", "AMBER": "re:AMBER", "RED": "re:RED"}

ACTION_PATTERN = regex.compile(
    r"re:(?P<name>\w+) a owl:NamedIndividual , re:(?:\w+) ;\s*\n\s*re:actionCode \"(?P<code>[^\"]+)\"",
    regex.MULTILINE,
)


def load_action_vocabulary() -> dict[str, str]:
    """Map action code strings to canonical individuals declared in re-core.ttl."""
    text = ONTOLOGY_PATH.read_text()
    vocabulary = {}
    for match in ACTION_PATTERN.finditer(text):
        vocabulary[match.group("code")] = f"re:{match.group('name')}"
    return vocabulary


def sanitize(local: str) -> str:
    """Restrict IRI local names to a safe Turtle PN_LOCAL subset."""
    cleaned = regex.sub(r"[^A-Za-z0-9_-]", "_", str(local))
    return cleaned or "unnamed"


def with_rule_ordinals(rules):
    """Pair each trigger rule with its 1-based ordinal among the rules sharing
    its sequenceId, in corpus order.

    Rule IRIs were minted from sequenceId alone, which is not injective: a
    sequence carrying several rules — one per output pattern it can match —
    collapsed into a single individual that then asserted GREEN, AMBER and RED
    on the functional re:hasRagStatus, making the merged graph inconsistent.
    HermiT rejects it; ELK does not implement functional properties and passed
    it silently, so the defect survived at 43/1,328 ABox coverage because no
    health-personal machine has a multi-rule sequence. Nine machines do
    (ai-services 7, agriculture 1, data-center 1).

    The ordinal, not the output vector, is the disambiguator: nine
    (sequenceId, outputMatches) pairs repeat within a machine, so the vector is
    not injective either. Suffixing is unconditional rather than applied only
    where a sequence has more than one rule — conditional suffixing would make
    an existing rule's IRI change when a sibling is added, which is worse for
    identity stability than the one-time rename this costs.
    """
    seen = {}
    out = []
    for rule in rules:
        seq = rule.get("sequenceId")
        seen[seq] = seen.get(seq, 0) + 1
        out.append((rule, seen[seq]))
    return out


def rule_term(rule: dict, ordinal: int) -> str:
    return f"m:rule-{sanitize(rule['sequenceId'])}-{ordinal}"


def escape(literal: str) -> str:
    return (
        str(literal)
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


def number(value: Any) -> str:
    """Render a JSON number as a Turtle literal (integer or decimal)."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value) if value != int(value) else f"{value:.1f}"
    return f'"{escape(value)}"'


def domain_for(path: Path) -> str:
    rel = path.resolve().relative_to(MACHINES_ROOT.resolve())
    parts = rel.parts
    if len(parts) >= 3 and parts[0] == "domains":
        return parts[1]
    return "core"


class MachineProjector:
    """Project one machine JSON document into Turtle lines."""

    def __init__(self, path: Path, doc: dict[str, Any], actions: dict[str, str],
                 strict_actions: bool) -> None:
        self.path = path
        self.machine = doc["machine"]
        self.actions = actions
        self.strict_actions = strict_actions
        self.domain = domain_for(path)
        self.base = f"{MACHINE_BASE}/{self.domain}/{sanitize(path.stem)}#"
        self.lines: list[str] = []
        self.warnings: list[str] = []
        self.local_actions: dict[str, str] = {}
        self.sequence_ids: set[str] = set()

    def project(self) -> str:
        rel = self.path.resolve().relative_to(REPO_ROOT.resolve())
        self.lines.append(
            f"# Generated by scripts/generate-owl.py from {rel}."
        )
        self.lines.append(
            "# Do not edit by hand; regenerate with: "
            f"python3 scripts/generate-owl.py --machine {rel} --write"
        )
        self.lines.append("")
        self.lines.append(PREFIXES.rstrip())
        self.lines.append(f"@prefix m:       <{self.base}> .")
        self.lines.append("")
        self.sequence_ids = {
            str(seq.get("id", "")) for seq in self.machine.get("sequences", [])
        }
        self.emit_machine()
        self.emit_perceptual_mapping()
        self.emit_governance()
        self.emit_sequences()
        self.emit_trigger_rules()
        self.emit_interconnections()
        self.emit_openclaw_projection()
        self.emit_agent_binding()
        self.emit_local_actions()
        return "\n".join(self.lines).rstrip() + "\n"

    # -- helpers ---------------------------------------------------------

    def block(self, subject: str, statements: list[str]) -> None:
        if not statements:
            return
        self.lines.append(f"{subject}")
        for statement in statements[:-1]:
            self.lines.append(f"    {statement} ;")
        self.lines.append(f"    {statements[-1]} .")
        self.lines.append("")

    def action_term(self, code: str) -> str:
        if code in self.actions:
            return self.actions[code]
        if self.strict_actions:
            raise ValueError(
                f"{self.path}: action code '{code}' is not declared in "
                f"{ONTOLOGY_PATH.relative_to(REPO_ROOT)}"
            )
        local = f"m:action-{sanitize(code)}"
        if code not in self.local_actions:
            self.local_actions[code] = local
            self.warnings.append(
                f"{self.path.name}: action code '{code}' not in core vocabulary; "
                f"minted {local}"
            )
        return local

    # -- emitters --------------------------------------------------------

    def emit_machine(self) -> None:
        machine = self.machine
        metadata = machine.get("metadata", {})
        statements = [
            "a owl:NamedIndividual , re:Machine",
            f'rdfs:label "{escape(machine["name"])}"',
            f'dcterms:description "{escape(machine["description"])}"',
            f're:domainName "{escape(self.domain)}"',
        ]
        if metadata.get("machineClass"):
            statements.append(f're:machineClass "{escape(metadata["machineClass"])}"')
        if metadata.get("severity"):
            statements.append(f're:severity "{escape(metadata["severity"])}"')
        if machine.get("arbiterRule"):
            statements.append(f're:arbiterRule "{escape(machine["arbiterRule"])}"')
        if machine.get("matchAlgorithm"):
            statements.append(f're:matchAlgorithm "{escape(machine["matchAlgorithm"])}"')
        rel = self.path.resolve().relative_to(REPO_ROOT.resolve())
        statements.append(f're:sourceFile "{escape(str(rel))}"')
        if machine.get("perceptualMapping"):
            statements.append("re:hasPerceptualMapping m:perceptual-mapping")
        if metadata.get("governance"):
            statements.append("re:hasGovernance m:governance")
        sequences = machine.get("sequences", [])
        if sequences:
            refs = " , ".join(
                f"m:seq-{sanitize(seq['id'])}" for seq in sequences if seq.get("id")
            )
            if refs:
                statements.append(f"re:hasSequence {refs}")
        rules = metadata.get("triggerConfig", {}).get("rules", [])
        rule_refs = " , ".join(
            rule_term(rule, ordinal)
            for rule, ordinal in with_rule_ordinals(rules)
            if rule.get("sequenceId")
        )
        if rule_refs:
            statements.append(f"re:hasTriggerRule {rule_refs}")
        interconnections = metadata.get("interconnections", [])
        ix_refs = " , ".join(
            f"m:ix-{sanitize(ix.get('id', str(index)))}"
            for index, ix in enumerate(interconnections)
        )
        if ix_refs:
            statements.append(f"re:hasInterconnection {ix_refs}")
        if metadata.get("openClawProjection"):
            statements.append("re:hasOpenClawProjection m:openclaw-projection")
        if metadata.get("agentBinding") or metadata.get("openClawProjection"):
            statements.append("re:hasAgentBinding m:agent-binding")
        self.block("m:machine", statements)

    def emit_perceptual_mapping(self) -> None:
        mapping = self.machine.get("perceptualMapping")
        if not mapping:
            return
        statements = ["a owl:NamedIndividual , re:PerceptualMapping"]
        input_region = mapping.get("input", {})
        output_region = mapping.get("output", {})
        if "offset" in input_region:
            statements.append(f"re:inputOffset {number(input_region['offset'])}")
        if "length" in input_region:
            statements.append(f"re:inputLength {number(input_region['length'])}")
        if "offset" in output_region:
            statements.append(f"re:outputOffset {number(output_region['offset'])}")
        if "length" in output_region:
            statements.append(f"re:outputLength {number(output_region['length'])}")
        if "bitsPerElement" in mapping:
            statements.append(f"re:bitsPerElement {number(mapping['bitsPerElement'])}")
        self.block("m:perceptual-mapping", statements)

    def emit_governance(self) -> None:
        governance = self.machine.get("metadata", {}).get("governance")
        if not governance:
            return
        statements = ["a owl:NamedIndividual , re:GovernancePolicy"]
        if governance.get("ownerTeam"):
            statements.append(f're:ownerTeam "{escape(governance["ownerTeam"])}"')
        if governance.get("runbook"):
            statements.append(
                f're:runbook "{escape(governance["runbook"])}"^^xsd:anyURI'
            )
        if governance.get("escalationPolicy"):
            statements.append(
                f're:escalationPolicy "{escape(governance["escalationPolicy"])}"'
            )
        self.block("m:governance", statements)

    def emit_sequences(self) -> None:
        for sequence in self.machine.get("sequences", []):
            seq_id = sequence.get("id")
            if not seq_id:
                continue
            seq_term = f"m:seq-{sanitize(seq_id)}"
            metadata = sequence.get("metadata", {})
            vectors = sequence.get("vectors", [])
            life_safety = metadata.get("severity") == "life-safety" or any(
                vector.get("metadata", {}).get("lifeSafety") for vector in vectors
            )
            types = "a owl:NamedIndividual , re:CriticalEventSequence"
            if life_safety:
                types += " , re:LifeSafetySequence"
            statements = [types, f're:sequenceId "{escape(seq_id)}"']
            if sequence.get("name"):
                statements.append(f'rdfs:label "{escape(sequence["name"])}"')
            if metadata.get("description"):
                statements.append(f'rdfs:comment "{escape(metadata["description"])}"')
            step_refs = " , ".join(
                f"m:step-{sanitize(vector['id'])}" for vector in vectors if vector.get("id")
            )
            if step_refs:
                statements.append(f"re:hasStep {step_refs}")
            initial_refs = " , ".join(
                f"m:step-{sanitize(vector['id'])}"
                for vector in vectors
                if vector.get("id") and vector.get("isInitial")
            )
            if initial_refs:
                statements.append(f"re:hasInitialStep {initial_refs}")
            self.block(seq_term, statements)
            for vector in vectors:
                self.emit_step(vector)

    def emit_step(self, vector: dict[str, Any]) -> None:
        vector_id = vector.get("id")
        if not vector_id:
            return
        step_term = f"m:step-{sanitize(vector_id)}"
        metadata = vector.get("metadata", {})
        statements = ["a owl:NamedIndividual , re:SequenceStep"]
        if metadata.get("name"):
            statements.append(f're:stateName "{escape(metadata["name"])}"')
        if metadata.get("stepIndex") is not None:
            statements.append(f"re:stepIndex {number(metadata['stepIndex'])}")
        statements.append(
            f"re:isInitialStep {'true' if vector.get('isInitial') else 'false'}"
        )
        if metadata.get("lifeSafety"):
            statements.append("re:lifeSafety true")
        elements = vector.get("elements", [])
        element_refs = " , ".join(
            f"m:step-{sanitize(vector_id)}-e{index}" for index in range(len(elements))
        )
        if element_refs:
            statements.append(f"re:hasElementValue {element_refs}")
        next_refs = " , ".join(
            f"m:step-{sanitize(next_id)}" for next_id in vector.get("nextVectorIds", [])
        )
        if next_refs:
            statements.append(f"re:hasNextStep {next_refs}")
        output_refs = " , ".join(
            f"m:out-{sanitize(output['id'])}"
            for output in vector.get("outputVectors", [])
            if output.get("id")
        )
        if output_refs:
            statements.append(f"re:emitsDetermination {output_refs}")
        self.block(step_term, statements)
        for index, element in enumerate(elements):
            element_statements = [
                "a owl:NamedIndividual , re:ElementValue",
                f"re:elementIndex {index}",
                f"re:elementLevel {number(element.get('value', 0))}",
            ]
            if element.get("threshold") is not None:
                element_statements.append(
                    f"re:elementThreshold {number(element['threshold'])}"
                )
            self.block(f"m:step-{sanitize(vector_id)}-e{index}", element_statements)
        for output in vector.get("outputVectors", []):
            self.emit_determination(output)

    def emit_determination(self, output: dict[str, Any]) -> None:
        output_id = output.get("id")
        if not output_id:
            return
        metadata = output.get("metadata", {})
        statements = ["a owl:NamedIndividual , re:Determination"]
        vector = output.get("vector", [])
        if len(vector) >= 1:
            statements.append(f"re:outputTier {number(vector[0])}")
        if len(vector) >= 2:
            statements.append(f"re:outputConfidence {number(vector[1])}")
        if metadata.get("tier"):
            statements.append(f're:tierLabel "{escape(metadata["tier"])}"')
        if metadata.get("confidence"):
            statements.append(f're:confidenceLabel "{escape(metadata["confidence"])}"')
        rag = metadata.get("ragStatusCode")
        if rag in RAG_INDIVIDUALS:
            statements.append(f"re:hasRagStatus {RAG_INDIVIDUALS[rag]}")
        if metadata.get("action"):
            statements.append(
                f"re:prescribesAction {self.action_term(metadata['action'])}"
            )
        if metadata.get("actionNarrative"):
            statements.append(
                f're:actionNarrative "{escape(metadata["actionNarrative"])}"'
            )
        if metadata.get("lifeSafety"):
            statements.append("re:lifeSafety true")
        if metadata.get("rationale"):
            statements.append(f'rdfs:comment "{escape(metadata["rationale"])}"')
        self.block(f"m:out-{sanitize(output_id)}", statements)

    def emit_trigger_rules(self) -> None:
        trigger_config = self.machine.get("metadata", {}).get("triggerConfig", {})
        for rule, ordinal in with_rule_ordinals(trigger_config.get("rules", [])):
            sequence_id = rule.get("sequenceId")
            if not sequence_id:
                continue
            term = rule_term(rule, ordinal)
            statements = ["a owl:NamedIndividual , re:TriggerRule"]
            if sequence_id in self.sequence_ids:
                statements.append(f"re:appliesToSequence m:seq-{sanitize(sequence_id)}")
            else:
                self.warnings.append(
                    f"{self.path.name}: trigger rule '{sequence_id}' has no matching "
                    "sequence"
                )
            # outputMatches is a value vector over the machine's output region,
            # not a (tier, confidence) pair — see re-core.ttl 0.3.0. Emit it
            # whole, and index the asserted cells for querying.
            matches = rule.get("outputMatches", [])
            if matches:
                joined = ",".join(str(number(value)) for value in matches)
                statements.append(f're:outputMatchVector "{joined}"')
                for index, value in enumerate(matches):
                    if value:
                        statements.append(f"re:matchesOutputPosition {index}")
            rag = rule.get("ragStatusCode")
            if rag in RAG_INDIVIDUALS:
                statements.append(f"re:hasRagStatus {RAG_INDIVIDUALS[rag]}")
            if rule.get("processStatus"):
                statements.append(f're:processStatus "{escape(rule["processStatus"])}"')
            if rule.get("description"):
                statements.append(f'rdfs:comment "{escape(rule["description"])}"')
            governance = rule.get("governance", {})
            if governance:
                statements.append(f"re:hasGovernance {term}-governance")
            self.block(term, statements)
            if governance:
                governance_statements = [
                    "a owl:NamedIndividual , re:GovernancePolicy"
                ]
                if governance.get("slaSeconds") is not None:
                    governance_statements.append(
                        f"re:slaSeconds {number(governance['slaSeconds'])}"
                    )
                if governance.get("runbook"):
                    governance_statements.append(
                        f're:runbook "{escape(governance["runbook"])}"^^xsd:anyURI'
                    )
                if governance.get("ownerTeam"):
                    governance_statements.append(
                        f're:ownerTeam "{escape(governance["ownerTeam"])}"'
                    )
                self.block(f"{term}-governance", governance_statements)

    def emit_interconnections(self) -> None:
        interconnections = self.machine.get("metadata", {}).get("interconnections", [])
        for index, interconnection in enumerate(interconnections):
            term = f"m:ix-{sanitize(interconnection.get('id', str(index)))}"
            statements = [
                "a owl:NamedIndividual , re:Interconnection",
                "re:sourceMachine m:machine",
            ]
            if interconnection.get("id"):
                statements.append(
                    f're:interconnectionId "{escape(interconnection["id"])}"'
                )
            if interconnection.get("type"):
                statements.append(
                    f're:interconnectionType "{escape(interconnection["type"])}"'
                )
            if interconnection.get("busId"):
                statements.append(f're:busId "{escape(interconnection["busId"])}"')
            if interconnection.get("targetMachine"):
                statements.append(
                    f're:targetMachineName "{escape(interconnection["targetMachine"])}"'
                )
            for key, prop in (("sourceOutputRegion", "SourceOutput"),
                              ("targetInputRegion", "TargetInput"),
                              ("publishedOutputRegion", "PublishedOutput")):
                region = interconnection.get(key) or {}
                if "offset" in region:
                    statements.append(
                        f"re:{prop[0].lower()}{prop[1:]}Offset {number(region['offset'])}"
                    )
                if "length" in region:
                    statements.append(
                        f"re:{prop[0].lower()}{prop[1:]}Length {number(region['length'])}"
                    )
            if interconnection.get("dispatchMode"):
                statements.append(
                    f're:dispatchMode "{escape(interconnection["dispatchMode"])}"'
                )
            if interconnection.get("privacyBoundary"):
                statements.append(
                    f're:privacyBoundary "{escape(interconnection["privacyBoundary"])}"'
                )
            if interconnection.get("purpose"):
                statements.append(f'rdfs:comment "{escape(interconnection["purpose"])}"')
            self.block(term, statements)

    def emit_openclaw_projection(self) -> None:
        projection = self.machine.get("metadata", {}).get("openClawProjection")
        if not projection:
            return
        statements = ["a owl:NamedIndividual , re:OpenClawProjection",
                      "re:sourceMachine m:machine"]
        if projection.get("projectionId"):
            statements.append(
                f're:projectionId "{escape(projection["projectionId"])}"'
            )
        if projection.get("dispatchMode"):
            statements.append(
                f're:dispatchMode "{escape(projection["dispatchMode"])}"'
            )
        region = projection.get("writeBackRegion") or {}
        if "offset" in region:
            statements.append(f"re:targetInputOffset {number(region['offset'])}")
        if "length" in region:
            statements.append(f"re:targetInputLength {number(region['length'])}")
        if projection.get("peContract"):
            statements.append(f'rdfs:comment "{escape(projection["peContract"])}"')
        self.block("m:openclaw-projection", statements)

    def emit_agent_binding(self) -> None:
        """Emit the agent vocabulary (re-core.ttl 0.2.0).

        The ontology previously modelled the write-back *slot*
        (re:OpenClawProjection) but not the agent that fills it, so the semantic
        layer could answer nothing about the agent corpus bound to these
        machines.

        Two sources in the corpus describe that binding and they do not agree on
        cardinality: metadata.agentBinding (curated, localAI provider) covers
        1058 machines, metadata.openClawProjection (OpenClaw input-analyst)
        covers 1184. Both are emitted when present rather than one being
        preferred, because which is authoritative is an open question
        (localOpenClawStack#16) and encoding a guess here would bake it in.

        re:axisName is functional, so the semantic axes below are the mechanism
        by which a disagreement about what a write-back position *means* becomes
        a reasoner-detectable inconsistency rather than a difference nothing
        compares.
        """
        metadata = self.machine.get("metadata", {})
        binding = metadata.get("agentBinding")
        projection = metadata.get("openClawProjection")
        if not binding and not projection:
            return

        statements = ["a owl:NamedIndividual , re:AgentBinding",
                      "re:writesToRegionOf m:machine"]

        # Agent identity. The curated binding names a provider agent; the
        # projection names a role. Prefer the explicit agent id when present.
        agent_id = None
        if binding and binding.get("agent"):
            agent_id = binding["agent"]
        elif projection and projection.get("owner"):
            agent_id = projection["owner"]
        if agent_id:
            statements.append("re:boundAgent m:agent")

        if binding:
            if binding.get("mode"):
                statements.append(f"re:autonomyMode {self.autonomy_term(binding['mode'])}")
            if binding.get("trigger"):
                statements.append(f're:agentTrigger "{escape(binding["trigger"])}"')
            for action in binding.get("allowedActions") or []:
                statements.append(f're:allowedAction "{escape(action)}"')
            controls = binding.get("riskControls") or {}
            if "requiresHumanApproval" in controls:
                flag = "true" if controls["requiresHumanApproval"] else "false"
                statements.append(f"re:requiresHumanApproval {flag}")
            if controls.get("maxAutonomy"):
                statements.append(f"re:maxAutonomy {self.autonomy_term(controls['maxAutonomy'])}")

        axes = self.semantic_axes()

        # One individual per binding source, never a union of both.
        #
        # These are two different bindings, and merging them produced a chimera:
        # the curated agentBinding's autonomy mode wearing the OpenClaw
        # projection's write-back axes. For the 109 observe-mode bindings that
        # is a straight contradiction — observe is egress-only
        # (writeBack {"type": "none"}, canWriteBack false, stage 0), so it has
        # no return leg and therefore no landing positions, which is exactly
        # what re:ObserveBinding rdfs:subClassOf (re:hasSemanticAxis max 0)
        # says. Every one of those 109 also carries an openClawProjection that
        # *does* write back, and the merge attached its four axes to the
        # observe binding. HermiT rejected the union, correctly: the five
        # domains it made inconsistent (transportation, built-space,
        # data-center, energy, agriculture) are precisely the five with observe
        # bindings.
        #
        # The corpus and the axiom were both right. Only the projection binding
        # carries the axes, because semantic_axes() derives them from
        # openClawProjection.semantics.
        if binding:
            self.block("m:agent-binding", statements)

        if projection:
            projection_statements = [
                "a owl:NamedIndividual , re:AgentBinding",
                "re:writesToRegionOf m:machine",
            ]
            if agent_id:
                projection_statements.append("re:boundAgent m:agent")
            # A projection asserts an autonomy posture of its own: it writes an
            # assessment for RE to evaluate, which is advisory by construction.
            projection_statements.append("re:autonomyMode re:Advise")
            if axes:
                projection_statements.append(
                    "re:hasSemanticAxis " + " , ".join(term for term, _ in axes)
                )
            self.block("m:openclaw-binding", projection_statements)

        if agent_id:
            agent_statements = ["a owl:NamedIndividual , re:Agent",
                                f're:agentId "{escape(agent_id)}"']
            if projection and projection.get("owner"):
                agent_statements.append(f're:agentRole "{escape(projection["owner"])}"')
            self.block("m:agent", agent_statements)

        for term, axis in axes:
            self.block(term, [
                "a owl:NamedIndividual , re:SemanticAxis",
                f"re:axisIndex {number(axis['index'])}",
                f're:axisName "{escape(axis["name"])}"',
                f're:axisNameSource "{escape(axis["source"])}"',
            ])

    @staticmethod
    def autonomy_term(mode: str) -> str:
        return {
            "observe": "re:Observe",
            "advise": "re:Advise",
            "supervised-act": "re:SupervisedAct",
            "automated-act": "re:AutomatedAct",
        }.get(mode, "re:Advise")

    def semantic_axes(self) -> list[tuple[str, dict[str, Any]]]:
        """One axis per element of the write-back region.

        Provenance is recorded because the corpus has two disagreeing sources for
        these names, and a resolution that cannot say where a name came from
        cannot be adjudicated (localOpenClawStack#17).
        """
        metadata = self.machine.get("metadata", {})
        projection = metadata.get("openClawProjection") or {}
        names = projection.get("semantics")
        source = "openclaw-projection"
        if not names:
            names = metadata.get("inputSemantics")
            source = "input-semantics"
        if not names:
            return []
        axes = []
        for index, name in enumerate(names):
            axes.append((
                f"m:axis-{index}",
                {"index": index, "name": name, "source": source},
            ))
        return axes

    def emit_local_actions(self) -> None:
        for code in sorted(self.local_actions):
            self.block(
                self.local_actions[code],
                [
                    "a owl:NamedIndividual , re:Action",
                    f're:actionCode "{escape(code)}"',
                ],
            )


def target_path(machine_path: Path) -> Path:
    return ABOX_ROOT / domain_for(machine_path) / f"{machine_path.stem}.ttl"


def collect_machines(args: argparse.Namespace) -> list[Path]:
    if args.machine:
        return [Path(p).resolve() for p in args.machine]
    if args.domain:
        root = MACHINES_ROOT / "domains" / args.domain
        if not root.is_dir():
            raise SystemExit(f"unknown domain: {args.domain}")
        return sorted(root.rglob("*.json"))
    return sorted(MACHINES_ROOT.rglob("*.json"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--machine", nargs="*", help="machine JSON path(s)")
    parser.add_argument("--domain", help="generate for one domain under machines/domains/")
    parser.add_argument("--all", action="store_true", help="generate for the whole corpus")
    parser.add_argument("--write", action="store_true", help="write ABox files")
    parser.add_argument(
        "--check", action="store_true",
        help="fail if any existing ABox file differs from regeneration",
    )
    parser.add_argument(
        "--strict-actions", action="store_true",
        help="fail on action codes missing from the core vocabulary",
    )
    parser.add_argument(
        "--manifest-write", action="store_true",
        help="write semantics/abox-manifest.json (name, IRI, sha256 per machine)",
    )
    parser.add_argument(
        "--manifest-check", action="store_true",
        help="fail if the checked-in manifest differs from regeneration",
    )
    args = parser.parse_args()
    if args.manifest_write or args.manifest_check:
        args.all = True
    if not (args.machine or args.domain or args.all):
        parser.error("choose --machine, --domain, or --all")

    actions = load_action_vocabulary()
    if not actions:
        raise SystemExit(f"no action vocabulary found in {ONTOLOGY_PATH}")

    drift: list[str] = []
    warnings: list[str] = []
    manifest: dict[str, dict[str, str]] = {}
    generated = 0
    for machine_path in collect_machines(args):
        with machine_path.open() as handle:
            doc = json.load(handle)
        if "machine" not in doc:
            continue
        projector = MachineProjector(machine_path, doc, actions, args.strict_actions)
        content = projector.project()
        warnings.extend(projector.warnings)
        generated += 1
        if args.manifest_write or args.manifest_check:
            key = f"{projector.domain}/{sanitize(machine_path.stem)}"
            manifest[key] = {
                "name": doc["machine"]["name"],
                "iri": f"{projector.base}machine",
                "sourceFile": str(
                    machine_path.resolve().relative_to(REPO_ROOT.resolve())
                ),
                "sha256": hashlib.sha256(content.encode()).hexdigest(),
            }
            continue
        out = target_path(machine_path)
        if args.check:
            if not out.exists():
                drift.append(f"missing ABox: {out.relative_to(REPO_ROOT)}")
            elif out.read_text() != content:
                drift.append(f"stale ABox: {out.relative_to(REPO_ROOT)}")
        elif args.write:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(content)
        else:
            sys.stdout.write(content)

    for warning in warnings:
        print(f"WARN {warning}", file=sys.stderr)
    if args.manifest_write or args.manifest_check:
        document = {
            "version": "1.0.0",
            "generator": "scripts/generate-owl.py",
            "ontology": "semantics/ontology/re-core.ttl",
            "machines": dict(sorted(manifest.items())),
        }
        rendered = json.dumps(document, indent=2) + "\n"
        if args.manifest_write:
            MANIFEST_PATH.write_text(rendered)
            print(f"generate-owl: wrote manifest for {len(manifest)} machine(s)")
            return 0
        if not MANIFEST_PATH.exists():
            print("DRIFT missing semantics/abox-manifest.json", file=sys.stderr)
            return 1
        if MANIFEST_PATH.read_text() != rendered:
            print("DRIFT stale semantics/abox-manifest.json — run "
                  "'python3 scripts/generate-owl.py --manifest-write'",
                  file=sys.stderr)
            return 1
        print(f"generate-owl: manifest OK ({len(manifest)} machines)")
        return 0
    if args.check and drift:
        for line in drift:
            print(f"DRIFT {line}", file=sys.stderr)
        return 1
    if args.write:
        print(f"generate-owl: wrote {generated} ABox file(s) under {ABOX_ROOT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
