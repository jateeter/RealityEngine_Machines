#!/usr/bin/env python3
"""Build (or verify) the arbitration registry at domains/arbitration-registry.json.

A position in the universal input event vector is *contended* when more than one
writer targets it. When that happens something must decide the resolved value,
and `docs/ARBITER_CONTRACT.md` requires that decision be declared rather than
defaulted: an undeclared contended cell is a corpus error, not a runtime default.

Writers are NOT only machines. A PE source emitting through an integration
surface is structurally identical to a machine emitting a final Reality Event —
both are contributions to a position (ARBITER_CONTRACT.md 1.1). Deriving from
machine outputs alone misses the dominant case: a deterministic machine
determination and a generated agent assessment landing on one cell.

Two writer classes are derived here:

  machine  — cells targeted by a final Reality Event, i.e. an output vector
             element within the machine's declared output region. Counted per
             MACHINE, not per output event: one machine's several mutually
             exclusive determinations writing its own output region are not
             contention, and counting them as such inflates the population by
             an order of magnitude.

  acp      — cells targeted by an OpenClaw input-analyst write-back, from
             metadata.openClawProjection.writeBackRegion.

Other integration surfaces (mcp, mqtt, healthkit, localai, sensor) register
their write-back regions outside the corpus, so they cannot be derived here.
They are admitted through the same registry by the same rule; see
ARBITER_CONTRACT.md 3.1.

Usage:
  python3 scripts/build-arbitration-registry.py --write
  python3 scripts/build-arbitration-registry.py --check   # CI / validate hook
  python3 scripts/build-arbitration-registry.py --summary
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
MACHINES = REPO_ROOT / "machines"
REGISTRY = REPO_ROOT / "domains" / "arbitration-registry.json"

SCHEMA_VERSION = "1.0.0"

# Default provider ranks for PRECEDENCE (ARBITER_CONTRACT.md 4.3a). Ranked by
# determinism class, not by provider identity: a deterministic contribution is
# derivable from the corpus and IS(k) alone, a generated one is not derivable
# from anything, and letting the irreproducible term win makes IS(k+1)
# irreproducible along with every determination downstream of it.
DEFAULT_RANKS = {"machine": 3, "acp": 1}

# The HSPH convergence blocks: four writers (signal-monitor, capacity-balancer,
# agent-dispatcher, outcome-stabilizer) converging on three readers
# (resource-router, referral-optimizer, governance-escalator), the same shape
# repeating across blocks. A plain OR would collapse four contributors to one
# bit and discard which of them asserted, so these resolve by SEVERITY with
# provenance retained.
HSPH_WRITER_ROLES = ("signal-monitor", "capacity-balancer",
                     "agent-dispatcher", "outcome-stabilizer")


def load_machines() -> list[tuple[str, dict[str, Any]]]:
    out = []
    for path in sorted(MACHINES.rglob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        machine = doc.get("machine")
        if machine:
            out.append((path.relative_to(MACHINES).as_posix(), machine))
    return out


def derive_writers(machines) -> tuple[dict[int, set], dict[int, set]]:
    """Return (writers, readers) keyed by cell.

    writers[cell] = {(provider, originId)}  — deduplicated per machine, so a
    machine's multiple output events over its own region count once.
    readers[cell] = {machineFile} whose declared input region covers the cell.
    """
    writers: dict[int, set] = defaultdict(set)
    readers: dict[int, set] = defaultdict(set)
    for rel, m in machines:
        pm = m.get("perceptualMapping") or {}
        inp, outp = pm.get("input"), pm.get("output")
        if inp:
            for c in range(inp["offset"], inp["offset"] + inp["length"]):
                readers[c].add(rel)
        if outp:
            for seq in m.get("sequences") or []:
                for vec in seq.get("vectors") or []:
                    for ov in vec.get("outputVectors") or []:
                        n = min(len(ov.get("vector") or []), outp["length"])
                        for k in range(n):
                            writers[outp["offset"] + k].add(("machine", rel))
        proj = (m.get("metadata") or {}).get("openClawProjection") or {}
        region = proj.get("writeBackRegion")
        if region:
            sid = proj.get("projectionId") or rel
            for c in range(region["offset"], region["offset"] + region["length"]):
                writers[c].add(("acp", sid))
    return writers, readers


def is_hsph_block(writer_files: list[str]) -> bool:
    if len(writer_files) < 2:
        return False
    if not all(Path(f).name.startswith("HSPH") for f in writer_files):
        return False
    return sum(any(role in f for role in HSPH_WRITER_ROLES) for f in writer_files) >= 2


def choose_rule(writers_at_cell: list[tuple[str, str]]) -> tuple[str, str | None, str]:
    """Return (rule, withinRank, rationale) for a contended cell.

    A cell can be contended on two axes at once, and in this corpus almost all of
    them are: a machine determination contending with a generated assessment
    (cross-class), while several machine determinations also contend with each
    other (within-class). PRECEDENCE alone resolves only the first and then falls
    back to MAX among the winners, which for a four-way convergence collapses the
    contributors to one bit and discards which asserted. `withinRank` declares how
    the winning class resolves among itself.
    """
    providers = {p for p, _ in writers_at_cell}
    machine_files = [o for p, o in writers_at_cell if p == "machine"]
    multi_machine = len(machine_files) > 1

    if providers - {"machine"}:
        if is_hsph_block(machine_files):
            return ("PRECEDENCE", "SEVERITY",
                    "HSPH convergence block that is also agent-projected: PRECEDENCE keeps "
                    "the generated assessment below the machine determinations, and SEVERITY "
                    "resolves among those determinations rather than collapsing four "
                    "contributors to one bit")
        if multi_machine:
            return ("PRECEDENCE", "SEVERITY",
                    "several machine determinations contend beneath a generated assessment; "
                    "PRECEDENCE ranks the classes and SEVERITY resolves within the winning one")
        return ("PRECEDENCE", None,
                "a single deterministic machine determination contends with a generated "
                "assessment; the irreproducible contribution may not override the "
                "reproducible one (ARBITER_CONTRACT.md 4.3a)")
    if is_hsph_block(machine_files):
        return ("SEVERITY", None,
                "HSPH convergence block: four writers onto shared readers. OR would "
                "collapse them to one bit and discard which asserted, so resolve by "
                "severity with provenance retained")
    return ("SEVERITY", None,
            "multiple machine determinations on one position; resolve by severity "
            "with provenance retained pending a domain-specific decision")


def build(machines) -> dict[str, Any]:
    writers, readers = derive_writers(machines)
    entries = []
    for cell in sorted(writers):
        at = sorted(writers[cell])
        if len(at) < 2:
            continue
        rule, within, rationale = choose_rule(at)
        entry: dict[str, Any] = {
            "cell": cell,
            "rule": rule,
            "writers": [{"provider": p, "originId": o} for p, o in at],
            "readers": sorted(readers.get(cell, [])),
            "rationale": rationale,
        }
        if within:
            entry["withinRank"] = within
        if rule == "PRECEDENCE":
            entry["providerRanks"] = {p: DEFAULT_RANKS.get(p, 1) for p in sorted({p for p, _ in at})}
        entries.append(entry)

    by_rule: dict[str, int] = defaultdict(int)
    by_class: dict[str, int] = defaultdict(int)
    by_within: dict[str, int] = defaultdict(int)
    for e in entries:
        key = e["rule"] + (f"+{e['withinRank']}" if e.get("withinRank") else "")
        by_rule[key] += 1
        by_within[e.get("withinRank") or "(none)"] += 1
        providers = {w["provider"] for w in e["writers"]}
        by_class["machine-only" if providers == {"machine"} else "machine+provider"] += 1

    return {
        "schemaVersion": SCHEMA_VERSION,
        "purpose": ("Generated arbitration registry — regenerate with "
                    "scripts/build-arbitration-registry.py --write; do not edit by hand. "
                    "Declares how each contended universal-vector position resolves. "
                    "A contended cell without an entry is a corpus error "
                    "(docs/ARBITER_CONTRACT.md 5)."),
        "counts": {
            "contendedCells": len(entries),
            "byRule": dict(sorted(by_rule.items())),
            "byWriterClass": dict(sorted(by_class.items())),
            "byWithinRank": dict(sorted(by_within.items())),
            "machineContendedCells": sum(
                1 for e in entries
                if sum(1 for w in e["writers"] if w["provider"] == "machine") > 1),
        },
        "defaultProviderRanks": DEFAULT_RANKS,
        "entries": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--summary", action="store_true")
    args = parser.parse_args()

    registry = build(load_machines())
    counts = registry["counts"]

    if args.summary:
        print(f"arbitration-registry: {counts['contendedCells']} contended cell(s)")
        print(f"  by rule        : {counts['byRule']}")
        print(f"  by writer class: {counts['byWriterClass']}")
        return 0

    rendered = json.dumps(registry, indent=2, sort_keys=False) + "\n"

    if args.write:
        REGISTRY.write_text(rendered, encoding="utf-8")
        print(f"arbitration-registry: wrote {counts['contendedCells']} contended cell(s) "
              f"— {counts['byWriterClass']}")
        return 0

    if not REGISTRY.exists():
        print("arbitration-registry: MISSING — run scripts/build-arbitration-registry.py --write",
              file=sys.stderr)
        return 1
    if REGISTRY.read_text(encoding="utf-8") != rendered:
        print("arbitration-registry: STALE — run scripts/build-arbitration-registry.py --write",
              file=sys.stderr)
        return 1
    print(f"arbitration-registry: OK ({counts['contendedCells']} contended cells)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
