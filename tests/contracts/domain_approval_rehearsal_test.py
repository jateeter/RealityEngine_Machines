"""Approval workflow exercise is test-only; it cannot clear production gates."""
import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('rehearsal',ROOT/'scripts/domain-approval/rehearsal.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)

class ApprovalRehearsalTest(unittest.TestCase):
    def waiver(self):
        return {'approvalContext':'TEST_ONLY','productionApproval':False,'domain':'ifrs-accounting',
                'independentSignoff':'WAIVED_BY_OPERATOR_FOR_WORKFLOW_TEST','operatorStatement':'Synthetic test authorization',
                'recordedDate':'2026-10-31','scope':'Workflow control-flow test only'}
    def test_explicit_test_waiver_required(self):
        self.assertEqual(r.validate_waiver(self.waiver(),'ifrs-accounting')['approvalContext'],'TEST_ONLY')
        for changes in [{'productionApproval':True},{'approvalContext':'PRODUCTION'},{'independentSignoff':'APPROVED'},{'domain':'other'}]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):r.validate_waiver({**self.waiver(),**changes},'ifrs-accounting')
    def test_fixture_native_receipt_cannot_enter_production_scope_gate(self):
        core=r.load_core()
        with self.assertRaisesRegex(ValueError,'not production native evidence'):
            core.validate_scope_receipt({'evidenceClass':'WORKFLOW_FIXTURE','productionApproval':False},'x','domain:x',{})
    def test_test_state_cannot_be_submitted_or_finalized_as_production(self):
        core=r.load_core();state={'approvalContext':'TEST_ONLY','productionApproval':False,'state':'SUBMITTED_PENDING_GITHUB_REVIEW'}
        with self.assertRaisesRegex(ValueError,'cannot be submitted or finalized'):core.verify_prepared(state,ROOT)
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'state.json').write_text(json.dumps(state))
            with self.assertRaisesRegex(ValueError,'cannot be submitted or finalized'):core.finalize(SimpleNamespace(evidence=p))
    def run_fixture(self,out,waiver,fail=None):
        args=SimpleNamespace(repo=ROOT,domain='ifrs-accounting',evidence=out,waiver=waiver,fail_stage=fail)
        with contextlib.redirect_stdout(io.StringIO()):return r.run(args)
    def test_entire_state_machine_uses_local_git_and_honest_waiver(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);waiver=root/'waiver.json';waiver.write_text(json.dumps(self.waiver()))
            summary=self.run_fixture(root/'positive',waiver)
            self.assertEqual(summary['state'],'TEST_WORKFLOW_COMPLETE')
            expected=json.loads((ROOT/'domains/domain-manifest.json').read_text())['domains']['ifrs-accounting']['status']
            self.assertEqual(summary['sourceManifestStatus'],expected)
            self.assertEqual(summary['testManifestStatus'],'accepted')
            self.assertFalse(summary['productionApproval'])
            self.assertEqual(summary['actualNativeParity'],'NOT_RUN')
            self.assertEqual(summary['candidateMachineCount'],len(r.load_core().inventory(ROOT,'ifrs-accounting')))
            final=json.loads((root/'positive/test-run/approval.json').read_text())
            self.assertEqual(final['machinesPR']['approvalReviews'][0]['state'],'WAIVED_FOR_WORKFLOW_TEST')
            self.assertFalse(final['machinesPR']['approvalReviews'][0]['independentReviewPerformed'])
    def test_failed_fixture_gate_stops_before_submission_and_release(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);waiver=root/'waiver.json';waiver.write_text(json.dumps(self.waiver()));out=root/'negative'
            with self.assertRaises(ValueError):self.run_fixture(out,waiver,'ifrs-accounting-readiness')
            state=json.loads((out/'test-run/state.json').read_text())
            self.assertEqual(state['state'],'FAILED_NOT_APPROVED')
            self.assertEqual(state['events'][-1]['exitCode'],7)
            self.assertFalse(list((out/'TEST_ONLY_FORGE_FIXTURES').glob('*release.json')))
            self.assertFalse((out/'test-run/approval.json').exists())
