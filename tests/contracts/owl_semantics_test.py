#!/usr/bin/env python3
"""Contract checks for the OWL semantic representation of machine behavior.

Prototype scope (Personal Health Fall Detection): the checked-in ABox under
semantics/abox/ must stay byte-identical to regeneration from the canonical
machine JSON, use only vocabulary declared in semantics/ontology/re-core.ttl,
and preserve the safety semantics the RE/PE verification path depends on
(life-safety sequences, RED escalation determinations, trigger-rule parity).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ONTOLOGY = REPO_ROOT / "semantics" / "ontology" / "re-core.ttl"
GENERATOR = REPO_ROOT / "scripts" / "generate-owl.py"
MACHINES_DIR = REPO_ROOT / "machines"
FALL_JSON = REPO_ROOT / "machines" / "domains" / "health-personal" / "FallDetection.json"
FALL_ABOX = REPO_ROOT / "semantics" / "abox" / "health-personal" / "FallDetection.ttl"

REQUIRED_CLASSES = [
    "Machine",
    "CriticalEventSequence",
    "LifeSafetySequence",
    "SequenceStep",
    "ElementValue",
    "Determination",
    "Action",
    "LoggingAction",
    "NotificationAction",
    "EscalationAction",
    "RagStatus",
    "TriggerRule",
    "GovernancePolicy",
    "Interconnection",
    "PerceptualMapping",
    "PerceptionEvent",
    "SequenceObservation",
    "DispatchRecord",
    "EscalationDetermination",
]


def declared_terms(ontology_text: str) -> set[str]:
    """All re: local names declared as a subject in the core ontology."""
    return set(re.findall(r"^re:(\w[\w-]*)\s", ontology_text, re.MULTILINE))


def used_terms(abox_text: str) -> set[str]:
    return set(re.findall(r"\bre:([\w-]+)", abox_text))


class OwlSemanticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ontology_text = ONTOLOGY.read_text()
        cls.abox_text = FALL_ABOX.read_text()
        with FALL_JSON.open() as handle:
            cls.machine = json.load(handle)["machine"]

    def test_core_ontology_declares_required_vocabulary(self) -> None:
        declared = declared_terms(self.ontology_text)
        for name in REQUIRED_CLASSES:
            self.assertIn(name, declared, f"re-core.ttl must declare re:{name}")
        for individual in ("GREEN", "AMBER", "RED", "EmergencyDispatch",
                           "CaregiverCheckIn", "CaregiverWatch", "LogOnly",
                           "LogActivity"):
            self.assertIn(individual, declared)

    def test_abox_is_deterministic_regeneration_of_machine_json(self) -> None:
        result = subprocess.run(
            [sys.executable, str(GENERATOR),
             "--domain", "health-personal", "--check", "--strict-actions"],
            capture_output=True, text=True,
        )
        self.assertEqual(
            result.returncode, 0,
            f"checked-in ABoxes drifted from generator output:\n{result.stderr}",
        )

    def test_domain_has_one_abox_per_machine(self) -> None:
        machines = sorted(FALL_JSON.parent.glob("*.json"))
        aboxes = sorted(FALL_ABOX.parent.glob("*.ttl"))
        self.assertEqual(
            [p.stem for p in machines], [p.stem for p in aboxes],
            "every health-personal machine must have a checked-in ABox",
        )

    def test_abox_uses_only_declared_core_vocabulary(self) -> None:
        declared = declared_terms(self.ontology_text)
        for abox in sorted(FALL_ABOX.parent.glob("*.ttl")):
            undeclared = used_terms(abox.read_text()) - declared
            self.assertEqual(
                undeclared, set(),
                f"{abox.name} references re: terms missing from re-core.ttl: "
                f"{sorted(undeclared)}",
            )

    def test_domain_actions_are_controlled_codes(self) -> None:
        """Every health-personal output action must be a code declared in the
        core ontology; normalized prose must be preserved as actionNarrative."""
        codes = set(re.findall(r're:actionCode "([^"]+)"', self.ontology_text))
        for machine_path in sorted(FALL_JSON.parent.glob("*.json")):
            with machine_path.open() as handle:
                machine = json.load(handle)["machine"]
            for sequence in machine.get("sequences", []):
                for vector in sequence.get("vectors", []):
                    for output in vector.get("outputVectors", []):
                        metadata = output.get("metadata", {})
                        action = metadata.get("action")
                        if action is None:
                            continue
                        self.assertIn(
                            action, codes,
                            f"{machine_path.name}:{output.get('id')} action "
                            f"'{action[:60]}' is not a controlled code",
                        )
                        if metadata.get("actionNarrative"):
                            self.assertNotIn(metadata["actionNarrative"], codes)

    def test_every_sequence_is_represented(self) -> None:
        for sequence in self.machine["sequences"]:
            self.assertIn(
                f're:sequenceId "{sequence["id"]}"', self.abox_text,
                f"sequence {sequence['id']} missing from ABox",
            )
        self.assertEqual(
            self.abox_text.count("re:CriticalEventSequence ;")
            + self.abox_text.count("re:CriticalEventSequence , re:LifeSafetySequence ;"),
            len(self.machine["sequences"]),
        )

    def test_life_safety_sequences_are_typed_as_such(self) -> None:
        expected = {
            seq["id"] for seq in self.machine["sequences"]
            if seq.get("metadata", {}).get("severity") == "life-safety"
            or any(v.get("metadata", {}).get("lifeSafety") for v in seq["vectors"])
        }
        self.assertEqual(expected, {"fall-confirmed", "fall-slow-collapse"})
        for seq_id in expected:
            block = self.abox_text.split(f"m:seq-{seq_id}\n", 1)[1].split("\n\n", 1)[0]
            self.assertIn("re:LifeSafetySequence", block, seq_id)

    def test_red_determinations_prescribe_escalation_actions(self) -> None:
        """Audit invariant: every RED output in the machine JSON must appear in
        the ABox as a determination whose prescribed action is a canonical
        EscalationAction individual."""
        escalation_individuals = re.findall(
            r"re:(\w+) a owl:NamedIndividual , re:EscalationAction",
            self.ontology_text,
        )
        self.assertIn("EmergencyDispatch", escalation_individuals)
        red_outputs = []
        for sequence in self.machine["sequences"]:
            for vector in sequence["vectors"]:
                for output in vector.get("outputVectors", []):
                    if output.get("metadata", {}).get("ragStatusCode") == "RED":
                        red_outputs.append(output)
        self.assertGreaterEqual(len(red_outputs), 2)
        for output in red_outputs:
            block = self.abox_text.split(f"m:out-{output['id']}\n", 1)[1].split("\n\n", 1)[0]
            self.assertIn("re:hasRagStatus re:RED", block, output["id"])
            self.assertTrue(
                any(f"re:prescribesAction re:{name}" in block
                    for name in escalation_individuals),
                f"RED determination {output['id']} lacks an escalation action",
            )

    def test_trigger_rules_match_sequence_outputs(self) -> None:
        rules = self.machine["metadata"]["triggerConfig"]["rules"]
        ordinals: dict[str, int] = {}
        for rule in rules:
            seq = rule["sequenceId"]
            ordinals[seq] = ordinals.get(seq, 0) + 1
            block = self.abox_text.split(
                f"m:rule-{seq}-{ordinals[seq]}\n", 1
            )[1].split("\n\n", 1)[0]
            self.assertIn(f"re:appliesToSequence m:seq-{seq}", block)
            joined = ",".join(str(v) for v in rule["outputMatches"])
            self.assertIn(f're:outputMatchVector "{joined}"', block)
            for index, value in enumerate(rule["outputMatches"]):
                if value:
                    self.assertIn(f"re:matchesOutputPosition {index}", block)
            self.assertIn(f"re:hasRagStatus re:{rule['ragStatusCode']}", block)

    def test_every_class_is_documented(self) -> None:
        """rdfs:comment is this project's documentation vehicle, so assert it.

        ROBOT's `missing_definition` looks for a definition annotation property
        (IAO:0000115 by convention) and reports 120 terms. That measures an OBO
        Foundry publishing convention this ontology does not follow: it documents
        with rdfs:comment, and every class already carries one. Rather than write
        120 definitions to satisfy a linter, or silently drop the rule, this
        asserts the rule the project does follow — so the 120 remaining INFOs are
        a known, deliberate difference rather than an unmeasured gap.

        Scoped to classes on purpose. Properties like re:hasSequence are fully
        described by their label, domain and range; requiring prose for each
        would add 104 restatements of the obvious.
        """
        text = self.ontology_text
        blocks = re.split(r"\n(?=re:)", text)
        undocumented = []
        unlabelled = []
        for block in blocks:
            match = re.match(r"re:([A-Za-z0-9_]+)\s", block)
            if not match or "owl:Class" not in block:
                continue
            # A term may be declared across several statement blocks; only the
            # one carrying its type declaration is checked.
            if "rdfs:label" not in block:
                unlabelled.append(match.group(1))
            if "rdfs:comment" not in block:
                undocumented.append(match.group(1))
        self.assertEqual(unlabelled, [], f"classes without rdfs:label: {unlabelled}")
        self.assertEqual(
            undocumented, [], f"classes without rdfs:comment: {undocumented}"
        )

    def test_escalation_invariant_is_stated_with_a_genus(self) -> None:
        """The audit axiom names re:Determination in its equivalence.

        re:prescribesAction already has rdfs:domain re:Determination, so the
        genus changes no entailment — but stating it is what lets the axiom be
        read without chasing the property's domain, and it is what ROBOT's
        equivalent_class_axiom_no_genus asks for. Asserting it here stops the
        genus being dropped again as a simplification.
        """
        block = self.ontology_text.split("re:EscalationDetermination a owl:Class", 1)[1]
        block = block.split("\n\n", 1)[0]
        self.assertIn("owl:intersectionOf", block)
        self.assertIn("re:Determination", block)
        self.assertIn("re:EscalationAction", block)

    def test_rule_iris_are_injective_across_the_corpus(self) -> None:
        """One trigger rule, one individual.

        Rule IRIs were minted from sequenceId alone, so a sequence with several
        rules produced one individual asserting several RAG statuses on the
        functional re:hasRagStatus. HermiT rejected the merged graph; ELK, which
        does not implement functional properties, passed it. This asserts the
        generator's side of that directly rather than relying on a reasoner the
        local gate may skip.
        """
        for machine_path in sorted(MACHINES_DIR.glob("domains/*/*.json")):
            document = json.loads(machine_path.read_text(encoding="utf-8"))
            machine = document.get("machine", document)
            rules = (
                (machine.get("metadata") or {}).get("triggerConfig") or {}
            ).get("rules") or []
            ordinals: dict[str, int] = {}
            terms = []
            for rule in rules:
                seq = rule.get("sequenceId")
                if not seq:
                    continue
                ordinals[seq] = ordinals.get(seq, 0) + 1
                terms.append(f"{seq}-{ordinals[seq]}")
            self.assertEqual(
                len(terms), len(set(terms)),
                f"{machine_path.name}: trigger rule IRIs collide",
            )

    def test_no_rule_pair_contradicts_itself(self) -> None:
        """Two rules matching the same output vector of the same sequence must
        not reach different determinations.

        Injective rule IRIs fix the inconsistency, and in doing so they stop the
        reasoner from surfacing this: each rule becomes its own individual with
        one RAG status, so a contradictory pair is merely two individuals that
        happen to disagree. The signal has to be asserted structurally instead.
        Redundant pairs that agree are permitted — eight exist and are harmless.

        No contradiction remains. AIHardwareResilience carried the last one —
        output position 5 was both "schedule maintenance" (GREEN) and "emergency
        replacement" (RED) — resolved in #56 by tagging its action rules with the
        severity of the state that emits them. The allowlist that stood here is
        gone; any contradiction now fails outright.
        """
        contradictions = []
        for machine_path in sorted(MACHINES_DIR.glob("domains/*/*.json")):
            document = json.loads(machine_path.read_text(encoding="utf-8"))
            machine = document.get("machine", document)
            rules = (
                (machine.get("metadata") or {}).get("triggerConfig") or {}
            ).get("rules") or []
            grouped: dict[tuple, set] = {}
            for rule in rules:
                key = (rule.get("sequenceId"), tuple(rule.get("outputMatches") or []))
                grouped.setdefault(key, set()).add(rule.get("ragStatusCode"))
            for (seq, vector), statuses in grouped.items():
                if len(statuses) > 1:
                    contradictions.append(
                        f"{machine_path.name}: {seq} {list(vector)} "
                        f"-> {sorted(statuses)}"
                    )
        self.assertEqual(
            contradictions, [],
            "trigger-rule contradictions:\n" + "\n".join(contradictions),
        )

    def test_manifest_matches_regeneration_and_covers_corpus(self) -> None:
        """semantics/abox-manifest.json is the corpus-wide semantic identity
        (name, IRI, sha256 of the generated ABox) that engines expose as
        semanticsIri/semanticsHash; it must stay in sync with the corpus."""
        result = subprocess.run(
            [sys.executable, str(GENERATOR), "--manifest-check", "--strict-actions"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads(
            (REPO_ROOT / "semantics" / "abox-manifest.json").read_text()
        )
        machines = manifest["machines"]
        corpus = [p for p in (REPO_ROOT / "machines").rglob("*.json")]
        self.assertEqual(len(machines), len(corpus))
        entry = machines["health-personal/FallDetection"]
        self.assertEqual(entry["name"], "Fall Detection")
        self.assertTrue(entry["iri"].endswith("/health-personal/FallDetection#machine"))
        self.assertRegex(entry["sha256"], r"^[0-9a-f]{64}$")
        names = [e["name"] for e in machines.values()]
        self.assertEqual(len(names), len(set(names)), "machine names must be unique")

    def test_interconnection_regions_are_projected(self) -> None:
        interconnections = self.machine["metadata"]["interconnections"]
        self.assertGreaterEqual(len(interconnections), 2)
        for interconnection in interconnections:
            term = "m:ix-" + re.sub(r"[^A-Za-z0-9_-]", "_", interconnection["id"])
            block = self.abox_text.split(f"{term}\n", 1)[1].split("\n\n", 1)[0]
            region = interconnection["sourceOutputRegion"]
            self.assertIn(f"re:sourceOutputOffset {region['offset']}", block)
            self.assertIn(f"re:sourceOutputLength {region['length']}", block)
            self.assertIn(
                f're:busId "{interconnection["busId"]}"', block,
            )

    def test_openclaw_projection_is_projected(self) -> None:
        projection = self.machine["metadata"]["openClawProjection"]
        block = self.abox_text.split("m:openclaw-projection\n", 1)[1].split("\n\n", 1)[0]
        self.assertIn(f're:projectionId "{projection["projectionId"]}"', block)
        self.assertIn(
            f"re:targetInputOffset {projection['writeBackRegion']['offset']}", block,
        )
        self.assertIn("re:hasOpenClawProjection m:openclaw-projection", self.abox_text)

    def test_generator_covers_health_personal_domain(self) -> None:
        """The generator must at minimum process every health-personal machine
        without error; corpus-wide ABox check-in is tracked in the roadmap."""
        result = subprocess.run(
            [sys.executable, str(GENERATOR), "--domain", "health-personal"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("m:machine", result.stdout)


if __name__ == "__main__":
    unittest.main()
