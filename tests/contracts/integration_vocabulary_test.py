#!/usr/bin/env python3
"""M2 of the Semantic OWL roadmap: the PE.x.MCP and PE.x.ACP integration vocabulary.

## Why this exists

Before this milestone, six of the seven concepts M2 requires had no
representation at all, and the seventh — `re:CompletionMapping` — was declared
with an **empty extension across all twelve domains**. Nothing in the corpus
described the route a completion takes into the vector; the ontology only said
that such a route could be described. So a completion that wrote through an
approved mapping was indistinguishable from a completion that had no right to
be written at all, because nothing named the invocation that produced it.

## Why the mapping check is here and not in the ontology

The property worth enforcing is that every `re:SourceMappingWrite` exercises a
declared `re:CompletionMapping`. The first attempt encoded it in OWL, as a
defined class over `owl:maxCardinality 0` on `re:writesThroughMapping`. It was
inert: under the open world a write with no asserted mapping is not a write with
*zero* mappings, it is a write whose mappings are unknown, so nothing is
entailed. HermiT classified the negative fixture as nothing, and an empty
extension is indistinguishable from a clean result.

That is the same shape as `re:EscalationDetermination`, which is correct,
open-world, and evaluated 2 of 80 escalations until `escalation_rag_test.py`
closed the corpus side. The remedy is the same: the OWL stays open-world, and
the closed-world half lives here, where the graph being read *is* the whole
graph and "no mapping" can be asserted and meant.

This file is therefore deliberately not a restatement of the ontology. It checks
the two things the ontology cannot: that the vocabulary is complete, and that a
violating write is actually caught.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ONTOLOGY = REPO_ROOT / "semantics" / "ontology" / "re-core.ttl"
EXAMPLES = REPO_ROOT / "semantics" / "integration" / "examples.ttl"

# The seven concepts M2's table requires. Named here rather than derived, so
# that deleting one from the ontology fails instead of shrinking the check.
M2_CLASSES = [
    "MCPInvocation",
    "MCPToolResult",
    "ACPDispatch",
    "OpenClawAgentBinding",
    "CompletionMapping",
    "SourceMappingWrite",
    "SemanticGuardrailViolation",
]

# Relationships M2 requires each concept to carry.
M2_RELATIONSHIPS = {
    "MCPInvocation": ["forMachine", "forSequence", "invokesProvider",
                      "integrationEndpoint", "requestClass", "resultClass"],
    "MCPToolResult": ["resultOfInvocation", "hasEvidenceArtifact",
                      "resultConfidence", "writesThroughMapping"],
    "ACPDispatch": ["forMachine", "forSequence", "dispatchId",
                    "viaAgentBinding", "noWaitDispatch"],
    "SourceMappingWrite": ["writesThroughMapping", "writeOffset",
                           "writeLength", "writtenBy", "correlationId"],
    "SemanticGuardrailViolation": ["violationType", "severity", "recordId",
                                   "violatesPolicy"],
}


def individuals(ttl: str) -> dict[str, dict[str, list[str]]]:
    """Parse the hand-authored examples into {subject: {predicate: [objects]}}.

    A deliberately small reader, not a general Turtle parser: it handles the one
    shape this file is written in — `subject` on its own line, indented
    `re:predicate object` lines, terminated by `.`. rdflib is not a dependency
    of this repo's test path and adding one to read a file we also author is a
    cost with no corresponding check.
    """
    out: dict[str, dict[str, list[str]]] = {}
    subject: str | None = None
    for raw in ttl.splitlines():
        line = raw.split("#")[0].rstrip() if not raw.lstrip().startswith("#") else ""
        if not line.strip():
            continue
        if not raw.startswith((" ", "\t")):
            m = re.match(r"^([A-Za-z][\w-]*:[\w-]+)\s*$", line.strip())
            subject = m.group(1) if m else None
            if subject:
                out.setdefault(subject, {})
            continue
        if subject is None:
            continue
        body = line.strip().rstrip(";.").strip()
        m = re.match(r"^(?:a\s+|(re:[\w-]+)\s+)(.*)$", body)
        if not m:
            continue
        pred = m.group(1) or "a"
        objs = [o.strip() for o in m.group(2).split(",") if o.strip()]
        out[subject].setdefault(pred.removeprefix("re:"), []).extend(objs)
        if line.rstrip().endswith("."):
            subject = None
    return out


class IntegrationVocabularyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ontology = ONTOLOGY.read_text()
        cls.examples = EXAMPLES.read_text()
        cls.inds = individuals(cls.examples)

    # ── The vocabulary itself ────────────────────────────────────────────────

    def test_every_m2_concept_is_declared(self) -> None:
        missing = [c for c in M2_CLASSES
                   if not re.search(rf"^re:{c} a owl:Class", self.ontology, re.M)]
        self.assertEqual(missing, [], f"M2 concepts absent from the ontology: {missing}")

    def test_every_m2_relationship_is_declared(self) -> None:
        declared = set(re.findall(r"^re:([\w-]+) a owl:(?:Object|Datatype)Property",
                                  self.ontology, re.M))
        missing = {cls: [p for p in props if p not in declared]
                   for cls, props in M2_RELATIONSHIPS.items()}
        missing = {k: v for k, v in missing.items() if v}
        self.assertEqual(missing, {}, f"relationships M2 requires but nothing declares: {missing}")

    def test_every_new_class_carries_a_definition(self) -> None:
        # ROBOT's missing_definition looks for obo:IAO_0000115. A class added
        # without one passes `report` at INFO and leaves the next reader to
        # guess what it denotes.
        for c in M2_CLASSES + ["IntegrationProvider", "EvidenceArtifact"]:
            block = re.search(rf"^re:{c} a owl:Class ;(.*?)\.\n", self.ontology,
                              re.M | re.S)
            if block is None:
                self.fail(f"re:{c} is not declared")
            self.assertIn("obo:IAO_0000115", block.group(1),
                          f"re:{c} has no obo:IAO_0000115 definition")

    def test_openclaw_binding_adds_no_duplicate_vocabulary(self) -> None:
        """Its five relationships must be re:AgentBinding's, not new names.

        The failure this prevents is a second vocabulary for the same facts:
        re:openClawMachine beside re:targetsMachine, re:openClawAutonomy beside
        re:autonomyMode. Two names for one fact is two things to keep in step,
        and they do not stay in step.
        """
        block = re.search(r"^re:OpenClawAgentBinding a owl:Class ;(.*?)\.\n",
                          self.ontology, re.M | re.S)
        if block is None:
            self.fail("re:OpenClawAgentBinding is not declared")
        self.assertIn("rdfs:subClassOf re:AgentBinding", block.group(1))
        for invented in ("openClawMachine", "openClawAgentId", "openClawAutonomy"):
            self.assertNotIn(f"re:{invented}", self.ontology,
                             f"re:{invented} duplicates a re:AgentBinding property")

    # ── M2 acceptance: one MCP and one ACP workflow ──────────────────────────

    def test_an_mcp_workflow_is_represented_end_to_end(self) -> None:
        """Invocation -> result -> evidence -> mapping -> write, one chain."""
        inv = self.inds.get("ex:mcp-invocation-1", {})
        self.assertIn("re:MCPInvocation", inv.get("a", []))
        res = self.inds.get("ex:mcp-result-1", {})
        self.assertEqual(res.get("resultOfInvocation"), ["ex:mcp-invocation-1"])
        self.assertTrue(res.get("hasEvidenceArtifact"),
                        "a result with no evidence is an unsupported completion")
        write = self.inds.get("ex:mcp-write-1", {})
        self.assertEqual(res.get("writesThroughMapping"),
                         write.get("writesThroughMapping"),
                         "the result's permitted mapping and the write's exercised "
                         "mapping must be the same individual")
        self.assertEqual(inv.get("correlationId"), write.get("correlationId"),
                         "the correlation id is what joins the round trip; "
                         "without it the write is attributable to a mapping but "
                         "not to the invocation that justified it")

    def test_an_acp_workflow_is_represented_end_to_end(self) -> None:
        disp = self.inds.get("ex:acp-dispatch-1", {})
        self.assertIn("re:ACPDispatch", disp.get("a", []))
        self.assertEqual(disp.get("noWaitDispatch"), ["true"],
                         "no-wait is what keeps agent execution off the "
                         "synchronous push path")
        self.assertTrue(disp.get("viaAgentBinding"))
        write = self.inds.get("ex:acp-write-1", {})
        self.assertEqual(disp.get("correlationId"), write.get("correlationId"))

    def test_the_acp_session_key_is_only_ever_a_hash(self) -> None:
        # The session must be identifiable across records without the material
        # being recoverable from a graph that gets merged, published and diffed.
        self.assertNotIn("re:sessionKey ", self.ontology)
        for subj, props in self.inds.items():
            for value in props.get("sessionKeyHash", []):
                self.assertRegex(value, r'^"(sha256|sha512):',
                                 f"{subj} session key hash names no digest")

    # ── The check OWL could not make ─────────────────────────────────────────

    def test_every_source_mapping_write_names_a_completion_mapping(self) -> None:
        """Closed-world. This is the check the inert OWL axiom could not make.

        The negative fixture must be found. A guard with no violating case to
        catch is a guard nobody has seen work — which is exactly how the
        max-cardinality version passed while checking nothing.
        """
        writes = {s: p for s, p in self.inds.items()
                  if "re:SourceMappingWrite" in p.get("a", [])}
        self.assertGreaterEqual(len(writes), 3, "expected the two workflows plus the fixture")

        unmapped = sorted(s for s, p in writes.items() if not p.get("writesThroughMapping"))
        self.assertEqual(
            unmapped, ["ex:unmapped-write-1"],
            "closed-world check disagrees with the fixture set: it must find the "
            "negative fixture and nothing else. Finding nothing means the check "
            "is inert; finding more means a real workflow lost its mapping.")

    def test_a_write_stays_inside_the_region_its_mapping_declares(self) -> None:
        """Half-open [offset, offset+length) on both sides, so they compare directly."""
        for subj, props in self.inds.items():
            if "re:SourceMappingWrite" not in props.get("a", []):
                continue
            mapping_ids = props.get("writesThroughMapping") or []
            if not mapping_ids:
                continue                      # the negative fixture; covered above
            mapping = self.inds[mapping_ids[0]]
            m_off = int(mapping["completionOffset"][0])
            m_len = int(mapping["completionLength"][0])
            w_off = int(props["writeOffset"][0])
            w_len = int(props["writeLength"][0])
            self.assertGreaterEqual(w_off, m_off, f"{subj} starts before its mapping")
            self.assertLessEqual(w_off + w_len, m_off + m_len,
                                 f"{subj} writes past the end of its declared region")

    def test_examples_join_to_real_corpus_machines(self) -> None:
        """Every re:forMachine target must be a machine IRI the corpus generates.

        An example on invented IRIs classifies just as cleanly and proves
        nothing about whether the vocabulary reaches the corpus — it would add
        two disconnected islands to the merged graph.
        """
        prefixes = dict(re.findall(r"^@prefix\s+([\w-]+):\s+<([^>]+)>", self.examples, re.M))
        targets = {t for p in self.inds.values() for t in p.get("forMachine", [])}
        self.assertTrue(targets, "no example names a machine")
        for t in targets:
            pfx, local = t.split(":", 1)
            self.assertIn(pfx, prefixes, f"{t} uses an undeclared prefix")
            iri = prefixes[pfx]
            m = re.match(r".*/machines/([\w-]+)/([\w-]+)#$", iri)
            if m is None:
                self.fail(f"{iri} is not a corpus machine IRI")
            domain, stem = m.groups()
            abox = REPO_ROOT / "semantics" / "abox" / domain / f"{stem}.ttl"
            self.assertTrue(abox.exists(), f"{t} names {abox}, which the corpus does not generate")
            self.assertIn(f"{local}\n", abox.read_text(),
                          f"{t} is not an individual in {abox.name}")


if __name__ == "__main__":
    unittest.main()
