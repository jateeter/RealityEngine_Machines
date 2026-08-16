#!/usr/bin/env python3
"""The curated interconnection graph, and which machines sit outside it (#49).

`metadata.interconnections` is a *curated* declaration of significant edges, not
a derivation. Region overlap is a separate, implicit coupling the corpus uses
deliberately — 1,429 overlaps are undeclared, and `region-allocation.json`
records 68 shared output lanes and 29 inter-domain buses on purpose. So "no
curated edge" does not mean "not connected", and isolation is not automatically
a defect.

What is a defect is isolation nobody decided on. This pins the set: a machine
joining or leaving it fails, so the question #49 asks — correct, or unfinished
wiring? — has to be answered per machine rather than drifting.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOMAINS_DIR = REPO_ROOT / "machines" / "domains"

# Machine stem -> why it carries no curated edge.
EXPECTED_ISOLATED = {
    # Conformance fixtures. Deliberately outside the graph for the same reason
    # they carry no agent (corpus-exit-v1.0 §3.3): they exist to prove a runtime
    # property in isolation, and coupling them to the corpus would let corpus
    # behaviour perturb what they are proving.
    "ArbitrationProviderPeer": "arbitration conformance fixture (9b)",
    "ArbitrationProviderTarget": "arbitration conformance fixture (9b)",
    "ArbitrationReader": "arbitration conformance fixture (9a)",
    "ArbitrationWriterA": "arbitration conformance fixture (9a)",
    "ArbitrationWriterB": "arbitration conformance fixture (9a)",
    "RSRingLatchStageA": "ring-latch fixture; couples to stage B by region, not by edge",
    "RSRingLatchStageB": "ring-latch fixture; couples to stage A by region, not by edge",

    # Coupled by region, undeclared in the curated graph. Not functionally
    # isolated: FallSensorMotionPreaggregator's output region overlaps
    # FallDetection's input, and HealthKitVitalsMonitor's input is written by
    # DailyActivityWellnessInterconnect. Declaring those edges would change the
    # semantic-bus registry and region allocation, so it is left as a curation
    # gap rather than folded into an unrelated change.
    "FallSensorMotionPreaggregator": "output overlaps FallDetection input; edge undeclared",
    "HealthKitVitalsMonitor": "input written by DailyActivityWellnessInterconnect and by "
                              "the localHealthkitBridge ingest path; edge undeclared",

    # Genuinely standalone, and the open half of #49. Their regions overlap no
    # other machine in either direction. Two are bridge-class, which is the one
    # class whose purpose is to interconnect, so these need a domain owner
    # rather than a mechanical fix.
    "HomeCaregiverSupportResponseInterconnect": "bridge-class, connects nothing — open (#49)",
    "HomeFoodSecurityResponseInterconnect": "bridge-class, connects nothing — open (#49)",
    "CommunityCommandAgent": "no region overlap in either direction — open (#49)",
}


def isolated_machines() -> dict[str, str]:
    """Machines with no curated edge in or out, mapped to their domain."""
    produced: set[str] = set()
    consumed: set[str] = set()
    machines: dict[str, tuple[str, str, bool]] = {}
    for path in sorted(DOMAINS_DIR.glob("*/*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        machine = document.get("machine", document)
        metadata = machine.get("metadata") or {}
        interconnections = metadata.get("interconnections") or []
        machines[path.stem] = (path.parent.name, str(machine.get("name") or ""),
                               bool(interconnections))
        for entry in interconnections:
            if entry.get("sourceMachine"):
                produced.add(str(entry["sourceMachine"]))
            if entry.get("targetMachine"):
                consumed.add(str(entry["targetMachine"]))

    isolated = {}
    for stem, (domain, name, declares) in machines.items():
        if not declares and name not in produced and name not in consumed:
            isolated[stem] = domain
    return isolated


class InterconnectionGraphTest(unittest.TestCase):
    def test_isolated_set_is_exactly_what_was_decided(self) -> None:
        found = set(isolated_machines())
        expected = set(EXPECTED_ISOLATED)
        newly_isolated = sorted(found - expected)
        newly_connected = sorted(expected - found)
        self.assertEqual(
            newly_isolated, [],
            "machines newly outside the curated interconnection graph — decide "
            "whether each is correct and record it in EXPECTED_ISOLATED, or wire "
            "it up:\n" + "\n".join(newly_isolated),
        )
        self.assertEqual(
            newly_connected, [],
            "machines that are no longer isolated — remove them from "
            "EXPECTED_ISOLATED:\n" + "\n".join(newly_connected),
        )

    def test_every_isolation_carries_a_reason(self) -> None:
        blank = sorted(k for k, v in EXPECTED_ISOLATED.items() if not v.strip())
        self.assertEqual(blank, [], f"isolation without a recorded reason: {blank}")


if __name__ == "__main__":
    unittest.main()
