"""Exact-version sample evidence cannot stand in for independent accounting approval."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
ASSETS=ROOT/'machine_factory/domains/ifrs-accounting'
SAMPLES=ASSETS/'acceptance/synthetic/review-samples'
spec=importlib.util.spec_from_file_location('review_samples',ASSETS/'tools/build_review_samples.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class ReviewSamplesTest(unittest.TestCase):
    def test_packet_is_reproducible_and_technical_checks_preserve_approval_boundary(self):
        subprocess.run([sys.executable,str(ASSETS/'tools/build_review_samples.py'),'--check'],check=True,capture_output=True)
        module.verify_packet(SAMPLES)

    def test_changed_content_is_detected_even_if_file_hash_is_rewritten(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);shutil.copytree(SAMPLES,p,dirs_exist_ok=True)
            rel='documents/FINANCIAL-POSITION/v1.json';path=p/rel;doc=json.loads(path.read_text());doc['content']['assets']['cash']['amount']='99999.00';path.write_text(json.dumps(doc))
            manifest=json.loads((p/'manifest.json').read_text());manifest['artifacts'][rel]=hashlib.sha256(path.read_bytes()).hexdigest();(p/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(AssertionError,'Canonical content hash mismatch'):module.verify_packet(p)

    def test_contribution_cannot_reference_another_revision(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);shutil.copytree(SAMPLES,p,dirs_exist_ok=True)
            rel='contribution-dispositions.json';path=p/rel;doc=json.loads(path.read_text());doc['rows'][0]['documentRef']['revision']=2;path.write_text(json.dumps(doc))
            manifest=json.loads((p/'manifest.json').read_text());manifest['artifacts'][rel]=hashlib.sha256(path.read_bytes()).hexdigest();(p/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(AssertionError,'Contribution exact-revision mismatch'):module.verify_packet(p)

    def test_development_closure_and_sample_hr_do_not_unlock_admission(self):
        spec=importlib.util.spec_from_file_location('ifrs_readiness_samples',ROOT/'scripts/check-ifrs-accounting-readiness.py');gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
        result=gate.assess(ROOT)
        self.assertEqual(result['result'],'BLOCKED_NOT_APPROVED')
        self.assertEqual(next(x for x in result['unresolved'] if x['gate']=='accounting-finding-closure')['count'],53)
        staff=json.loads((SAMPLES/'hr-reviewers.json').read_text())['staff']
        self.assertTrue(all(x['actualAppointment'] is False for x in staff))
        ledger=json.loads((SAMPLES/'finding-dispositions.json').read_text())
        self.assertEqual(ledger['closedDevelopmentFindings'],53)
        self.assertEqual(ledger['closedAdmissionFindings'],0)

    def test_attested_baseline_can_be_verified_without_git_history(self):
        attestation=json.loads((SAMPLES/'operator-review-attestation.json').read_text())
        with patch('subprocess.check_output',side_effect=AssertionError('Git history unavailable')):
            self.assertEqual(len(module.reviewed_findings(attestation)),53)

    def test_changed_retained_review_baseline_is_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);shutil.copytree(SAMPLES,p,dirs_exist_ok=True)
            baseline=p/'reviewed-baseline/accounting-findings.json'
            baseline.write_text('{}')
            attestation=json.loads((p/'operator-review-attestation.json').read_text())
            with patch.object(module,'SAMPLES',p):
                with self.assertRaisesRegex(AssertionError,'Attested source baseline differs'):
                    module.reviewed_findings(attestation)
