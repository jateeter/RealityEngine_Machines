#!/usr/bin/env python3
"""UCUM canonicalizer.

The guardrail shapes in semantics/shapes/re-guardrails.shacl.ttl compare unit
codes as strings: SHACL cannot parse UCUM, so `mg/dL` and `mg.dL-1` are
different codes there even though UCUM makes them equal, as are `/min` and
`min-1`, and `{beats}/min` and `/min`. Codes must therefore already be in one
canonical form by the time they reach a boundary graph.

This module produces that form. It belongs in the lane projector and in the
adapter SDK — never in the guardrail, and never in a PE push cycle.

Scope, deliberately narrow
--------------------------

Canonicalization here is **syntactic**. It normalizes operator form, exponent
form, term order and annotations, and it validates that every atom exists. It
does NOT reduce units to a base-unit magnitude, because that would conflate
units that must stay distinct: `mg/dL` and `g/L` share a dimension but differ
by a factor of ten thousand, and an axis contract that accepts one must not
silently accept the other. Dimensional reasoning is QUDT's job, through
reg:quantityKind — see docs/SEMANTIC_GUARDRAIL_CONTRACT.md.

Canonical form
--------------

    factor? term ( '.' term )*        terms sorted by unit code
    term := unit exponent?            exponent omitted when 1, negatives as -n

No '/' ever appears in output; division becomes a negative exponent.
Annotations are dropped — UCUM treats them as semantically empty, and the
human-readable text is preserved separately in the unit object's `display`
field, so nothing is lost. Unity is `1`.

    /min          -> min-1
    min-1         -> min-1
    {beats}/min   -> min-1
    mg/dL         -> dL-1.mg
    mg.dL-1       -> dL-1.mg
    10*3/uL       -> 1000.uL-1

Term order is alphabetical rather than the conventional numerator-first
reading order. The canonical form is a comparison key, not a display value.

The atom table is a curated subset, not all of UCUM. An unrecognised atom
raises UcumError rather than passing through: silent acceptance of an unknown
unit is the failure this module exists to prevent. Extend ATOMS when the
corpus needs a unit, and add a case to tests/contracts/ucum_test.py.

Usage
-----

    from ucum import canonical, equal, UcumError
    canonical("{beats}/min")      # 'min-1'
    equal("mg/dL", "mg.dL-1")     # True

    python3 scripts/ucum.py "mg/dL" "/min"     # canonicalize codes
    python3 scripts/ucum.py --atoms            # list the known atoms
    python3 scripts/ucum.py --scan FILE.json   # report non-canonical codes
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

__all__ = ["canonical", "equal", "is_canonical", "validate", "UcumError"]


class UcumError(ValueError):
    """A UCUM expression is malformed or uses an atom outside the table."""


# ── Prefixes ─────────────────────────────────────────────────────────────
# Metric prefixes, applicable only to metric atoms (a UCUM rule, and the
# reason `cd` is candela rather than centi-day: exact atoms match first).

PREFIXES: dict[str, int] = {
    "Y": 24, "Z": 21, "E": 18, "P": 15, "T": 12, "G": 9, "M": 6, "k": 3,
    "h": 2, "da": 1, "d": -1, "c": -2, "m": -3, "u": -6, "n": -9, "p": -12,
    "f": -15, "a": -18, "z": -21, "y": -24,
}

# ── Atoms ────────────────────────────────────────────────────────────────
# code -> (is_metric, description). is_metric governs whether a prefix may be
# attached. Curated subset; extend as the corpus requires.

ATOMS: dict[str, tuple[bool, str]] = {
    # SI base
    "m": (True, "metre"),
    "s": (True, "second"),
    "g": (True, "gram"),
    "rad": (True, "radian"),
    "K": (True, "kelvin"),
    "C": (True, "coulomb"),
    "cd": (True, "candela"),
    "mol": (True, "mole"),
    "sr": (True, "steradian"),
    # SI derived
    "Hz": (True, "hertz"),
    "N": (True, "newton"),
    "Pa": (True, "pascal"),
    "J": (True, "joule"),
    "W": (True, "watt"),
    "A": (True, "ampere"),
    "V": (True, "volt"),
    "F": (True, "farad"),
    "Ohm": (True, "ohm"),
    "S": (True, "siemens"),
    "Wb": (True, "weber"),
    "T": (True, "tesla"),
    "H": (True, "henry"),
    "lm": (True, "lumen"),
    "lx": (True, "lux"),
    "Bq": (True, "becquerel"),
    "Gy": (True, "gray"),
    "Sv": (True, "sievert"),
    "Cel": (True, "degree Celsius"),
    "kat": (True, "katal"),
    # Common metric non-SI
    "L": (True, "litre"),
    "l": (True, "litre"),
    "t": (True, "tonne"),
    "bar": (True, "bar"),
    "u": (True, "unified atomic mass unit"),
    "eV": (True, "electronvolt"),
    "eq": (True, "equivalent"),
    "osm": (True, "osmole"),
    # Time, non-metric
    "min": (False, "minute"),
    "h": (False, "hour"),
    "d": (False, "day"),
    "wk": (False, "week"),
    "mo": (False, "month"),
    "a": (False, "year"),
    # Dimensionless
    "%": (False, "percent"),
    "[ppth]": (False, "parts per thousand"),
    "[ppm]": (False, "parts per million"),
    "[ppb]": (False, "parts per billion"),
    "[pptr]": (False, "parts per trillion"),
    # Clinical and customary
    "[degF]": (False, "degree Fahrenheit"),
    "[degR]": (False, "degree Rankine"),
    "[in_i]": (False, "inch"),
    "[ft_i]": (False, "foot"),
    "[lb_av]": (False, "pound"),
    "[oz_av]": (False, "ounce"),
    # Pressure columns. UCUM's atom is the metre form, so millimetres of
    # mercury is the milli prefix applied to it: mm[Hg].
    "m[Hg]": (True, "metre of mercury column"),
    "m[H2O]": (True, "metre of water column"),
    "[iU]": (True, "international unit"),
    "[IU]": (True, "international unit"),
    "[pH]": (False, "pH"),
    "[drp]": (False, "drop"),
    "[psi]": (False, "pound per square inch"),
}


def _is_simple_unit(token: str) -> bool:
    """True when token is an atom, or a prefix applied to a metric atom."""
    if token in ATOMS:
        return True
    for length in (2, 1):
        prefix, rest = token[:length], token[length:]
        if prefix in PREFIXES and rest in ATOMS and ATOMS[rest][0]:
            return True
    return False


class _Parser:
    """Recursive-descent parser over the UCUM expression grammar."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0

    # -- scanning helpers --------------------------------------------------

    def _peek(self) -> str:
        return self.text[self.pos] if self.pos < len(self.text) else ""

    def _eof(self) -> bool:
        return self.pos >= len(self.text)

    def _skip_annotation(self) -> bool:
        if self._peek() != "{":
            return False
        end = self.text.find("}", self.pos)
        if end == -1:
            raise UcumError(f"unterminated annotation in {self.text!r}")
        self.pos = end + 1
        return True

    def _read_exponent(self) -> int:
        start = self.pos
        if self._peek() in "+-":
            self.pos += 1
        digits_at = self.pos
        while self._peek().isdigit():
            self.pos += 1
        if self.pos == digits_at:
            self.pos = start
            return 1
        return int(self.text[start:self.pos])

    def _read_unit_token(self) -> str:
        start = self.pos
        while not self._eof():
            char = self._peek()
            if char == "[":
                end = self.text.find("]", self.pos)
                if end == -1:
                    raise UcumError(f"unterminated bracket in {self.text!r}")
                self.pos = end + 1
                continue
            if char.isalpha() or char == "%" or char == "'":
                self.pos += 1
                continue
            break
        return self.text[start:self.pos]

    # -- grammar -----------------------------------------------------------

    def parse(self) -> tuple[float, dict[str, int]]:
        factor, terms = 1.0, {}
        sign = 1
        if self._peek() == "/":
            sign = -1
            self.pos += 1
        sub_factor, sub_terms = self._term()
        factor *= sub_factor ** sign
        _merge(terms, sub_terms, sign)

        while not self._eof():
            operator = self._peek()
            if operator not in ".":
                if operator != "/":
                    raise UcumError(
                        f"unexpected {operator!r} at position {self.pos} in {self.text!r}"
                    )
            sign = -1 if operator == "/" else 1
            self.pos += 1
            sub_factor, sub_terms = self._term()
            factor *= sub_factor ** sign
            _merge(terms, sub_terms, sign)

        return factor, terms

    def _term(self) -> tuple[float, dict[str, int]]:
        if self._peek() == "(":
            self.pos += 1
            depth, start = 1, self.pos
            while self.pos < len(self.text) and depth:
                if self.text[self.pos] == "(":
                    depth += 1
                elif self.text[self.pos] == ")":
                    depth -= 1
                self.pos += 1
            if depth:
                raise UcumError(f"unbalanced parentheses in {self.text!r}")
            inner = self.text[start:self.pos - 1]
            factor, terms = _Parser(inner).parse()
            exponent = self._read_exponent()
            self._skip_annotation()
            if exponent != 1:
                factor = factor ** exponent
                terms = {unit: power * exponent for unit, power in terms.items()}
            return factor, terms

        # A bare annotation is dimensionless.
        if self._skip_annotation():
            return 1.0, {}

        # Power-of-ten atoms: 10*3, 10^-6.
        if self.text.startswith(("10*", "10^"), self.pos):
            self.pos += 3
            power = self._read_exponent()
            self._skip_annotation()
            return float(10 ** power), {}

        # A plain numeric factor.
        if self._peek().isdigit():
            start = self.pos
            while self._peek().isdigit():
                self.pos += 1
            value = float(self.text[start:self.pos])
            self._skip_annotation()
            return value, {}

        token = self._read_unit_token()
        if not token:
            raise UcumError(
                f"expected a unit at position {self.pos} in {self.text!r}"
            )
        if not _is_simple_unit(token):
            raise UcumError(
                f"unknown UCUM atom {token!r} in {self.text!r}; "
                "add it to ATOMS in scripts/ucum.py if the corpus needs it"
            )
        exponent = self._read_exponent()
        self._skip_annotation()
        return 1.0, {token: exponent}


def _merge(target: dict[str, int], source: dict[str, int], sign: int) -> None:
    for unit, power in source.items():
        target[unit] = target.get(unit, 0) + power * sign


def _render_factor(factor: float) -> str:
    if factor == int(factor):
        return str(int(factor))
    return repr(factor)


def canonical(code: str) -> str:
    """Return the canonical comparison key for a UCUM expression.

    Raises UcumError when the expression is malformed or uses an atom outside
    the table.
    """
    if not isinstance(code, str) or not code.strip():
        raise UcumError("empty UCUM code")
    factor, terms = _Parser(code.strip()).parse()

    rendered = []
    for unit in sorted(term for term, power in terms.items() if power):
        power = terms[unit]
        rendered.append(unit if power == 1 else f"{unit}{power}")

    if not rendered:
        return _render_factor(factor)
    if factor != 1:
        return ".".join([_render_factor(factor), *rendered])
    return ".".join(rendered)


def equal(left: str, right: str) -> bool:
    """True when two UCUM expressions have the same canonical form."""
    return canonical(left) == canonical(right)


def is_canonical(code: str) -> bool:
    """True when the code is already written in canonical form."""
    try:
        return canonical(code) == code
    except UcumError:
        return False


def validate(code: str) -> None:
    """Raise UcumError when the code is not a usable UCUM expression."""
    canonical(code)


# ── CLI ──────────────────────────────────────────────────────────────────

_UNIT_KEYS = ("canonicalUcum", "expectedUcum", "acceptedUcum", "unitCode", "code")


def _scan(path: Path) -> int:
    """Report every non-canonical or invalid unit code in a JSON document."""
    document = json.loads(path.read_text())
    findings: list[str] = []

    def walk(node, trail: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                where = f"{trail}.{key}"
                if key in _UNIT_KEYS:
                    codes = value if isinstance(value, list) else [value]
                    for code in codes:
                        if not isinstance(code, str):
                            continue
                        try:
                            form = canonical(code)
                        except UcumError as error:
                            findings.append(f"{where}: {code!r} invalid — {error}")
                            continue
                        if form != code:
                            findings.append(f"{where}: {code!r} -> {form!r}")
                else:
                    walk(value, where)
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{trail}[{index}]")

    walk(document, path.name)

    if not findings:
        print(f"ucum: {path} clean")
        return 0
    print(f"ucum: {len(findings)} finding(s) in {path}")
    for finding in findings:
        print(f"  {finding}")
    return 1


def main(argv: list[str]) -> int:
    if not argv:
        print("ucum: canonicalize UCUM unit codes for comparison")
        print("usage: ucum.py CODE... | --atoms | --scan FILE.json")
        return 2

    if argv[0] == "--atoms":
        for code in sorted(ATOMS):
            metric, description = ATOMS[code]
            print(f"{code:12} {'metric' if metric else '      '}  {description}")
        print(f"\n{len(ATOMS)} atoms, {len(PREFIXES)} prefixes")
        return 0

    if argv[0] == "--scan":
        if len(argv) < 2:
            print("ucum: --scan needs a file", file=sys.stderr)
            return 2
        return max(_scan(Path(target)) for target in argv[1:])

    status = 0
    for code in argv:
        try:
            print(f"{code}\t{canonical(code)}")
        except UcumError as error:
            print(f"{code}\tERROR: {error}", file=sys.stderr)
            status = 1
    return status


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
