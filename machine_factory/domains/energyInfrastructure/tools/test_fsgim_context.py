import json
from pathlib import Path
import shutil
import tempfile
import unittest
from build_fsgim_context import ROOT,render,check

class FsgimContextTests(unittest.TestCase):
    def fixture(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);r=Path(temp.name)
        shutil.copytree(ROOT/'assets',r/'assets');shutil.copytree(ROOT/'intake/fsgim-context',r/'intake/fsgim-context');shutil.copytree(ROOT/'examples',r/'examples');return r
    def mutate(self,r,name,fn):
        p=r/'assets'/name;d=json.loads(p.read_text());fn(d);p.write_text(json.dumps(d))
    def test_all_role_and_source_type_dispositions(self):
        self.assertEqual(check(ROOT),[]);d=render(ROOT)
        self.assertEqual(len(d['roleMappings']),19);self.assertEqual(len(d['sourceClassBindings']),170)
        self.assertEqual(len(d['catalogDispositions']),4);self.assertEqual(len(d['concepts']),5)
    def test_storage_composition_and_optional_ev_generation(self):
        d=render(ROOT);roles={r['roleId']:r for r in d['roleMappings']}
        for role in ['battery-pack','battery-inverter']:self.assertEqual(roles[role]['functionConcepts'],['Load','Generator'])
        self.assertEqual(roles['battery-pack']['accountingGroup'],roles['battery-inverter']['accountingGroup'])
        self.assertEqual(roles['ev']['functionConcepts'],['Load']);self.assertTrue(roles['ev']['conditionalFunctions'])
        self.assertFalse(roles['threat-feed']['functionConcepts']);self.assertFalse(roles['carbon-provider']['functionConcepts'])
        self.assertFalse(d['carbonExtension']['normativeFSGIMClassClaim']);self.assertEqual(d['carbonExtension']['missingData'],'UNKNOWN_NOT_ZERO')
    def test_missing_role_rejected(self):
        r=self.fixture();self.mutate(r,'fsgim-integration-context.json',lambda d:d['roleMappings'].pop());self.assertTrue(check(r))
    def test_missing_source_class_rejected(self):
        r=self.fixture();self.mutate(r,'fsgim-integration-context.json',lambda d:d['sourceClassBindings'].pop());self.assertTrue(check(r))
    def test_false_equivalence_rejected(self):
        r=self.fixture();self.mutate(r,'fsgim-integration-context.json',lambda d:d.update(normativeEquivalenceVerified=True));self.assertTrue(check(r))
    def test_unknown_catalog_requires_disposition(self):
        r=self.fixture();(r/'assets/extra-class-catalog.json').write_text('{}');self.assertTrue(check(r))
    def test_changed_source_rejected(self):
        r=self.fixture();p=r/'intake/fsgim-context/fsgim.ttl';p.write_text(p.read_text()+'\nchanged');self.assertTrue(check(r))
    def test_fake_official_collection_rejected(self):
        r=self.fixture();self.mutate(r,'fsgim-source-receipt.json',lambda d:d['officialModelArchive'].update(state='RECEIVED',sha256='invented'));self.assertTrue(check(r))
    def test_invented_control_authority_rejected(self):
        r=self.fixture();self.mutate(r,'fsgim-integration-context.json',lambda d:d['roleMappings'][0].update(controlAuthorityGranted=True));self.assertTrue(check(r))
    def test_unlisted_source_rejected(self):
        r=self.fixture();(r/'intake/fsgim-context/unreviewed-draft.pdf').write_bytes(b'fixture only');self.assertTrue(check(r))

if __name__=='__main__':unittest.main()
