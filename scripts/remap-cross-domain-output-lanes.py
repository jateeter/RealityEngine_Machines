#!/usr/bin/env python3
"""Remap cross-domain output-lane collisions (2026-07 allocation pass).

The 35 cross-domain sharedOutputLanes groups in the allocation registry all
follow one pattern: a domain's chained stage pipeline owns a band (HSPH
3823-3851, TFX 3855-3899, legacy digital-logic 3915-3921, health-personal
wellness 3923-3949, AGX 3971-4049, DCX 4061-4109) and machines from other
domains were generated onto the same cells. Domain-bus publication is
PE-composed from each machine's declared sourceOutputRegion, so relocating an
interloper's output lane keeps its bus routing intact — cross-domain flow
stays on the published domain buses.

This script moves ONLY writer lanes (machine perceptualMapping.output); no
machine input lane moves, so external write-backs, PE source mappings, and
OpenClaw agent projections stay valid. For every mover it updates:

  - perceptualMapping.output.offset in the mover's file
  - metadata.interconnections sourceOutputRegion entries matching the old lane
  - "[old:end]" textual ranges in the mover's own metadata strings
  - region dicts equal to the old lane in ANY corpus file whose enclosing
    object names the mover (busOutputRegion/publishedOutputRegion/composition
    references to a moved bus or producer)

Relocation blocks live in the free window at 7300-7440 (verified against the
allocation registry: no machine lanes, bus lanes, service lanes, or reserved
bands). Regenerate the derived artifacts afterwards:

  npm run semantic-buses:write && npm run corpus-index:write && \
  npm run region-allocation:write && node scripts/cesgen-oracles.mjs && \
  node scripts/cesgen-contracts.mjs

Usage: python3 scripts/remap-cross-domain-output-lanes.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
MACHINES = REPO_ROOT / "machines"

# mover basename -> (old_offset, length, new_offset)
PLAN: dict[str, tuple[int, int, int]] = {
    # community-services interlopers on the HSPH/TFX bands -> 7300-7343
    "CSX021_behavioral-health-and-crisis-988-warm-handoff-router.json": (3831, 4, 7300),
    "CSX025_behavioral-health-and-crisis-youth-crisis-pathway.json": (3823, 4, 7304),
    "CSX032_law-enforcement-and-public-safety-community-policing-beat-monitor.json": (3867, 4, 7308),
    "CSX045_courts-diversion-and-victim-services-victim-advocate-assignment.json": (3891, 4, 7312),
    "CSX052_homelessness-outreach-encampment-risk-assessment.json": (3855, 4, 7316),
    "CSX057_homelessness-outreach-meal-outreach-routing.json": (3843, 4, 7320),
    "CSX064_shelter-housing-and-supportive-services-rapid-rehousing-progress.json": (3887, 4, 7324),
    "CSX073_city-service-operations-streetlight-safety-repair.json": (3827, 4, 7328),
    "CSX075_city-service-operations-public-restroom-operations.json": (3859, 4, 7332),
    "CSX088_community-executive-optimization-community-operations-digital-twin.json": (3847, 4, 7336),
    "CSX089_community-executive-optimization-public-trust-feedback-loop.json": (3895, 4, 7340),
    # life-balance interlopers -> 7350-7365
    "LBL093_projection-automation-and-outcomes-plan-adjustment-dispatcher.json": (3931, 4, 7350),
    "LBL094_projection-automation-and-outcomes-care-team-escalation-router.json": (3831, 4, 7354),
    "LBL098_projection-automation-and-outcomes-medication-lifestyle-e2e.json": (3939, 4, 7358),
    "LBL100_projection-automation-and-outcomes-life-balance-command-center.json": (3847, 4, 7362),
    # health-personal interlopers -> 7370-7381
    "NewPatientInflow.json": (3915, 8, 7370),
    "PatientSafetyTransportInterconnect.json": (3827, 4, 7378),
    # ai-services interlopers -> 7390-7403
    "AIHardwareResilience.json": (3923, 6, 7390),
    "AIWellnessCoach.json": (3941, 8, 7396),
    # digital-logic interlopers on the AGX/DCX bands -> 7410-7439
    "DLX001_rising-edge-detector.json": (3971, 2, 7410),
    "DLX004_pulse-stretch-start.json": (3987, 2, 7412),
    "DLX005_pulse-stretch-end.json": (3993, 2, 7414),
    "DLX008_stable-high-window.json": (4007, 2, 7416),
    "DLX009_stable-low-window.json": (4009, 2, 7418),
    "DLX012_req-hold-ack.json": (4025, 2, 7420),
    "DLX013_req-ack-done.json": (4031, 2, 7422),
    "DLX016_ready-before-valid.json": (4045, 2, 7424),
    "DLX017_start-busy-done.json": (4047, 2, 7426),
    "DLX039_fifo-full-to-not-full.json": (4061, 2, 7428),
    "DLX042_mutex-lock-unlock.json": (4075, 2, 7430),
    "DLX043_arbiter-request-grant-release.json": (4077, 2, 7432),
    "DLX046_write-response.json": (4091, 2, 7434),
    "DLX047_read-response.json": (4093, 2, 7436),
    "DLX050_metastability-settled.json": (4107, 2, 7438),
}


def is_region(node: Any, offset: int, length: int) -> bool:
    return (
        isinstance(node, dict)
        and node.get("offset") == offset
        and node.get("length") == length
    )


def retext(value: str, old: tuple[int, int], new_offset: int) -> str:
    """Rewrite '[old:oldend]' range literals in metadata prose."""
    old_lit = f"[{old[0]}:{old[0] + old[1]}]"
    new_lit = f"[{new_offset}:{new_offset + old[1]}]"
    return value.replace(old_lit, new_lit)


def rewrite_strings(node: Any, old: tuple[int, int], new_offset: int) -> Any:
    if isinstance(node, str):
        return retext(node, old, new_offset)
    if isinstance(node, list):
        return [rewrite_strings(x, old, new_offset) for x in node]
    if isinstance(node, dict):
        return {k: rewrite_strings(v, old, new_offset) for k, v in node.items()}
    return node


def mentions_mover(node: dict[str, Any], mover_names: set[str]) -> bool:
    for v in node.values():
        if isinstance(v, str) and any(n in v for n in mover_names):
            return True
    return False


def update_regions(node: Any, old: tuple[int, int], new_offset: int,
                   mover_names: set[str], require_mention: bool, path: str = "") -> int:
    """Update region dicts equal to OLD. When require_mention is set, only
    inside objects whose direct string values name the mover."""
    changed = 0
    if isinstance(node, dict):
        allowed = not require_mention or mentions_mover(node, mover_names)
        for k, v in node.items():
            if is_region(v, old[0], old[1]) and allowed:
                v["offset"] = new_offset
                changed += 1
            else:
                changed += update_regions(v, old, new_offset, mover_names, require_mention, f"{path}/{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            changed += update_regions(v, old, new_offset, mover_names, require_mention, f"{path}[{i}]")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    files = {p.name: p for p in MACHINES.rglob("*.json")}
    missing = [n for n in PLAN if n not in files]
    if missing:
        print(f"ABORT — movers not found: {missing}", file=sys.stderr)
        return 1

    # mover name lookup for cross-file reference matching
    mover_names: dict[str, set[str]] = {}
    for basename in PLAN:
        root = json.loads(files[basename].read_text())
        machine_name = str(root.get("machine", {}).get("name", ""))
        mover_names[basename] = {basename, basename[:-5]} | ({machine_name} if machine_name else set())

    total_region_updates = 0
    # 1) mover files: output mapping + own sourceOutputRegion entries + prose
    for basename, (old_o, length, new_o) in sorted(PLAN.items()):
        path = files[basename]
        root = json.loads(path.read_text())
        machine = root["machine"]
        out = machine.get("perceptualMapping", {}).get("output", {})
        if out.get("offset") != old_o or out.get("length") != length:
            print(f"ABORT — {basename} output is {out}, expected {{offset:{old_o},length:{length}}}", file=sys.stderr)
            return 1
        out["offset"] = new_o
        n = update_regions(machine.get("metadata", {}), (old_o, length), new_o, mover_names[basename], require_mention=False)
        root["machine"] = rewrite_strings(machine, (old_o, length), new_o)
        total_region_updates += n
        print(f"  {basename}: output {old_o}:{length} -> {new_o} (+{n} metadata region refs)")
        if not args.dry_run:
            path.write_text(json.dumps(root, indent=2) + "\n")

    # 2) other corpus files referencing a mover's old lane by name
    for path in sorted(files.values()):
        if path.name in PLAN:
            continue
        raw = path.read_text()
        root = json.loads(raw)
        changed = 0
        for basename, (old_o, length, new_o) in PLAN.items():
            changed += update_regions(root, (old_o, length), new_o, mover_names[basename], require_mention=True)
        if changed:
            print(f"  {path.name}: {changed} cross-file region ref(s) updated")
            total_region_updates += changed
            if not args.dry_run:
                path.write_text(json.dumps(root, indent=2) + "\n")

    print(f"{'DRY RUN — ' if args.dry_run else ''}movers: {len(PLAN)}, region reference updates: {total_region_updates}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
