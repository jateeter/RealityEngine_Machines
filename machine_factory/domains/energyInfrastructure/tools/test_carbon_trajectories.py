import json
from pathlib import Path
import shutil
import tempfile
import unittest
from build_carbon_trajectories import ROOT,build,check,digest

class CarbonTrajectoryTests(unittest.TestCase):
    def fixture(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);r=Path(t.name);shutil.copytree(ROOT/'assets',r/'assets');return r
    def test_reproduction(self):
        self.assertEqual(check(ROOT),[]);self.assertEqual(len(build(ROOT)['observedRevisions']),2)
    def test_independent_canonical_vector(self):
        self.assertEqual(digest({'b':2,'a':1}),'43258cff783fe7036d8a43033f830adfc60ec037382473548ac742b888292777')
    def test_missing_output(self):
        r=self.fixture();(r/'assets/carbon-trajectories.json').unlink();self.assertTrue(check(r))
    def test_target_drift(self):
        r=self.fixture();p=r/'assets/carbon-trajectories.json';d=json.loads(p.read_text());d['draftTargets'][0]['status']='APPROVED';p.write_text(json.dumps(d));self.assertTrue(check(r))
    def test_source_bytes_drift(self):
        r=self.fixture();p=r/'assets/import-carbon-ledger.json';p.write_text(p.read_text()+'\n');self.assertTrue(check(r))

if __name__=='__main__':unittest.main()
