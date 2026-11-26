import json
from pathlib import Path
import shutil
import tempfile
import unittest
from build_asset_templates import ROOT, check, render

class AssetTemplateTests(unittest.TestCase):
    def fixture(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);root=Path(tmp.name)
        for rel in ['assets','intake/public-models/sunspec']:
            shutil.copytree(ROOT/rel,root/rel)
        shutil.copyfile(ROOT/'standards-inventory.json',root/'standards-inventory.json')
        for rel in ['examples/reference-microgrids.json','acceptance/cases.json']:
            (root/rel).parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/rel,root/rel)
        return root

    def mutate(self,root,fn):
        p=root/'assets/asset-class-catalog.json';d=json.loads(p.read_text());fn(d);p.write_text(json.dumps(d))

    def test_reproducible(self):
        self.assertEqual(check(ROOT),[])
        catalog=render(ROOT)
        self.assertEqual(len(catalog['templates']),112)
        self.assertEqual(len(catalog['standardCoverage']),47)
        self.assertEqual(len(catalog['genericRoleTemplates']),19)
        self.assertEqual(len(catalog['genericDocumentTemplates']),7)
        self.assertTrue(all(len(d['genericAllowedCaseIds'])==43 for d in catalog['genericDocumentTemplates']))
        self.assertTrue(any('/groups/' in p['sourcePointer'] for t in catalog['templates'] for p in t['properties']))
        self.assertTrue(any(p['definition'].get('access')=='RW' for t in catalog['templates'] for p in t['properties']))

    def test_missing_model_rejected(self):
        root=self.fixture();self.mutate(root,lambda d:d['templates'].pop());self.assertTrue(check(root))

    def test_lost_units_rejected(self):
        root=self.fixture()
        def change(d):
            p=next(p for t in d['templates'] for p in t['properties'] if 'units' in p['definition']);p['definition']['units']='invented'
        self.mutate(root,change);self.assertTrue(check(root))

    def test_normative_completion_rejected(self):
        root=self.fixture();self.mutate(root,lambda d:d.update(normativeCoverageComplete=True));self.assertTrue(check(root))

    def test_missing_standard_rejected(self):
        root=self.fixture();self.mutate(root,lambda d:d['standardCoverage'].pop());self.assertTrue(check(root))

    def test_orphan_role_binding_rejected(self):
        root=self.fixture();self.mutate(root,lambda d:d['genericRoleTemplates'][0].update(referenceRoleId='absent'));self.assertTrue(check(root))

    def test_fabricated_generic_evidence_rejected(self):
        root=self.fixture();self.mutate(root,lambda d:d['genericDocumentTemplates'][0].update(authenticEvidence=True));self.assertTrue(check(root))

    def test_fabricated_simulator_rejected(self):
        root=self.fixture();self.mutate(root,lambda d:d['templates'][0]['instantiation'].update(simulatorVersion='fiction'));self.assertTrue(check(root))

    def test_modified_source_rejected(self):
        root=self.fixture();(root/'intake/public-models/sunspec/model_1.json').write_text('{}');self.assertTrue(check(root))

    def test_unlisted_source_rejected(self):
        root=self.fixture();(root/'intake/public-models/sunspec/model_999.json').write_text('{}');self.assertTrue(check(root))

if __name__=='__main__':unittest.main()
