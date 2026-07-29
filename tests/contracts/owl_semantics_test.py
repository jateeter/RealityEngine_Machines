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
             "--machine", str(FALL_JSON), "--check", "--strict-actions"],
            capture_output=True, text=True,
        )
        self.assertEqual(
            result.returncode, 0,
            f"checked-in ABox drifted from generator output:\n{result.stderr}",
        )

    def test_abox_uses_only_declared_core_vocabulary(self) -> None:
        declared = declared_terms(self.ontology_text)
        undeclared = used_terms(self.abox_text) - declared
        self.assertEqual(
            undeclared, set(),
            f"ABox references re: terms missing from re-core.ttl: {sorted(undeclared)}",
        )

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
        for rule in rules:
            block = self.abox_text.split(f"m:rule-{rule['sequenceId']}\n", 1)[1].split("\n\n", 1)[0]
            self.assertIn(f"re:appliesToSequence m:seq-{rule['sequenceId']}", block)
            self.assertIn(f"re:matchesOutputTier {rule['outputMatches'][0]}", block)
            self.assertIn(
                f"re:matchesOutputConfidence {rule['outputMatches'][1]}", block,
            )
            self.assertIn(f"re:hasRagStatus re:{rule['ragStatusCode']}", block)

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
