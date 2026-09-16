#!/usr/bin/env python3
"""M3 static workflow provability, as a gate rather than a script (criteria 1 and 2).

`scripts/prove-workflows.py` implements M3's six rules. This makes running it a
requirement of the contract suite, for the same reason M3 criterion 3 needed
`openclaw_profile_drift_test.py`: a check that exists and is never invoked is
not a gate. The repository already had one of those — `--check` on the OpenClaw
profile generator, present since it was written and called by nothing.

Two criteria, two tests:

- **Limited corpus profile passes.** `standard-deployment` must prove clean.
- **Intentional bad fixtures fail.** Each fixture under
  `semantics/shapes/fixtures/bad-workflows/` must produce exactly the violation
  it exists to produce.

The second is not decoration. M2 shipped an OWL axiom over `owl:maxCardinality
0` that could never fire, and the passing suite looked identical to a working
one. The fixtures are the difference between "found nothing" and "cannot find
anything".

## What this deliberately does not assert

It does not assert the **whole corpus** proves clean. It does not:
`RealityEngine_Machines#149` records 13 violations across 1328 machines, and
they are corpus-correction decisions with an open design question about
`re:DispatchAgent`. Gating on them here would either block every unrelated
change or, far worse, invite the rule to be widened until the corpus passed —
which is the failure this milestone exists to prevent.

That split is the roadmap's own, in S7: "Limited profile remains checkable;
wider profiles become blocking after drift is eliminated."
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = REPO_ROOT.parent
PROVER = REPO_ROOT / "scripts" / "prove-workflows.py"
FIXTURES = REPO_ROOT / "semantics" / "shapes" / "fixtures" / "bad-workflows"
MANIFEST = WORKSPACE / "RealityEngine_CI" / "config" / "standard-deployment-corpus.txt"

# The six rules M3 names. Listed so that a rule quietly dropped from the prover
# fails here, rather than shrinking what "proves clean" means.
M3_RULES = {
    "R1": "every dispatchable action has a known machine IRI",
    "R2": "MCP endpoints are allowed for the workflow class",
    "R3": "one machine binding per generated OpenClaw agent",
    "R4": "agent input axes map to authored regions",
    "R5": "completions write only through approved source mappings",
    "R6": "RED and life-safety cannot be downgraded to non-critical automation",
}


def run_prover(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(PROVER), *args],
                          cwd=REPO_ROOT, capture_output=True, text=True, timeout=600)


class StaticProvabilityTests(unittest.TestCase):
    def test_the_prover_implements_all_six_rules(self) -> None:
        src = PROVER.read_text()
        missing = [r for r in M3_RULES if f'"{r}' not in src and f"'{r}" not in src]
        self.assertEqual(missing, [],
                         f"prove-workflows.py no longer references M3 rules: "
                         f"{[f'{r}: {M3_RULES[r]}' for r in missing]}")

    def test_the_limited_corpus_profile_proves_clean(self) -> None:
        """M3 acceptance criterion 1."""
        if not MANIFEST.is_file():
            self.skipTest(f"{MANIFEST} not present; RealityEngine_CI is a sibling repo")

        proc = run_prover("--profile", "standard-deployment")
        self.assertEqual(
            proc.returncode, 0,
            "the limited corpus profile no longer proves under the M3 rules.\n"
            "Reproduce with: npm run prove:workflows\n"
            f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}")

    def test_the_limited_profile_run_actually_evaluated_something(self) -> None:
        """A clean run over nothing is not a clean run.

        The prover reports a `checked` count per rule, and this asserts the
        counts are non-zero for the rules the limited profile can exercise. Rule
        R6 is the reason this test exists: an early version read RED only from
        the determination, and on this profile that evaluated **0** critical
        determinations while reporting OK — 5 of the 12 machines carry a RED
        trigger rule. The prover now reports that as an explicit UNGATED reach
        limit instead of passing quietly, and this test requires the reach line
        to be present rather than the count to be fabricated.
        """
        if not MANIFEST.is_file():
            self.skipTest("RealityEngine_CI manifest not present")

        out = run_prover("--profile", "standard-deployment").stdout
        for rule in ("R1", "R3", "R4"):
            self.assertRegex(
                out, rf"checked\s+{rule}[^\n]*: [1-9]",
                f"{rule} evaluated nothing on the limited profile; a rule that "
                f"checks zero cases passes for the wrong reason")
        # Every rule that cannot be evaluated must say so in its own line.
        for rule in ("R2", "R6"):
            self.assertTrue(
                f"checked  {rule}" in out or f"UNGATED  {rule}" in out,
                f"{rule} neither reported a checked count nor declared itself "
                f"ungated — it is silently absent from the gate")

    def test_every_bad_fixture_produces_its_violation(self) -> None:
        """M3 acceptance criterion 2: the intentional bad fixture must fail."""
        self.assertTrue(FIXTURES.is_dir(), f"{FIXTURES} is missing")
        cases = json.loads((FIXTURES / "cases.json").read_text())["cases"]
        self.assertGreaterEqual(len(cases), 5, "too few negative fixtures to cover the rules")

        proc = run_prover("--fixtures")
        self.assertEqual(
            proc.returncode, 0,
            "a bad-workflow fixture did not produce the violation it exists to "
            "produce, so that rule is not proven to fire.\n"
            "Reproduce with: npm run prove:workflows:fixtures\n"
            f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}")
        for case in cases:
            self.assertIn(case["expect"], proc.stdout,
                          f"{case['graph']} did not report {case['expect']}")

    def test_the_fixtures_cover_more_than_one_rule(self) -> None:
        # Five fixtures all exercising R6 would leave R1 and R5 unproven while
        # looking like coverage.
        cases = json.loads((FIXTURES / "cases.json").read_text())["cases"]
        rules = {c["rule"] for c in cases}
        self.assertGreaterEqual(
            len(rules), 3,
            f"negative fixtures cover only {sorted(rules)}; a rule with no "
            f"fixture has never been seen to fire")

    def test_fixtures_are_not_merged_into_the_reasoned_graph(self) -> None:
        """They are deliberately invalid; reasoning over them would fail the gate.

        `reason-owl.sh` merges `semantics/integration/examples.ttl` in every
        scope. It must not do the same for these.
        """
        gate = (REPO_ROOT / "scripts" / "reason-owl.sh").read_text()
        self.assertNotIn("bad-workflows", gate,
                         "reason-owl.sh merges the bad-workflow fixtures; they are "
                         "invalid by construction and would fail the reasoner gate")


if __name__ == "__main__":
    unittest.main()
