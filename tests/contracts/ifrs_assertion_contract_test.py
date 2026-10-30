"""IFRS token/translation contracts; not connected accounting acceptance."""
import hashlib,importlib.util,itertools,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
ASSETS=ROOT/'machine_factory/domains/ifrs-accounting'
spec=importlib.util.spec_from_file_location('ifrs_boundary',ASSETS/'tools/bounded_assertions.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
class IFRSAssertionTests(unittest.TestCase):
 def test_all_candidate_bytes_preserved(self):
  manifest=json.loads((ASSETS/'admission-source-manifest.json').read_text())
  self.assertEqual(manifest['machineCount'],225)
  for item in manifest['files']:
   self.assertEqual(hashlib.sha256((ROOT/item['path']).read_bytes()).hexdigest(),item['sha256'])
 def test_declared_fold_inventory_is_exact_and_nonfabricating(self):
  declarations=json.loads((ROOT/'domains/ifrs-fold-declarations.json').read_text())['machines']
  files={p.relative_to(ROOT/'machines').as_posix():p for p in (ROOT/'machines/domains/ifrs-accounting').glob('*.json')}
  self.assertEqual(set(files),set(declarations))
  for rel,p in files.items():
   m=json.loads(p.read_text())['machine'];meta=m['metadata']
   self.assertEqual(m['arbiterRule'],'PASSTHROUGH');self.assertEqual(m['outputMergeTransformation'],'join')
   self.assertEqual(meta['arbitrationPolicy']['resolvedRule'],'PRECEDENCE');self.assertEqual(meta['arbitrationPolicy']['withinRank'],'MAX')
   self.assertEqual(meta['sensorNormalization']['method'],'native-divide-by-two-then-canonicalize-bands')
   for seq in m['sequences']:
    for event in seq['events']:
     for output in event.get('outputEvents',[]):self.assertTrue(set(output['vector'])<={0,0.5,1})
 def test_assertion_bands_and_round_trip(self):
  for native in itertools.product([0,1,2],repeat=4):
   self.assertEqual(b.decode_assertion_lane([b.bound_native(x) for x in native]),list(native))
  for value,expected in [(0,0),(0.249999,0),(0.25,.5),(.749999,.5),(.75,1),(1,1)]:self.assertEqual(b.canonicalize_bounded(value),expected)
 def test_invalid_inputs_never_become_zero(self):
  for value in [True,None,'1',float('nan'),float('inf'),-.01,1.01]:
   with self.subTest(value=value),self.assertRaises(ValueError):b.canonicalize_bounded(value)
 def test_precedence_preserves_rank_before_value(self):
  self.assertEqual(b.precedence_max([(1,1),(3,.5)]),(3,.5))
  self.assertEqual(b.precedence_max([(3,.5),(3,1)]),(3,1))
 def test_ifrs_owl_preserves_categorical_cells_not_tier_confidence(self):
  for path in (ROOT/'semantics/abox/ifrs-accounting').glob('*.ttl'):
   text=path.read_text()
   self.assertIn('re:OutputCellValue',text)
   self.assertNotIn('re:outputTier ',text)
   self.assertNotIn('re:outputConfidence ',text)
   self.assertEqual(text.count('a owl:NamedIndividual , re:OutputCellValue'),8)
 def test_fall_ordinal_semantics_remain_unchanged(self):
  text=(ROOT/'semantics/abox/health-personal/FallDetection.ttl').read_text()
  self.assertIn('re:outputTier ',text);self.assertIn('re:outputConfidence ',text)
  self.assertNotIn('re:OutputCellValue',text)
if __name__=='__main__':unittest.main()
