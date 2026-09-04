#!/usr/bin/env python3
"""Contract checks for the intra-machine output fold (RealityEngine_CI docs/FOLD_PLACEMENT.md).

The Reality Engine is moving the output fold into the machine's atomic step, so
a machine contributes ONE value per output cell instead of one per completed
Reality Event. That move is sound only under a construction constraint the doc
states as constraint A:

    "The constructor assigns two CESs the same output position only when that
     position is identical across every possible fold configuration."

Nothing enforces it. It is a guarantee about the *constructors*, so a machine
that breaks it is discovered as a cross-runtime divergence rather than rejected
at internment. FallDetection is the incident: its seven sequences assert
0/1/2/3/4/4/0 on output index 0, and at the sweep failure the arbiter resolved
2.0 on C++ and LSP and 0.0 on Scala — neither the maximum nor the minimum,
because only a subset fires on any step and each runtime picks differently among
same-machine contributions.

WHAT THESE CHECKS ESTABLISH, and what they deliberately do not:

The constraint has two readings and they converge on the same formal condition.
Read "fold configuration" as the firing subset, and invariance across singleton
subsets forces every contributor at a position to assert the same value. Read it
as the choice of transformation, and `or` (=join) disagrees with `and` (=meet)
the moment two contributors differ. Either way the checkable condition is:

    at a shared output position, all contributors assert the same value,
    OR the machine declares a fold that selects one of them.

FoldConfigurationInvarianceTests derives that by exhaustion rather than
asserting it. SharedOutputPositionTests applies it to the corpus.

THE HONEST LIMIT, stated here because an unenforceable guarantee that looks
enforced is worse than a documented gap. 1326 of 1328 machines emit only {0,1},
so every non-zero contributor asserts 1 and value-agreement holds because the
alphabet cannot express disagreement. The corpus does not corroborate constraint
A; it is silent on it. The gate's discriminating power today is confined to the
two multi-valued machines and to whatever is added next -- which is the point of
landing it before the fold moves, not after.
"""

from __future__ import annotations

import itertools
import json
import sys
import unittest
from collections import defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
MACHINES = REPO_ROOT / "machines"
SCHEMA = REPO_ROOT / "schemas" / "machine.schema.json"

# Folds that return one of their contributors (re:returnsAContributor true in
# semantics/ontology/re-core.ttl, executed there by OutputMergeTransformationTests).
# A machine whose shared positions disagree is well defined under exactly these.
SELECTION_FOLDS = frozenset({"meet", "join", "discrete-median"})

# The severity chain the arbiter ranks on: GREEN/absent 0 < AMBER 1 < RED 2 <
# lifeSafety 3 (resolve_cell, reality.cpp).
SEVERITY_RANK = {None: 0, "GREEN": 0, "AMBER": 1, "RED": 2}
LIFE_SAFETY_RANK = 3


def severity_rank(rag_status_code: str | None, life_safety: bool = False) -> int:
    if life_safety:
        return LIFE_SAFETY_RANK
    return SEVERITY_RANK[rag_status_code]


def load_corpus() -> list[tuple[Path, dict[str, Any]]]:
    corpus = []
    for path in sorted(MACHINES.rglob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        machine = document.get("machine", document)
        if isinstance(machine, dict):
            corpus.append((path, machine))
    return corpus


def output_vectors(machine: dict[str, Any]):
    """(sequenceId, outputVector) for every potential output the machine holds."""
    for sequence in machine.get("sequences") or []:
        for vector in (sequence.get("events") or []):
            for output in (vector.get("outputEvents") or []):
                yield sequence.get("id"), output


def shared_positions(machine: dict[str, Any]) -> dict[int, dict[str, set[int]]]:
    """Output indices where two or more CESs assert a non-zero value.

    Non-zero is the operative notion of contention. Every output vector spans
    the machine's whole output region (pinned below), so on a positional reading
    every sequence "asserts" at every index and the question would be vacuous.
    This is the definition behind the doc's measured 215.
    """
    per_index: dict[int, dict[str, set[int]]] = defaultdict(lambda: defaultdict(set))
    for sequence_id, output in output_vectors(machine):
        for index, value in enumerate(output.get("vector") or []):
            if value:
                per_index[index][sequence_id].add(value)
    return {i: contributors for i, contributors in per_index.items()
            if len(contributors) > 1}


def output_alphabet(machine: dict[str, Any]) -> set[int]:
    return {value for _, output in output_vectors(machine)
            for value in (output.get("vector") or [])}


class SharedOutputPositionTests(unittest.TestCase):
    """Constraint A applied to the corpus."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.corpus = load_corpus()

    def test_output_vectors_span_exactly_the_declared_output_region(self) -> None:
        """"Same output position" has to denote the same universal cell.

        The output region is machine-level, so two CESs sharing index i share
        the cell at offset+i only if both vectors are laid over the same region.
        A short or long vector would make index i mean different cells for
        different sequences and every check below would be comparing nothing.
        Trivially true today -- 0 exceptions -- and worth pinning because it is
        the premise the rest of this file rests on rather than a result.
        """
        bad = []
        for path, machine in self.corpus:
            region = (machine.get("perceptualMapping") or {}).get("output")
            if not isinstance(region, dict):
                bad.append(f"{path.name}: no perceptualMapping.output region")
                continue
            length = region.get("length")
            for sequence_id, output in output_vectors(machine):
                actual = len(output.get("vector") or [])
                if actual != length:
                    bad.append(
                        f"{path.name}:{sequence_id}:{output.get('id')} spans "
                        f"{actual} cells, output region declares {length}")
        self.assertEqual(bad, [], "output vectors do not span the declared region:\n"
                                  + "\n".join(bad[:10]))

    def test_shared_positions_are_value_agreed_or_declare_a_selection_fold(self) -> None:
        """The gate. A machine whose CESs share an output position must either
        agree on the value there, or declare a fold that selects a contributor.

        Agreement makes the position identical under every reading of "fold
        configuration" -- every firing subset and every selection transformation
        return the same value. Disagreement makes the folded value depend on
        which subset fired, which is legitimate composition (a severity ladder)
        but only once the machine says how to collapse it. Left to the default
        `or`, a ladder folds to 1: the rung is gone, the value is outside the
        machine's own alphabet, and nothing at the point of use can tell.

        FROZEN, not allowlisted. Both directions fail: a new violator fails as
        NEW, and fixing one fails as STALE so the baseline shrinks deliberately.

        The baseline is now EMPTY, and it shrank the way it was meant to. Both
        original violators were the multi-valued Fall machines, and both were
        remediated by declaring `"outputMergeTransformation": "join"` -- the
        safety-preserving reading for a severity ladder, since join returns the
        highest rung any contributor asserted and cannot hide a confirmed fall
        behind a concurrent nominal reading. The gate caught the fix as STALE
        and this baseline was emptied deliberately in response, which is the
        behaviour it exists to force.
        """
        known_violators: set[str] = set()
        violators = {}
        for path, machine in self.corpus:
            shared = shared_positions(machine)
            if not shared:
                continue
            declared = machine.get("outputMergeTransformation")
            if declared in SELECTION_FOLDS:
                continue
            disagreed = sorted(
                (index, sorted(set().union(*contributors.values())))
                for index, contributors in shared.items()
                if len(set().union(*contributors.values())) > 1
            )
            if disagreed:
                violators[str(path.relative_to(REPO_ROOT))] = (declared, disagreed)

        new = sorted(set(violators) - known_violators)
        stale = sorted(known_violators - set(violators))
        message = []
        if new:
            message.append(
                "NEW machines whose CESs disagree at a shared output position with no "
                "selection fold declared -- the folded value depends on which subset "
                "fired, which is the FallDetection divergence: "
                + "; ".join(f"{name} (fold={violators[name][0]}, "
                            f"positions={violators[name][1][:3]})" for name in new))
        if stale:
            message.append(
                "STALE: these no longer violate constraint A; remove them from "
                f"known_violators: {stale}")
        self.assertEqual((new, stale), ([], []), " | ".join(message))

    def test_multi_valued_machines_are_exactly_the_segregated_pair(self) -> None:
        """Value-agreement is vacuous wherever the alphabet is {0,1}.

        This is the check that keeps the gate above from being read as evidence
        the constructors upheld constraint A. They may have; the corpus cannot
        say. 1326 machines emit only {0,1}, so their non-zero contributors all
        assert 1 and agreement is forced by the alphabet rather than by
        construction. The two machines whose alphabet can express disagreement
        both do disagree -- 2 for 2 -- which is why they are already segregated
        out of the binary parity sweep.
        """
        multi_valued = sorted(
            str(path.relative_to(REPO_ROOT)) for path, machine in self.corpus
            if max(output_alphabet(machine) or {0}) > 1)
        self.assertEqual(multi_valued, [
            "machines/domains/health-personal/FallDetection.json",
            "machines/domains/health-personal/FallSensorMotionPreaggregator.json",
        ], "the multi-valued set has changed; constraint A has real force on these "
           "machines and none on the binary rest, so this set is what the gate above "
           "actually measures")

        binary = [path.name for path, machine in self.corpus
                  if max(output_alphabet(machine) or {0}) <= 1]
        self.assertEqual(len(binary), 1326)
        for path, machine in self.corpus:
            if max(output_alphabet(machine) or {0}) <= 1:
                for index, contributors in shared_positions(machine).items():
                    self.assertEqual(
                        set().union(*contributors.values()), {1},
                        f"{path.name} index {index}: a binary machine's non-zero "
                        f"contributors must all assert 1")

    def test_latent_multi_valued_surface_is_frozen(self) -> None:
        """Machines one value-edit away from violating constraint A silently.

        Segregation is by *observed* values, so it cannot see a machine that is
        permitted to go multi-valued and has not yet. 55 machines declare
        bitsPerElement > 1; 9 of those are still binary AND already have shared
        CES output positions. Raise any cell in those 9 above 1 and the machine
        starts disagreeing at a position two sequences share -- while remaining
        in the binary parity sweep, because the segregation criterion never
        re-runs. That is the gap this file exists to close, and it is the one
        thing here that the existing segregation does not already account for.

        Frozen so the set is reviewed when it grows, not so it may not grow.
        """
        latent = sorted(
            path.name for path, machine in self.corpus
            if isinstance((machine.get("perceptualMapping") or {}).get("bitsPerElement"), int)
            and (machine["perceptualMapping"]["bitsPerElement"]) > 1
            and max(output_alphabet(machine) or {0}) <= 1
            and shared_positions(machine))
        self.assertEqual(latent, [
            "AICapacityThrottler.json", "AICoolingRegulator.json",
            "AIHardwareResilience.json", "AIModelWellness.json",
            "AIPowerEfficiency.json", "AISecurityMonitor.json",
            "AIWellnessCoach.json", "NewPatientInflow.json", "PatientWellness.json",
        ], "the latent multi-valued surface changed: these machines have shared CES "
           "output positions and headroom above {0,1}, so a value edit makes them "
           "constraint-A violators without tripping the multi-valued segregation")

    def test_no_machine_declares_a_fold_that_could_fabricate_a_value(self) -> None:
        """A machine with shared positions may not declare a fabricating fold.

        The Lukasiewicz pair can return a value no contributor asserted -- on an
        ordinal severity ladder, a rung the machine invented. "Identical across
        every possible fold configuration" cannot hold for a position whose
        folded value is not any contributor's, so a machine with shared outputs
        is restricted to the selection folds.

        NO LONGER VACUOUS. This check was written when no corpus machine
        declared any transformation, with a tripwire on the first declaration so
        the vacuity note could not quietly become false. The tripwire fired:
        FallDetection and FallSensorMotionPreaggregator now declare `join`,
        remediating the constraint-A violation they carried as severity ladders
        folded by the default `or`. The check has content from that point on.

        The declaring set is asserted rather than merely counted, so a machine
        that starts declaring a fold has to be looked at here — the substantive
        arm above only rejects a *fabricating* fold, and a machine acquiring any
        transformation is a semantic change worth a second pair of eyes.
        """
        fabricating = {"strong-disjunction", "strong-conjunction"}
        enum = set(json.loads(SCHEMA.read_text(encoding="utf-8"))
                   ["$defs"]["machine"]["properties"]["outputMergeTransformation"]["enum"])
        self.assertTrue(fabricating <= enum,
                        "the schema no longer offers the transformations this check guards")

        # The substantive arm first, so a real violation is reported as itself
        # rather than masked by the vacuity note below.
        bad = [path.name for path, machine in self.corpus
               if machine.get("outputMergeTransformation") in fabricating
               and shared_positions(machine)]
        self.assertEqual(bad, [],
                         "machines with shared output positions declaring a fold that can "
                         f"return a value no contributor asserted: {bad}")

        declared = sorted((path.name, machine["outputMergeTransformation"])
                          for path, machine in self.corpus
                          if machine.get("outputMergeTransformation") is not None)
        self.assertEqual(
            declared,
            [("FallDetection.json", "join"),
             ("FallSensorMotionPreaggregator.json", "join")],
            "the set of machines declaring an output merge transformation changed. "
            "Every declaration is a semantic decision about how a machine collapses "
            "concurrent completions, so it is pinned here rather than counted: "
            "confirm the new declaration is intended and that a machine with shared "
            "output positions has not taken a fabricating fold, then update this list")


class FoldConfigurationInvarianceTests(unittest.TestCase):
    """Why value-agreement is the checkable form of constraint A, by exhaustion.

    The gate above encodes a condition. These derive it, so the condition cannot
    quietly drift from the claim it is supposed to enforce.
    """

    CHAIN_TOP = 3
    MAX_N = 4

    FOLDS = {
        "meet":            lambda x: min(x),
        "join":            lambda x: max(x),
        "discrete-median": lambda x: sorted(x)[(len(x) - 1) // 2],
        "or":              lambda x: int(any(x)),
        "and":             lambda x: int(all(x)),
    }

    def _subsets(self, values):
        for size in range(1, len(values) + 1):
            for combo in itertools.combinations(values, size):
                yield list(combo)

    def test_agreement_makes_a_position_invariant_under_subset_and_transformation(self) -> None:
        """If contributors agree on v, every non-empty firing subset folds to v
        under every selection transformation. This is the positive half."""
        for value in range(self.CHAIN_TOP + 1):
            for n in range(1, self.MAX_N + 1):
                results = {self.FOLDS[name](subset)
                           for name in SELECTION_FOLDS
                           for subset in self._subsets([value] * n)}
                self.assertEqual(
                    results, {value},
                    f"{n} contributors all asserting {value} folded to {results}; "
                    f"agreement is supposed to make the position configuration-invariant")

    def test_disagreement_forces_a_fold_to_vary_or_to_fabricate(self) -> None:
        """The negative half, and the sharp form of it.

        The tempting claim -- that no fold is subset-invariant on a disagreeing
        position -- is FALSE, and this check was written asserting it and failed.
        `or` folds every non-empty subset of [1,2] to 1: perfectly invariant. It
        buys that invariance by returning a value neither contributor asserted,
        which on FallDetection's ladder is the rung being erased.

        So the true dichotomy is: on a disagreeing position every fold either
        varies across firing subsets (non-determinate, the arbiter divergence)
        or returns a non-contributor (determinate but lossy, the flattened
        ladder). Never neither. That is what makes agreement necessary for a
        position to be "identical across every possible fold configuration"
        without loss, and why the gate demands agreement OR an explicit
        selection fold rather than accepting any declaration at all.
        """
        for name, fold in self.FOLDS.items():
            for values in ([0, 1], [1, 2], [0, 4], [2, 3], [1, 2, 3]):
                subsets = list(self._subsets(values))
                invariant = len({fold(s) for s in subsets}) == 1
                selects = all(fold(s) in s for s in subsets)
                self.assertFalse(
                    invariant and selects,
                    f"{name} is both subset-invariant and contributor-selecting on the "
                    f"disagreeing position {values}; agreement would then not be "
                    f"necessary for configuration-invariance and the gate is too strict")

        # The two escape routes, named on a concrete case so a change to either
        # arm is legible rather than showing up as a flipped boolean.
        self.assertEqual({self.FOLDS["meet"](s) for s in self._subsets([1, 2])}, {1, 2},
                         "meet no longer varies with the firing subset on [1,2]")
        self.assertEqual({self.FOLDS["or"](s) for s in self._subsets([1, 2])}, {1},
                         "or no longer collapses [1,2] to a single value")
        self.assertNotIn(self.FOLDS["or"]([2]), [2],
                         "or no longer fabricates on a lone multi-valued contributor")

    def test_the_default_or_selects_a_contributor_exactly_on_binary_alphabets(self) -> None:
        """Why 1326 machines need no declaration and 2 do.

        `or` is join restricted to {0,1}: on a binary alphabet it returns a
        contributor and preserves the alphabet, so the default is safe. One rung
        higher it returns 1 for inputs of 2, 3, 4 -- a value nobody asserted and,
        for FallDetection, outside its own {0,1,2,3,4}. The default is not
        neutral for a multi-valued machine; it is lossy.
        """
        for n in range(1, self.MAX_N + 1):
            for combo in itertools.product((0, 1), repeat=n):
                self.assertEqual(self.FOLDS["or"](list(combo)),
                                 self.FOLDS["join"](list(combo)),
                                 f"or and join diverge on the binary vector {combo}")

        ladder = [0, 1, 2, 3, 4]
        self.assertEqual(self.FOLDS["or"](ladder), 1)
        self.assertNotIn(self.FOLDS["or"]([2, 3]), [2, 3],
                         "or no longer fabricates on a multi-valued position; the reason "
                         "the two ladder machines need an explicit fold has changed")
        self.assertEqual(self.FOLDS["join"](ladder), 4,
                         "join must return the ladder's top rung, which is what a "
                         "severity ladder means by folding")


class SeverityJoinTests(unittest.TestCase):
    """Governance for a folded contribution: the join over contributors' ranks.

    A folded contribution has no single sequenceId, but the 270 severity-ranked
    cells need one ragStatusCode. FOLD_PLACEMENT.md resolves this as the join
    over the severity ranks of the contributing sequences' matched rules. The
    join is well defined for the same reasons the fold is -- max over a finite
    chain -- and these checks execute that rather than restate it.

    135 of 1328 machines have an outputMatches pattern mapping to more than one
    RAG code. That is NOT a violation and nothing here fails on it: governance
    is resolved per contributing sequence, so the sequenceId filter disambiguates
    before the join ever runs. The invariant worth pinning is that the filter is
    sufficient, which is checked directly below.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.corpus = load_corpus()

    def test_corpus_governance_codes_lie_in_the_ranked_chain(self) -> None:
        """The join is max over a chain, so an unranked code has no rank and the
        join silently has no answer. This is what makes it total in fact."""
        codes: set[str | None] = set()
        for _, machine in self.corpus:
            for _, output in output_vectors(machine):
                codes.add((output.get("metadata") or {}).get("ragStatusCode"))
            for rule in ((machine.get("metadata") or {}).get("triggerConfig")
                         or {}).get("rules") or []:
                codes.add(rule.get("ragStatusCode"))
        self.assertEqual(codes, {None, "GREEN", "AMBER", "RED"},
                         "a governance code outside the ranked chain would make the join "
                         "over contributors undefined")
        for code in codes:
            self.assertIsInstance(severity_rank(code), int)

    def test_the_join_is_symmetric_closed_and_returns_a_contributor(self) -> None:
        """The three properties the fold contract demands of it, executed.

        Safety-preservation is the one that matters: a RED-governed firing must
        not be hidden by a GREEN one folded beside it, which is precisely what
        SEVERITY arbitration existed to guarantee.
        """
        ranks = [0, 1, 2, 3]
        for n in range(1, 5):
            for combo in itertools.product(ranks, repeat=n):
                joined = max(combo)
                self.assertEqual({max(p) for p in itertools.permutations(combo)}, {joined},
                                 f"the join is order dependent on {combo}")
                self.assertIn(joined, combo, f"the join fabricated a rank on {combo}")
                self.assertGreaterEqual(joined, max(combo),
                                        f"a higher-severity contributor was hidden on {combo}")
        self.assertEqual(severity_rank("GREEN", life_safety=True), LIFE_SAFETY_RANK,
                         "lifeSafety must outrank every RAG code, including GREEN")
        self.assertGreater(severity_rank(None, life_safety=True), severity_rank("RED"),
                           "a life-safety firing must outrank RED")

    def test_the_tie_break_key_is_total_within_every_machine(self) -> None:
        """Ties go to the lexicographically smallest sequenceId, so that key has
        to be unique among a machine's contributors or the choice is not
        deterministic and the runtimes may differ on it -- reintroducing exactly
        the divergence the fold move exists to remove."""
        bad = []
        for path, machine in self.corpus:
            ids = [sequence.get("id") for sequence in machine.get("sequences") or []]
            if len(ids) != len(set(ids)):
                bad.append(f"{path.name}: duplicate sequence ids {sorted(ids)}")
            for sequence_id in ids:
                self.assertIsInstance(sequence_id, str,
                                      f"{path.name}: a sequence id is not a string, so the "
                                      f"lexicographic tie-break has no order to use")
        self.assertEqual(bad, [], "sequence ids must be unique within a machine:\n"
                                  + "\n".join(bad[:10]))

    def test_ambiguous_output_patterns_are_resolved_by_the_sequence_filter(self) -> None:
        """The 135, pinned as safe rather than failed on.

        An outputMatches pattern mapping to several RAG codes is ambiguous only
        if you match on the folded values alone. Governance is resolved per
        contributing sequence against that sequence's own asserted values, so
        the ambiguity has to survive the sequenceId filter to matter. It does
        not, anywhere: every ambiguous pattern spans two or more distinct
        sequences. That is what makes the filter load-bearing and sufficient.

        The residual case -- one sequence, one pattern, two RAG codes -- is a
        genuine contradiction and is already gated by
        owl_semantics_test.test_no_rule_pair_contradicts_itself.
        """
        ambiguous_machines = 0
        survivors = []
        for path, machine in self.corpus:
            rules = ((machine.get("metadata") or {}).get("triggerConfig")
                     or {}).get("rules") or []
            by_pattern: dict[tuple, list] = defaultdict(list)
            for rule in rules:
                by_pattern[tuple(rule.get("outputMatches") or [])].append(rule)
            ambiguous = {pattern: group for pattern, group in by_pattern.items()
                         if len({r.get("ragStatusCode") for r in group}) > 1}
            if not ambiguous:
                continue
            ambiguous_machines += 1
            for pattern, group in ambiguous.items():
                per_sequence: dict[str, set] = defaultdict(set)
                for rule in group:
                    per_sequence[rule.get("sequenceId")].add(rule.get("ragStatusCode"))
                for sequence_id, codes in per_sequence.items():
                    if len(codes) > 1:
                        survivors.append(
                            f"{path.name}: {sequence_id} {list(pattern)} -> {sorted(codes)}")
        self.assertEqual(ambiguous_machines, 135,
                         "the ambiguous-pattern population moved; the claim that the "
                         "sequenceId filter is doing real work is measured on it")
        self.assertEqual(survivors, [],
                         "an outputMatches ambiguity survived the sequenceId filter, so "
                         "governance for a folded contribution is undecidable there:\n"
                         + "\n".join(survivors[:10]))

    def test_every_trigger_rule_names_a_sequence_that_exists(self) -> None:
        """The filter can only disambiguate if its key resolves. A rule naming a
        sequence the machine does not have contributes governance that no firing
        can ever claim, and would be silently dropped from the join."""
        bad = []
        for path, machine in self.corpus:
            ids = {sequence.get("id") for sequence in machine.get("sequences") or []}
            for rule in ((machine.get("metadata") or {}).get("triggerConfig")
                         or {}).get("rules") or []:
                if rule.get("sequenceId") not in ids:
                    bad.append(f"{path.name}: rule names unknown sequence "
                               f"{rule.get('sequenceId')!r}")
        self.assertEqual(bad, [], "dangling trigger-rule sequence references:\n"
                                  + "\n".join(bad[:10]))


if __name__ == "__main__":
    unittest.main()
