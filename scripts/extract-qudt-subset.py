#!/usr/bin/env python3
"""Extract the pinned QUDT subset the guardrail shapes reason over.

The unit contract is UCUM canonical in data, QUDT canonical in semantics
(docs/SEMANTIC_GUARDRAIL_CONTRACT.md). QUDT is what makes conversion and
dimension compatibility provable rather than conventional — but all of QUDT is
2,428 units and 60,457 triples, and merging that into every CI validation run
will not stay tractable.

So: extract only the units and quantity kinds the corpus actually references,
from a pinned upstream release, deterministically. The result is committed as
semantics/ontology/qudt-subset.ttl and is small enough to merge into a
validation graph without thought.

What the subset carries, and why each one earns its place:

    qudt:ucumCode              joins QUDT to the wire code; must agree with the
                               axis canonicalUcum, which catches a qudtUnitIri
                               pointing at the wrong unit
    qudt:conversionOffset      asserted only where non-zero — DEG_C (273.15)
                               and DEG_F (459.67). This is what makes "this
                               axis must be affine, not linear" decidable
    qudt:conversionMultiplier  the linear factor
    qudt:hasDimensionVector    dimension compatibility. Two units are
                               compatible iff these are equal; far stronger
                               than comparing quantity kinds, since one unit
                               carries many (DEG_C has 9, UNITLESS has 135)
    qudt:unitForQuantityKind   the QUDT predicate linking unit to quantity
                               kind. Note: NOT qudt:hasQuantityKind, which
                               does not appear in the v3 vocabulary files
    qudt:omUnit                upstream's own OM mapping, which seeds the OM
                               bridge rather than having it hand-written.
                               Coverage is partial: 132 of 2,428 units

Usage:

    python3 scripts/extract-qudt-subset.py --download --write
    python3 scripts/extract-qudt-subset.py --source ~/qudt --check

Without a source and without --download the script prints SKIPPED and exits 0,
mirroring scripts/reason-owl.sh: an external toolchain is not a
developer-laptop requirement.
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "semantics" / "ontology" / "qudt-subset.ttl"
SCAN_ROOTS = [
    REPO_ROOT / "semantics" / "shapes",
    REPO_ROOT / "domains",
]

# Pinned upstream release. Bumping this is a contract change: re-extract,
# re-run the guardrail suite, and note the version in the commit.
QUDT_VERSION = "v3.5.0"
QUDT_BASE = (
    "https://raw.githubusercontent.com/qudt/qudt-public-repo/"
    f"{QUDT_VERSION}/src/main/rdf/vocab"
)
SOURCES = {
    "qudt-units.ttl": f"{QUDT_BASE}/unit/VOCAB_QUDT-UNITS-ALL.ttl",
    "qudt-quantitykinds.ttl": f"{QUDT_BASE}/quantitykinds/VOCAB_QUDT-QUANTITY-KINDS-ALL.ttl",
}

QUDT = "http://qudt.org/schema/qudt/"
UNIT_NS = "http://qudt.org/vocab/unit/"
QKIND_NS = "http://qudt.org/vocab/quantitykind/"

UNIT_PREDICATES = [
    "ucumCode",
    "conversionMultiplier",
    "conversionOffset",
    "hasDimensionVector",
    "symbol",
    "omUnit",
]

REFERENCE_PATTERN = re.compile(
    r"(?:qudt\.org/vocab/(unit|quantitykind)/|\b(?:unit|qkind):)([A-Za-z0-9_\-]+)"
)


def referenced_iris() -> tuple[set[str], set[str]]:
    """Collect the unit and quantity-kind local names the corpus references."""
    units: set[str] = set()
    kinds: set[str] = set()
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.suffix not in {".ttl", ".trig", ".json"} or not path.is_file():
                continue
            if path.resolve() == OUTPUT.resolve():
                continue
            text = path.read_text(errors="replace")
            for line in text.splitlines():
                for match in re.finditer(
                    r"unit:([A-Za-z0-9_\-]+)|qudt\.org/vocab/unit/([A-Za-z0-9_\-]+)", line
                ):
                    units.add(match.group(1) or match.group(2))
                for match in re.finditer(
                    r"qkind:([A-Za-z0-9_\-]+)|qudt\.org/vocab/quantitykind/([A-Za-z0-9_\-]+)",
                    line,
                ):
                    kinds.add(match.group(1) or match.group(2))
    return units, kinds


def load(source_dir: Path):
    from rdflib import Graph  # imported lazily so --help works without rdflib

    graph = Graph()
    for name in SOURCES:
        path = source_dir / name
        if not path.exists():
            raise FileNotFoundError(path)
        graph.parse(path, format="turtle")
    return graph


def download(target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for name, url in SOURCES.items():
        destination = target / name
        if destination.exists():
            continue
        print(f"extract-qudt-subset: fetching {name} at {QUDT_VERSION}")
        with urllib.request.urlopen(url, timeout=120) as response:
            destination.write_bytes(response.read())


def english_label(graph, subject) -> str | None:
    from rdflib import RDFS

    for value in graph.objects(subject, RDFS.label):
        language = getattr(value, "language", None)
        if language in (None, "en"):
            return str(value)
    return None


def render(graph, units: set[str], kinds: set[str]) -> str:
    from rdflib import URIRef

    lines = [
        "# QUDT subset — GENERATED. Do not edit by hand.",
        "#",
        f"# Extracted by scripts/extract-qudt-subset.py from QUDT {QUDT_VERSION}",
        "# (github.com/qudt/qudt-public-repo), restricted to the units and",
        "# quantity kinds this corpus references. Regenerate with:",
        "#",
        "#     python3 scripts/extract-qudt-subset.py --download --write",
        "#",
        "# Upstream is the authority; this file is a pinned projection of it.",
        "# Bumping QUDT_VERSION is a contract change — re-run the guardrail",
        "# conformance suite afterwards.",
        "",
        "@prefix qudt:  <http://qudt.org/schema/qudt/> .",
        "@prefix unit:  <http://qudt.org/vocab/unit/> .",
        "@prefix qkind: <http://qudt.org/vocab/quantitykind/> .",
        "@prefix dim:   <http://qudt.org/vocab/dimensionvector/> .",
        "@prefix rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
        "@prefix rdfs:  <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix xsd:   <http://www.w3.org/2001/XMLSchema#> .",
        "",
        f'<https://realityengine.example.org/ontology/qudt-subset> '
        f'rdfs:comment "QUDT {QUDT_VERSION} subset" .',
        "",
    ]

    missing: list[str] = []

    lines.append("#" * 65)
    lines.append("# Quantity kinds")
    lines.append("#" * 65)
    lines.append("")
    for name in sorted(kinds):
        subject = URIRef(QKIND_NS + name)
        if (subject, None, None) not in graph:
            missing.append(f"qkind:{name}")
            continue
        statements = ["a qudt:QuantityKind"]
        label = english_label(graph, subject)
        if label:
            statements.append(f'rdfs:label "{label}"')
        for value in sorted(graph.objects(subject, URIRef(QUDT + "hasDimensionVector"))):
            statements.append(f"qudt:hasDimensionVector <{value}>")
        lines.append(f"qkind:{name}")
        lines.append("    " + " ;\n    ".join(statements) + " .")
        lines.append("")

    lines.append("#" * 65)
    lines.append("# Units")
    lines.append("#" * 65)
    lines.append("")
    for name in sorted(units):
        subject = URIRef(UNIT_NS + name)
        if (subject, None, None) not in graph:
            missing.append(f"unit:{name}")
            continue
        statements = ["a qudt:Unit"]
        label = english_label(graph, subject)
        if label:
            statements.append(f'rdfs:label "{label}"')
        for predicate in UNIT_PREDICATES:
            for value in sorted(graph.objects(subject, URIRef(QUDT + predicate))):
                if isinstance(value, URIRef):
                    statements.append(f"qudt:{predicate} <{value}>")
                else:
                    text = str(value).replace('"', '\\"')
                    statements.append(f'qudt:{predicate} "{text}"')
        # Only the quantity kinds the corpus references, not all of them:
        # UNITLESS alone carries 135 upstream.
        for value in sorted(graph.objects(subject, URIRef(QUDT + "unitForQuantityKind"))):
            local = str(value).rsplit("/", 1)[-1]
            if local in kinds:
                statements.append(f"qudt:unitForQuantityKind qkind:{local}")
        lines.append(f"unit:{name}")
        lines.append("    " + " ;\n    ".join(statements) + " .")
        lines.append("")

    if missing:
        print(
            "extract-qudt-subset: referenced but absent upstream: "
            + ", ".join(sorted(missing)),
            file=sys.stderr,
        )

    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Extract the pinned QUDT subset the guardrail shapes reason over."
    )
    parser.add_argument("--source", type=Path, help="directory holding the QUDT TTL files")
    parser.add_argument("--download", action="store_true", help=f"fetch QUDT {QUDT_VERSION}")
    parser.add_argument("--write", action="store_true", help="write the subset")
    parser.add_argument("--check", action="store_true", help="fail when the subset is stale")
    arguments = parser.parse_args(argv)

    source = arguments.source
    if arguments.download:
        source = source or (REPO_ROOT / ".qudt-cache")
        try:
            download(source)
        except Exception as error:  # network is optional, never fatal
            print(f"extract-qudt-subset: SKIPPED (download failed: {error})")
            return 0

    if source is None or not source.exists():
        print(
            "extract-qudt-subset: SKIPPED (no QUDT source; pass --source DIR or "
            "--download)"
        )
        return 0

    try:
        import rdflib  # noqa: F401
    except ImportError:
        print("extract-qudt-subset: SKIPPED (rdflib not installed)")
        return 0

    units, kinds = referenced_iris()
    if not units and not kinds:
        print("extract-qudt-subset: no QUDT references found in the corpus")
        return 0

    graph = load(source)
    rendered = render(graph, units, kinds)

    if arguments.check:
        if not OUTPUT.exists():
            print(f"extract-qudt-subset: {OUTPUT} missing")
            return 1
        if OUTPUT.read_text() != rendered:
            print(f"extract-qudt-subset: {OUTPUT} is stale; rerun with --write")
            return 1
        print(f"extract-qudt-subset: OK ({len(units)} units, {len(kinds)} quantity kinds)")
        return 0

    if arguments.write:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(rendered)
        print(
            f"extract-qudt-subset: wrote {OUTPUT.relative_to(REPO_ROOT)} "
            f"({len(units)} units, {len(kinds)} quantity kinds)"
        )
        return 0

    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
