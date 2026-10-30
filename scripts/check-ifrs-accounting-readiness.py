#!/usr/bin/env python3
"""Substantive IFRS admission gate, separate from mechanical corpus validity.

Synthetic entity evidence is allowed by the user. Synthetic normative text,
self-reviewed finding closure and a connector-only pass are not substitutes for
the existing source/accounting acceptance requirements in Machines issue 229.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def assess(root=ROOT):
    assets = root / "machine_factory/domains/ifrs-accounting"
    source = json.loads((assets / "source-access-status.json").read_text())
    findings = json.loads((assets / "accounting-findings.json").read_text())["findings"]
    unresolved = []
    if source["status"] not in {"VERIFIED_COMPLETE_SOURCE_INGESTED", "USER_CONFIRMED_COMPLETE_VERSION_3_SOURCE"}:
        unresolved.append({"gate": "authoritative-source-completeness", "status": source["status"], "details": source["unresolved"]})
    open_findings = []
    for finding in findings:
        closure = finding.get("closure", {})
        if finding["status"] != "CLOSED_WITH_REVIEWED_CONNECTED_PROOF" or any(not closure.get(key) for key in ["sourceDisposition", "implementationReferences", "caseReceipts", "independentReviewReference"]):
            open_findings.append(finding["id"])
    if open_findings:
        unresolved.append({"gate": "accounting-finding-closure", "count": len(open_findings), "findingIds": open_findings})
    return {"domain": "ifrs-accounting", "result": "BLOCKED_NOT_APPROVED" if unresolved else "READY_FOR_LIVE_PARITY_AND_INDEPENDENT_PR_REVIEW", "entityEvidencePolicy": "EXPLICIT_SYNTHETIC_ASSETS_ALLOWED", "unresolved": unresolved}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = assess()
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 1 if report["unresolved"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
