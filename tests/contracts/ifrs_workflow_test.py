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
