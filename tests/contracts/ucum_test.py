#!/usr/bin/env python3
"""Contract checks for the UCUM canonicalizer.

The guardrail shapes compare unit codes as strings, so `mg/dL` and `mg.dL-1`
are different codes to SHACL even though UCUM makes them equal. Canonical form
is what closes that gap, and it has to hold two properties at once:

- codes that mean the same unit must collapse to one form, or valid device
  payloads get rejected
- codes that mean *different* units must not collapse, or a guardrail admits a
  value off by a factor. `mg/dL` and `g/L` share a dimension and differ by ten
  thousand; canonicalization is syntactic precisely so it cannot conflate them

Gates:

- the equivalences the boundary actually sees (`/min`, `{beats}/min`, `min-1`)
- non-equivalences that must survive canonicalization
- idempotence, since the projector may run over already-canonical data
- prefix/atom disambiguation: `cd` is candela, not centi-day
- an unknown atom raises rather than passing through
- every atom in the table is its own canonical form
- every unit code in the guardrail fixtures is already canonical, so the
  fixtures cannot drift away from what an adapter would produce
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from ucum import (  # noqa: E402
    ATOMS,
    PREFIXES,
    UcumError,
    canonical,
    equal,
    is_canonical,
)

FIXTURES = REPO_ROOT / "semantics" / "shapes" / "fixtures"
LANE_REGISTRY = FIXTURES / "lane-registry.ttl"


class UcumCanonicalizationTest(unittest.TestCase):
    def test_operator_forms_collapse(self) -> None:
        """Division and negative exponents are the same statement."""
        self.assertEqual(canonical("/min"), "min-1")
        self.assertEqual(canonical("min-1"), "min-1")
        self.assertEqual(canonical("mg/dL"), canonical("mg.dL-1"))
        self.assertEqual(canonical("kg.m/s2"), canonical("kg.m.s-2"))

    def test_annotations_are_dropped(self) -> None:
        """UCUM annotations carry no meaning; display text preserves them."""
        self.assertEqual(canonical("{beats}/min"), "min-1")
        self.assertEqual(canonical("/min"), canonical("{beats}/min"))
        self.assertEqual(canonical("{steps}"), "1")

    def test_term_order_is_stable(self) -> None:
        """Order is alphabetical: the form is a comparison key, not display."""
        self.assertEqual(canonical("mg/dL"), "dL-1.mg")
        self.assertEqual(canonical("dL-1.mg"), "dL-1.mg")

    def test_distinct_units_stay_distinct(self) -> None:
        """Same dimension, different unit. Conflating these admits a value
        off by a factor of ten thousand."""
        self.assertNotEqual(canonical("mg/dL"), canonical("g/L"))
        self.assertNotEqual(canonical("Cel"), canonical("K"))
        self.assertNotEqual(canonical("m"), canonical("mm"))

    def test_unity_and_percent(self) -> None:
        self.assertEqual(canonical("1"), "1")
        self.assertEqual(canonical("%"), "%")
        self.assertNotEqual(canonical("%"), canonical("1"))

    def test_powers_of_ten(self) -> None:
        self.assertEqual(canonical("10*3/uL"), "1000.uL-1")
        self.assertEqual(canonical("10*3/uL"), canonical("10^3.uL-1"))

    def test_parentheses(self) -> None:
        self.assertEqual(canonical("(kg.m)/s2"), "kg.m.s-2")

    def test_pressure_columns(self) -> None:
        """mm[Hg] is the milli prefix on UCUM's metre-of-mercury atom."""
        self.assertEqual(canonical("mm[Hg]"), "mm[Hg]")
        self.assertEqual(canonical("cm[H2O]"), "cm[H2O]")

    def test_idempotence(self) -> None:
        """The projector may run over data it has already canonicalized."""
        for code in ("/min", "{beats}/min", "mg/dL", "10*3/uL", "(kg.m)/s2",
                     "%", "1", "Cel", "mm[Hg]", "mol/L"):
            once = canonical(code)
            self.assertEqual(canonical(once), once, code)
            self.assertTrue(is_canonical(once), once)

    def test_prefix_atom_disambiguation(self) -> None:
        """Exact atoms match before prefix+atom, which is why cd is candela."""
        for atom in ("cd", "mol", "min", "Pa", "mo", "eq"):
            self.assertEqual(canonical(atom), atom)

    def test_prefixes_apply_to_metric_atoms(self) -> None:
        self.assertEqual(canonical("mg"), "mg")
        self.assertEqual(canonical("dam"), "dam")
        self.assertEqual(canonical("kPa"), "kPa")

    def test_prefixes_do_not_apply_to_non_metric_atoms(self) -> None:
        """A prefixed non-metric atom is not a unit; refusing it is the point."""
        with self.assertRaises(UcumError):
            canonical("mmin")

    def test_unknown_atom_raises(self) -> None:
        """Silent acceptance of an unknown unit is the failure this prevents."""
        for code in ("furlong", "bpm", "beats/min"):
            with self.assertRaises(UcumError, msg=code):
                canonical(code)

    def test_malformed_raises(self) -> None:
        for code in ("mg//dL", "{unterminated", "", "   ", "mg.[dL"):
            with self.assertRaises(UcumError, msg=repr(code)):
                canonical(code)

    def test_equal_helper(self) -> None:
        self.assertTrue(equal("mg/dL", "mg.dL-1"))
        self.assertTrue(equal("/min", "{beats}/min"))
        self.assertFalse(equal("mg/dL", "g/L"))

    def test_every_atom_is_its_own_canonical_form(self) -> None:
        """A table entry that does not round-trip would make canonical output
        non-idempotent and comparison unsound."""
        for atom in ATOMS:
            self.assertEqual(canonical(atom), atom, atom)

    def test_prefix_table_is_unambiguous(self) -> None:
        """Two-character prefixes must not shadow one-character ones in a way
        that changes which atom a token resolves to."""
        for prefix in PREFIXES:
            self.assertTrue(1 <= len(prefix) <= 2, prefix)


class FixtureUnitCodesTest(unittest.TestCase):
    """Unit codes in the guardrail fixtures must already be canonical.

    An adapter canonicalizes on the way in, so every code in a boundary graph
    is canonical by construction. If the fixtures drift from that they stop
    representing what a runtime will actually be handed.
    """

    # Always UCUM by definition.
    UCUM_PATTERN = re.compile(
        r'reg:(?:canonicalUcum|expectedUcum|acceptedUcum|bridgesToUcum)\s+'
        r'((?:"[^"]*"\s*,\s*)*"[^"]*")'
    )
    # UCUM only when the enclosing unit declares the UCUM system; an OM-native
    # unit carries a code in OM's system and a separate reg:bridgesToUcum.
    UNIT_CODE_PATTERN = re.compile(r'reg:unitCode\s+"([^"]*)"')
    UCUM_SYSTEM = "http://unitsofmeasure.org"

    def _codes(self) -> list[str]:
        text = LANE_REGISTRY.read_text()
        codes: list[str] = []
        for match in self.UCUM_PATTERN.finditer(text):
            codes.extend(re.findall(r'"([^"]*)"', match.group(1)))
        for block in re.split(r"\n\s*\n", text):
            if self.UCUM_SYSTEM in block:
                codes.extend(self.UNIT_CODE_PATTERN.findall(block))
        return codes

    def test_lane_registry_codes_are_canonical(self) -> None:
        codes = self._codes()
        self.assertGreater(len(codes), 0, "no unit codes found in the fixture")
        for code in codes:
            with self.subTest(code=code):
                self.assertEqual(
                    canonical(code), code,
                    f"{code!r} is not canonical; adapters emit {canonical(code)!r}",
                )

    def test_fixture_exercises_a_bridged_non_ucum_unit(self) -> None:
        """The OM path must stay covered: a unit in a foreign system whose
        bridge is what makes it admissible."""
        text = LANE_REGISTRY.read_text()
        self.assertIn("reg:bridgesToUcum", text)
        self.assertIn("om-2", text)


if __name__ == "__main__":
    unittest.main()
