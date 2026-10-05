#!/usr/bin/env python3
"""scripts/check-input-sequence-contradictions.py (RealityEngine_Machines#165).

Two inputSequences of one machine with identical events are the same input;
expecting two different outputs from it is unsatisfiable by construction. The
check must find that, must not flag the two legitimate neighbours (same input
and same output, or different inputs), and the corpus must pass --check against
its baseline.
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
SCRIPT = REPO_ROOT / "scripts" / "check-input-sequence-contradictions.py"
spec = importlib.util.spec_from_file_location("contradictions", SCRIPT)
mod = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(mod)


def machine(*sequences: tuple[str, list, list]) -> dict:
    return {"version": "1.0", "machine": {"name": "Probe", "inputSequences": [
        {"name": name, "events": events,
         "metadata": {"expectedOutputVector": out, "expectedOutputRegion": {"offset": 0, "length": 4}}}
        for name, events, out in sequences]}}


class ContradictionTests(unittest.TestCase):
    def found(self, doc: dict) -> list[dict]:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "probe.json").write_text(json.dumps(doc))
            return mod.contradictions(Path(tmp))

    def test_same_input_different_output_is_a_contradiction(self) -> None:
        got = self.found(machine(("a", [[0, 1]], [1, 0, 0, 0]), ("b", [[0, 1]], [0, 1, 0, 0])))
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["sequences"], ["a", "b"])

    def test_same_input_same_output_is_not(self) -> None:
        self.assertEqual(self.found(machine(("a", [[0, 1]], [1, 0, 0, 0]),
                                            ("b", [[0, 1]], [1, 0, 0, 0]))), [])

    def test_different_inputs_are_not(self) -> None:
        self.assertEqual(self.found(machine(("a", [[0, 1]], [1, 0, 0, 0]),
                                            ("b", [[1, 0]], [0, 1, 0, 0]))), [])

    def test_the_corpus_passes_against_its_baseline(self) -> None:
        proc = subprocess.run([sys.executable, str(SCRIPT), "--check"],
                              capture_output=True, text=True, cwd=REPO_ROOT)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
