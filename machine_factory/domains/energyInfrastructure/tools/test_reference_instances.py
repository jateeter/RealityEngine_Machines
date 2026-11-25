import json
from pathlib import Path
import shutil
import tempfile
import unittest
from build_reference_instances import ROOT, build, check

class ReferenceInstanceTests(unittest.TestCase):
    def fixture(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name)
        for rel in ['assets/reference-instances','examples']:
            shutil.copytree(ROOT/rel,root/rel)
        shutil.copyfile(ROOT/'assets/generic-instance-fixture.json',root/'assets/generic-instance-fixture.json')
        return root

    def test_reproducible_three_scenarios(self):
        self.assertEqual(check(ROOT),[])
        fixtures=build(ROOT)
        self.assertEqual(len(fixtures),3)
        self.assertEqual([len(next(d for d in f['documents'] if d['templateId']=='generic-document-topology')['fields']['connections']['value']) for f in fixtures.values()],[9,9,11])

    def test_missing_fixture_rejected(self):
        root=self.fixture();next((root/'assets/reference-instances').glob('*.json')).unlink();self.assertTrue(check(root))

    def test_extra_fixture_rejected(self):
        root=self.fixture();(root/'assets/reference-instances/extra.json').write_text('{}');self.assertTrue(check(root))

    def test_modified_connection_rejected(self):
        root=self.fixture();p=next((root/'assets/reference-instances').glob('*.json'));d=json.loads(p.read_text());next(x for x in d['documents'] if x['templateId']=='generic-document-topology')['fields']['connections']['value'].pop();p.write_text(json.dumps(d));self.assertTrue(check(root))

    def test_source_change_requires_regeneration(self):
        root=self.fixture();p=root/'examples/reference-microgrids.json';d=json.loads(p.read_text());d['scenarios'][0]['nominalReference']['localVoltage']['value']=240;p.write_text(json.dumps(d));self.assertTrue(check(root))

if __name__=='__main__':unittest.main()
