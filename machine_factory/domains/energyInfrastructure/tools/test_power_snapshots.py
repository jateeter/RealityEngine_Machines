import json
from pathlib import Path
import shutil
import tempfile
import unittest
from build_power_snapshots import ROOT,build,check

class PowerSnapshotTests(unittest.TestCase):
    def fixture(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);r=Path(temp.name)
        shutil.copytree(ROOT/'assets',r/'assets');return r
    def test_four_reproducible_sets(self):
        self.assertEqual(check(ROOT),[]);self.assertEqual(len(build(ROOT)),4)
        for snapshot in build(ROOT).values():
            self.assertEqual(snapshot['controlAction'],'DENY')
            self.assertTrue(all(s['synthetic'] for s in snapshot['samples']))
    def test_missing_set(self):
        r=self.fixture();(r/'assets/power-snapshots/generic.json').unlink();self.assertTrue(check(r))
    def test_extra_set(self):
        r=self.fixture();(r/'assets/power-snapshots/extra.json').write_text('{}');self.assertTrue(check(r))
    def test_source_bytes_change(self):
        r=self.fixture();p=r/'assets/function-bindings/generic.json';p.write_text(p.read_text()+'\n');self.assertTrue(check(r))
    def test_sample_drift(self):
        r=self.fixture();p=r/'assets/power-snapshots/generic.json';d=json.loads(p.read_text());d['samples'][0]['rawValue']=0;p.write_text(json.dumps(d));self.assertTrue(check(r))

if __name__=='__main__':unittest.main()
