"""Synthetic lifecycle proof only; fixture review identities are not professionals."""
import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "machine_factory/domains/ifrs-accounting"

def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ASSETS / "tools" / file)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

rules = load("compliance_fixture_lifecycle", "document_workflow.py")
controls = load("compliance_fixture_control", "compliance_evidence.py")

class ComplianceEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        ids = ["ELIGIBILITY-MEMO", "EDITION-TRANSITION-PACK", "STATEMENT-BUNDLE", "DISCLOSURE-CHECKLIST"]
        self.catalog = {"assetTypes": [{"assetTypeId": aid, "ownerName": "synthetic-owner", "reviewerName": "synthetic-reviewer",
            "requiredFields": ["conclusion" if aid == "ELIGIBILITY-MEMO" else "requirements" if aid == "DISCLOSURE-CHECKLIST" else "value"],
            "dependencies": [], "sourceRequirements": [{"controlId": "S03-C02"}]} for aid in ids]}
        self.requirements = {"controls": [{"id": "S03-C02", "sectionId": "03", "paragraphs": "3.3"}]}
        self.context = dict(entityId="SYNTHETIC", period="2027", evidenceClass="synthetic", factsFingerprint="facts", sourceFingerprint="source", policyFingerprint="policy", indexSnapshot="index", unresolvedRequirements=[])
        self.store = rules.Store(self.temp.name, self.catalog)
        for aid in ids[:-1]:
            self.approve(aid, {"conclusion": "ELIGIBLE_SUBJECT_TO_REVIEW"} if aid == "ELIGIBILITY-MEMO" else {"value": "synthetic reviewed fixture"})
        head = self.store.head(self.context, "STATEMENT-BUNDLE")
        self.row = {"controlId": "S03-C02", "disposition": "MET", "basis": "Synthetic mechanical acceptance fixture only", "evidenceRefs": ["synthetic:record"],
                    "assetRefs": [{"assetTypeId": "STATEMENT-BUNDLE", "revision": head["revision"], "contentHash": head["contentHash"]}]}
        self.approve("DISCLOSURE-CHECKLIST", {"requirements": [self.row]})
        self._baseline_head = self.store.head(self.context, "STATEMENT-BUNDLE")
        self._baseline_revision = self.store.revision(self.context, "STATEMENT-BUNDLE", 1)

    def approve(self, aid, content):
        old = self.store.head(self.context, aid)
        head = self.store.draft(self.context, aid, content, ["synthetic:record"], old["revision"] if old else 0, "synthetic fixture update")
        self.store.request_review(self.context, aid, head["revision"])
        self.store.approve(self.context, aid, dict(reviewerName="synthetic-reviewer", ownerName="synthetic-owner", evidenceChecked=True, citationsChecked=True,
            reconciliationsChecked=True, unresolvedItems=[], revision=head["revision"], contentHash=head["contentHash"],
            ragReceipt=dict(interactionId="synthetic-interaction", sourceHash="synthetic-hash", sourceFingerprint=self.context["sourceFingerprint"], indexSnapshot="index", verifiedPassageRefs=["synthetic-chunk"], citationVerified=True)))

    def assess(self):
        return controls.assess(self.store, rules, self.context, self.requirements, self.catalog)

    def test_complete_current_reviewed_fixture_is_only_advisory(self):
        result = self.assess()
        self.assertEqual(result["decision"], "READY_FOR_INDEPENDENT_COMPLIANCE_CONCLUSION")
        self.assertEqual(result["status"], "ADVISORY")
        self.assertTrue(result["reviewRequired"])
        self.assertFalse(result["releasePerformed"])

    def test_inventory_and_row_failures_cannot_be_approved_by_assertion(self):
        mutations = [
            lambda row: [],
            lambda row: [row, row],
            lambda row: [{**row, "controlId": "UNKNOWN"}],
            lambda row: [{**row, "controlId": []}],
            lambda row: [{**row, "disposition": "NOT_APPLICABLE"}],
            lambda row: [{**row, "disposition": "EXCEPTION"}],
            lambda row: [{**row, "basis": ""}],
            lambda row: [{**row, "assetRefs": []}],
            lambda row: [{**row, "assetRefs": [{**row["assetRefs"][0], "revision": 99}]}],
            lambda row: [{**row, "assetRefs": [{**row["assetRefs"][0], "contentHash": "fabricated"}]}],
            lambda row: [{**row, "assetRefs": [{**row["assetRefs"][0], "assetTypeId": "DISCLOSURE-CHECKLIST"}]}],
        ]
        # The generic lifecycle cannot approve malformed/empty content. Model
        # bad approved imports directly only to exercise this second boundary.
        original = self.store.head(self.context, "DISCLOSURE-CHECKLIST")
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                revision = self.store.revision(self.context, "DISCLOSURE-CHECKLIST", original["revision"])
                revision["content"]["requirements"] = mutation(copy.deepcopy(self.row))
                keys = ["assetTypeId", "entityId", "period", "evidenceClass", "content", "evidenceRefs", "upstreamRefs", "inputFingerprint"]
                digest = rules.hashed({k: revision[k] for k in keys})
                revision["contentHash"] = digest
                head = copy.deepcopy(original); head["contentHash"] = digest; head["review"]["contentHash"] = digest
                self.store._write(self.store._path(self.context, "DISCLOSURE-CHECKLIST") / "head.json", head)
                self.store._write(self.store._path(self.context, "DISCLOSURE-CHECKLIST") / "v1.json", revision)
                self.assertEqual(self.assess()["status"], "UNRESOLVED")

    def test_open_requirements_stale_scope_draft_or_self_review_blocks(self):
        for mode in ["open", "stale", "draft", "self-review", "wrong-evidence-class"]:
            with self.subTest(mode=mode):
                context = copy.deepcopy(self.context)
                head = self.store.head(context, "STATEMENT-BUNDLE")
                revision = self.store.revision(context, "STATEMENT-BUNDLE", 1)
                if mode == "open": context["unresolvedRequirements"] = ["synthetic open finding"]
                elif mode == "stale": context["sourceFingerprint"] = "changed-source"
                elif mode == "draft": head["status"] = "DRAFT"
                elif mode == "self-review": head["review"]["reviewerName"] = "synthetic-owner"
                else: revision["evidenceClass"] = "actual"
                self.store._write(self.store._path(context, "STATEMENT-BUNDLE") / "head.json", head)
                self.store._write(self.store._path(context, "STATEMENT-BUNDLE") / "v1.json", revision)
                self.assertEqual(controls.assess(self.store, rules, context, self.requirements, self.catalog)["status"], "UNRESOLVED")
                self.store._write(self.store._path(context, "STATEMENT-BUNDLE") / "head.json", self.baseline_head)
                self.store._write(self.store._path(context, "STATEMENT-BUNDLE") / "v1.json", self.baseline_revision)

    @property
    def baseline_head(self):
        return self._baseline_head

    @property
    def baseline_revision(self):
        return self._baseline_revision
