#!/usr/bin/env python3
"""M4 runtime trace RDF, as a gate (all three acceptance criteria).

`scripts/export-runtime-trace.py` converts one PE->RE->PE cycle into a graph in
the M2/M4 vocabulary. This makes running it a requirement, for the reason M3
needed the same treatment: a checker nobody invokes is not a gate, and this
repository already had one of those — `generate-regression-profile.py --check`,
present since it was written and called by nothing.

## The three criteria, and which of them needs a universe

| Criterion | Needs a live universe |
|---|---|
| Trace export — a complete RDF/JSON-LD trace for one cycle | yes |
| Joinability — every event joins to a machine IRI or an explicit provider IRI | yes |
| Non-blocking PE — no synchronous ROBOT call in `POST /api/push` | **no** |

The third is a property of the source, not of a run, so it is checked always and
never skipped. That split matters: the two that need a universe would otherwise
take the third down with them on every hosted run, and criterion 3 is the one
that protects the hot path.

## What is deliberately not asserted

That the trace is non-empty *without* `--push`. A universe that has not been
driven has an empty audit surface, and requiring records there would make the
gate depend on whatever happened to run before it.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import unittest
import urllib.error
import urllib.request
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = REPO_ROOT.parent
EXPORTER = REPO_ROOT / "scripts" / "export-runtime-trace.py"
ONTOLOGY = REPO_ROOT / "semantics" / "ontology" / "re-core.ttl"
REGISTRY = os.environ.get("RE_REGISTRY_URL", "http://127.0.0.1:5999/re-registry.json")

# The four runtimes that own a PE push path. ROBOT must never appear in any of
# them; the reasoner runs out of band, over an exported trace.
PUSH_PATH_SOURCES = [
    WORKSPACE / "RealityEngine_CPP" / "src",
    WORKSPACE / "RealityEngine_LSP" / "src",
    WORKSPACE / "RealityEngine_Scala" / "src",
    WORKSPACE / "RealityEngine_Manager" / "perception-engine" / "backend" / "src",
]

# The six runtime event kinds M4 requires RDF for.
M4_EVENT_CLASSES = [
    "re:PerceptionEvent",       # PE source write
    "re:PerceptionPush",        # PE push
    "re:SequenceObservation",   # RE sequence observation
    "re:MCPInvocation",         # MCP/localAIStack invocation
    "re:ACPDispatch",           # ACP/OpenClaw dispatch
    "re:SourceMappingWrite",    # completion write-back
]


def universe_is_up() -> bool:
    try:
        with urllib.request.urlopen(REGISTRY, timeout=5) as r:
            return bool(json.loads(r.read()).get("instances"))
    except Exception:
        return False


def run_exporter(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(EXPORTER), *args],
                          cwd=REPO_ROOT, capture_output=True, text=True, timeout=900)


class NonBlockingPushTests(unittest.TestCase):
    """Criterion 3. Always runs — it is a property of the source."""

    def test_no_engine_push_path_references_a_reasoner(self) -> None:
        offenders = []
        for root in PUSH_PATH_SOURCES:
            if not root.is_dir():
                continue          # sibling repo not checked out
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                if path.suffix not in (".cpp", ".hpp", ".h", ".lisp", ".scala",
                                       ".ts", ".js"):
                    continue
                text = path.read_text(errors="ignore")
                if re.search(r"\b(robot|HermiT|OWLAPI|owlapi|reasoner)\b", text):
                    offenders.append(str(path.relative_to(WORKSPACE)))
        self.assertEqual(
            offenders, [],
            "a reasoner is referenced inside a runtime's source tree. M4's third "
            "criterion is that trace export adds no synchronous ROBOT call to "
            "POST /api/push; ROBOT takes seconds to minutes and the push path is "
            "the hot path:\n  " + "\n  ".join(offenders))

    def test_the_exporter_lives_outside_the_engines(self) -> None:
        # Structural, and the reason criterion 3 holds by construction rather
        # than by discipline: the exporter reads finished surfaces over HTTP and
        # is not linked into any runtime, so it cannot be on the push path.
        self.assertTrue(EXPORTER.is_file())
        for root in PUSH_PATH_SOURCES:
            if root.is_dir():
                self.assertNotIn(
                    "export-runtime-trace",
                    " ".join(p.name for p in root.rglob("*") if p.is_file()),
                    f"the exporter appears inside {root}")


class RuntimeTraceVocabularyTests(unittest.TestCase):
    """The vocabulary M4 needs must exist, universe or not."""

    def test_every_m4_event_kind_has_a_class(self) -> None:
        ontology = ONTOLOGY.read_text()
        missing = [c for c in M4_EVENT_CLASSES
                   if not re.search(rf"^{re.escape(c)} a owl:Class", ontology, re.M)]
        self.assertEqual(missing, [],
                         f"M4 requires RDF for event kinds with no class: {missing}")

    def test_the_run_grouping_exists(self) -> None:
        ontology = ONTOLOGY.read_text()
        for term in ("re:TraceRun", "re:runId", "re:inTraceRun", "re:engineId"):
            self.assertIn(term, ontology,
                          f"{term} is missing; without a run grouping, two merged "
                          f"traces are one indistinguishable pile of events")


class TraceExportTests(unittest.TestCase):
    """Criteria 1 and 2. Need a live universe, and say so when they skip."""

    @classmethod
    def setUpClass(cls) -> None:
        if not universe_is_up():
            raise unittest.SkipTest(
                f"no instance registry at {REGISTRY}; criteria 1 and 2 describe a "
                f"run, and there is nothing running. Criterion 3 is checked "
                f"separately and does not skip.")

    def test_export_produces_a_complete_trace_for_one_cycle(self) -> None:
        """M4 acceptance criterion 1."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            ttl = Path(tmp) / "trace.ttl"
            jsonld = Path(tmp) / "trace.jsonld"
            proc = run_exporter("--push", "--out", str(ttl), "--jsonld", str(jsonld))
            self.assertEqual(proc.returncode, 0,
                             f"export failed\n{proc.stdout}\n{proc.stderr}")
            self.assertTrue(ttl.is_file() and ttl.stat().st_size > 0,
                            "no Turtle was written")
            self.assertTrue(jsonld.is_file(), "no JSON-LD was written")
            json.loads(jsonld.read_text())      # must be parseable, not merely present

            text = ttl.read_text()
            # A trace with a header and no events is a file, not a trace.
            for required in ("re:TraceRun", "re:PerceptionPush", "re:SequenceObservation"):
                self.assertIn(required, text,
                              f"the exported trace contains no {required}")

    def test_every_event_joins_to_a_machine_or_a_provider(self) -> None:
        """M4 acceptance criterion 2."""
        proc = run_exporter("--push", "--check-joinability")
        self.assertEqual(
            proc.returncode, 0,
            "runtime events join to nothing. Every event must reach either a "
            "corpus machine IRI or an explicit external-provider IRI; an event "
            "that reaches neither cannot be reasoned about alongside the corpus "
            "it came from.\n" + proc.stdout + proc.stderr)
        self.assertRegex(proc.stdout, r"joinability: (\d+)/\1 events",
                         "the exporter did not report full joinability")

    def test_the_joinability_check_can_fail(self) -> None:
        """The negative case, on the parsing rule rather than on a live universe.

        `--check-joinability` returning 0 must mean "everything joined", not
        "nothing was examined". The provider fallback is what decides whether an
        unknown machine joins, so that decision is exercised directly: a name
        with no provider prefix must not resolve.
        """
        import importlib.util

        spec = importlib.util.spec_from_file_location("exporter", EXPORTER)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        self.assertEqual(mod.provider_of("localai/agent_activity_classifier"), "localai")
        self.assertIsNone(mod.provider_of("FallDetection"),
                          "a bare machine name must not be treated as provider-supplied, "
                          "or an unjoinable event would be silently attributed")
        self.assertIsNone(mod.provider_of(None))

    def test_the_corpus_join_goes_through_the_stable_key(self) -> None:
        """machineName, never machineId.

        Machine ids are re-minted by each runtime on import, so the same machine
        is `machine-falldetection` on one engine and a different string on
        another. A trace keyed on the id measures the runtime rather than the
        corpus — the defect the CES contract recorder was rebuilt to remove.
        """
        import importlib.util

        spec = importlib.util.spec_from_file_location("exporter", EXPORTER)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        iris = mod.corpus_machine_iris()
        self.assertGreater(len(iris), 100, "the corpus IRI map is implausibly small")
        # Keys are display names, not ids: no key may look like a runtime id.
        id_shaped = [k for k in iris if k.startswith("machine-")]
        self.assertEqual(id_shaped, [],
                         f"the corpus join is keyed on runtime ids: {id_shaped[:5]}")


if __name__ == "__main__":
    unittest.main()
