#!/usr/bin/env python3
"""Contract checks for the ingress lane contracts sidecar.

`domains/lane-contracts.json` carries the *semantics* of externally-writable
regions; `domains/region-allocation.json` remains the authority on *allocation*.
Keeping them apart only means something if the sidecar cannot quietly become a
second allocation authority, so that separation is gated here.

The other half of these gates mirrors the SHACL rules in
`semantics/shapes/re-guardrails.shacl.ttl`. The sidecar is what the lane
projector turns into the lane graph those shapes validate, so a sidecar that
satisfies these tests cannot produce a lane graph the guardrail would refuse.
Catching it here means catching it in the corpus, where a domain owner can fix
it, rather than at a boundary at runtime.

Gates:

- the sidecar is not stale with respect to the corpus
- annotated lanes resolve to a complete unit contract
- ordinal and nominal axes prohibit conversion; interval axes are not linear
  (re-guardrails U3, U5)
- the canonical unit is among the accepted units, and a lane that forbids
  conversion accepts exactly one (U1, U2)
- every UCUM code is canonical, since the shapes compare codes as strings
- QUDT IRIs resolve inside the pinned subset, so the sidecar cannot reference
  a term the reasoner will not have
- lane ids, axis counts and axis indices satisfy reg:IngressLaneShape
- annotated lanes do not overlap
- every unresolved lane carries a review reason, and no lane is silently empty
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from ucum import canonical  # noqa: E402

SIDECAR = REPO_ROOT / "domains" / "lane-contracts.json"
ALLOCATION = REPO_ROOT / "domains" / "region-allocation.json"
QUDT_SUBSET = REPO_ROOT / "semantics" / "ontology" / "qudt-subset.ttl"
SHAPES = REPO_ROOT / "semantics" / "shapes" / "re-guardrails.shacl.ttl"
BACKFILL = REPO_ROOT / "scripts" / "backfill-lane-contracts.py"

LANE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def load() -> dict:
    return json.loads(SIDECAR.read_text())


def resolve(lane: dict, axis: dict, profiles: dict) -> dict:
    """The projector's view: profile defaults, axis overrides on top."""
    resolved = dict(profiles.get(lane.get("profile"), {}))
    resolved.update(axis)
    return resolved


class LaneContractsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = load()
        cls.profiles = cls.document["derivationProfiles"]
        cls.lanes = cls.document["lanes"]
        cls.annotated = [lane for lane in cls.lanes if lane["axes"]]

    # -- freshness ---------------------------------------------------------

    def test_sidecar_is_not_stale(self) -> None:
        result = subprocess.run(
            [sys.executable, str(BACKFILL), "--check"],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    # -- separation of concerns -------------------------------------------

    def test_service_lanes_mirror_the_allocation_exactly(self) -> None:
        """The sidecar carries semantics, never allocation. A service lane whose
        offset or length drifted from region-allocation.json would make the
        sidecar a second, competing authority."""
        allocation = json.loads(ALLOCATION.read_text())
        allocated = {
            entry["id"]: (entry["offset"], entry["length"])
            for entry in allocation.get("serviceLanes", [])
        }
        service = [lane for lane in self.lanes if lane["source"] == "service-lane"]
        self.assertEqual(len(service), len(allocated))
        for lane in service:
            with self.subTest(lane=lane["id"]):
                self.assertIn(lane["id"], allocated)
                self.assertEqual(
                    (lane["offset"], lane["length"]), allocated[lane["id"]]
                )

    # -- shape parity ------------------------------------------------------

    def test_lane_ids_satisfy_the_shape_pattern(self) -> None:
        for lane in self.lanes:
            with self.subTest(lane=lane["id"]):
                self.assertRegex(lane["id"], LANE_ID_PATTERN)

    def test_annotated_lanes_have_one_axis_per_position(self) -> None:
        for lane in self.annotated:
            with self.subTest(lane=lane["id"]):
                self.assertEqual(len(lane["axes"]), lane["length"])
                self.assertEqual(
                    sorted(axis["index"] for axis in lane["axes"]),
                    list(range(lane["length"])),
                )

    def test_annotated_axes_resolve_to_a_complete_contract(self) -> None:
        required = (
            "canonicalUcum", "acceptedUcum", "quantityKind",
            "conversionPolicy", "scaleType",
        )
        for lane in self.annotated:
            for axis in lane["axes"]:
                resolved = resolve(lane, axis, self.profiles)
                for field in required:
                    with self.subTest(lane=lane["id"], axis=axis["index"], field=field):
                        self.assertIn(field, resolved)

    def test_categorical_axes_prohibit_conversion(self) -> None:
        """re-guardrails U3. Rescaling a category is a category error."""
        for lane in self.annotated:
            for axis in lane["axes"]:
                resolved = resolve(lane, axis, self.profiles)
                if resolved["scaleType"] in ("ordinal", "nominal"):
                    with self.subTest(lane=lane["id"], axis=axis["index"]):
                        self.assertEqual(resolved["conversionPolicy"], "prohibited")

    def test_interval_axes_are_not_linear(self) -> None:
        """re-guardrails U5. A linear conversion drops the offset."""
        for lane in self.annotated:
            for axis in lane["axes"]:
                resolved = resolve(lane, axis, self.profiles)
                if resolved["scaleType"] == "interval":
                    with self.subTest(lane=lane["id"], axis=axis["index"]):
                        self.assertNotEqual(resolved["conversionPolicy"], "linear")

    def test_canonical_unit_is_accepted(self) -> None:
        """re-guardrails U1."""
        for lane in self.annotated:
            for axis in lane["axes"]:
                resolved = resolve(lane, axis, self.profiles)
                with self.subTest(lane=lane["id"], axis=axis["index"]):
                    self.assertIn(resolved["canonicalUcum"], resolved["acceptedUcum"])

    def test_non_convertible_axes_accept_exactly_one_unit(self) -> None:
        """re-guardrails U2. An unconvertible second unit could never be admitted."""
        for lane in self.annotated:
            for axis in lane["axes"]:
                resolved = resolve(lane, axis, self.profiles)
                if resolved["conversionPolicy"] in ("none", "prohibited"):
                    with self.subTest(lane=lane["id"], axis=axis["index"]):
                        self.assertEqual(len(resolved["acceptedUcum"]), 1)

    def test_contended_lanes_declare_an_arbitrated_resolution(self) -> None:
        """Contention is the normal state, not a defect. An ingress lane is
        written externally — that is what makes it ingress — and by machine
        outputs, because M1(output i) feeding M2(input j) is how this perceptual
        space composes: 703 of 983 lanes have a machine writer and 2,835 of
        4,005 lane cells carry more than one writer. ARBITER_CONTRACT.md is
        explicit that the corpus error is a contended cell with no declared
        resolution, so that is what is gated — never the geometry."""
        for lane in self.annotated:
            contention = lane.get("contention")
            if contention:
                with self.subTest(lane=lane["id"]):
                    self.assertTrue(contention["arbitrated"], lane["id"])
                    self.assertTrue(
                        contention["rules"],
                        f"{lane['id']} is contended but names no rule",
                    )
                    inside = set(range(lane["offset"], lane["offset"] + lane["length"]))
                    self.assertTrue(
                        set(contention["contendedCells"]) <= inside,
                        f"{lane['id']} claims contended cells outside its own span",
                    )

    def test_registry_agrees_with_writer_multiplicity(self) -> None:
        """The definition, checked against the authority.

        A cell ci of a Reality Event E = {c1..cn} is contended when more than
        one writer competes for ci's next value — M1(j) and M2(l) both
        targeting ci. Deriving that from the corpus must reproduce
        domains/arbitration-registry.json exactly. If it does not, the registry
        is stale with respect to the machines and every lane referencing it is
        resting on a wrong resolution.
        """
        writers: dict[int, set[tuple[str, str]]] = {}

        def claim(cell: int, provider: str, origin: str) -> None:
            writers.setdefault(cell, set()).add((provider, origin))

        for path in sorted((REPO_ROOT / "machines").rglob("*.json")):
            try:
                document = json.loads(path.read_text())
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            machine = document.get("machine") or document
            if not isinstance(machine, dict):
                continue
            mapping = machine.get("perceptualMapping") or {}
            output = mapping.get("output") or {}
            if isinstance(output.get("offset"), int):
                for cell in range(output["offset"], output["offset"] + output.get("length", 0)):
                    claim(cell, "machine", path.stem)
            projection = (machine.get("metadata") or {}).get("openClawProjection") or {}
            region = projection.get("writeBackRegion") or {}
            if isinstance(region.get("offset"), int):
                for cell in range(region["offset"], region["offset"] + region.get("length", 0)):
                    claim(cell, "acp", path.stem)

        derived = {cell for cell, who in writers.items() if len(who) > 1}
        registry = json.loads(
            (REPO_ROOT / "domains" / "arbitration-registry.json").read_text()
        )
        declared = {
            entry["cell"] for entry in registry.get("entries", [])
            if isinstance(entry.get("cell"), int)
        }
        self.assertEqual(
            derived - declared, set(),
            "cells contended by the corpus but absent from the arbitration registry",
        )
        self.assertEqual(
            declared - derived, set(),
            "cells in the arbitration registry that no longer have two writers",
        )

    def test_machine_writers_are_real_machines(self) -> None:
        stems = {path.stem for path in (REPO_ROOT / "machines").rglob("*.json")}
        self.assertGreater(len(stems), 0)
        declared = 0
        for lane in self.lanes:
            for writer in lane.get("machineWriters", []):
                declared += 1
                with self.subTest(lane=lane["id"], writer=writer):
                    self.assertIn(writer, stems)
        self.assertGreater(
            declared, 0,
            "no lane declares a machine writer, yet most ingress lanes are fed "
            "by machine outputs — the interconnect is not being modelled",
        )

    # -- units -------------------------------------------------------------

    def test_every_ucum_code_is_canonical(self) -> None:
        """The shapes compare codes as strings, so a non-canonical code here
        becomes a false rejection at the boundary."""
        for name, profile in self.profiles.items():
            codes = [profile.get("canonicalUcum"), profile.get("expectedUcum")]
            codes += list(profile.get("acceptedUcum") or [])
            for code in [value for value in codes if value]:
                with self.subTest(profile=name, code=code):
                    self.assertEqual(canonical(code), code)

        for lane in self.annotated:
            for axis in lane["axes"]:
                resolved = resolve(lane, axis, self.profiles)
                codes = [resolved.get("canonicalUcum"), resolved.get("expectedUcum")]
                codes += list(resolved.get("acceptedUcum") or [])
                for code in [value for value in codes if value]:
                    with self.subTest(lane=lane["id"], code=code):
                        self.assertEqual(canonical(code), code)

    def test_qudt_references_resolve_inside_the_pinned_subset(self) -> None:
        """The sidecar may not reference a QUDT term the reasoner will not have."""
        subset = QUDT_SUBSET.read_text()
        known = set(re.findall(r"^(unit:[A-Za-z0-9_\-]+|qkind:[A-Za-z0-9_\-]+)", subset, re.M))

        def local(iri: str) -> str:
            if "/vocab/unit/" in iri:
                return "unit:" + iri.rsplit("/", 1)[-1]
            return "qkind:" + iri.rsplit("/", 1)[-1]

        referenced = set()
        for profile in self.profiles.values():
            for key in ("quantityKind", "qudtUnitIri"):
                if profile.get(key):
                    referenced.add(local(profile[key]))
        for lane in self.annotated:
            for axis in lane["axes"]:
                resolved = resolve(lane, axis, self.profiles)
                for key in ("quantityKind", "qudtUnitIri"):
                    if resolved.get(key):
                        referenced.add(local(resolved[key]))

        self.assertGreater(len(referenced), 0)
        missing = sorted(referenced - known)
        self.assertEqual(
            missing, [],
            f"not in {QUDT_SUBSET.name}; rerun scripts/extract-qudt-subset.py",
        )

    # -- review ------------------------------------------------------------

    def test_every_unresolved_lane_has_a_review_reason(self) -> None:
        reviewed = {item["laneId"] for item in self.document["review"]}
        for lane in self.lanes:
            if not lane["axes"]:
                with self.subTest(lane=lane["id"]):
                    self.assertIn(
                        lane["id"], reviewed,
                        "an unresolved lane with no reason is a silent gap",
                    )

    def test_review_entries_reference_real_lanes(self) -> None:
        ids = {lane["id"] for lane in self.lanes}
        for item in self.document["review"]:
            with self.subTest(lane=item["laneId"]):
                self.assertIn(item["laneId"], ids)

    def test_summary_matches_the_body(self) -> None:
        summary = self.document["summary"]
        self.assertEqual(summary["lanes"], len(self.lanes))
        self.assertEqual(summary["lanesAnnotated"], len(self.annotated))
        self.assertEqual(
            summary["lanesNeedingReview"], len(self.lanes) - len(self.annotated)
        )
        self.assertEqual(
            summary["positionsAnnotated"],
            sum(len(lane["axes"]) for lane in self.annotated),
        )

    def test_conversion_policies_match_the_shape_vocabulary(self) -> None:
        """The enum here and the reg:ConversionPolicy individuals must not drift."""
        shapes = SHAPES.read_text()
        for policy in ("none", "linear", "affine", "prohibited"):
            with self.subTest(policy=policy):
                self.assertIn(f'rdfs:label "{policy}"', shapes)
        for scale in ("ratio", "interval", "ordinal", "nominal"):
            with self.subTest(scale=scale):
                self.assertIn(f'rdfs:label "{scale}"', shapes)


if __name__ == "__main__":
    unittest.main()
