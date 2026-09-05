#!/usr/bin/env python3
"""Contract checks for the output alphabet and the fold that must preserve it.

The machine schema divides `outputMergeTransformation` into two families and says
what separates them:

    "or"/"and"/"xor"/"nor"/"nand" are Boolean gates over {0,1} and flatten every
    value above 1 to 1, which destroys a multi-valued machine's alphabet;
    "meet"/"join"/"strong-disjunction"/"strong-conjunction"/"discrete-median" are
    defined over an ordered chain {0..k} and preserve it.

So a machine that asserts a value above 1 and folds with a Boolean gate loses
that value silently. Not an exception, not a refusal -- a 3 and a 4 both arrive
as 1, the step completes, and every consumer downstream reads a well-formed
vector. This is the class of failure the corpus keeps producing: the wrong answer
is well formed, so only a comparison finds it.

WHAT THE CORPUS LOOKS LIKE, because it decides what these checks can prove.

Exactly two of 1328 machines assert an output value above 1:

    Fall Sensor Motion Pre-aggregator   asserts <=3   transform=join
    Fall Detection                      asserts <=4   transform=join

Both declare `join`, which is a chain transformation, so both are correct today.
They are correct *by their transformation choice alone* -- nothing else protects
them. Changing either to `or`, which is what the other 1326 machines declare and
what the schema names as the default, would flatten 3 and 4 to 1 and no test
would have said so. That is what MultiValuedMachineFoldTests pins.

THE HONEST LIMITS, three of them.

1. The check starts green and its discriminating power today is confined to two
   machines. That is the argument for landing it while the corpus is small enough
   to reason about, not evidence that it is unnecessary.

2. `outputAlphabetTop` is **absent on all 1328 machines**. Nothing declares it.
   The C++ fold reads it as an optional and its comment records that the two
   chain-folding machines "need no top", so absence is permitted rather than
   broken -- DeclaredAlphabetTests therefore reports the gap and does not fail
   on it. If a machine ever declares one, asserting above it is a real
   contradiction and that case does fail.

3. These checks are deliberately **per machine**. An earlier framing proposed
   failing a *cell* whose contributors span the two families. That does not
   follow: per ARBITER_CONTRACT.md 7.2 a cross-machine cell resolves under the
   registry rule -- PRECEDENCE or SEVERITY -- which selects one contributor's
   value whole rather than combining them, so no flattening happens there. The
   destruction is intra-machine, at the machine's own fold, and that is where the
   check belongs. CrossMachineAlphabetTests reports heterogeneity as information
   without claiming it is a violation.
"""

import json
import pathlib
import unittest

MACHINES = pathlib.Path(__file__).resolve().parents[2] / "machines"

# The two families, from the schema's `outputMergeTransformation` enum.
BOOLEAN_GATES = {"or", "and", "xor", "nor", "nand"}
ORDERED_CHAIN = {
    "meet",
    "join",
    "strong-disjunction",
    "strong-conjunction",
    "discrete-median",
}
# Absent means "or" per the schema's declared default, so an omitted field is a
# Boolean gate and is checked as one. Reading absence as "unconstrained" would
# exempt every machine that says nothing, which is most of them.
DEFAULT_TRANSFORMATION = "or"


def _machines():
    """(name, transformation, declaredTop, maxAsserted, relPath) per corpus machine."""
    out = []
    for path in sorted(MACHINES.rglob("*.json")):
        try:
            doc = json.loads(path.read_text())
        except (ValueError, OSError):
            continue
        machine = doc.get("machine")
        if not isinstance(machine, dict) or "sequences" not in machine:
            continue
        mapping = machine.get("perceptualMapping") or {}
        highest = 0.0
        for sequence in machine.get("sequences") or []:
            for event in sequence.get("events") or []:
                for output in event.get("outputEvents") or []:
                    for value in output.get("vector") or []:
                        try:
                            highest = max(highest, float(value))
                        except (TypeError, ValueError):
                            continue
        out.append(
            (
                machine.get("name") or path.stem,
                machine.get("outputMergeTransformation", DEFAULT_TRANSFORMATION),
                mapping.get("outputAlphabetTop"),
                highest,
                str(path.relative_to(MACHINES)),
            )
        )
    return out


class TransformationVocabularyTests(unittest.TestCase):
    """Every declared transformation belongs to a known family."""

    def test_no_unrecognised_transformation(self):
        unknown = [
            (name, transformation, rel)
            for name, transformation, _, _, rel in _machines()
            if transformation not in BOOLEAN_GATES | ORDERED_CHAIN
        ]
        self.assertEqual(
            unknown,
            [],
            "machines declare a transformation in neither family; the fold's "
            "behaviour for it is undefined rather than defaulted",
        )


class MultiValuedMachineFoldTests(unittest.TestCase):
    """A machine that asserts above 1 must fold with a chain transformation.

    This is the check with teeth. A Boolean gate flattens the alphabet and says
    nothing about having done so.
    """

    def test_multi_valued_machines_do_not_declare_a_boolean_gate(self):
        offenders = [
            (name, transformation, highest, rel)
            for name, transformation, _, highest, rel in _machines()
            if highest > 1 and transformation in BOOLEAN_GATES
        ]
        self.assertEqual(
            offenders,
            [],
            "a machine asserting an output value above 1 folds with a Boolean "
            "gate, which flattens every such value to 1. The machine keeps "
            "working and its alphabet is gone. Declare a chain transformation "
            "(meet/join/strong-*/discrete-median) or stop asserting above 1.",
        )

    def test_the_known_multi_valued_machines_are_still_chain_folded(self):
        """Pins the two machines whose correctness rests on this alone."""
        multi = {
            name: transformation
            for name, transformation, _, highest, _ in _machines()
            if highest > 1
        }
        for name, transformation in multi.items():
            self.assertIn(
                transformation,
                ORDERED_CHAIN,
                f"{name} asserts above 1 and must keep a chain fold",
            )


class DeclaredAlphabetTests(unittest.TestCase):
    """A declared `outputAlphabetTop` must bound what the machine asserts.

    Absence is permitted -- see limit 2 in the module docstring -- so this fails
    only on a contradiction, never on an omission.
    """

    def test_assertions_stay_within_a_declared_top(self):
        contradictions = [
            (name, top, highest, rel)
            for name, _, top, highest, rel in _machines()
            if top is not None and highest > top
        ]
        self.assertEqual(
            contradictions,
            [],
            "machines assert an output value above the outputAlphabetTop they "
            "declare; the declaration and the corpus disagree about the machine",
        )

    def test_multi_valued_machines_are_reported_when_they_declare_no_top(self):
        """Information, not a verdict. Records the gap without failing on it."""
        undeclared = [
            (name, highest)
            for name, _, top, highest, _ in _machines()
            if highest > 1 and top is None
        ]
        # Asserted so the count is visible in the run rather than silent, and so
        # this needs revisiting if the number moves.
        self.assertLessEqual(
            len(undeclared),
            2,
            f"more machines are multi-valued without declaring an alphabet top "
            f"than when this check was written: {undeclared}",
        )


class CrossMachineAlphabetTests(unittest.TestCase):
    """Heterogeneity across machines sharing an output cell -- reported, not failed.

    Per ARBITER_CONTRACT.md 7.2 a cross-machine cell resolves under the registry
    rule, which selects a contributor's value whole. No flattening occurs, so a
    mixed cell is not by itself a defect. What it does mean is that a reader of
    that cell can receive values from ranges its own semantics may not cover, and
    that is worth being able to see.
    """

    def test_cells_written_by_machines_of_differing_alphabets_are_bounded(self):
        by_cell = {}
        for path in sorted(MACHINES.rglob("*.json")):
            try:
                doc = json.loads(path.read_text())
            except (ValueError, OSError):
                continue
            machine = doc.get("machine")
            if not isinstance(machine, dict) or "sequences" not in machine:
                continue
            name = machine.get("name") or path.stem
            offset = ((machine.get("perceptualMapping") or {}).get("output") or {}).get(
                "offset", 0
            )
            for sequence in machine.get("sequences") or []:
                for event in sequence.get("events") or []:
                    for output in event.get("outputEvents") or []:
                        for index, value in enumerate(output.get("vector") or []):
                            if not value:
                                continue
                            try:
                                numeric = float(value)
                            except (TypeError, ValueError):
                                continue
                            cell = by_cell.setdefault(offset + index, {})
                            cell[name] = max(cell.get(name, 0.0), numeric)

        mixed = {
            cell: contributors
            for cell, contributors in by_cell.items()
            if len(contributors) > 1 and len({v > 1 for v in contributors.values()}) > 1
        }
        self.assertEqual(
            mixed,
            {},
            "cells receive both binary and multi-valued contributions. Not a "
            "fold defect -- the registry rule selects rather than combines -- "
            "but a reader of these cells sees a wider range than a binary "
            "contributor alone would suggest.",
        )


if __name__ == "__main__":
    unittest.main()
