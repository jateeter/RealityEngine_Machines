#!/usr/bin/env python3
"""M5 dynamic ROBOT runtime validation, as a gate (all three acceptance criteria).

M3 proved the authored corpus. M4 exported what actually ran. M5 puts them in one
graph and asks whether the run obeyed the semantics the corpus declares —
`scripts/validate-runtime-trace.py`, merging ontology + profile ABoxes + trace,
then ROBOT report, ROBOT reason (HermiT), then deterministic closed-world checks.

## What each criterion needs

| Criterion | Needs a live universe | Needs ROBOT |
|---|---|---|
| MCP/localAIStack chain classifies cleanly | partly | yes |
| ACP/OpenClaw chain classifies cleanly | partly | yes |
| Guardrail fixture fails with a **named violation record** | no | no |

The third needs neither, so it never skips. That is deliberate: it is the
criterion that proves the guard fires at all, and a suite where every M5 test
skips on a machine without ROBOT would report "OK" while checking nothing —
which is the exact failure this milestone's predecessors kept producing.

## Why "classify cleanly" is checked over examples plus live data

The MCP chain's invocation and evidence halves have **no runtime surface**: a
`POST /api/integrations/localai/invoke` succeeds and leaves no record in the
dispatch ledger or the audit surface. So a live trace cannot contain them today.
The worked examples in `semantics/integration/examples.ttl` carry the full chain,
and merging them with a live trace is what makes "these classify" answerable at
all. The split is reported rather than blurred — see the module docstring of
`scripts/validate-runtime-trace.py` and the M5 section of the roadmap.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import unittest
import urllib.request
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = REPO_ROOT.parent
VALIDATOR = REPO_ROOT / "scripts" / "validate-runtime-trace.py"
EXPORTER = REPO_ROOT / "scripts" / "export-runtime-trace.py"
FIXTURES = REPO_ROOT / "semantics" / "shapes" / "fixtures" / "bad-traces"
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from registry_url import registry_url  # noqa: E402

REGISTRY = registry_url()

# M5's validation sequence, from the roadmap. Named so a step silently dropped
# from the validator fails here rather than shrinking what "validated" means.
M5_STEPS = ["merge", "report", "reason", "closed-world"]


def robot_available() -> bool:
    return bool(os.environ.get("ROBOT_BIN") or shutil.which("robot"))


def universe_is_up() -> bool:
    try:
        with urllib.request.urlopen(REGISTRY, timeout=5) as r:
            return bool(json.loads(r.read()).get("instances"))
    except Exception:
        return False


def traced_instances() -> list[tuple[str, str]]:
    """Every instance the instance registry lists, with its PE URL, by id.

    Every engine is validated, not the first one: no engine is the reference
    (owner rule, 3-of-3 at every observation point). Validating only cpp-1 left
    a forbidden call logged by lsp-1 or scala-1 invisible to this gate. Each
    trace is validated against the catalogue of the PE whose ledger it came from.
    """
    with urllib.request.urlopen(REGISTRY, timeout=5) as r:
        instances = json.loads(r.read()).get("instances", [])
    return sorted((i["id"], i["pe_url"].rstrip("/")) for i in instances if i.get("pe_url"))


def run(script: Path, *args: str, timeout: int = 3600) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(script), *args],
                          cwd=REPO_ROOT, capture_output=True, text=True, timeout=timeout)


class GuardrailFixtureTests(unittest.TestCase):
    """Criterion 3. Never skips — it is what proves the guard fires."""

    def test_every_bad_trace_is_rejected_with_a_named_record(self) -> None:
        cases = json.loads((FIXTURES / "cases.json").read_text())["cases"]
        self.assertGreaterEqual(len(cases), 5, "too few bad traces to cover the checks")

        proc = run(VALIDATOR, "--fixtures")
        self.assertEqual(
            proc.returncode, 0,
            "a bad trace was not rejected, or was rejected without emitting a "
            "named re:SemanticGuardrailViolation record. M5 asks for a named "
            "violation record, not an exit code: a run that fails should say "
            "which rule and which record.\n" + proc.stdout + proc.stderr)
        for case in cases:
            self.assertIn(case["expect"], proc.stdout,
                          f"{case['graph']} did not report {case['expect']}")

    def test_the_fixtures_cover_the_closed_world_checks_m5_names(self) -> None:
        """"Exact region writes, cardinality, and forbidden endpoint use."

        Six fixtures all exercising one check would look like coverage while
        leaving the other two never seen to fire.
        """
        cases = json.loads((FIXTURES / "cases.json").read_text())["cases"]
        expects = {c["expect"] for c in cases}
        for required in ("write-outside-declared-region",     # exact region writes
                         "ambiguous-completion-mapping",      # cardinality
                         "forbidden-endpoint-use"):           # forbidden endpoint use
            self.assertIn(required, expects,
                          f"no fixture exercises {required}; M5 names that check "
                          f"explicitly and it has never been seen to fire")

    def test_forbidden_use_is_read_from_the_pes_own_resolution(self) -> None:
        """The PE decides what is allowed and records the operation id on every
        allowed call; a refused call has none (SURFACE_SPEC.md, localAI invoke
        contract). Owner rule, 2026-10-04: every attempt the PE resolved to no
        operation is a violation, except a contract probe the PE refused.

        The quorum spec probes the refusal path on purpose and every PE records
        those refusals in its ledger. The answered case (the PE let a probe
        through) is the bad trace answered-contract-probe.ttl.
        """
        import importlib.util

        spec = importlib.util.spec_from_file_location("validate_runtime_trace", VALIDATOR)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader
        spec.loader.exec_module(mod)

        def inv(name: str, endpoint: str, *extra: str) -> str:
            return (f"t:{name}\n    a owl:NamedIndividual , re:MCPInvocation ;\n"
                    f'    re:integrationEndpoint "{endpoint}"^^xsd:anyURI ;\n'
                    + "".join(f"    {e} ;\n" for e in extra)
                    + "    re:inTraceRun t:run .\n\n")

        g = mod.parse_ttl(
            "t:run\n    a owl:NamedIndividual , re:TraceRun .\n\n"
            # Refused contract probe: the guard working on a call made to test it.
            + inv("probe", "/v1/models", 're:requestClass "contract-probe"')
            # Refused, made by the run: a GET /graphql the PE correctly refused.
            + inv("refused", "/graphql")
            # Allowed calls carry the operation the PE resolved them to, query
            # string or not.
            + inv("health", "/health?probe=1", 're:allowedOperationId "health"')
            + inv("graphql", "/graphql", 're:allowedOperationId "graphql"')
            # An operation id the catalogue does not list.
            + inv("unlisted", "/admin/drop", 're:allowedOperationId "admin_drop"'))
        r = mod.Result()
        mod.check_forbidden_endpoints(g, {"health", "graphql"}, r)

        flagged = sorted(v.record for v in r.violations if v.kind == "forbidden-endpoint-use")
        self.assertEqual(flagged, ["t:refused", "t:unlisted"])
        self.assertEqual(r.checked.get("refusal probes observed (exempt)"), 1)
        self.assertTrue(any("t:probe" in n for n in r.notes),
                        "an exempt probe must be listed by name, not dropped")

        # The PE's own resolution needs no catalogue: without one, the refused
        # attempt is still caught and only the id cross-check is skipped.
        r = mod.Result()
        mod.check_forbidden_endpoints(g, None, r)
        self.assertEqual([v.record for v in r.violations], ["t:refused"])
        self.assertTrue(any("cross-check SKIPPED" in u for u in r.ungated))

    def test_fixtures_are_not_merged_into_the_reasoned_graph(self) -> None:
        gate = (REPO_ROOT / "scripts" / "reason-owl.sh").read_text()
        self.assertNotIn("bad-traces", gate,
                         "reason-owl.sh merges the bad traces; they are invalid by "
                         "construction and would fail the gate they exist to test")


class ValidationSequenceTests(unittest.TestCase):
    """The validator must implement the sequence the roadmap names."""

    def test_the_validator_runs_merge_report_reason_and_closed_world(self) -> None:
        src = VALIDATOR.read_text()
        for step in M5_STEPS:
            self.assertIn(step, src,
                          f"the validator no longer references the '{step}' step")
        self.assertIn("HermiT", src,
                      "reasoning must use HermiT: ELK does not implement the "
                      "constructs the escalation invariant relies on and passes a "
                      "corpus that violates it")

    def test_a_missing_robot_is_reported_rather_than_passed_over(self) -> None:
        # A validator that silently skips its ROBOT half on a host without ROBOT
        # reports OK for a run it never reasoned about.
        self.assertIn("ROBOT half SKIPPED", VALIDATOR.read_text(),
                      "a missing ROBOT must be named in the output, not absorbed")


class LiveTraceValidationTests(unittest.TestCase):
    """Criteria 1 and 2, against a real run."""

    @classmethod
    def setUpClass(cls) -> None:
        if not universe_is_up():
            raise unittest.SkipTest(
                f"no instance registry at {REGISTRY}; criteria 1 and 2 describe a "
                f"run. Criterion 3 is checked separately and does not skip.")
        if not robot_available():
            raise unittest.SkipTest(
                "no ROBOT on PATH and no ROBOT_BIN; merge/report/reason cannot run. "
                "Criterion 3 is checked separately and does not skip.")

    def test_a_live_run_validates_against_the_corpus_it_came_from(self) -> None:
        """On every engine the instance registry lists. Each engine's problems
        are collected and reported together, named by engine."""
        import tempfile

        engines = traced_instances()
        self.assertTrue(engines, f"the instance registry at {REGISTRY} lists no engine")
        problems: dict[str, list[str]] = {}
        for engine, pe_url in engines:
            found = problems.setdefault(engine, [])
            with tempfile.TemporaryDirectory() as tmp:
                trace = Path(tmp) / "trace.ttl"
                violations = Path(tmp) / "violations.ttl"

                exported = run(EXPORTER, "--engine", engine, "--push", "--out", str(trace))
                if exported.returncode != 0:
                    found.append(f"export failed\n{exported.stdout}\n{exported.stderr}")
                    continue

                # --pe-url adds the catalogue cross-check of operation ids. Before
                # Machines#201 this test passed none, and the whole
                # forbidden-endpoint check printed UNGATED on every stack.
                proc = run(VALIDATOR, "--trace", str(trace), "--pe-url", pe_url,
                           "--emit", str(violations))
                if proc.returncode != 0:
                    found.append("the run does not obey the semantics the corpus "
                                 "declares\n" + proc.stdout + proc.stderr)
                if "catalogue cross-check SKIPPED" in proc.stdout:
                    found.append(f"the allowed-endpoint catalogue could not be read "
                                 f"from {pe_url}, so operation ids were not cross-checked")
                # The sequence must actually have run, not been skipped into silence.
                for step in ("ROBOT merge", "ROBOT report", "ROBOT reason (HermiT)"):
                    if step not in proc.stdout:
                        found.append(f"'{step}' did not run; a clean result from a "
                                     f"step that never executed is not a clean result")
                if "profile ABoxes merged" not in proc.stdout:
                    found.append("no profile ABoxes were merged, so the trace was "
                                 "validated against the ontology alone and never met "
                                 "its corpus")

        failing = {e: p for e, p in problems.items() if p}
        if failing:
            self.fail(
            f"live trace validation failed on {', '.join(sorted(failing))} "
            f"(of {', '.join(e for e, _ in engines)}):\n\n"
            + "\n\n".join(f"== {e}\n" + "\n".join(p) for e, p in sorted(failing.items())))

    def test_both_integration_chains_classify_in_the_merged_graph(self) -> None:
        """Criteria 1 and 2, stated as what must classify.

        The live trace supplies the ACP dispatch and the completion write-back;
        the worked examples supply the MCP invocation, its evidence and the
        OpenClaw agent binding, because no runtime surface records an
        invocation. Both halves are merged, and the assertion is that every
        element of both chains classifies — not that every element came from a
        live run, which today it cannot.
        """
        import tempfile

        robot = os.environ.get("ROBOT_BIN") or shutil.which("robot")
        assert robot
        engines = traced_instances()
        self.assertTrue(engines, f"the instance registry at {REGISTRY} lists no engine")
        missing: dict[str, list[str]] = {}
        for engine, _pe_url in engines:
            missing[engine] = self._unclassified(robot, engine)
        failing = {e: m for e, m in missing.items() if m}
        if failing:
            self.fail(
            "M5 requires both integration chains to classify; in the merged graph "
            + "; ".join(f"{e} classifies no re:{', re:'.join(m)}"
                        for e, m in sorted(failing.items())))

    def _unclassified(self, robot: str, engine: str) -> list[str]:
        """The chain classes that classify nowhere for this engine's trace."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            trace = Path(tmp) / "trace.ttl"
            merged = Path(tmp) / "merged.owl"
            reasoned = Path(tmp) / "reasoned.owl"
            out = Path(tmp) / "q.csv"

            exported = run(EXPORTER, "--engine", engine, "--push", "--out", str(trace))
            self.assertEqual(exported.returncode, 0,
                             f"{engine}: export failed\n{exported.stdout}\n{exported.stderr}")
            subprocess.run(
                [robot, "merge",
                 "--input", str(REPO_ROOT / "semantics" / "ontology" / "re-core.ttl"),
                 "--input", str(REPO_ROOT / "semantics" / "integration" / "examples.ttl"),
                 "--input", str(trace), "--output", str(merged)],
                check=True, capture_output=True, timeout=1800)
            subprocess.run(
                [robot, "reason", "--reasoner", "HermiT", "--input", str(merged),
                 "--output", str(reasoned)],
                check=True, capture_output=True, timeout=3600)

            query = Path(tmp) / "q.rq"
            query.write_text(
                "PREFIX re: <https://realityengine.example.org/ontology/re-core#>\n"
                "SELECT ?c (COUNT(?i) AS ?n) WHERE {\n"
                "  VALUES ?c { re:MCPInvocation re:MCPToolResult re:EvidenceArtifact\n"
                "              re:ACPDispatch re:OpenClawAgentBinding\n"
                "              re:CompletionMapping re:SourceMappingWrite }\n"
                "  ?i a ?c .\n} GROUP BY ?c\n")
            subprocess.run([robot, "query", "--input", str(reasoned),
                            "--query", str(query), str(out)],
                           check=True, capture_output=True, timeout=1800)

            text = out.read_text()
            return [cls for cls in ("MCPInvocation", "MCPToolResult", "EvidenceArtifact",
                                    "ACPDispatch", "OpenClawAgentBinding",
                                    "CompletionMapping", "SourceMappingWrite")
                    if cls not in text]


if __name__ == "__main__":
    unittest.main()
