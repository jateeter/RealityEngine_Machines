import json
from pathlib import Path
import shutil
import tempfile
import unittest
from build_sunspec_power import ROOT,build,check

class SunSpecPowerTests(unittest.TestCase):
    def fixture(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);r=Path(t.name)
        shutil.copytree(ROOT/'assets',r/'assets');shutil.copytree(ROOT/'intake/public-models/sunspec',r/'intake/public-models/sunspec');return r
    def test_reproduction(self):
        self.assertEqual(check(ROOT),[])
        d=build(ROOT);self.assertEqual([m['modelId'] for m in d['sunspec-power-profile.json']['models']],[103,203])
    def test_missing_output(self):
        r=self.fixture();(r/'assets/sunspec-power-profile.json').unlink();self.assertTrue(check(r))
    def test_replay_drift(self):
        r=self.fixture();p=r/'assets/sunspec-power-replay.json';d=json.loads(p.read_text());d['networkExecution']=True;p.write_text(json.dumps(d));self.assertTrue(check(r))
    def test_input_byte_drift(self):
        r=self.fixture();p=r/'intake/public-models/sunspec/model_103.json';p.write_text(p.read_text()+'\n');self.assertTrue(check(r))

if __name__=='__main__':unittest.main()
