#!/usr/bin/env python3
"""Contract checks for the arbitration registry.

A position in the universal input event vector is contended when more than one
writer targets it. Something must then decide the resolved value, and
docs/ARBITER_CONTRACT.md requires that decision be declared rather than
defaulted — an undeclared contended cell is a corpus error, not a runtime
default.

Gates:

- every contended cell has a registry entry, counting machine final Reality
  Events and PE-source contributions alike. Deriving contention from machine
  outputs alone misses the dominant case (a deterministic machine determination
  against a generated agent assessment) and understates the population by an
  order of magnitude
- no uncontended cell has an entry — the registry declares resolution, and a
  single-writer cell has nothing to resolve
- writers are counted per MACHINE, not per output event: one machine's several
  mutually exclusive determinations over its own output region are not
  contention
- every entry carries a rationale, so a resolution decision is never inherited
  silently
- every rule is a commutative monoid (ARBITER_CONTRACT.md 4.1), which is what
  permits parallel reduction in any order and what makes four independent
  runtime implementations agree
- a generated provider never outranks a deterministic one unless the entry says
  so explicitly and explains why
- the registry is not stale with respect to the corpus
"""

from __future__ import annotations

import json
import sys
import unittest
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

# Corpus reads go through the shared accessors so both schema spellings
# resolve while RealityEngine_CI#220 layer 1 is in flight.
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from event_keys import output_events, sequence_events  # noqa: E402
MACHINES = REPO_ROOT / "machines"
REGISTRY = REPO_ROOT / "domains" / "arbitration-registry.json"

# Rules admissible under ARBITER_CONTRACT.md 4.2. Each is commutative,
# associative and idempotent; "first" and "last" are not, which is why the
# current merge behaviour is a defect rather than a style choice.
COMMUTATIVE_MONOIDS = {"OR", "AND", "MAX", "MIN", "SEVERITY", "PRECEDENCE", "MEAN"}
WITHIN_RANK_RULES = {"OR", "AND", "MAX", "MIN", "SEVERITY"}

# Determinism ranking (ARBITER_CONTRACT.md 4.3a). A deterministic contribution
# is derivable from the corpus and IS(k) alone; a generated one is not derivable
# from anything. If the irreproducible term wins, IS(k+1) becomes irreproducible
# and so does every determination downstream of it.
DETERMINISM_CLASS = {
    "machine": "deterministic",
    "sensor": "measured", "mqtt": "measured", "healthkit": "measured",
    "stream": "measured", "ui": "measured", "synthetic": "measured",
    "acp": "generated", "mcp": "generated", "localai": "generated",
}
CLASS_RANK = {"deterministic": 3, "measured": 2, "generated": 1}


def load_machines() -> list[tuple[str, dict[str, Any]]]:
    out = []
    for path in sorted(MACHINES.rglob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        machine = doc.get("machine")
        if machine:
            out.append((path.relative_to(MACHINES).as_posix(), machine))
    return out


def derive_writers(machines) -> dict[int, set]:
    """cell -> {(provider, originId)}, deduplicated per writer."""
    writers: dict[int, set] = defaultdict(set)
    for rel, m in machines:
        pm = m.get("perceptualMapping") or {}
        outp = pm.get("output")
        if outp:
            for seq in m.get("sequences") or []:
                for vec in sequence_events(seq):
                    for ov in output_events(vec):
                        n = min(len(ov.get("vector") or []), outp["length"])
                        for k in range(n):
                            writers[outp["offset"] + k].add(("machine", rel))
        proj = (m.get("metadata") or {}).get("openClawProjection") or {}
        region = proj.get("writeBackRegion")
        if region:
            sid = proj.get("projectionId") or rel
            for c in range(region["offset"], region["offset"] + region["length"]):
                writers[c].add(("acp", sid))
    return writers


class ArbitrationRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.machines = load_machines()
        cls.writers = derive_writers(cls.machines)
        cls.contended = {c for c, w in cls.writers.items() if len(w) > 1}
        cls.registry_present = REGISTRY.exists()
        cls.registry: dict[str, Any] = (
            json.loads(REGISTRY.read_text(encoding="utf-8"))
            if cls.registry_present else {"counts": {}, "entries": []})

    def test_registry_exists(self) -> None:
        self.assertTrue(
            self.registry_present,
            "domains/arbitration-registry.json missing — run "
            "scripts/build-arbitration-registry.py --write")

    def test_every_contended_cell_is_declared(self) -> None:
        """The gate. An undeclared contended cell is a corpus error."""
        declared = {e["cell"] for e in self.registry["entries"]}
        missing = sorted(self.contended - declared)
        self.assertEqual(
            [], missing[:20],
            f"{len(missing)} contended cell(s) have no arbitration entry; "
            f"resolution would fall to merge order. First: {missing[:20]}")

    def test_no_uncontended_cell_is_declared(self) -> None:
        declared = {e["cell"] for e in self.registry["entries"]}
        spurious = sorted(declared - self.contended)
        self.assertEqual(
            [], spurious[:20],
            f"{len(spurious)} entr(ies) declare a cell with fewer than two writers; "
            f"a single-writer cell has nothing to resolve. First: {spurious[:20]}")

    def test_entries_match_derived_writers(self) -> None:
        """Guards the per-machine counting rule.

        Counting writers per output event instead of per machine inflates the
        population roughly tenfold, so a mismatch here usually means the
        derivation regressed to event granularity.
        """
        mismatched = []
        for e in self.registry["entries"]:
            declared = {(w["provider"], w["originId"]) for w in e["writers"]}
            if declared != self.writers.get(e["cell"], set()):
                mismatched.append(e["cell"])
        self.assertEqual([], mismatched[:20],
                         f"{len(mismatched)} entr(ies) disagree with the corpus about who "
                         f"writes the cell. First: {mismatched[:20]}")

    def test_rules_are_commutative_monoids(self) -> None:
        bad = [(e["cell"], e["rule"]) for e in self.registry["entries"]
               if e["rule"] not in COMMUTATIVE_MONOIDS]
        self.assertEqual([], bad[:20],
                         "rule must be a commutative monoid so parallel reduction in any "
                         f"order agrees (ARBITER_CONTRACT.md 4.1): {bad[:20]}")

    def test_within_rank_only_on_precedence(self) -> None:
        bad = [e["cell"] for e in self.registry["entries"]
               if "withinRank" in e and e["rule"] != "PRECEDENCE"]
        self.assertEqual([], bad[:20],
                         f"withinRank is a PRECEDENCE tie-break only: {bad[:20]}")
        bad_rule = [(e["cell"], e["withinRank"]) for e in self.registry["entries"]
                    if e.get("withinRank") and e["withinRank"] not in WITHIN_RANK_RULES]
        self.assertEqual([], bad_rule[:20], f"unknown withinRank rule: {bad_rule[:20]}")

    def test_multi_machine_contention_declares_a_within_rank_rule(self) -> None:
        """PRECEDENCE alone would fall back to MAX among the winners.

        Where several machine determinations contend beneath a generated
        assessment, MAX collapses them to one value and discards which asserted.
        Those cells must say how the winning class resolves among itself.
        """
        missing = []
        for e in self.registry["entries"]:
            machines = [w for w in e["writers"] if w["provider"] == "machine"]
            if e["rule"] == "PRECEDENCE" and len(machines) > 1 and not e.get("withinRank"):
                missing.append(e["cell"])
        self.assertEqual([], missing[:20],
                         f"{len(missing)} cell(s) have multiple machine writers under "
                         f"PRECEDENCE with no withinRank rule. First: {missing[:20]}")

    def test_every_entry_has_a_rationale(self) -> None:
        bare = [e["cell"] for e in self.registry["entries"] if not e.get("rationale", "").strip()]
        self.assertEqual([], bare[:20],
                         f"resolution decisions must not be inherited silently: {bare[:20]}")

    def test_generated_never_outranks_deterministic_by_default(self) -> None:
        """A raised generated rank imports irreproducibility deliberately.

        It is permitted, but it must be explicit in the entry and explained,
        never inherited from a default.
        """
        offenders = []
        for e in self.registry["entries"]:
            ranks = e.get("providerRanks") or {}
            for provider, rank in ranks.items():
                cls = DETERMINISM_CLASS.get(provider)
                if cls and rank > CLASS_RANK[cls]:
                    offenders.append((e["cell"], provider, rank, cls))
        for cell, provider, rank, cls in offenders:
            entry = next(e for e in self.registry["entries"] if e["cell"] == cell)
            self.assertIn(
                "irreproducib", entry["rationale"].lower(),
                f"cell {cell} raises {provider} ({cls}) to rank {rank} without saying "
                f"in the rationale that this imports irreproducibility into the lane")

    def test_counts_match_entries(self) -> None:
        counts = self.registry["counts"]
        self.assertEqual(counts["contendedCells"], len(self.registry["entries"]))
        machine_contended = sum(
            1 for e in self.registry["entries"]
            if sum(1 for w in e["writers"] if w["provider"] == "machine") > 1)
        if "machineContendedCells" in counts:
            self.assertEqual(counts["machineContendedCells"], machine_contended)


if __name__ == "__main__":
    unittest.main()
