#!/usr/bin/env python3
"""Conformance runner for the ingress/egress semantic guardrails.

Validates each named graph in semantics/shapes/fixtures/cases.trig against
semantics/shapes/re-guardrails.shacl.ttl and compares the decision with the
expectation recorded in semantics/shapes/fixtures/cases.json.

The data graph for each case is the merge of:

    semantics/ontology/re-core.ttl        the machine/action/autonomy vocabulary
    semantics/shapes/re-guardrails.shacl.ttl   guardrail vocabulary + autonomy ranks
    semantics/ontology/qudt-subset.ttl    pinned QUDT units and quantity kinds
    semantics/shapes/fixtures/lane-registry.ttl the lane contracts
    <the case's named graph>              the admission or dispatch under test

The shapes file appears on both sides deliberately: it is the single source of
truth, so the terms its constraints join against (provenance classes, lane
binding modes, autonomy ranks) are declared there rather than duplicated into
a second vocabulary file. Runtimes compile those declarations into their
decision table at load; only this runner needs the merge.

Requires pyshacl. Run through scripts/validate-guardrails.sh, which skips
cleanly when pyshacl is absent.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from pyshacl import validate
    from rdflib import Dataset, Graph, URIRef
except ImportError:  # pragma: no cover - the wrapper script gates on this
    print("validate-guardrails: pyshacl/rdflib not installed", file=sys.stderr)
    raise SystemExit(2)

REPO_ROOT = Path(__file__).resolve().parent.parent
ONTOLOGY = REPO_ROOT / "semantics" / "ontology" / "re-core.ttl"
SHAPES = REPO_ROOT / "semantics" / "shapes" / "re-guardrails.shacl.ttl"
FIXTURES = REPO_ROOT / "semantics" / "shapes" / "fixtures"
CASES_TRIG = FIXTURES / "cases.trig"
CASES_JSON = FIXTURES / "cases.json"
LANE_REGISTRY = FIXTURES / "lane-registry.ttl"
LANE_GRAPH = REPO_ROOT / "semantics" / "lanes" / "lane-graph.ttl"
QUDT_SUBSET = REPO_ROOT / "semantics" / "ontology" / "qudt-subset.ttl"

FIXTURE_NS = "https://realityengine.example.org/fixtures/guardrails#"

SHACL = "http://www.w3.org/ns/shacl#"


def load_base() -> Graph:
    base = Graph()
    for path in (ONTOLOGY, SHAPES, QUDT_SUBSET, LANE_REGISTRY):
        base.parse(path, format="turtle")
    return base


def result_strings(results_graph: Graph) -> list[str]:
    """Every message and constraint-component name in the validation report."""
    out: list[str] = []
    for _, _, message in results_graph.triples((None, URIRef(SHACL + "resultMessage"), None)):
        out.append(str(message))
    for _, _, component in results_graph.triples(
        (None, URIRef(SHACL + "sourceConstraintComponent"), None)
    ):
        out.append(str(component).rsplit("#", 1)[-1])
    return out


def main() -> int:
    manifest = json.loads(CASES_JSON.read_text())
    cases = manifest["cases"]

    dataset = Dataset()
    dataset.parse(CASES_TRIG, format="trig")
    graphs = dataset.graphs() if hasattr(dataset, "graphs") else dataset.contexts()
    available = {
        str(ctx.identifier).replace(FIXTURE_NS, "")
        for ctx in graphs
        if str(ctx.identifier).startswith(FIXTURE_NS)
    }

    shapes = Graph()
    shapes.parse(SHAPES, format="turtle")
    base = load_base()

    declared = {case["graph"] for case in cases}
    orphans = sorted(available - declared)
    missing = sorted(declared - available)

    failures: list[str] = []
    passed = 0

    for case in cases:
        name = case["graph"]
        if name not in available:
            failures.append(f"{name}: no such named graph in cases.trig")
            continue

        data = Graph()
        for triple in base:
            data.add(triple)
        for triple in dataset.graph(URIRef(FIXTURE_NS + name)):
            data.add(triple)

        conforms, results_graph, _ = validate(
            data,
            shacl_graph=shapes,
            advanced=True,
            inference="none",
            abort_on_first=False,
            meta_shacl=False,
        )

        expected = case["conforms"]
        strings = result_strings(results_graph)

        if conforms != expected:
            verdict = "accepted" if conforms else "refused"
            wanted = "accept" if expected else "refuse"
            detail = "; ".join(sorted(set(strings))[:4]) or "no results"
            failures.append(f"{name}: expected {wanted}, {verdict}. {detail}")
            continue

        fragment = case.get("expect")
        if fragment and not any(fragment in s for s in strings):
            detail = "; ".join(sorted(set(strings))[:4]) or "no results"
            failures.append(f"{name}: refused, but not for {fragment!r}. Got: {detail}")
            continue

        passed += 1

    for name in missing:
        failures.append(f"{name}: declared in cases.json but absent from cases.trig")
    for name in orphans:
        failures.append(f"{name}: present in cases.trig but not declared in cases.json")

    # The fixtures prove the rules; the projected corpus proves they hold on
    # the real thing. A guardrail green on fixtures and silent about 941 live
    # lanes would be measuring the wrong system.
    if LANE_GRAPH.exists():
        corpus = Graph()
        for path in (ONTOLOGY, SHAPES, QUDT_SUBSET, LANE_GRAPH):
            corpus.parse(path, format="turtle")
        conforms, results_graph, _ = validate(
            corpus, shacl_graph=shapes, advanced=True, inference="none",
            abort_on_first=False, meta_shacl=False,
        )
        lanes = len(set(corpus.subjects(
            URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
            URIRef("https://realityengine.example.org/ontology/re-guardrails#IngressLane"),
        )))
        if conforms:
            print(f"validate-guardrails: projected lane graph conforms ({lanes} lanes)")
        else:
            detail = sorted(set(result_strings(results_graph)))[:5]
            failures.append(
                "projected lane graph does not conform: " + "; ".join(detail)
            )

    total = len(cases)
    if failures:
        print(f"validate-guardrails: {passed}/{total} cases passed\n")
        for failure in failures:
            print(f"  FAIL  {failure}")
        return 1

    print(f"validate-guardrails: {passed}/{total} cases passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
