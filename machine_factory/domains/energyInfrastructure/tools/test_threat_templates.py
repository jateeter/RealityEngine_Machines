import json
from pathlib import Path
import shutil
import tempfile
import unittest
from build_threat_templates import ROOT,render,check

class ThreatTemplateTests(unittest.TestCase):
    def fixture(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);root=Path(t.name)
        (root/'assets').mkdir()
        for name in ['stix-source-receipt.json','threat-class-catalog.json']:shutil.copyfile(ROOT/'assets'/name,root/'assets'/name)
        shutil.copytree(ROOT/'intake/public-models/stix21',root/'intake/public-models/stix21')
        return root

    def mutate(self,root,name,change):
        p=root/'assets'/name;d=json.loads(p.read_text());change(d);p.write_text(json.dumps(d))

    def test_reproduces_all_source_schemas_and_class_locators(self):
        self.assertEqual(check(ROOT),[]);d=render(ROOT)
        self.assertEqual(len(d['templates']),57)
        self.assertEqual(sum(t['clause'] is not None for t in d['templates']),43)
        self.assertEqual(len({t['templateId'] for t in d['templates']}),57)
        self.assertTrue(all(t['schemaAuthority']=='NON_NORMATIVE' for t in d['templates']))

    def test_missing_template_rejected(self):
        r=self.fixture();self.mutate(r,'threat-class-catalog.json',lambda d:d['templates'].pop());self.assertTrue(check(r))

    def test_fabricated_clause_rejected(self):
        r=self.fixture();self.mutate(r,'threat-class-catalog.json',lambda d:d['templates'][0].update(clause='invented'));self.assertTrue(check(r))

    def test_normative_completion_rejected(self):
        r=self.fixture();self.mutate(r,'threat-class-catalog.json',lambda d:d.update(normativeCoverageComplete=True));self.assertTrue(check(r))

    def test_modified_source_rejected(self):
        r=self.fixture();(r/'intake/public-models/stix21/schemas/sdos/indicator.json').write_text('{}');self.assertTrue(check(r))

    def test_unlisted_source_rejected(self):
        r=self.fixture();(r/'intake/public-models/stix21/schemas/extra.json').write_text('{}');self.assertTrue(check(r))

    def test_unsupported_indexing_claim_rejected(self):
        r=self.fixture();self.mutate(r,'stix-source-receipt.json',lambda d:d.update(ragIndexed=True));self.assertTrue(check(r))

if __name__=='__main__':unittest.main()
