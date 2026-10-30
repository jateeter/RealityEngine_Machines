#!/usr/bin/env python3
"""Reproduce IFRS document handoffs from declared duties and accountable families.

These are document-sidecar edges, never vector copying or accounting assertions.
Steward selection is a stable routing representative within the owning family;
all contributors keep their own duties. No accounting authority follows from it.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "machine_factory/domains/ifrs-accounting"


def plan():
    catalog = json.loads((ASSETS / "document-asset-catalog.json").read_text())["assetTypes"]
    machines = {p.stem: json.loads(p.read_text()) for p in sorted((ROOT / "machines/domains/ifrs-accounting").glob("*.json"))}
    duties = {mid: {d["assetTypeId"] for d in doc["machine"]["metadata"]["documentAssetWorkflow"]["duties"]} for mid, doc in machines.items()}
    owners = {}
    for asset in catalog:
        choices = [mid for mid, doc in machines.items() if asset["assetTypeId"] in duties[mid] and doc["machine"]["metadata"]["documentAssetWorkflow"]["familyId"] == asset["familyId"]]
        if not choices:
            # Catalog accountability can include a new supporting document not
            # named in legacy recognizer duties. Give its owning family an
            # explicit work address; do not pretend a recognizer implements it.
            choices = [mid for mid, doc in machines.items() if doc["machine"]["metadata"]["documentAssetWorkflow"]["familyId"] == asset["familyId"]]
        if not choices:
            raise ValueError("No accountable family representative for " + asset["assetTypeId"])
        owners[asset["assetTypeId"]] = min(choices)
    edges = []
    for mid in machines:
        for aid in sorted(duties[mid]):
            owner = owners[aid]
            if owner != mid:
                edges.append({"id": "ifrs.document." + mid + "." + aid,
                              "type": "document-workflow-handoff", "sourceMachine": mid,
                              "targetMachine": owner, "assetTypeId": aid,
                              "compositionOwner": "document-workflow-dispatcher",
                              "purpose": "Submit scoped evidence/contribution to the accountable document steward; never infer a financial determination from recognizer tokens.",
                              "nativeVectorWrite": False})
    return machines, {"schemaVersion": "1.0.0", "reviewStatus": "INDEPENDENT_REVIEW_REQUIRED",
                      "routingBasis": "Stable representative among declared contributors in the catalog's accountable family; not accounting rank or authority.",
                      "assetStewards": owners, "documentDependencies": json.loads((ASSETS / "document-dependencies.json").read_text()), "handoffs": edges}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    machines, graph = plan()
    expected = {ASSETS / "accounting-workflow-graph.json": graph}
    for mid, doc in machines.items():
        meta = doc["machine"]["metadata"]
        meta["documentStewardship"] = sorted(aid for aid, owner in graph["assetStewards"].items() if owner == mid)
        meta["interconnections"] = [e for e in graph["handoffs"] if e["sourceMachine"] == mid]
        meta["conversion"]["isolationDecision"] = "Document-sidecar handoffs are explicit. Native vector regions and token semantics unchanged; connected financial acceptance still required."
        expected[ROOT / "machines/domains/ifrs-accounting" / (mid + ".json")] = doc
    differences = []
    for path, data in expected.items():
        text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        if args.write:
            path.write_text(text)
        elif not path.exists() or path.read_text() != text:
            differences.append(str(path.relative_to(ROOT)))
    if differences:
        raise SystemExit("IFRS workflow drift: " + ", ".join(differences))
    print(f"IFRS document handoffs: {len(graph['handoffs'])}; asset stewards: {len(graph['assetStewards'])}; independent review required")


if __name__ == "__main__":
    main()
