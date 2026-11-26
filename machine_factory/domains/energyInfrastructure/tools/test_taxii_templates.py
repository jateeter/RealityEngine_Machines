import json
from pathlib import Path
import shutil
import tempfile
import unittest
from build_taxii_templates import ROOT,render,check

class TaxiiTemplateTests(unittest.TestCase):
    def fixture(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);r=Path(t.name)
        (r/'assets').mkdir();shutil.copytree(ROOT/'intake/taxii21',r/'intake/taxii21')
        for name in ['taxii-source-receipt.json','taxii-resource.schema.json','taxii-resource-catalog.json']:shutil.copyfile(ROOT/'assets'/name,r/'assets'/name)
        return r
    def mutate(self,r,name,fn):
        p=r/'assets'/name;d=json.loads(p.read_text());fn(d);p.write_text(json.dumps(d))
    def test_reproducible_complete_property_table_inventory(self):
        self.assertEqual(check(ROOT),[]);d=render(ROOT)
        catalog=d['assets/taxii-resource-catalog.json'];self.assertEqual(len(catalog['templates']),11)
        self.assertEqual(sum(t['classKind']=='TAXII_RESOURCE' for t in catalog['templates']),9)
        self.assertEqual(len(d['assets/taxii-resource.schema.json']['$defs']),11)
    def test_missing_class_rejected(self):
        r=self.fixture();self.mutate(r,'taxii-resource-catalog.json',lambda d:d['templates'].pop());self.assertTrue(check(r))
    def test_false_normative_completion_rejected(self):
        r=self.fixture();self.mutate(r,'taxii-resource-catalog.json',lambda d:d.update(normativeCoverageComplete=True));self.assertTrue(check(r))
    def test_weakened_property_requirement_rejected(self):
        r=self.fixture();self.mutate(r,'taxii-resource.schema.json',lambda d:d['$defs']['collection']['required'].remove('can_read'));self.assertTrue(check(r))
    def test_changed_source_rejected(self):
        r=self.fixture();p=r/'intake/taxii21/taxii-v2.1-os.html';p.write_bytes(p.read_bytes()+b'changed');self.assertTrue(check(r))
    def test_false_indexing_claim_rejected(self):
        r=self.fixture();self.mutate(r,'taxii-source-receipt.json',lambda d:d.update(ragIndexed=True));self.assertTrue(check(r))
    def test_fabricated_clause_rejected(self):
        r=self.fixture();self.mutate(r,'taxii-resource-catalog.json',lambda d:d['templates'][0].update(sourceSection='99'));self.assertTrue(check(r))

if __name__=='__main__':unittest.main()
