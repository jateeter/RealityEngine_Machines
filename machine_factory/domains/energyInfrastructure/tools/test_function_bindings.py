import json
from pathlib import Path
import shutil
import tempfile
import unittest
from build_function_bindings import ROOT,build,check

class FunctionBindingTests(unittest.TestCase):
    def fixture(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);r=Path(temp.name)
        shutil.copytree(ROOT/'assets',r/'assets');shutil.copytree(ROOT/'examples',r/'examples');return r
    def test_four_reproducible_projections(self):
        self.assertEqual(check(ROOT),[]);all_data=build(ROOT);self.assertEqual(len(all_data),4)
        d=all_data['generic.json'];self.assertEqual(len(d['bindings']),19)
        self.assertEqual(len(d['accounting']['resourceGroups']),5)
        roles={b['roleId']:b for b in d['bindings']};self.assertIsNone(roles['utility-grid']['opcuaDITypeFacet'])
        self.assertTrue(roles['meter']['opcuaDITypeFacet']['sourceIsAbstract'])
    def test_missing_projection_rejected(self):
        r=self.fixture();next((r/'assets/function-bindings').glob('*.json')).unlink();self.assertTrue(check(r))
    def test_extra_projection_rejected(self):
        r=self.fixture();(r/'assets/function-bindings/extra.json').write_text('{}');self.assertTrue(check(r))
    def test_source_change_requires_regeneration(self):
        r=self.fixture();p=r/'assets/generic-instance-fixture.json';p.write_text(p.read_text()+'\n');self.assertTrue(check(r))
    def test_multiple_meters_need_explicit_policy(self):
        r=self.fixture();p=r/'assets/generic-instance-fixture.json';d=json.loads(p.read_text());a=dict(next(a for a in d['assets'] if a['roleId']=='meter'));a['id']='fixture.extra-meter';d['assets'].append(a);p.write_text(json.dumps(d));self.assertTrue(check(r))
    def test_fabricated_execution_rejected(self):
        r=self.fixture();p=r/'assets/function-bindings/generic.json';d=json.loads(p.read_text());d['execution']['controlAction']='ALLOW';p.write_text(json.dumps(d));self.assertTrue(check(r))

if __name__=='__main__':unittest.main()
