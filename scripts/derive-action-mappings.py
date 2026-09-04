#!/usr/bin/env python3
"""Derive per-domain action-code mapping files from ordered pattern rules.

Milestone M2 tooling (docs/SEMANTIC_OWL_ROADMAP.md): the corpus carries
thousands of templated free-text output `action` strings. This script
classifies each distinct string into the controlled action vocabulary declared
in semantics/ontology/re-core.ttl and writes exact-string mapping files under
semantics/action-mapping/<domain>.json, which scripts/backfill-action-codes.py
then applies.

Rules are ordered: mechanism-specific rules (publish, agent dispatch, workflow
trigger, work order, operational adjustment) win over urgency, and urgency
wins over routing/monitoring, mirroring the hand-curated health-personal
mapping. Curated mapping files are never overwritten unless --force is given;
health-personal is always preserved.

Usage:
  python3 scripts/derive-action-mappings.py           # report coverage
  python3 scripts/derive-action-mappings.py --write   # write mapping files
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MACHINES_ROOT = REPO_ROOT / "machines"
MAPPING_ROOT = REPO_ROOT / "semantics" / "action-mapping"
ONTOLOGY_PATH = REPO_ROOT / "semantics" / "ontology" / "re-core.ttl"

CURATED = {"health-personal"}

AGENT_DISPATCH = re.compile(r"^dispatch (\w+ )*?agent\b")

# Final curated overrides for microgrid mode directives that no verb rule
# covers (reviewed individually; see PR for milestone M2).
OVERRIDES = {
    "LOAD_SHED_BLOCKED_HUMAN_SAFETY": "urgent-intervention",
    "STABILIZATION_ACTION_REQUIRED": "urgent-intervention",
    "SERVICE_DEGRADATION": "urgent-intervention",
    "RECOVERY_REGRESSION": "urgent-intervention",
    "PREPARE_ISLANDING": "adjust-operations",
    "RECONNECT_READY": "adjust-operations",
    "PROTECT_STORAGE_ASSET": "adjust-operations",
    "USE_BACKUP_GENERATION": "adjust-operations",
    "FALLBACK_PROTOCOL_ACTIVE": "adjust-operations",
    "GENERATION_CONSTRAINED": "route-review",
    "LOGISTICS_BLOCKING_RESILIENCE": "route-review",
    "PROTOCOL_CONTROL_UNAVAILABLE": "route-review",
    "DEGRADED_PROTOCOL_PATH": "route-review",
    "REQUIRE_HUMAN_APPROVAL": "human-review-gate",
    "FLEXIBLE_LOAD_AVAILABLE": "continue-monitoring",
    "RECOVERY_IN_PROGRESS": "continue-monitoring",
    "CYBER_SAFE": "continue-monitoring",
    "COMPLETION_EVIDENCE_PENDING": "continue-monitoring",
    "MICROGRID_MONITORING_REQUIRED": "continue-monitoring",
}
NON_URGENT_GUARDS = ("non-emergency", "before crisis escalation",
                     "before acute escalation", "without urgent dispatch",
                     "no urgent")
URGENT_CUES = re.compile(r"\b(urgent|emergency|critical|crisis|immediately|escalate)\b")


def classify(action: str) -> str:
    for token, code in OVERRIDES.items():
        if action.startswith(token):
            return code
    t = " ".join(action.lower().replace("_", " ").split())
    if "publish" in t:
        return "publish-bus"
    if "human review" in t:
        return "human-review-gate"
    if AGENT_DISPATCH.match(t):
        return "dispatch-agent"
    if t.startswith(("trigger", "run ", "invoke", "execute")):
        return "trigger-agent-workflow"
    if t.startswith(("create", "open work order", "submit work order",
                     "schedule maintenance", "schedule inspection")):
        return "create-work-order"
    if t.startswith(("adjust", "tune", "rebalance", "recalibrate", "throttle",
                     "activate", "enable", "disable", "add ", "reduce",
                     "increase", "decrease", "extend", "flush", "switch",
                     "set ", "apply", "deploy", "start", "stop", "restart",
                     "begin", "shed ", "curtail", "ramp", "isolate",
                     "reroute", "divert", "shift", "inject", "inspect",
                     "power ", "clear ", "charge", "commit", "allow",
                     "block", "island", "dispatch", "harvest timeline",
                     "expedite", "override", "close ", "open ")) or \
            " will reset" in t or " will set" in t:
        return "adjust-operations"
    if t.startswith("project "):
        return "create-work-order"
    guarded = any(g in t for g in NON_URGENT_GUARDS)
    if not guarded and URGENT_CUES.search(t):
        return "urgent-intervention"
    if t.startswith(("continue", "keep", "maintain", "record", "hold",
                     "monitor", "log ", "document", "no ", "mark ",
                     "expected", "normal", "nominal", "resume", "confirm",
                     "track", "observe", "verify")) or \
            "stable" in t or "baseline" in t or "keep monitoring" in t or \
            re.search(r"\b(registers?|logs?|continues?)\b", t):
        return "continue-monitoring"
    if t.startswith("schedule") or t.startswith("convene"):
        return "schedule-care-review"
    if "referral" in t:
        return "route-referral"
    if t.startswith(("route", "coordinate", "plan", "offer", "engage",
                     "assign", "queue", "review", "prioritize", "initiate",
                     "notify", "alert", "inform", "publish", "escort",
                     "request", "recommend", "refer", "consult", "connect",
                     "contact")) or any(k in t for k in (
            "review", "coordination", "support", "navigat", "resolution",
            "follow-up", "routing", "optimization", "alignment", "outreach",
            "notification", "queue", "workflow", "screening", "assessment",
            "inspection", "audit", "remediation", "engagement", "planning",
            "response", "check")):
        return "route-review"
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true",
                        help="write semantics/action-mapping/<domain>.json")
    parser.add_argument("--force", action="store_true",
                        help="also rewrite curated mapping files")
    args = parser.parse_args()

    codes = set(re.findall(r're:actionCode "([^"]+)"', ONTOLOGY_PATH.read_text()))
    per_domain: dict[str, dict[str, str]] = defaultdict(dict)
    unmapped: dict[str, list[str]] = defaultdict(list)
    for path in sorted(MACHINES_ROOT.rglob("*.json")):
        rel = path.relative_to(MACHINES_ROOT)
        domain = rel.parts[1] if rel.parts[0] == "domains" else "core"
        doc = json.loads(path.read_text())
        for sequence in doc.get("machine", {}).get("sequences", []):
            for vector in (sequence.get("events") or []):
                for output in (vector.get("outputEvents") or []):
                    action = output.get("metadata", {}).get("action")
                    if not action or action in codes:
                        continue
                    code = classify(action)
                    if code:
                        if code not in codes:
                            raise SystemExit(
                                f"rule produced undeclared code '{code}'")
                        per_domain[domain][action] = code
                    else:
                        unmapped[domain].append(action)

    total = sum(len(m) for m in per_domain.values())
    missing = sum(len(v) for v in unmapped.values())
    print(f"derive-action-mappings: {total} distinct string(s) mapped, "
          f"{missing} unmapped")
    for domain, actions in sorted(unmapped.items()):
        for action in sorted(set(actions))[:10]:
            print(f"UNMAPPED [{domain}] {action[:130]}")
    if args.write and not missing:
        MAPPING_ROOT.mkdir(parents=True, exist_ok=True)
        for domain, mapping in sorted(per_domain.items()):
            out = MAPPING_ROOT / f"{domain}.json"
            if domain in CURATED and out.exists() and not args.force:
                print(f"skip curated {out.relative_to(REPO_ROOT)}")
                continue
            out.write_text(json.dumps(dict(sorted(mapping.items())),
                                      indent=2) + "\n")
            print(f"wrote {out.relative_to(REPO_ROOT)} ({len(mapping)})")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
