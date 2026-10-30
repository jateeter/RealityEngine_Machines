"""Mechanical lifecycle tests with isolated synthetic fixtures, not accounting proofs."""
import concurrent.futures,copy,importlib.util,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('workflow',ROOT/'tools/document_workflow.py');w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
class WorkflowTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();full=json.loads((ROOT/'document-asset-catalog.json').read_text());ids={'SOURCE-REGISTER','EVIDENCE-REGISTER','RAG-RECEIPTS','POLICY-REGISTER','TAX-SCHEDULE'};self.catalog={'assetTypes':[a for a in full['assetTypes'] if a['assetTypeId'] in ids]};self.store=w.Store(self.tmp.name,self.catalog);self.ctx={'entityId':'TEST-ENTITY','period':'2026-test-period','factsFingerprint':'fixture-facts-v1','sourceFingerprint':'fixture-source-v1','policyFingerprint':'fixture-policy-v1','indexSnapshot':'fixture-index-v1','unresolvedRequirements':[]};self.event={'eventId':'test-event','entityId':self.ctx['entityId'],'period':self.ctx['period'],'type':'period-opened'}
 def tearDown(self):self.tmp.cleanup()
 def content(self,aid):return {k:{'value':'Synthetic fixture only','evidenceRef':'fixture://not-production'} for k in self.store.catalog[aid]['requiredFields']}
 def review(self,aid,h):
  a=self.store.catalog[aid]
  return {'ownerName':a['ownerName'],'reviewerName':a['reviewerName'],'evidenceChecked':True,'citationsChecked':True,'reconciliationsChecked':True,'unresolvedItems':[],'revision':h['revision'],'contentHash':h['contentHash'],'ragReceipt':{'interactionId':'FIXTURE-NOT-LIVE','sourceHash':'0'*64,'sourceFingerprint':self.ctx['sourceFingerprint'],'indexSnapshot':self.ctx['indexSnapshot'],'verifiedPassageRefs':['fixture://source'],'citationVerified':True}}
 def approved(self,aid):
  for dep in self.store.catalog[aid]['dependencies']:
   if not self.store.head(self.ctx,dep):self.approved(dep)
  h=self.store.draft(self.ctx,aid,self.content(aid),['fixture://not-production']);self.store.request_review(self.ctx,aid,h['revision']);return self.store.approve(self.ctx,aid,self.review(aid,h))
 def test_missing_asset_creates_named_motivated_task(self):
  t=self.store.reconcile_event(self.ctx,self.event,['SOURCE-REGISTER'])[0];self.assertEqual(t['action'],'CREATE_DRAFT_AND_REQUEST_EVIDENCE');self.assertTrue(t['motivation']);self.assertTrue(t['ownerName'])
 def test_duplicate_events_coalesce(self):
  a=self.store.reconcile_event(self.ctx,self.event,['SOURCE-REGISTER']);b=self.store.reconcile_event(self.ctx,{**self.event,'eventId':'retry'},['SOURCE-REGISTER']);self.assertEqual(a,b);self.assertEqual(len(json.loads((Path(self.tmp.name)/'outbox.json').read_text())),1)
 def test_cross_entity_event_rejected(self):
  with self.assertRaises(w.EvidenceError):self.store.reconcile_event(self.ctx,{**self.event,'entityId':'OTHER'},['SOURCE-REGISTER'])
 def test_cross_period_event_rejected(self):
  with self.assertRaises(w.EvidenceError):self.store.reconcile_event(self.ctx,{**self.event,'period':'OTHER'},['SOURCE-REGISTER'])
 def test_missing_context_rejected(self):
  c={**self.ctx};del c['sourceFingerprint']
  with self.assertRaises(w.EvidenceError):self.store.reconcile_event(c,self.event,['SOURCE-REGISTER'])
 def test_draft_retry_is_idempotent(self):
  a=self.store.draft(self.ctx,'SOURCE-REGISTER',{},[]);b=self.store.draft(self.ctx,'SOURCE-REGISTER',{},[]);self.assertEqual(a,b);self.assertEqual(a['revision'],1)
 def test_concurrent_duplicate_drafts_single_revision(self):
  def make(_):return w.Store(self.tmp.name,self.catalog).draft(self.ctx,'SOURCE-REGISTER',{},[])['revision']
  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:revs=list(pool.map(make,range(8)))
  self.assertEqual(revs,[1]*8)
 def test_compare_and_swap_rejects_lost_update(self):
  self.store.draft(self.ctx,'SOURCE-REGISTER',{},[])
  with self.assertRaises(w.ConflictError):self.store.draft(self.ctx,'SOURCE-REGISTER',{'edition':'changed'},[],expected_revision=0,change_reason='test change')
 def test_revision_is_immutable(self):
  a=self.store.draft(self.ctx,'SOURCE-REGISTER',{},[]);p=self.store._path(self.ctx,'SOURCE-REGISTER')/'v1.json';before=p.read_bytes();self.store.draft(self.ctx,'SOURCE-REGISTER',{'edition':'updated'},[],1,'new facts');self.assertEqual(before,p.read_bytes());self.assertEqual(self.store.head(self.ctx,'SOURCE-REGISTER')['revision'],2)
 def test_missing_fields_cannot_approve(self):
  h=self.store.draft(self.ctx,'SOURCE-REGISTER',{},['fixture://source']);self.store.request_review(self.ctx,'SOURCE-REGISTER',1)
  with self.assertRaises(w.EvidenceError):self.store.approve(self.ctx,'SOURCE-REGISTER',self.review('SOURCE-REGISTER',h))
 def test_direct_approval_without_review_request_rejected(self):
  h=self.store.draft(self.ctx,'SOURCE-REGISTER',self.content('SOURCE-REGISTER'),['fixture://source'])
  with self.assertRaises(w.EvidenceError):self.store.approve(self.ctx,'SOURCE-REGISTER',self.review('SOURCE-REGISTER',h))
 def test_owner_cannot_self_approve(self):
  h=self.store.draft(self.ctx,'SOURCE-REGISTER',self.content('SOURCE-REGISTER'),['fixture://source']);self.store.request_review(self.ctx,'SOURCE-REGISTER',1);r=self.review('SOURCE-REGISTER',h);r['reviewerName']=r['ownerName']
  with self.assertRaises(w.EvidenceError):self.store.approve(self.ctx,'SOURCE-REGISTER',r)
 def test_exact_revision_review_required(self):
  h=self.store.draft(self.ctx,'SOURCE-REGISTER',self.content('SOURCE-REGISTER'),['fixture://source']);self.store.request_review(self.ctx,'SOURCE-REGISTER',1);r=self.review('SOURCE-REGISTER',h);r['revision']=2
  with self.assertRaises(w.ConflictError):self.store.approve(self.ctx,'SOURCE-REGISTER',r)
 def test_unresolved_review_items_block_approval(self):
  h=self.store.draft(self.ctx,'SOURCE-REGISTER',self.content('SOURCE-REGISTER'),['fixture://source']);self.store.request_review(self.ctx,'SOURCE-REGISTER',1);r=self.review('SOURCE-REGISTER',h);r['unresolvedItems']=['source uncertainty']
  with self.assertRaises(w.EvidenceError):self.store.approve(self.ctx,'SOURCE-REGISTER',r)
 def test_wrong_rag_index_blocks_approval(self):
  h=self.store.draft(self.ctx,'SOURCE-REGISTER',self.content('SOURCE-REGISTER'),['fixture://source']);self.store.request_review(self.ctx,'SOURCE-REGISTER',1);r=self.review('SOURCE-REGISTER',h);r['ragReceipt']['indexSnapshot']='old-index'
  with self.assertRaises(w.EvidenceError):self.store.approve(self.ctx,'SOURCE-REGISTER',r)
 def test_missing_rag_provenance_blocks_approval(self):
  h=self.store.draft(self.ctx,'SOURCE-REGISTER',self.content('SOURCE-REGISTER'),['fixture://source']);self.store.request_review(self.ctx,'SOURCE-REGISTER',1);r=self.review('SOURCE-REGISTER',h);del r['ragReceipt']['verifiedPassageRefs']
  with self.assertRaises(w.EvidenceError):self.store.approve(self.ctx,'SOURCE-REGISTER',r)
 def test_unapproved_upstream_blocks_approval(self):
  self.store.draft(self.ctx,'SOURCE-REGISTER',self.content('SOURCE-REGISTER'),['fixture://source']);h=self.store.draft(self.ctx,'RAG-RECEIPTS',self.content('RAG-RECEIPTS'),['fixture://source']);self.store.request_review(self.ctx,'RAG-RECEIPTS',1)
  with self.assertRaises(w.EvidenceError):self.store.approve(self.ctx,'RAG-RECEIPTS',self.review('RAG-RECEIPTS',h))
 def test_upstream_revision_invalidates_transitively(self):
  self.approved('TAX-SCHEDULE');self.store.draft(self.ctx,'SOURCE-REGISTER',{**self.content('SOURCE-REGISTER'),'edition':'changed'},['fixture://updated'],1,'source edition changed');self.assertEqual(self.store.head(self.ctx,'POLICY-REGISTER')['status'],'STALE');self.assertEqual(self.store.head(self.ctx,'TAX-SCHEDULE')['status'],'STALE')
 def test_invalidation_does_not_cross_entity_or_period(self):
  self.approved('SOURCE-REGISTER');other={**self.ctx,'entityId':'OTHER'};h=self.store.draft(other,'SOURCE-REGISTER',self.content('SOURCE-REGISTER'),['fixture://other']);self.store.invalidate(self.ctx,['SOURCE-REGISTER'],'test');self.assertEqual(self.store.head(other,'SOURCE-REGISTER')['status'],'DRAFT')
 def test_close_detects_unannounced_fact_drift(self):
  self.approved('SOURCE-REGISTER');c={**self.ctx,'factsFingerprint':'fixture-facts-v2'};self.store.reconcile_event(c,{**self.event,'type':'period-close-requested'},['SOURCE-REGISTER']);self.assertEqual(self.store.head(c,'SOURCE-REGISTER')['status'],'STALE')
 def test_stale_idempotent_retry_does_not_restore_approval(self):
  self.approved('SOURCE-REGISTER');self.store.invalidate(self.ctx,['SOURCE-REGISTER'],'contradiction');h=self.store.draft(self.ctx,'SOURCE-REGISTER',self.content('SOURCE-REGISTER'),['fixture://not-production']);self.assertEqual(h['status'],'STALE')
 def test_outbox_closes_satisfied_tasks(self):
  self.store.reconcile_event(self.ctx,self.event,['SOURCE-REGISTER']);self.approved('SOURCE-REGISTER');self.store.reconcile_event(self.ctx,self.event,['SOURCE-REGISTER']);tasks=json.loads((Path(self.tmp.name)/'outbox.json').read_text());self.assertTrue(all(t['status']=='DONE' for t in tasks.values()))
 def test_render_discloses_unresolved_and_preserves_money(self):
  self.store.draft(self.ctx,'SOURCE-REGISTER',{'edition':{'amount':'123456.78','currency':'USD'}},[]);text=self.store.render(self.ctx,'SOURCE-REGISTER');self.assertIn('UNRESOLVED',text);self.assertIn('DRAFT',text);self.assertIn('123456.78',text)
 def test_cycle_rejected(self):
  c=copy.deepcopy(self.catalog);next(a for a in c['assetTypes'] if a['assetTypeId']=='SOURCE-REGISTER')['dependencies']=['RAG-RECEIPTS']
  with self.assertRaises(w.EvidenceError):w.Store(Path(self.tmp.name)/'cycle',c)
 def test_unsupported_nonapplicability_rejected(self):
  c={**self.ctx,'notApplicableAssets':{'SOURCE-REGISTER':{'basis':'convenience'}}}
  with self.assertRaises(w.EvidenceError):self.store.draft(c,'RAG-RECEIPTS',{},[])
 def observation(self):
  self.store=w.Store(self.tmp.name,json.loads((ROOT/'document-asset-catalog.json').read_text()))
  m=json.loads((ROOT.parents[2]/'machines/domains/ifrs-accounting/IFRS_Sec03_Compliance_Assertion_Arbiter.json').read_text())
  seq=m['machine']['sequences'][0]
  return m,{'machineId':m['machine']['id'],'sequenceId':seq['id'],'outputVector':seq['events'][0]['outputEvents'][0]['vector'],'providerRef':'fixture://not-a-live-engine-trace'}
 def test_native_observation_creates_assessment_not_financial_fact(self):
  m,o=self.observation();tasks=self.store.observe_machine(self.ctx,m,o);self.assertTrue(tasks);self.assertEqual({t['action'] for t in tasks},{'ASSESS_DOCUMENT_IMPACT'});self.assertIsNone(self.store.head(self.ctx,'COMPLIANCE-REVIEW'))
 def test_native_observation_does_not_invalidate_approved_document(self):
  m,o=self.observation();self.approved('SOURCE-REGISTER');tasks=self.store.observe_machine(self.ctx,m,o);self.assertEqual(self.store.head(self.ctx,'SOURCE-REGISTER')['status'],'APPROVED');self.store.reconcile_event(self.ctx,self.event,['SOURCE-REGISTER']);outbox=json.loads((Path(self.tmp.name)/'outbox.json').read_text());self.assertTrue(all(t['status']=='OPEN' for t in outbox.values() if t['action']=='ASSESS_DOCUMENT_IMPACT'))
 def test_unknown_native_machine_identity_rejected(self):
  m,o=self.observation();o['machineId']='not-the-machine'
  with self.assertRaises(w.EvidenceError):self.store.observe_machine(self.ctx,m,o)
 def test_invalid_native_token_rejected(self):
  m,o=self.observation();o['outputVector'][0]=1.5
  with self.assertRaises(w.EvidenceError):self.store.observe_machine(self.ctx,m,o)
 def test_native_trace_provenance_required(self):
  m,o=self.observation();del o['providerRef']
  with self.assertRaises(w.EvidenceError):self.store.observe_machine(self.ctx,m,o)
 def test_observation_cannot_claim_fact_changes(self):
  with self.assertRaises(w.EvidenceError):self.store.reconcile_event(self.ctx,{**self.event,'type':'recognizer-observed','machineId':'fixture','observationRef':{},'changedAssetTypeIds':['SOURCE-REGISTER']},['SOURCE-REGISTER'])
 def test_unresolved_observation_stays_open(self):
  m,o=self.observation();task=self.store.observe_machine(self.ctx,m,o)[0];a=self.store.catalog[task['assetTypeId']];r=self.store.resolve_assessment(self.ctx,task['taskId'],{'ownerName':a['ownerName'],'basis':'Fixture missing actual evidence','evidenceRefs':['fixture://missing-evidence-ticket'],'disposition':'UNRESOLVED'});self.assertEqual(r['status'],'OPEN')
 def test_verified_observation_impact_invalidates_target(self):
  m,o=self.observation();self.approved('SOURCE-REGISTER');task=next(t for t in self.store.observe_machine(self.ctx,m,o) if t['assetTypeId']=='SOURCE-REGISTER');self.store.resolve_assessment(self.ctx,task['taskId'],{'ownerName':self.store.catalog['SOURCE-REGISTER']['ownerName'],'basis':'Fixture independently verified input correction','evidenceRefs':['fixture://input-correction'],'disposition':'REFRESH_REQUIRED'});self.assertEqual(self.store.head(self.ctx,'SOURCE-REGISTER')['status'],'STALE')
if __name__=='__main__':unittest.main(verbosity=2)
