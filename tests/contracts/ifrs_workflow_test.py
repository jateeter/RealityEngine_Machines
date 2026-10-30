import importlib.util
import json
from pathlib import Path
import subprocess
import unittest
import tempfile

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "machine_factory/domains/ifrs-accounting"
spec = importlib.util.spec_from_file_location("controls", ASSETS / "tools/accounting_controls.py")
controls = importlib.util.module_from_spec(spec); spec.loader.exec_module(controls)


class IFRSWorkflowTests(unittest.TestCase):
    def test_graph_is_reproducible_and_routes_to_accountable_families(self):
        subprocess.run(["python3", str(ROOT / "scripts/build-ifrs-workflow.py"), "--check"], check=True, capture_output=True)
        graph = json.loads((ASSETS / "accounting-workflow-graph.json").read_text())
        catalog = {a["assetTypeId"]: a for a in json.loads((ASSETS / "document-asset-catalog.json").read_text())["assetTypes"]}
        for aid, mid in graph["assetStewards"].items():
            machine = json.loads((ROOT / "machines/domains/ifrs-accounting" / (mid + ".json")).read_text())["machine"]
            self.assertEqual(machine["metadata"]["documentAssetWorkflow"]["familyId"], catalog[aid]["familyId"])
        self.assertEqual(graph["reviewStatus"], "INDEPENDENT_REVIEW_REQUIRED")
        self.assertTrue(all(not e["nativeVectorWrite"] for e in graph["handoffs"]))

    def test_synthetic_cases_and_decimal_reconciliation(self):
        package = json.loads((ASSETS / "acceptance/synthetic/accounting-package.json").read_text())
        self.assertTrue(package["synthetic"])
        for case in package["cases"]:
            result = controls.determine(case["control"], case["facts"])
            for key, value in case["expected"].items():
                self.assertEqual(result[key], value, case["caseId"])
        reconciliation = controls.reconcile_trial_balance(package["trialBalance"])
        for key, value in package["expectedReconciliation"].items():
            self.assertEqual(reconciliation[key], value)
        self.assertFalse(reconciliation["postingPerformed"])
        package["trialBalance"][0]["amount"] = "92200.01"
        self.assertEqual(controls.reconcile_trial_balance(package["trialBalance"])["status"], "UNRESOLVED_IMBALANCE")

    def test_malformed_evidence_cannot_produce_a_decision(self):
        for refs in [None, [], "record-1", {"record": "1"}, [""], [" "], [1], ["record-1", None]]:
            with self.subTest(refs=refs):
                result = controls.determine("section-1-eligibility", {
                    "evidenceRefs": refs, "publicAccountability": False,
                    "generalPurposeStatements": True, "jurisdictionPermits": True})
                self.assertEqual(result["status"], "UNRESOLVED")
                self.assertNotIn("decision", result)
                with self.assertRaises(ValueError):
                    controls.reconcile_trial_balance([{"amount": "1.00", "currency": "USD",
                        "asOf": "2027-12-31", "side": "debit", "evidenceRefs": refs}])
        self.assertEqual(controls.determine("section-1-eligibility", None)["status"], "UNRESOLVED")

    def test_plan_covers_every_finding_once(self):
        plan = json.loads((ASSETS / "resolution-workplan.json").read_text())
        findings = json.loads((ASSETS / "accounting-findings.json").read_text())["findings"]
        ids = [item["findingId"] for wave in plan["waves"] for item in wave["items"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), {f["id"] for f in findings})
        self.assertFalse(plan["policy"]["historicalComparisonRequired"])

    def test_foundation_source_disposition_cases(self):
        package = json.loads((ASSETS / "acceptance/synthetic/foundation-cases.json").read_text())
        self.assertTrue(package["synthetic"])
        for case in package["cases"]:
            with self.subTest(case=case["caseId"]):
                actual = controls.determine(case["control"], case["facts"])
                for key, expected in case["expected"].items():
                    self.assertEqual(actual[key], expected)
                if actual["status"] == "ADVISORY":
                    self.assertTrue(actual["reviewRequired"])
                missing = dict(case["facts"], evidenceRefs=[])
                self.assertEqual(controls.determine(case["control"], missing)["status"], "UNRESOLVED")

    def test_foundation_correction_proposals_are_bound_to_current_machine_files(self):
        import hashlib
        proposals = json.loads((ASSETS / "foundation-machine-dispositions.json").read_text())
        self.assertEqual(len(proposals["items"]), 5)
        for item in proposals["items"]:
            path = ROOT / "machines/domains/ifrs-accounting" / (item["machineId"] + ".json")
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item["machineFileSHA256"])
            self.assertEqual(json.loads(path.read_text())["machine"]["description"], item["currentDescription"])
            self.assertFalse(item["appliedToMachineCorpus"])
            self.assertEqual(item["reviewStatus"], "INDEPENDENT_ACCOUNTING_REVIEW_REQUIRED")
            self.assertNotEqual(item["currentDescription"], item["proposedDescription"])

    def test_money_is_not_a_token_or_float(self):
        for value in [.5, "NaN", "Infinity"]:
            with self.assertRaises(ValueError):
                controls.amount({"amount": value, "currency": "USD", "asOf": "2027-12-31"})

    def test_version_comparison_is_out_of_scope_but_findings_are_not_silently_closed(self):
        spec = importlib.util.spec_from_file_location("readiness", ROOT / "scripts/check-ifrs-accounting-readiness.py")
        readiness = importlib.util.module_from_spec(spec); spec.loader.exec_module(readiness)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); assets = root / "machine_factory/domains/ifrs-accounting"; assets.mkdir(parents=True)
            (assets / "source-access-status.json").write_text(json.dumps({"status": "USER_CONFIRMED_COMPLETE_VERSION_3_SOURCE", "unresolved": []}))
            (assets / "accounting-findings.json").write_text(json.dumps({"findings": [{"id": "SYNTHETIC-OPEN-FINDING", "status": "OPEN"}]}))
            result = readiness.assess(root)
        self.assertEqual(result["entityEvidencePolicy"], "EXPLICIT_SYNTHETIC_ASSETS_ALLOWED")
        self.assertEqual([gate["gate"] for gate in result["unresolved"]], ["accounting-finding-closure"])
        self.assertEqual(result["result"], "BLOCKED_NOT_APPROVED")


if __name__ == "__main__":
    unittest.main()
