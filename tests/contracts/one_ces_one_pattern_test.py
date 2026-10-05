#!/usr/bin/env python3
"""scripts/check-one-ces-one-pattern.py: owner rule 2026-10-05, without exception.

Each CES in a machine reflects exactly one regular expression of its own; two
CESs sharing one are competing regular expressions (RealityEngine_Machines#165).
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "check-one-ces-one-pattern.py"
spec = importlib.util.spec_from_file_location("one_ces", SCRIPT)
mod = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(mod)


def ces(cid: str, bits: list[int]) -> dict:
    return {"id": cid, "events": [{"id": f"{cid}-state", "isInitial": True,
                                   "elements": [{"value": b} for b in bits]}]}


def inp(name: str, bits: list[int], out: list[int]) -> dict:
    return {"name": name, "events": [bits],
            "metadata": {"expectedOutputVector": out, "expectedOutputRegion": {"offset": 0, "length": 4}}}


class OneCesOnePatternTests(unittest.TestCase):
    def found(self, sequences: list[dict], inputs: list[dict] | None = None) -> list[str]:
        doc = {"version": "1.0", "machine": {"name": "Probe", "sequences": sequences,
                                             "inputSequences": inputs or []}}
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "probe.json").write_text(json.dumps(doc))
            return mod.violations(Path(tmp))

    def test_two_cess_sharing_a_pattern_are_a_violation(self) -> None:
        got = self.found([ces("opt", [0, 1, 0]), ces("mon", [0, 1, 0])])
        self.assertEqual(len(got), 1)
        self.assertIn("CESs share one pattern: mon, opt", got[0])

    def test_distinct_patterns_are_not(self) -> None:
        self.assertEqual(self.found([ces("opt", [0, 1, 0]), ces("mon", [0, 0, 1])]), [])

    def test_ids_do_not_make_a_pattern_distinct(self) -> None:
        # Same Reality Events under different ids is still one regular expression.
        self.assertEqual(len(self.found([ces("a", [1, 1]), ces("b", [1, 1])])), 1)

    def test_same_input_expecting_two_outputs_is_a_violation(self) -> None:
        got = self.found([ces("opt", [0, 1]), ces("mon", [1, 0])],
                         [inp("a", [0, 1], [0, 1, 0, 0]), inp("b", [0, 1], [0, 0, 1, 0])])
        self.assertEqual(len(got), 1)
        self.assertIn("expect different outputs: a, b", got[0])

    def test_same_input_same_output_is_not(self) -> None:
        self.assertEqual(self.found([ces("x", [0, 1])],
                                    [inp("a", [0, 1], [1, 0, 0, 0]), inp("b", [0, 1], [1, 0, 0, 0])]), [])

    def test_the_corpus_has_no_violation(self) -> None:
        proc = subprocess.run([sys.executable, str(SCRIPT), "--check"],
                              capture_output=True, text=True, cwd=REPO_ROOT)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
