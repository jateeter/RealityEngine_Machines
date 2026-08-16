#!/usr/bin/env python3
"""Name uniqueness, at the three scopes the corpus declares (#68).

The policy is scope-relative, not "everything is unique everywhere":

    a) every CES name is unique within its encapsulating machine
    b) every machine is unique within its encapsulating domain
    c) every domain is unique within its encapsulating universe

Names were chosen as the identity mechanism for the MVP release. UUIDs would be
the sturdier choice and are the intended direction; until then these tests are
what stops the corpus drifting out of a property the runtime and the semantics
layer both depend on.

Why each scope matters concretely:

(a) is the one that breaks a graph. `generate-owl.py` mints `m:seq-<id>` and
    `m:step-<id>` per machine, so two sequences sharing an id inside one machine
    collapse onto one individual which then carries contradictory assertions.
    That is exactly the failure #65 fixed for trigger rules — HermiT rejected the
    merged graph, ELK passed it silently. Across machines the same id is fine and
    is used: `rs-set-sequence` appears in three flip-flop machines, and their
    IRIs differ because the namespace carries the machine.

(b) is asserted here at the scope the policy states. Note the corpus is in fact
    globally unique and must stay so for a reason outside this policy: every
    engine's `GET /api/machines/json/:name` accepts a bare basename and falls
    back to a recursive search, so two domains holding the same filename makes
    that endpoint ambiguous. Both are checked — the domain-scoped rule because it
    is the declared policy, the global one because the runtime depends on it.

(c) domain ids cannot collide, being object keys in the manifest. Code prefixes
    can, and nothing checked them: two domains claiming `HSPH` would make machine
    codes ambiguous across the corpus with no error anywhere.
"""

from __future__ import annotations

import json
import unittest
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOMAINS_DIR = REPO_ROOT / "machines" / "domains"
MANIFEST = REPO_ROOT / "domains" / "domain-manifest.json"


def machine_files() -> list[Path]:
    return sorted(DOMAINS_DIR.glob("*/*.json"))


def load(path: Path) -> dict:
    document = json.loads(path.read_text(encoding="utf-8"))
    return document.get("machine", document)


class NameUniquenessTest(unittest.TestCase):
    """One test per scope, so a failure names the scope that broke."""

    def test_a_ces_names_are_unique_within_their_machine(self) -> None:
        violations = []
        for path in machine_files():
            machine = load(path)
            sequences = machine.get("sequences") or []
            for key in ("id", "name"):
                counts = Counter(
                    str(sequence[key]) for sequence in sequences if sequence.get(key)
                )
                for value, count in sorted(counts.items()):
                    if count > 1:
                        violations.append(f"{path.name}: {count}x sequence {key}={value!r}")
        self.assertEqual(
            violations, [],
            "CES names must be unique within a machine:\n" + "\n".join(violations),
        )

    def test_b_machines_are_unique_within_their_domain(self) -> None:
        by_domain: dict[str, Counter] = defaultdict(Counter)
        names_by_domain: dict[str, Counter] = defaultdict(Counter)
        for path in machine_files():
            domain = path.parent.name
            by_domain[domain][path.stem] += 1
            name = load(path).get("name")
            if name:
                names_by_domain[domain][str(name)] += 1

        violations = []
        for domain, counts in sorted(by_domain.items()):
            violations += [f"{domain}: {n}x file stem {v!r}"
                           for v, n in sorted(counts.items()) if n > 1]
        for domain, counts in sorted(names_by_domain.items()):
            violations += [f"{domain}: {n}x machine.name {v!r}"
                           for v, n in sorted(counts.items()) if n > 1]
        self.assertEqual(
            violations, [],
            "machines must be unique within a domain:\n" + "\n".join(violations),
        )

    def test_b_machine_file_stems_are_also_globally_unique(self) -> None:
        """Stronger than the declared policy, and required by the runtime.

        `GET /api/machines/json/:name` resolves a bare basename with a recursive
        fallback search, so a stem repeated across two domains makes the endpoint
        ambiguous — it would return whichever the walk reached first. Asserted
        here as well as in tests/integration/machine-json-listing.spec.ts so it
        fails without a live engine.
        """
        stems = Counter(path.stem for path in machine_files())
        collisions = {stem: count for stem, count in stems.items() if count > 1}
        self.assertEqual(
            collisions, {},
            "machine file stems must be globally unique: " + repr(collisions),
        )

    def test_c_domains_are_unique_within_the_universe(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        domains = manifest.get("domains") or manifest

        # Domain ids are manifest object keys, so JSON parsing already collapses
        # a duplicate rather than reporting it. Compare against the directories
        # instead, which is where a genuine second declaration would show up.
        declared = set(domains)
        on_disk = {path.name for path in DOMAINS_DIR.iterdir()
                   if path.is_dir() and not path.name.startswith(".")}
        self.assertEqual(
            on_disk - declared, set(),
            "domain directories with no manifest entry",
        )

        prefixes: dict[str, list[str]] = defaultdict(list)
        for domain, entry in domains.items():
            for prefix in entry.get("codePrefixes") or []:
                prefixes[str(prefix)].append(domain)
        shared = {prefix: owners for prefix, owners in prefixes.items()
                  if len(owners) > 1}
        self.assertEqual(
            shared, {},
            "code prefixes must belong to exactly one domain; a shared prefix "
            "makes machine codes ambiguous across the corpus: " + repr(shared),
        )


if __name__ == "__main__":
    unittest.main()
