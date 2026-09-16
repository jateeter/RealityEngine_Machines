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
REGISTRY = os.environ.get("RE_REGISTRY_URL", "http://127.0.0.1:5999/re-registry.json")

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
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            trace = Path(tmp) / "trace.ttl"
            violations = Path(tmp) / "violations.ttl"

            exported = run(EXPORTER, "--push", "--out", str(trace))
            self.assertEqual(exported.returncode, 0,
                             f"export failed\n{exported.stdout}\n{exported.stderr}")

            proc = run(VALIDATOR, "--trace", str(trace), "--emit", str(violations))
            self.assertEqual(
                proc.returncode, 0,
                "a live run does not obey the semantics the corpus declares.\n"
                + proc.stdout + proc.stderr)

            # The sequence must actually have run, not been skipped into silence.
            for step in ("ROBOT merge", "ROBOT report", "ROBOT reason (HermiT)"):
                self.assertIn(step, proc.stdout,
                              f"'{step}' did not run; a clean result from a step "
                              f"that never executed is not a clean result")
            self.assertIn("profile ABoxes merged", proc.stdout,
                          "no profile ABoxes were merged, so the trace was validated "
                          "against the ontology alone and never met its corpus")

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
        with tempfile.TemporaryDirectory() as tmp:
            trace = Path(tmp) / "trace.ttl"
            merged = Path(tmp) / "merged.owl"
            reasoned = Path(tmp) / "reasoned.owl"
            out = Path(tmp) / "q.csv"

            self.assertEqual(run(EXPORTER, "--push", "--out", str(trace)).returncode, 0)
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
            for cls in ("MCPInvocation", "MCPToolResult", "EvidenceArtifact",
                        "ACPDispatch", "OpenClawAgentBinding",
                        "CompletionMapping", "SourceMappingWrite"):
                self.assertIn(cls, text,
                              f"re:{cls} classifies nowhere in the merged graph; "
                              f"M5 requires both integration chains to classify")


if __name__ == "__main__":
    unittest.main()
