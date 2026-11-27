import json
from pathlib import Path
import shutil
import tempfile
import unittest
from build_risk_assessment import ROOT,build,check
class RiskAssessmentTests(unittest.TestCase):
    def fixture(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);r=Path(t.name);shutil.copytree(ROOT/'assets',r/'assets');return r
    def test_reproduction(self):
        self.assertEqual(check(ROOT),[]);self.assertEqual(len(build(ROOT)),3)
    def test_missing_output(self):
        r=self.fixture();(r/'assets/risk-assessment-fixture.json').unlink();self.assertTrue(check(r))
    def test_policy_drift(self):
        r=self.fixture();p=r/'assets/generic-risk-policy.json';d=json.loads(p.read_text());d['clearanceSupported']=True;p.write_text(json.dumps(d));self.assertTrue(check(r))
    def test_source_bytes_drift(self):
        r=self.fixture();p=r/'assets/synthetic-threat-fixture.json';p.write_text(p.read_text()+'\n');self.assertTrue(check(r))
if __name__=='__main__':unittest.main()
