"""Admission guards; entirely local, synthetic, no live services or forge writes."""
import copy,importlib.util,json,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('domain_approval',ROOT/'scripts/domain-approval/approval.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)

class AdmissionGuards(unittest.TestCase):
    def test_slug_injection_and_traversal_rejected(self):
        for value in ['../main','x;exit','UPPER','--all','a/b','']:
            with self.subTest(value=value),self.assertRaises(ValueError):a.slug(value)
        self.assertEqual(a.slug('health-personal'),'health-personal')
    def test_version_immutable_namespace(self):
        self.assertEqual(a.version('1.2.3-rc.1'),'1.2.3-rc.1')
        for value in ['v1','latest','01.2.3','1.2.3/evil','1.2.3;exit']:
            with self.subTest(value=value),self.assertRaises(ValueError):a.version(value)
    def receipt(self):
        return {'domain':'x','scope':'domain:x','testedMachines':{'domains/x/a.json':'a'*64},'result':'PASS','checks':{'isreParity':'PASS','osreParity':'PASS','domainIntegration':'PASS'},'engines':['cpp','lsp','scala'],'artifacts':[{'path':'evidence.json','sha256':'b'*64}],'instanceRegistryURL':'http://127.0.0.1:10001/re-registry.json'}
    def test_complete_scope_receipt(self):
        r=self.receipt();self.assertTrue(a.validate_scope_receipt(r,'x','domain:x',r['testedMachines']))
    def test_partial_or_skipped_scope_evidence_rejected(self):
        for key,value in [('domain','other'),('scope','corpus:other'),('testedMachines',{}),('result','SKIPPED'),('artifacts',[]),('engines',['cpp','cpp','lsp']),('instanceRegistryURL','file:///tmp/fake')]:
            r=self.receipt();r[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):a.validate_scope_receipt(r,'x','domain:x',self.receipt()['testedMachines'])
    def test_each_gate_mandatory(self):
        for key in ['isreParity','osreParity','domainIntegration']:
            r=self.receipt();r['checks'][key]='NOT_RUN'
            with self.subTest(key=key),self.assertRaises(ValueError):a.validate_scope_receipt(r,'x','domain:x',r['testedMachines'])
    def review(self,user='reviewer',state='APPROVED',commit='head'):
        return {'user':{'login':user},'state':state,'commit_id':commit}
    def test_self_approval_not_accepted(self):self.assertFalse(a.approved_reviewers([self.review('author')],'head','author'))
    def test_old_head_approval_not_accepted(self):self.assertFalse(a.approved_reviewers([self.review(commit='old')],'head','author'))
    def test_independent_current_head_accepted(self):self.assertEqual(len(a.approved_reviewers([self.review()],'head','author')),1)
    def test_dismissed_approval_not_accepted(self):self.assertFalse(a.approved_reviewers([self.review(),self.review(state='DISMISSED')],'head','author'))
    def test_outstanding_changes_request_blocks_other_approval(self):
        with self.assertRaises(ValueError):a.approved_reviewers([self.review(),self.review('other','CHANGES_REQUESTED')],'head','author')
    def test_comment_does_not_erase_prior_decision(self):self.assertEqual(len(a.approved_reviewers([self.review(),self.review(state='COMMENTED')],'head','author')),1)
    def test_pending_pr_cannot_finalize(self):
        with patch.object(a,'gh_json',return_value={'state':'OPEN','baseRefName':'main'}),self.assertRaises(ValueError):a.merged_pr(ROOT,'https://github.com/o/r/pull/1','head')
    def test_changed_head_cannot_finalize(self):
        with patch.object(a,'gh_json',return_value={'state':'MERGED','baseRefName':'main','headRefOid':'new'}),self.assertRaises(ValueError):a.merged_pr(ROOT,'url','tested')
    def test_missing_scope_fingerprint_not_empty_success(self):
        with tempfile.TemporaryDirectory() as td,self.assertRaises(ValueError):a.inventory(Path(td),'empty')
    def test_snapshot_includes_generated_new_aboxes_not_unrelated_files(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);subprocess.run(['git','init','-q',str(r)],check=True)
            (r/'candidate').write_text('one');subprocess.run(['git','add','candidate'],cwd=r,check=True)
            p=r/'semantics/abox/x/a.ttl';p.parent.mkdir(parents=True);p.write_text('new semantics')
            (r/'unrelated').write_text('do not stage')
            snap=a.snapshot(r);self.assertIn('semantics/abox/x/a.ttl',snap);self.assertNotIn('unrelated',snap)
            (r/'candidate').write_text('two');self.assertNotEqual(snap,a.snapshot(r))
    def test_snapshot_includes_new_ci_ces_shard(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);subprocess.run(['git','init','-q',str(root)],check=True)
            p=root/'config/ces-contracts/domain-new.json';p.parent.mkdir(parents=True);p.write_text('{}')
            self.assertIn('config/ces-contracts/domain-new.json',a.snapshot(root))
            self.assertEqual(a.snapshot(root,('config/ces-contracts/',)),{})
    def test_failed_gate_persists_exit_and_log_without_success(self):
        with tempfile.TemporaryDirectory() as td:
            run=a.Run(Path(td))
            with self.assertRaises(ValueError):run.execute('negative',['python3','-c','raise SystemExit(9)'],Path(td))
            events=a.read(Path(td)/'events.json');self.assertEqual(events[0]['exitCode'],9)
            self.assertEqual(events[0]['logSHA256'],a.filehash(Path(td)/events[0]['log']))
    def test_evidence_tamper_rejected_before_publication(self):
        with tempfile.TemporaryDirectory() as td:
            f=Path(td);(f/'gate.log').write_text('changed')
            state={'state':'PREPARED_PENDING_GITHUB_REVIEW','machinesRepo':'one','ciRepo':'two','machinesSnapshot':{},'ciSnapshot':{},'events':[{'exitCode':0,'log':'gate.log','logSHA256':'0'*64}],'scopeEvidence':{}}
            with patch.object(a,'snapshot',return_value={}),self.assertRaises(ValueError):a.verify_prepared(state,f)
    def test_unprepared_submission_rejected(self):
        with self.assertRaises(ValueError):a.verify_prepared({'state':'FAILED_NOT_APPROVED'},ROOT)
    def test_reviewed_ledger_binds_local_snapshots(self):
        state={'machinesSnapshot':{'file':'hash'},'ciSnapshot':{'shard':'hash'}}
        ledger={'machinesSnapshotSHA256':a.objecthash(state['machinesSnapshot']),'ciSnapshotSHA256':a.objecthash(state['ciSnapshot'])}
        a.validate_bound_state(ledger,state)
        state['machinesSnapshot']={}
        with self.assertRaises(ValueError):a.validate_bound_state(ledger,state)
    def test_reviewed_ledger_binds_version_and_run(self):
        state={'runId':'changed','machinesSnapshot':{},'ciSnapshot':{}}
        with self.assertRaises(ValueError):a.validate_bound_state({'runId':'reviewed'},state)
if __name__=='__main__':unittest.main()
