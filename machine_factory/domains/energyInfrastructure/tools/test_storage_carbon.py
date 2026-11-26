import json
from pathlib import Path
import shutil
import tempfile
import unittest
from build_storage_carbon import ROOT,build,check

class StorageCarbonTests(unittest.TestCase):
    def fixture(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);r=Path(t.name);shutil.copytree(ROOT/'assets',r/'assets');return r
    def test_reproduction(self):
        self.assertEqual(check(ROOT),[]);self.assertEqual(len(build(ROOT)['events']),3)
    def test_missing_output(self):
        r=self.fixture();(r/'assets/storage-carbon-allocation.json').unlink();self.assertTrue(check(r))
    def test_input_drift(self):
        r=self.fixture();p=r/'assets/storage-carbon-allocation.json';d=json.loads(p.read_text());d['events'][0]['storedKWh']='1';p.write_text(json.dumps(d));self.assertTrue(check(r))
    def test_source_bytes_drift(self):
        r=self.fixture();p=r/'assets/import-carbon-ledger.json';p.write_text(p.read_text()+'\n');self.assertTrue(check(r))

if __name__=='__main__':unittest.main()
