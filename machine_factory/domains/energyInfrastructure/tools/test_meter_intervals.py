import json
from pathlib import Path
import shutil
import tempfile
import unittest
from build_meter_intervals import ROOT,build,check

class MeterIntervalTests(unittest.TestCase):
    def fixture(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);r=Path(t.name)
        shutil.copytree(ROOT/'assets',r/'assets');shutil.copytree(ROOT/'intake/public-models/sunspec',r/'intake/public-models/sunspec');return r
    def test_reproduction(self):
        self.assertEqual(check(ROOT),[]);self.assertEqual(len(build(ROOT)),2)
    def test_missing_output(self):
        r=self.fixture();(r/'assets/meter-energy-profile.json').unlink();self.assertTrue(check(r))
    def test_interval_drift(self):
        r=self.fixture();p=r/'assets/meter-energy-interval.json';d=json.loads(p.read_text());d['controlAction']='ALLOW';p.write_text(json.dumps(d));self.assertTrue(check(r))
    def test_source_bytes_drift(self):
        r=self.fixture();p=r/'intake/public-models/sunspec/model_203.json';p.write_text(p.read_text()+'\n');self.assertTrue(check(r))

if __name__=='__main__':unittest.main()
