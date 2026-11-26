import json
from pathlib import Path
import shutil
import tempfile
import unittest
from build_carbon_ledger import ROOT,build,check

class CarbonLedgerTests(unittest.TestCase):
    def fixture(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);r=Path(t.name);shutil.copytree(ROOT/'assets',r/'assets');return r
    def test_reproduction(self):
        self.assertEqual(check(ROOT),[]);self.assertEqual(len(build(ROOT)['rows']),2)
    def test_missing_output(self):
        r=self.fixture();(r/'assets/import-carbon-ledger.json').unlink();self.assertTrue(check(r))
    def test_factor_drift(self):
        r=self.fixture();p=r/'assets/import-carbon-ledger.json';d=json.loads(p.read_text());d['rows'][0]['factor']['intensity']='0';p.write_text(json.dumps(d));self.assertTrue(check(r))
    def test_source_bytes_drift(self):
        r=self.fixture();p=r/'assets/meter-energy-interval.json';p.write_text(p.read_text()+'\n');self.assertTrue(check(r))

if __name__=='__main__':unittest.main()
