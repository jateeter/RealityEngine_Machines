#!/usr/bin/env python3
"""Contract checks for the OWL semantic representation of machine behavior.

Prototype scope (Personal Health Fall Detection): the checked-in ABox under
semantics/abox/ must stay byte-identical to regeneration from the canonical
machine JSON, use only vocabulary declared in semantics/ontology/re-core.ttl,
and preserve the safety semantics the RE/PE verification path depends on
(life-safety sequences, RED escalation determinations, trigger-rule parity).
"""

from __future__ import annotations

import itertools
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


class OutputMergeTransformationTests(unittest.TestCase):
    """The declared merge gates, and the properties they claim.

    Folding a machine's collection of potential outputs is the last thing the
    Reality Engine does in a step, and the collection carries no order. The
    transformation is an n-input gate over the whole collection — not a chain of
    two-input gates.

    What these checks establish: each of the five declared gates is symmetric,
    verified by exhaustion over every permutation of every input combination,
    and each agrees with the truth condition the ontology states for it.

    CONTESTED, and deliberately NOT asserted here: that symmetry is the
    *admissibility rule* for transformations added later — that an exotic
    transformation must be a function of k and n alone. That generalisation is
    disputed and unsettled. These tests therefore verify a property of the five
    gates that exist; they do not enforce a criterion on gates that do not.
    Should the rule be settled affirmatively, a test rejecting non-symmetric
    declarations belongs here — it is absent because the rule is not settled.

    Adding the five multi-valued folds did not settle it, and nothing below
    reads as if it had. Five more symmetric transformations is five more
    instances of the property, not evidence that the property is required.

    THE MULTI-VALUED HALF. Those five gates are defined over {0,1} and flatten
    everything above 1 to 1, so folding a multi-valued machine with one loses
    its alphabet — FallDetection's severity ladder {0,1,2,3,4} answered by `or`
    is 1, asserted with the rung gone. The chain transformations declared
    alongside them fold over {0..k} instead, and the checks here treat their
    ontology declarations the way the Boolean ones are treated: each declared
    property is executed against the definition, not taken on the ontology's
    word. Negative claims are checked by counterexample for the same reason —
    `re:idempotent false` on the Łukasiewicz operations is a load-bearing
    statement (a runtime that folds x with itself and expects x is wrong), so
    an unchecked `false` that quietly became true would be a silent defect.

    NAME COLLISION, inherited from the ontology and confined to reading: `k` in
    the Boolean half is the count of asserted contributions, `k` in the chain
    half is the chain top. `n` is the collection size in both. GATES is written
    over the first, FOLDS over the second, and they never mix.
    """

    TRANSFORMATIONS = ("or", "and", "xor", "nor", "nand")
    MV_TRANSFORMATIONS = ("meet", "join", "strong-disjunction",
                          "strong-conjunction", "discrete-median")

    # The definitions the ontology states, as executable predicates.
    GATES = {
        "or":   lambda k, n: k >= 1,
        "and":  lambda k, n: k == n,
        "xor":  lambda k, n: k % 2 == 1,
        "nor":  lambda k, n: k == 0,
        "nand": lambda k, n: k < n,
    }

    # The chain definitions, transcribed from re:mergeFormula. Written in the
    # definitional form, not the shape a runtime should implement: an engine is
    # expected to fold in a single pass with early exit at the chain bound, and
    # to select the median in O(n) rather than sorting. Those are the same
    # function, and this is the one the ontology states, so it is the one that
    # gets pinned here.
    #
    # Every fold takes (values, k) whether or not it reads k, so the table can
    # be driven by one dispatch. meet, join and the median ignoring k is not an
    # oversight a linter should tidy away — it IS the claim re:requiresChainTop
    # false makes, and test_chain_top_dependence_matches_the_declaration sweeps
    # k across five values at the call site to hold them to it. Same for the
    # GATES table above, where or and nor ignore n.
    FOLDS = {
        "meet":               lambda x, k: min(x),
        "join":               lambda x, k: max(x),
        "strong-disjunction": lambda x, k: min(k, sum(x)),
        "strong-conjunction": lambda x, k: max(0, sum(x) - k * (len(x) - 1)),
        "discrete-median":    lambda x, k: sorted(x)[(len(x) - 1) // 2],
    }

    MV_FORMULAS = {
        "meet":               "min(x_i)",
        "join":               "max(x_i)",
        "strong-disjunction": "min(k, sum(x_i))",
        "strong-conjunction": "max(0, sum(x_i) - k(n-1))",
        "discrete-median":    "sort(x)[floor((n-1)/2)]",
    }

    # (idempotent, returnsAContributor, requiresChainTop) as the ontology
    # declares them. Every entry — true and false alike — is executed below.
    MV_CLAIMS = {
        "meet":               (True,  True,  False),
        "join":               (True,  True,  False),
        "strong-disjunction": (False, False, True),
        "strong-conjunction": (False, False, True),
        "discrete-median":    (True,  True,  False),
    }

    # Exhaustion bounds. The chain {0..3} is the smallest one that separates
    # every claim here: it has an interior, so a fold can land on a value no
    # contributor asserted, and it is wide enough for ⊕ to saturate and ⊙ to
    # extinguish at n=2. Collections to n=5 cover both median parities twice.
    CHAIN_TOP = 3
    MAX_N = 5

    def setUp(self) -> None:
        self.ttl = ONTOLOGY.read_text(encoding="utf-8")

    def _chain_collections(self, max_n: int | None = None):
        """Every collection of size 1..max_n over the chain {0..CHAIN_TOP}."""
        alphabet = range(self.CHAIN_TOP + 1)
        for n in range(1, (max_n or self.MAX_N) + 1):
            for combo in itertools.product(alphabet, repeat=n):
                yield list(combo)

    def test_every_schema_transformation_is_declared_in_the_ontology(self) -> None:
        machine = json.loads(
            (REPO_ROOT / "schemas" / "machine.schema.json").read_text(encoding="utf-8")
        )["$defs"]["machine"]
        prop = machine["properties"]["outputMergeTransformation"]
        self.assertEqual(sorted(prop["enum"]),
                         sorted(self.TRANSFORMATIONS + self.MV_TRANSFORMATIONS),
                         "schema enum and the ontology's transformation set have drifted apart")
        for name in prop["enum"]:
            self.assertIn(f're:transformationName "{name}"', self.ttl,
                          f"{name} is accepted by the schema but not declared in the ontology")

    def test_the_fold_stays_optional_and_defaults_to_or(self) -> None:
        """Absent means "or", and adding transformations must not change that.

        Every machine in the corpus omits the property, so making it required —
        or moving the default — would invalidate the whole corpus at once while
        looking like a vocabulary extension.
        """
        machine = json.loads(
            (REPO_ROOT / "schemas" / "machine.schema.json").read_text(encoding="utf-8")
        )["$defs"]["machine"]
        self.assertEqual(machine["properties"]["outputMergeTransformation"]["default"], "or")
        self.assertNotIn("outputMergeTransformation", machine.get("required", []),
                         "the fold is optional: absent means \"or\"")

    def test_the_two_merge_domains_are_declared_and_disjoint(self) -> None:
        """Which domain a transformation folds over is stated, not inferred.

        The mismatch this vocabulary exists to make visible — a multi-valued
        machine declaring a Boolean fold — is only checkable if the declaration
        says which domain it is defined over. Disjointness is what makes a
        transformation claiming both an inconsistency a reasoner finds.
        """
        for cls in ("BooleanMergeTransformation", "ChainMergeTransformation"):
            block = self._class_block(cls)
            self.assertIn("rdfs:subClassOf re:OutputMergeTransformation", block,
                          f"re:{cls} is not a kind of output merge transformation")
        self.assertIn("owl:disjointWith re:ChainMergeTransformation",
                      self._class_block("BooleanMergeTransformation"),
                      "the two merge domains are not declared disjoint, so a transformation "
                      "could claim both without contradiction")

        for name in self.TRANSFORMATIONS:
            block = self._individual_block(name)
            self.assertIn("re:BooleanMergeTransformation", block,
                          f"{name} is a gate over {{0,1}} but does not say so")
            self.assertNotIn("re:mergeFormula", block,
                             f"{name} states a chain formula; it is defined by a truth table")
        for name in self.MV_TRANSFORMATIONS:
            block = self._individual_block(name)
            self.assertIn("re:ChainMergeTransformation", block,
                          f"{name} folds over a chain but does not say so")
            self.assertNotIn("re:assertedWhen", block,
                             f"{name} states a Boolean truth condition; it has no truth table "
                             f"over the count of asserted contributions")

    def test_multi_valued_transformations_declare_the_properties_they_are_checked_on(self) -> None:
        for name in self.MV_TRANSFORMATIONS:
            block = self._individual_block(name)
            self.assertIn("re:deterministic true", block,
                          f"{name} does not assert re:deterministic")
            self.assertIn("re:symmetric true", block,
                          f"{name} does not record re:symmetric, which it is verified to be")
            idempotent, contributor, chain_top = self.MV_CLAIMS[name]
            for prop, claim in (("re:idempotent", idempotent),
                                ("re:returnsAContributor", contributor),
                                ("re:requiresChainTop", chain_top)):
                self.assertIn(f"{prop} {str(claim).lower()}", block,
                              f"{name} does not declare {prop} {str(claim).lower()}; the "
                              f"executable check below was written against that claim, so the "
                              f"two have drifted")

    def test_merge_formulas_match_their_stated_form(self) -> None:
        # The ontology is the definition; this pins the executable folds to it
        # so the two cannot drift, exactly as the Boolean gates are pinned.
        for name, formula in self.MV_FORMULAS.items():
            self.assertIn(f're:mergeFormula "{formula}"', self._individual_block(name),
                          f"{name}'s stated formula changed; update the executable fold in "
                          f"this test to match, or the two have drifted")

    def test_multi_valued_folds_are_closed_and_permutation_invariant(self) -> None:
        """Closure and symmetry of the five chain folds, checked by exhaustion.

        Closure is the property that makes these usable where a Boolean gate is
        not: the result is a member of the machine's alphabet, so the fold
        cannot hand the Perception Engine a level the chain does not contain.

        As with the Boolean gates, this establishes symmetry for these five. It
        does not establish that a fold lacking it is inadmissible — that is the
        contested generalisation described in the class docstring.
        """
        chain = set(range(self.CHAIN_TOP + 1))
        for name in self.MV_TRANSFORMATIONS:
            fold = self.FOLDS[name]
            for values in self._chain_collections():
                got = fold(values, self.CHAIN_TOP)
                self.assertIn(got, chain,
                              f"{name}{tuple(values)} -> {got}, outside the chain "
                              f"{{0..{self.CHAIN_TOP}}} it is declared closed over")
                results = {fold(list(p), self.CHAIN_TOP)
                           for p in itertools.permutations(values)}
                self.assertEqual(len(results), 1,
                                 f"{name} is order dependent on {tuple(values)}: {results}, "
                                 f"contradicting the re:symmetric it declares")

    def test_closure_depends_on_inputs_lying_in_the_chain(self) -> None:
        """The precondition the closure claim rests on, made visible.

        test_multi_valued_folds_are_closed_and_permutation_invariant draws its
        inputs from {0..k}, so it verifies closure *given* well-formed cells. It
        is worth knowing how sharp that precondition is, because the two strong
        operations fail it in opposite directions and only one is loud about it.

        strong-disjunction clamps — min(k, ...) cannot exceed k whatever it is
        fed — so a k below the machine's real alphabet silently flattens every
        rung above it, which is the exact failure these transformations exist to
        avoid, reintroduced through the parameter instead of the gate.

        strong-conjunction does not clamp. Its bound sum(x_i) - k(n-1) <= k
        holds only because each x_i <= k, so cells above k walk straight out of
        the chain. That makes a wrong k detectable there and undetectable in its
        own De Morgan dual — worth stating before anyone picks a default k.
        """
        for k in (1, 2):
            over_chain = [k + 1] * 2
            self.assertGreater(self.FOLDS["strong-conjunction"](over_chain, k), k,
                               "strong-conjunction no longer escapes the chain on inputs above "
                               "k; the precondition recorded on re:mergeFormula is now wrong")
            self.assertLessEqual(self.FOLDS["strong-disjunction"](over_chain, k), k,
                                 "strong-disjunction no longer clamps, so the asymmetry "
                                 "described here has changed")

        # The ontology must keep saying so; this is the note's only enforcement.
        self.assertIn("PRECONDITION", self._property_block("mergeFormula"),
                      "re:mergeFormula no longer records the precondition its closure needs")

    def test_idempotence_holds_where_claimed_and_fails_where_denied(self) -> None:
        """Both directions, because the `false` entries are load-bearing.

        x ⊕ x saturating and x ⊙ x extinguishing is what those two operations
        are chosen for. A runtime that collapses a repeated contribution — a
        reasonable-looking optimisation over a collection — changes the answer,
        so `re:idempotent false` is checked by counterexample rather than left
        as an unverified absence.
        """
        for name in self.MV_TRANSFORMATIONS:
            fold = self.FOLDS[name]
            claimed = self.MV_CLAIMS[name][0]
            counterexamples = [
                (x, n, fold([x] * n, self.CHAIN_TOP))
                for n in range(1, self.MAX_N + 1)
                for x in range(self.CHAIN_TOP + 1)
                if fold([x] * n, self.CHAIN_TOP) != x
            ]
            if claimed:
                self.assertEqual(counterexamples, [],
                                 f"{name} declares re:idempotent true but f(x..x) != x at "
                                 f"{counterexamples[:3]}")
            else:
                self.assertNotEqual(counterexamples, [],
                                    f"{name} declares re:idempotent false but is idempotent "
                                    f"everywhere on the chain; either the declaration or the "
                                    f"definition is wrong")

    def test_no_fabrication_holds_where_claimed_and_fails_where_denied(self) -> None:
        """re:returnsAContributor — strictly stronger than closure.

        Bitwise or of 1 and 2 is 3: inside a chain {0..3}, asserted by nobody,
        and on an ordinal severity ladder a rung the machine invented. meet,
        join and the median cannot do that because they select rather than
        compute. The Łukasiewicz pair can and are declared so — they combine
        evidence, and landing between contributors is the intent.
        """
        for name in self.MV_TRANSFORMATIONS:
            fold = self.FOLDS[name]
            claimed = self.MV_CLAIMS[name][1]
            fabrications = [
                (tuple(values), fold(values, self.CHAIN_TOP))
                for values in self._chain_collections(max_n=4)
                if fold(values, self.CHAIN_TOP) not in values
            ]
            if claimed:
                self.assertEqual(fabrications, [],
                                 f"{name} declares re:returnsAContributor true but returns a "
                                 f"value no contributor asserted at {fabrications[:3]}")
            else:
                self.assertNotEqual(fabrications, [],
                                    f"{name} declares re:returnsAContributor false but always "
                                    f"returns one of its inputs; the declaration understates it")

    def test_chain_top_dependence_matches_the_declaration(self) -> None:
        """re:requiresChainTop false must mean the answer does not move with k.

        join reads k as an early-exit optimisation, and an optimisation that
        changes the result is a defect. This is the check that keeps `false`
        from meaning "we did not look".
        """
        tops = range(self.CHAIN_TOP, self.CHAIN_TOP + 5)
        for name in self.MV_TRANSFORMATIONS:
            fold = self.FOLDS[name]
            claimed = self.MV_CLAIMS[name][2]
            moved = [tuple(values) for values in self._chain_collections(max_n=4)
                     if len({fold(values, k) for k in tops}) > 1]
            if claimed:
                self.assertNotEqual(moved, [],
                                    f"{name} declares re:requiresChainTop true but its result "
                                    f"never moves with k; then k is not a parameter of it")
            else:
                self.assertEqual(moved, [],
                                 f"{name} declares re:requiresChainTop false but its result "
                                 f"moves with k at {moved[:3]}; k is not an optimisation there")

    def test_strong_conjunction_is_the_de_morgan_dual_of_strong_disjunction(self) -> None:
        """⊙ = ¬(¬x ⊕ ¬y) under the chain's negation ¬x = k − x.

        The cheapest correctness check a runtime has: implement one, derive the
        other, and a disagreement names which of the two is broken.
        """
        for a, b in (("strong-disjunction", "strong-conjunction"),
                     ("strong-conjunction", "strong-disjunction")):
            self.assertIn(f"re:deMorganDualOf re:merge-{b}", self._individual_block(a),
                          f"{a} does not record its dual; the derivation check has nothing "
                          f"in the ontology to stand on")

        k = self.CHAIN_TOP
        conjunction, disjunction = self.FOLDS["strong-conjunction"], self.FOLDS["strong-disjunction"]
        for values in self._chain_collections(max_n=4):
            derived = k - disjunction([k - x for x in values], k)
            self.assertEqual(conjunction(values, k), derived,
                             f"de Morgan duality fails at {tuple(values)}: "
                             f"{conjunction(values, k)} != {derived}")

    def test_the_undeclared_chain_top_is_recorded_as_unresolved(self) -> None:
        """k is a parameter nothing in the corpus supplies, and that is stated.

        The tempting derivation — read k off bitsPerElement — is wrong, and
        wrong quietly: FallDetection declares 4 bits, representable 0..15, and
        ranks severity over {0,1,2,3,4}. Folding its ladder with k=15 puts
        strong-disjunction at 14, a rung outside the machine's own alphabet,
        with nothing at the point of use able to tell. This asserts both the
        corpus fact and that the ontology still carries the open question, so
        the note cannot be tidied away while the gap is open.
        """
        block = self.ttl[self.ttl.find("# Multi-valued output merge transformations"):]
        self.assertIn("UNRESOLVED", block,
                      "the ontology no longer records that the chain top is undeclared")
        self.assertIn("bitsPerElement", block,
                      "the ontology no longer warns against deriving k from bitsPerElement")

        fall = json.loads(FALL_JSON.read_text(encoding="utf-8"))["machine"]
        outputs = [o["vector"] for s in fall["sequences"] for v in s["vectors"]
                   for o in (v.get("outputVectors") or [])]
        alphabet = {x for vector in outputs for x in vector}
        representable = (1 << fall["perceptualMapping"]["bitsPerElement"]) - 1
        self.assertGreater(representable, max(alphabet),
                           "FallDetection's representable range now equals its alphabet, which "
                           "would make bitsPerElement a plausible source for k — recheck the "
                           "corpus before trusting this note")

        ladder = [vector[0] for vector in outputs]
        self.assertNotIn(self.FOLDS["strong-disjunction"](ladder, representable), alphabet,
                         "deriving k from bitsPerElement no longer escapes FallDetection's "
                         "alphabet; the worked example in the ontology needs revisiting")
        self.assertIn(self.FOLDS["strong-disjunction"](ladder, max(alphabet)), alphabet,
                      "the alphabet's own top no longer keeps the fold inside the alphabet")

    def test_every_transformation_asserts_determinism_and_symmetry(self) -> None:
        for name in self.TRANSFORMATIONS:
            block = self._individual_block(name)
            self.assertIn("re:deterministic true", block,
                          f"{name} does not assert re:deterministic")
            # Each of the five is symmetric in fact — verified below. This
            # checks the ontology records it, not that symmetry is required of
            # anything else (contested; see the class docstring).
            self.assertIn("re:symmetric true", block,
                          f"{name} does not record re:symmetric, which it is verified to be")
            self.assertIn("re:assertedWhen", block,
                          f"{name} does not state its truth condition over k and n")

    def test_declared_gates_are_permutation_invariant(self) -> None:
        """Symmetry of the five declared gates, checked by exhaustion.

        Every gate is applied to every permutation of every input combination up
        to n=5. This establishes the property for these five.

        It does not establish that a gate lacking the property is inadmissible —
        that is the contested generalisation described in the class docstring.
        """
        for name in self.TRANSFORMATIONS:
            gate = self.GATES[name]
            for n in range(1, 6):
                for combo in itertools.product((0, 1), repeat=n):
                    results = {gate(sum(p), n) for p in itertools.permutations(combo)}
                    self.assertEqual(
                        len(results), 1,
                        f"{name} is order dependent on {combo}: {results}, contradicting the "
                        f"re:symmetric it declares.")

    def test_gate_definitions_match_their_stated_truth_condition(self) -> None:
        # The ontology is the definition; this pins the executable form to it so
        # the two cannot drift.
        stated = {"or": "k >= 1", "and": "k = n", "xor": "k odd",
                  "nor": "k = 0", "nand": "k < n"}
        for name, condition in stated.items():
            block = self._individual_block(name)
            self.assertIn(f're:assertedWhen "{condition}"', block,
                          f"{name}'s stated truth condition changed; update the executable "
                          f"gate in this test to match, or the two have drifted")

    def _individual_block(self, name: str) -> str:
        return self._block(f"re:merge-{name} a owl:NamedIndividual",
                           f"re:merge-{name} is not declared in the ontology")

    def _class_block(self, name: str) -> str:
        return self._block(f"re:{name} a owl:Class",
                           f"re:{name} is not declared in the ontology")

    def _property_block(self, name: str) -> str:
        return self._block(f"re:{name} a owl:",
                           f"re:{name} is not declared in the ontology")

    def _block(self, marker: str, missing: str) -> str:
        start = self.ttl.find(marker)
        self.assertNotEqual(start, -1, missing)
        end = self.ttl.find("\n\n", start)
        return self.ttl[start:end if end != -1 else len(self.ttl)]


class OutputAlphabetTopTests(unittest.TestCase):
    """k is declarable, optional, and demanded exactly where it is needed.

    The two Lukasiewicz transformations are undefined without a chain top, and
    no value can be assumed for them: a Boolean-chain default flattens the
    ladder through the parameter for one and violates closure for the other
    (k=1 over [2,2] gives 3, outside {0,1}). So the schema requires the
    declaration where it matters and nowhere else, and the runtimes refuse to
    fold rather than guess.

    No corpus machine declares it today and none needs to, which is the
    property these checks pin — a conditional requirement that quietly applied
    to everything would be a corpus-wide break.
    """

    def setUp(self) -> None:
        self.schema = json.loads(
            (REPO_ROOT / "schemas" / "machine.schema.json").read_text(encoding="utf-8"))
        self.ttl = ONTOLOGY.read_text(encoding="utf-8")

    def test_declared_optional_on_the_perceptual_mapping(self) -> None:
        mapping = self.schema["$defs"]["perceptualMapping"]
        self.assertIn("outputAlphabetTop", mapping["properties"],
                      "the chain top belongs beside bitsPerElement, where the two are confused")
        self.assertNotIn("outputAlphabetTop", mapping.get("required", []),
                         "the chain top must stay optional — no corpus machine declares it")
        spec = mapping["properties"]["outputAlphabetTop"]
        self.assertEqual(spec["type"], "integer")
        self.assertEqual(spec["minimum"], 1, "{0..0} is not a chain")

    def test_required_exactly_for_the_lukasiewicz_pair(self) -> None:
        conditionals = self.schema["$defs"]["machine"].get("allOf") or []
        guards = [c for c in conditionals
                  if "outputAlphabetTop" in json.dumps(c.get("then", {}))]
        self.assertEqual(len(guards), 1,
                         "exactly one rule should demand the chain top")
        triggers = (guards[0]["if"]["properties"]["outputMergeTransformation"]["enum"])
        self.assertEqual(sorted(triggers), ["strong-conjunction", "strong-disjunction"],
                         "only the two transformations that are undefined without k "
                         "may demand it; meet, join and discrete-median take no k")

    def test_no_corpus_machine_declares_or_needs_it(self) -> None:
        declaring = [p for p in (REPO_ROOT / "machines").rglob("*.json")
                     if "outputAlphabetTop" in p.read_text(encoding="utf-8")]
        self.assertEqual(declaring, [],
                         "no corpus machine declares a chain top yet; when one does, "
                         "it must also declare a Lukasiewicz transformation or the "
                         "field is inert")

    def test_ontology_declares_it_and_says_why_it_is_not_bitsPerElement(self) -> None:
        self.assertIn("re:outputAlphabetTop a owl:DatatypeProperty", self.ttl)
        block_start = self.ttl.find("re:outputAlphabetTop a owl:DatatypeProperty")
        block = self.ttl[block_start:self.ttl.find("\n\n", block_start)]
        self.assertIn("bitsPerElement", block,
                      "the distinction from bitsPerElement is the whole reason this "
                      "property exists and must be stated where it is declared")

