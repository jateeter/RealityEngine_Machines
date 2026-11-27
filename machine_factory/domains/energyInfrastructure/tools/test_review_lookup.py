import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from build_review_lookup import ROOT,build,check
from prepare_review_context import prepare_review_context,verify_review_packet,DI

class ReviewLookupTests(unittest.TestCase):
    def query(self):return copy.deepcopy(build(ROOT)['public-model-review-query.json'])
    def policy_root(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);root=Path(t.name);(root/'assets').mkdir();shutil.copyfile(ROOT/'assets/public-model-review-policy.json',root/'assets/public-model-review-policy.json');return root
    def source_root(self):
        root=self.policy_root()
        paths=['assets/source-receipt.json','assets/opcua-source-receipt.json','intake/public-models/sunspec/LICENSE','intake/public-models/sunspec/model_103.json','intake/public-models/sunspec/model_203.json','intake/opcua-di/Opc.Ua.Di.NodeSet2.xml','intake/opcua-di/Opc.Ua.NodeSet2.xml']
        for path in paths:
            (root/path).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/path,root/path)
        return root
    def change_policy(self,root,q,change):
        p=root/'assets/public-model-review-policy.json';d=json.loads(p.read_text());change(d);p.write_text(json.dumps(d));q['policySHA256']=hashlib.sha256(p.read_bytes()).hexdigest()
    def test_reproduction(self):self.assertEqual(check(ROOT),[])
    def test_ac_power_locator_unit_scale_and_notice_are_grounded(self):
        q=self.query();p=prepare_review_context(q);self.assertEqual(p['status'],'REVIEW_PACKET');c=p['results'][0]
        self.assertEqual(c['identity'],'model:103/point:W');self.assertEqual(c['locator'],'/group/points/14');point=json.loads(c['excerpt']);self.assertEqual(point['type'],'int16');self.assertEqual(point['units'],'W');self.assertEqual(c['context']['scaleFactorPoint']['name'],'W_SF')
        original=json.loads((ROOT/c['sourcePath']).read_text())['group']['points'][14];self.assertEqual(point,original)
        self.assertEqual(p['sourceNotices'][0]['noticeText'],(ROOT/'intake/public-models/sunspec/LICENSE').read_text());self.assertFalse(p['readyForModelUse']);self.assertFalse(p['normativeAuthority']);self.assertFalse(p['answerGenerated']);self.assertFalse(p['persistedIndexCreated']);self.assertEqual(p['controlAction'],'DENY');self.assertEqual(verify_review_packet(p,q),[])
    def test_di_namespace_abstract_type_and_exact_core_context(self):
        q=self.query();q.update(sourceIds=['OPCUA_DI'],query='DeviceType');p=prepare_review_context(q);c=p['results'][0]
        self.assertEqual(c['locator'],'ns=1;i=1002');self.assertTrue(c['identity'].startswith(DI+'|i=1002|'));self.assertEqual(c['context']['attributes']['IsAbstract'],'true');self.assertEqual(c['context']['model']['Version'],'1.05.0');self.assertEqual(c['context']['requiredModels'][0]['Version'],'1.05.04');self.assertIn('OPC Foundation MIT License 1.00',p['sourceNotices'][0]['noticeText']);self.assertEqual(verify_review_packet(p,q),[])
    def test_declaration_lookup_preserves_source_identity(self):
        q=self.query();q.update(sourceIds=['OPCUA_DI'],query='SerialNumber');p=prepare_review_context(q);self.assertEqual(p['status'],'REVIEW_PACKET');self.assertTrue(all('SerialNumber' in c['identity'] for c in p['results']));self.assertTrue(all(c['incompleteContext'] for c in p['results']))
    def test_deterministic_bounded_packets(self):
        q=self.query();q['limit']=1;a=prepare_review_context(q);self.assertEqual(a,prepare_review_context(q));self.assertEqual(len(a['results']),1);self.assertLessEqual(len(a['results'][0]['excerpt'].encode()),8192);self.assertLessEqual(len((json.dumps(a,ensure_ascii=False,indent=2)+'\n').encode()),a['maxPacketBytes']);self.assertIn('python',a['parserVersions'])
    def test_no_support_abstains_without_fabricated_citations(self):
        q=self.query();q['query']='zzunsupportedtokenzz';p=prepare_review_context(q);self.assertEqual(p['status'],'ABSTAIN');self.assertEqual(p['reason'],'NO_LEXICAL_SUPPORT');self.assertEqual(p['results'],[]);self.assertEqual(p['sourceNotices'],[])
    def test_denials_precede_any_source_text_read(self):
        root=self.policy_root() # No receipts or source texts exist here.
        variants=[('role','MODEL_AGENT'),('purpose','OPERATING_CONTROL'),('scope','CONFIDENTIAL'),('tenantId','other-tenant'),('siteId','private-site'),('questionType','NORMATIVE_REQUIREMENT'),('questionType','LIVE_OPERATIONAL_STATE'),('questionType','OPERATING_ADVICE'),('sourceIds',['DNP3']),('sourceIds',['../../Downloads/restricted.pdf'])]
        for key,value in variants:
            with self.subTest(key=key,value=value):
                q=self.query();q[key]=value;p=prepare_review_context(q,root);self.assertEqual(p['status'],'ABSTAIN');self.assertEqual(p['results'],[]);self.assertEqual(p['sourceCoverage'],[])
    def test_disabled_source_abstains_before_text_read(self):
        root=self.policy_root();q=self.query();self.change_policy(root,q,lambda p:p['disabledSourceIds'].append('SUNSPEC_SELECTED'));p=prepare_review_context(q,root);self.assertEqual(p['reason'],'SOURCE_DISABLED');self.assertEqual(p['results'],[])
    def test_policy_cannot_enable_a_model_or_index(self):
        for key in ['modelUseEnabled','embeddingIndexEnabled']:
            with self.subTest(key=key):
                root=self.policy_root();q=self.query();self.change_policy(root,q,lambda p:p.update({key:True}));self.assertRaises(ValueError,prepare_review_context,q,root)
    def test_packet_revalidation_rejects_fabricated_excerpt_locator_and_notice(self):
        q=self.query();original=prepare_review_context(q)
        for mutate in [lambda p:p['results'][0].update(excerpt='invented requirement'),lambda p:p['results'][0].update(locator='/group/points/999'),lambda p:p['results'][0].update(parentSHA256='0'*64),lambda p:p['sourceNotices'][0].update(noticeText='license removed'),lambda p:p.update(readyForModelUse=True)]:
            p=copy.deepcopy(original);mutate(p);self.assertTrue(verify_review_packet(p,q))
    def test_source_byte_change_invalidates_packet(self):
        root=self.source_root();q=self.query();p=prepare_review_context(q,root);path=root/'intake/public-models/sunspec/model_103.json';path.write_text(path.read_text()+'\n');self.assertTrue(verify_review_packet(p,q,root));self.assertRaises(ValueError,prepare_review_context,q,root)
    def test_xml_byte_change_or_entity_injection_is_rejected_before_excerpt(self):
        root=self.source_root();q=self.query();q.update(sourceIds=['OPCUA_DI'],query='DeviceType');path=root/'intake/opcua-di/Opc.Ua.Di.NodeSet2.xml';path.write_text('<!DOCTYPE bad [<!ENTITY x SYSTEM "file:///private/never-read">]><bad/>');self.assertRaises(ValueError,prepare_review_context,q,root)
    def test_revocation_invalidates_an_existing_packet(self):
        root=self.source_root();q=self.query();p=prepare_review_context(q,root);self.change_policy(root,q,lambda p:p['disabledSourceIds'].append('SUNSPEC_SELECTED'));self.assertTrue(verify_review_packet(p,q,root));self.assertEqual(prepare_review_context(q,root)['results'],[])
    def test_query_scope_change_cannot_reuse_a_packet(self):
        q=self.query();p=prepare_review_context(q);q['questionType']='NORMATIVE_REQUIREMENT';self.assertTrue(verify_review_packet(p,q))
    def test_invalid_shapes_and_bounds_fail(self):
        variants=[('limit',0),('limit',4),('limit',True),('query','x'*257),('sourceIds',[]),('sourceIds',['OPCUA_DI','OPCUA_DI']),('policySHA256','0'*64),('controlAction','ALLOW')]
        for key,value in variants:
            with self.subTest(key=key,value=value):
                q=self.query();q[key]=value;self.assertRaises((ValueError,TypeError),prepare_review_context,q)
        q=self.query();q['sourcePath']='/etc/passwd';self.assertRaises(ValueError,prepare_review_context,q)
    def test_generator_detects_query_and_parent_drift(self):
        root=self.policy_root();outputs=build(ROOT)
        (root/'assets/public-model-review-query.json').write_text(json.dumps(outputs['public-model-review-query.json']));self.assertEqual(check(root),[])
        p=root/'assets/public-model-review-query.json';d=json.loads(p.read_text());d['questionType']='OPERATING_ADVICE';p.write_text(json.dumps(d));self.assertTrue(check(root))

if __name__=='__main__':unittest.main()
