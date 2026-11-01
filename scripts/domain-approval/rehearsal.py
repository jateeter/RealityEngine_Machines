#!/usr/bin/env python3
"""Test-only prepare/submit/finalize rehearsal using disposable Git/forge fixtures.

The production state machine runs unchanged. Native/toolchain/forge adapters are
explicit fixtures, not runtime evidence. No network or production acceptance.
"""
from __future__ import annotations
import argparse, importlib.util, io, json, os, shutil, subprocess, sys, uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def load_core():
    spec=importlib.util.spec_from_file_location('approval_rehearsal_core',HERE/'approval.py')
    core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core);return core

def validate_waiver(value,domain):
    if value.get('approvalContext')!='TEST_ONLY' or value.get('productionApproval') is not False:
        raise ValueError('An explicit TEST_ONLY, productionApproval=false waiver is required')
    if value.get('domain')!=domain or value.get('independentSignoff')!='WAIVED_BY_OPERATOR_FOR_WORKFLOW_TEST':
        raise ValueError('Waiver does not cover this domain and independent-signoff test')
    for key in ['operatorStatement','recordedDate','scope']:
        if not isinstance(value.get(key),str) or not value[key].strip():raise ValueError('Missing waiver '+key)
    return value

def run(args):
    core=load_core();domain=core.slug(args.domain)
    waiver=validate_waiver(core.read(args.waiver),domain)
    source=args.repo.resolve();out=args.evidence.resolve()
    core.ensure(not out.exists(),'Use a new evidence directory; test evidence is immutable')
    core.ensure(not out.is_relative_to(source),'Test evidence must be outside the source repository')
    out.mkdir(parents=True);core.write(out/'operator-waiver.json',waiver)
    source_before=core.snapshot(source)
    candidate=core.inventory(source,domain)
    runid=str(uuid.uuid4());version='1.4.0-workflow-test.run'+runid[:8]
    sandbox=out/'TEST_ONLY_SANDBOX';sandbox.mkdir()
    repo=sandbox/'RealityEngine_Machines';ci=sandbox/'RealityEngine_CI'
    forge=out/'TEST_ONLY_FORGE_FIXTURES';forge.mkdir()
    git_env=dict(os.environ,GIT_CONFIG_NOSYSTEM='1',GIT_TERMINAL_PROMPT='0')
    def git_at(path,*argv):
        return subprocess.check_output(['git',*map(str,argv)],cwd=path,text=True,stderr=subprocess.PIPE,env=git_env).strip()
    for path in [repo,ci]:
        path.mkdir();git_at(path,'init','-q','-b','main')
        git_at(path,'config','user.name','Workflow test fixture')
        git_at(path,'config','user.email','workflow-test@example.invalid')
        git_at(path,'config','commit.gpgsign','false');git_at(path,'config','tag.gpgsign','false')
        git_at(path,'config','core.hooksPath',sandbox/'NO_HOOKS')
        bare=sandbox/(path.name+'.git')
        git_at(sandbox,'init','--bare','-q',bare)
        git_at(path,'remote','add','origin',bare)
    for rel in candidate:
        src=source/'machines'/rel;dst=repo/'machines'/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
    assets=source/'machine_factory/domains'/domain
    catalog=core.read(assets/'document-asset-catalog.json')
    findings=core.read(assets/'accounting-findings.json')['findings']
    core.write(out/'test-acceptance-decisions.json',{
        'approvalContext':'TEST_ONLY','productionApproval':False,'independentSignoff':waiver['independentSignoff'],
        'waiverSHA256':core.filehash(out/'operator-waiver.json'),'sourceCommit':git_at(source,'rev-parse','HEAD'),
        'findings':[{'findingId':f['id'],'decision':'APPROVED_FOR_WORKFLOW_TEST_ONLY','originalStatus':f['status']} for f in findings],
        'documents':[{'assetTypeId':a['assetTypeId'],'decision':'APPROVED_FOR_WORKFLOW_TEST_ONLY'} for a in catalog['assetTypes']],
        'limitations':'Does not resolve substantive accounting gaps, independently approve documents, or authorize production.'})
    core.write(repo/'domains/domain-manifest.json',{'domains':{domain:{'status':'experimental','currentMachineCount':len(candidate)}}})
    core.write(repo/'domains/domain-registry.json',{'domains':{domain:{'approvalContext':'TEST_ONLY'}}})
    scopes=['domain:'+domain,'corpus:'+domain]
    core.write(repo/'domains/ces-contract-registry.json',{'scopes':{s:{'status':'unrecorded'} for s in scopes}})
    (repo/'node_modules/ajv').mkdir(parents=True)
    (ci/'config').mkdir();(ci/'config'/f'{domain}-corpus.txt').write_text('\n'.join(candidate)+'\n')
    (ci/'README.md').write_text('TEST ONLY: isolated CI fixture, no runtime startup.\n')
    for path in [repo,ci]:
        git_at(path,'add','machines','domains') if path==repo else git_at(path,'add','README.md','config')
        git_at(path,'commit','-qm','TEST ONLY initial fixture')
        git_at(path,'push','-q','-u','origin','main')
        git_at(path,'switch','-qc','workflow-test/'+runid[:8])
    runner=sandbox/'test-scope-runner.sh';runner.write_text('#!/bin/sh\nexit 98 # Never executed: explicit workflow fixture adapter\n');runner.chmod(0o755)
    stage=out/'test-run';original_write=core.write;original_cmd=core.cmd
    def tagged_write(path,value):
        if isinstance(value,dict) and ('schemaVersion' in value or 'state' in value):
            value={**value,'approvalContext':'TEST_ONLY','productionApproval':False}
        original_write(path,value)
    def origin(path):
        core.ensure(Path(path).resolve() in [repo.resolve(),ci.resolve()],'Fixture origin outside sandbox')
        return 'workflow-fixture.invalid/'+Path(path).name
    def forge_file(path):return forge/(Path(path).name+'-pr.json')
    def command(argv,cwd=None):
        cwd=Path(cwd or repo);argv=list(map(str,argv))
        core.ensure(cwd.resolve().is_relative_to(sandbox.resolve()),'Command outside test sandbox')
        if argv[0]=='node' and len(argv)>1 and argv[1]==str(repo/'scripts/validate-schemas.mjs'):
            original_write(forge/'direct-schema-fixture.json',{'evidenceClass':'WORKFLOW_FIXTURE','requestedArguments':argv,'actualValidation':'NOT_RUN_FIXTURE_CONTROL_FLOW_ONLY'})
            return 'WORKFLOW_FIXTURE_SCHEMA_STAGE'
        if argv[0]!='gh':
            core.ensure(argv[0]=='git','Non-Git external command must use explicit stage fixture')
            if argv[1] in {'push','fetch','ls-remote'}:
                remote=git_at(cwd,'remote','get-url','origin')
                core.ensure(Path(remote).resolve().is_relative_to(sandbox.resolve()),'Nonlocal Git remote prohibited')
            return original_cmd(argv,cwd)
        if argv[1:3]==['pr','create']:
            view={'number':1,'url':'https://forge.workflow-test.invalid/'+cwd.name+'/pull/1','state':'OPEN',
                  'headRefOid':git_at(cwd,'rev-parse','HEAD'),'baseRefName':'main','author':{'login':'test-operator'},
                  'statusCheckRollup':[{'name':'Workflow fixture checks','conclusion':'SUCCESS','evidenceClass':'WORKFLOW_FIXTURE'}],
                  'approvalContext':'TEST_ONLY','productionApproval':False}
            original_write(forge_file(cwd),view);return view['url']
        if argv[1:3]==['pr','view']:return json.dumps(core.read(forge_file(cwd)))
        if argv[1]=='api':return '[[]]' # No fictional reviewer APPROVED event.
        if argv[1:3]==['release','create']:
            tag=argv[3];core.ensure('workflow-test' in tag,'Release must have test version')
            original_write(forge/(cwd.name+'-'+core.digest(tag.encode())[:12]+'-release.json'),{
                'approvalContext':'TEST_ONLY','productionApproval':False,'forgeOperation':'SIMULATED_RELEASE_CREATE',
                'tag':tag,'arguments':argv,'remote':'LOCAL_FIXTURE_ONLY'})
            return 'workflow-fixture-release'
        raise ValueError('Unsupported fixture forge operation '+repr(argv[:3]))
    class FixtureRun(core.Run):
        def execute(self,label,argv,cwd=None,env=None):
            cwd=Path(cwd or repo)
            requested=list(map(str,argv))
            if getattr(args,'fail_stage',None)==label:
                return super().execute('FIXTURE-INTENTIONAL-FAILURE-'+label,[sys.executable,'-c','print("INTENTIONAL_WORKFLOW_TEST_FAILURE");raise SystemExit(7)'],cwd)
            if label.startswith('scope-'):
                request=core.read(Path(requested[1]));scope_out=Path(requested[2]);scope=request['scope']
                core.write(scope_out/'fixture-native.json',{'evidenceClass':'WORKFLOW_FIXTURE','nativeExecution':'NOT_RUN',
                    'testedMachines':request['testedMachines'],'purpose':'Exercises receipt validation/control flow, not native parity'})
                core.write(scope_out/'receipt.json',{'domain':domain,'scope':scope,'testedMachines':request['testedMachines'],
                    'result':'PASS','checks':{'isreParity':'PASS','osreParity':'PASS','domainIntegration':'PASS'},
                    'engines':['cpp','lsp','scala'],'evidenceClass':'WORKFLOW_FIXTURE','productionApproval':False,
                    'instanceRegistryURL':'http://127.0.0.1:1/re-registry.json','artifacts':[{'path':'fixture-native.json','sha256':core.filehash(scope_out/'fixture-native.json')}]})
            if label.startswith('record-'):
                scope='domain:'+domain if '--only' in requested else 'corpus:'+domain
                core.write(ci/'config/ces-contracts'/(scope.replace(':','-')+'.json'),{'evidenceClass':'WORKFLOW_FIXTURE','scope':scope,'notNativeEvidence':True})
            if label in {'cesgen-refresh','admitted-cesgen'}:
                core.write(repo/'domains/ces-contract-registry.json',{'scopes':{s:{'status':'recorded','evidenceClass':'WORKFLOW_FIXTURE'} for s in scopes}})
            if label=='domain-reasoning':
                for name in ['lane-graph.ttl','decision-table.json']:
                    target=repo/'semantics/lanes'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text('TEST_ONLY_WORKFLOW_FIXTURE\n')
            fixture={'evidenceClass':'WORKFLOW_FIXTURE','requestedStage':label,'requestedArguments':requested,
                     'actualExecution':'Control-flow fixture, not the requested native/toolchain/accounting gate',
                     'reviewWaiver':waiver['independentSignoff'] if label=='ifrs-accounting-readiness' else None}
            super().execute('FIXTURE-'+label,[sys.executable,'-c','import json;print(json.dumps('+repr(fixture)+'))'],cwd)
            self.events[-1].update(requestedStage=label,evidenceClass='WORKFLOW_FIXTURE')
            core.write(self.folder/'events.json',self.events)
    original_scope=core.validate_scope_receipt
    def fixture_scope(receipt,*values):
        return original_scope(receipt,*values,allow_workflow_fixture=True)
    waiver_review={'state':'WAIVED_FOR_WORKFLOW_TEST','independentReviewPerformed':False,
                   'operatorWaiverSHA256':core.filehash(out/'operator-waiver.json'),'approvalContext':'TEST_ONLY'}
    def test_approvers(reviews,head,author):
        core.ensure(not reviews,'Unexpected reviewer records in no-signoff rehearsal')
        return [waiver_review]
    def fixture_context(record):
        core.ensure(record.get('approvalContext')=='TEST_ONLY' and record.get('productionApproval') is False,'Fixture context missing')
        for key in ['machinesRepo','ciRepo']:
            if key in record:core.ensure(Path(record[key]).resolve().is_relative_to(sandbox.resolve()),'Fixture state escapes sandbox')
    from contextlib import ExitStack
    fixture_inventory={'evidenceClass':'WORKFLOW_FIXTURE','nativeInstancesLaunched':0}
    with ExitStack() as stack:
        for name,value in [('MACHINES',repo),('write',tagged_write),('cmd',command),('origin',origin),('Run',FixtureRun),
                           ('validate_scope_receipt',fixture_scope),('approved_reviewers',test_approvers),('require_production_context',fixture_context),
                           ('urlopen',lambda *a,**k:io.BytesIO(json.dumps(fixture_inventory).encode()))]:
            stack.enter_context(patch.object(core,name,value))
        stack.enter_context(patch.object(core.shutil,'which',return_value=sys.executable))
        core.prepare(SimpleNamespace(repo=repo,ci=ci,domain=domain,version=version,evidence=stage,
                                   scope_runner=runner,regression_profile=domain,allow_runtime_reset=True))
        prepared=core.read(stage/'state.json');core.ensure(prepared['state']=='PREPARED_PENDING_GITHUB_REVIEW','Preparation did not complete')
        core.submit(SimpleNamespace(evidence=stage,evidence_reviewed=True))
        submitted=core.read(stage/'state.json');core.ensure(submitted['state']=='SUBMITTED_PENDING_GITHUB_REVIEW','Submission did not complete')
        for path in [ci,repo]:
            if not forge_file(path).exists():continue
            view=core.read(forge_file(path));head=view['headRefOid']
            git_at(path,'switch','-q','main');git_at(path,'merge','--ff-only',head)
            git_at(path,'push','-q','origin','main');view.update(state='MERGED',mergeCommit={'oid':head})
            original_write(forge_file(path),view)
        core.finalize(SimpleNamespace(evidence=stage,sign_tag=False))
    final=core.read(stage/'state.json');core.ensure(final['state']=='APPROVED_MERGED','Finalization did not complete')
    core.ensure(core.snapshot(source)==source_before,'Source candidate was modified')
    source_manifest=core.read(source/'domains/domain-manifest.json')['domains'][domain]
    fixture_manifest=core.read(repo/'domains/domain-manifest.json')['domains'][domain]
    core.ensure(fixture_manifest['status']=='accepted','Test catalog admission missing')
    events=core.read(stage/'events.json')
    core.ensure(all(core.filehash(stage/x['log'])==x['logSHA256'] for x in events),'Test log digest mismatch')
    summary={'schemaVersion':'1.0.0','state':'TEST_WORKFLOW_COMPLETE','approvalContext':'TEST_ONLY','productionApproval':False,
        'runId':runid,'domain':domain,'version':version,'sourceCandidateCommit':git_at(source,'rev-parse','HEAD'),
        'productionWorkflowScriptSHA256':core.filehash(HERE/'approval.py'),'testHarnessSHA256':core.filehash(Path(__file__)),
        'operatorWaiverSHA256':core.filehash(out/'operator-waiver.json'),'independentSignoff':'WAIVED_BY_OPERATOR_FOR_WORKFLOW_TEST',
        'stages':['PREPARED_PENDING_GITHUB_REVIEW','SUBMITTED_PENDING_GITHUB_REVIEW','APPROVED_MERGED'],
        'stageSemantics':'All stages ran in disposable local Git and explicitly simulated forge/native adapters',
        'fixtureScopeCount':len(scopes),'fixtureGateEventCount':len(events),'candidateMachineCount':len(candidate),
        'testFindingApprovals':len(findings),'testDocumentApprovals':len(catalog['assetTypes']),
        'testManifestStatus':fixture_manifest['status'],'sourceManifestStatus':source_manifest['status'],
        'productionCandidateUnchanged':True,'productionFindingClosures':0,'actualNativeParity':'NOT_RUN',
        'actualGitHubApprovalOrRelease':'NOT_PUBLISHED','managerLiveLoadVerification':'NOT_RUN_TEST_MANIFEST_ONLY',
        'localTestTag':final['approval']['tag'],'fixtureOnlyTagRemote':str(sandbox/'RealityEngine_Machines.git'),
        'evidenceFiles':{str(p.relative_to(out)):core.filehash(p) for p in [out/'operator-waiver.json',out/'test-acceptance-decisions.json',stage/'plan.json',stage/'events.json',stage/'state.json',stage/'approval.json',stage/'evidence.tar.gz']}}
    original_write(out/'test-workflow-summary.json',summary)
    print(json.dumps(summary,indent=2));return summary

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,default=ROOT);parser.add_argument('--domain',required=True)
    parser.add_argument('--fail-stage',choices=['ifrs-accounting-readiness','domain-reasoning'],help='Intentional negative-path test; no submission/finalization')
    parser.add_argument('--waiver-file',dest='waiver',type=Path,required=True);parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args(argv);run(args)
if __name__=='__main__':main()
