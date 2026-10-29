#!/usr/bin/env python3
"""Versioned domain admission orchestration. No implicit merge or self-approval."""
from __future__ import annotations
import argparse, datetime as dt, fcntl, gzip, hashlib, json, os, re, shutil, subprocess, sys, tarfile, uuid
from pathlib import Path
from urllib.request import urlopen

BASH='/opt/homebrew/bin/bash'
MACHINES=Path(__file__).resolve().parents[2]
GENERATORS=['build-corpus-index.py','build-region-allocation.py',
            'build-arbitration-registry.py','inventory-semantic-buses.py',
            'backfill-lane-contracts.py','project-lanes.py','compile-decision-table.py']
# Authored domain/arbiter semantics are inputs. Never fabricate them from counts.
DERIVED=['domains/corpus-index.json','domains/region-allocation.json',
         'domains/arbitration-registry.json','domains/semantic-bus-registry.json',
         'domains/lane-contracts.json','domains/ces-contract-registry.json',
         'semantics/abox','semantics/abox-manifest.json','semantics/released']

def ensure(ok,message):
    if not ok: raise ValueError(message)
def read(path): return json.loads(Path(path).read_text())
def write(path,obj):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    temp=p.with_name(p.name+'.tmp');temp.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n');temp.replace(p)
def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def digest(data): return hashlib.sha256(data).hexdigest()
def filehash(path):
    hasher=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):hasher.update(chunk)
    return hasher.hexdigest()
def objecthash(obj): return digest(json.dumps(obj,sort_keys=True,separators=(',',':')).encode())
def cmd(argv,cwd=MACHINES):
    return subprocess.check_output([str(x) for x in argv],cwd=cwd,text=True).strip()
def git(repo,*args): return cmd(['git',*args],repo)
def origin(repo):
    url=git(repo,'remote','get-url','origin')
    m=re.fullmatch(r'(?:https://github\.com/|git@github\.com:)([^/]+/[^/]+?)(?:\.git)?',url)
    ensure(m is not None,'Only a verified github.com origin is supported: '+url)
    return m.group(1)
def slug(value):
    ensure(bool(re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*',value)),'Invalid domain slug')
    return value
def version(value):
    ensure(bool(re.fullmatch(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?',value)),'Use a SemVer release version (without v)')
    if '-' in value:
        identifiers=value.split('-',1)[1].split('.')
        ensure(all(x and not (x.isdigit() and len(x)>1 and x.startswith('0')) for x in identifiers),'Invalid SemVer prerelease identifiers')
    return value
def unused_version(repo,domain,ver):
    tag=f'refs/tags/domain/{domain}/v{ver}'
    ensure(not cmd(['git','ls-remote','--tags','origin',tag],repo),'This domain version already has an approval tag; use a new version')

def clean(repo):
    ensure(not git(repo,'status','--porcelain','--untracked-files=no'),'Commit tracked candidate changes before starting: '+str(repo))
    # Never let untracked corpus/config/semantic input silently enter approval.
    paths=git(repo,'ls-files','--others','--exclude-standard').splitlines()
    protected=('machines/','domains/','schemas/','semantics/','config/')
    ensure(not any(p.startswith(protected) for p in paths),'Untracked admission inputs; commit or remove intentionally: '+str(repo))
def branch(repo):
    b=git(repo,'branch','--show-current');ensure(b and b not in ('main','master'),'Use a named development branch: '+str(repo));return b

def snapshot(repo,exclude=()):
    paths=git(repo,'ls-files','-z').split('\0');out={}
    paths += [p for p in git(repo,'ls-files','--others','--exclude-standard','-z').split('\0') if any(p==d or p.startswith(d+'/') for d in DERIVED) or p.startswith('config/ces-contracts/')]
    paths=sorted(set(paths))
    for rel in paths:
        if not rel or any(rel.startswith(x) for x in exclude):continue
        p=repo/rel
        out[rel]=filehash(p) if p.is_file() else 'DELETED'
    return out

def input_snapshot(repo):
    return snapshot(repo,tuple(DERIVED)+('domains/approvals/', 'semantics/lanes/'))

def inventory(repo,domain):
    files=sorted((repo/'machines/domains'/domain).rglob('*.json'))
    ensure(files,'Domain has no canonical machine files: '+domain)
    result={}
    for p in files:
        d=read(p);ensure(isinstance(d.get('machine'),dict),'Not a machine: '+str(p))
        result[p.relative_to(repo/'machines').as_posix()]=filehash(p)
    return result

def plan(repo,ci,domain,ver):
    slug(domain);version(ver)
    manifest=read(repo/'domains/domain-manifest.json');ensure(domain in manifest['domains'],'Author a non-accepted manifest entry before admission')
    architecture=read(repo/'domains/domain-registry.json')
    ensure(domain in architecture['domains'],'Author the architecture domain registry entry before admission')
    members=inventory(repo,domain)
    scopes=read(repo/'domains/ces-contract-registry.json')['scopes']
    # Universal-vector contention can change peer output even without a peer file
    # hash changing. Re-certify every known scope rather than guess dependency closure.
    names=set(scopes)|{'domain:'+domain}
    for p in (ci/'config').glob('*-corpus.txt'):names.add('corpus:'+p.name[:-len('-corpus.txt')])
    for p in (repo/'machines/domains').iterdir():
        if p.is_dir() and any(p.glob('*.json')):names.add('domain:'+p.name)
    return {'schemaVersion':'1.0.0','domain':domain,'version':ver,'candidateCommit':git(repo,'rev-parse','HEAD'),
            'candidateMachines':members,'machineCount':len(members),
            'refreshScope':'All known CES domain/corpus scopes conservatively: shared-space changes can affect peer commits',
            'cesScopes':sorted(names),'derivedArtifacts':DERIVED+['semantics/lanes/lane-graph.ttl','semantics/lanes/decision-table.json'],
            'authoredInputs':['domains/domain-manifest.json','domains/domain-registry.json','machine schemas, semantics, arbitration and regression profile selection'],
            'protocol':'RealityEngine_CI/MACHINE_CONCEPT.md section 9; RealityEngine_CI/docs/ENGINEERING_CONTRACT.md',
            'state':'PLAN_ONLY_NOT_APPROVED'}

class Run:
    def __init__(self,folder):self.folder=Path(folder);self.events=[]
    def execute(self,label,argv,cwd=MACHINES,env=None):
        log=self.folder/'logs'/f'{len(self.events):03}-{label}.log';log.parent.mkdir(parents=True,exist_ok=True)
        started=now()
        with log.open('wb') as stream:
            p=subprocess.run([str(x) for x in argv],cwd=cwd,stdout=stream,stderr=subprocess.STDOUT,env=env)
        event={'step':label,'argv':[str(x) for x in argv],'cwd':str(cwd),'startedAt':started,'finishedAt':now(),
               'exitCode':p.returncode,'log':str(log.relative_to(self.folder)),'logSHA256':filehash(log)}
        self.events.append(event);write(self.folder/'events.json',self.events)
        ensure(p.returncode==0,f'{label} failed ({p.returncode}); inspect {log}. No approval recorded.')
    def python(self,label,script,*args,repo=MACHINES):self.execute(label,['python3',repo/'scripts'/script,*args],repo)

def validate_scope_receipt(receipt,domain,scope,members):
    ensure(receipt.get('domain')==domain and receipt.get('scope')==scope,'Scope evidence bound to a different request')
    ensure(receipt.get('result')=='PASS','Integration/parity runner did not pass')
    ensure(receipt.get('testedMachines')==members,'Runner must fingerprint every requested machine, not just attest a domain name')
    ensure(receipt.get('checks',{}).get('isreParity')=='PASS' and receipt['checks'].get('osreParity')=='PASS','Both ISRE and OSRE parity required')
    ensure(receipt['checks'].get('domainIntegration')=='PASS','Domain-specific source/provider/action integration evidence required')
    ensure(len(receipt.get('engines',[]))==3 and set(receipt['engines'])=={'cpp','lsp','scala'},'Exactly one C++, LSP and Scala instance required')
    ensure(receipt.get('artifacts'),'Runner must name actual evidence artifacts, not only an exit code')
    url=receipt.get('instanceRegistryURL','')
    ensure(re.fullmatch(r'https?://[^\s]+',url) is not None,'Runner must supply a resolved instance registry URL')
    return url

def scope_members(repo,ci,scope):
    kind,name=scope.split(':',1)
    if kind=='domain':return inventory(repo,name)
    paths=(ci/'config'/f'{name}-corpus.txt').read_text().splitlines(); result={}
    for rel in paths:
        rel=rel.strip()
        if not rel or rel.startswith('#'):continue
        p=repo/'machines'/rel
        if not p.is_file():p=repo.parent/'localAIStack/data/machines'/rel
        ensure(p.is_file(),'Unresolved corpus member: '+rel);result[rel]=filehash(p)
    ensure(result,'Empty corpus scope: '+scope);return result

def prepare(args):
    repo=args.repo.resolve();ci=args.ci.resolve();folder=args.evidence.resolve()
    ensure(not folder.exists(),'Use a new evidence directory; failed/successful ledgers are never overwritten')
    ensure(not folder.is_relative_to(repo) and not folder.is_relative_to(ci),'Evidence directory must be outside both repositories')
    for tool in ['git','gh','python3','node']:ensure(shutil.which(tool),'Missing required prerequisite: '+tool)
    ensure(shutil.which(os.environ.get('ROBOT_BIN','robot')),'ROBOT must be available via PATH or ROBOT_BIN; reasoning cannot be skipped')
    ensure((repo/'node_modules/ajv').is_dir(),'Install declared Node dependencies first; schema validation may not be skipped')
    ensure(ci==(repo.parent/'RealityEngine_CI').resolve(),'Canonical generators require the sibling RealityEngine_CI checkout')
    runner=args.scope_runner.resolve();ensure(runner.is_file() and os.access(runner,os.X_OK),'Scope runner must be an executable file')
    ensure(args.allow_runtime_reset,'Preparation drives/resets development engines; specify --allow-runtime-reset after reviewing the plan')
    for r in [repo,ci]:
        clean(r);branch(r);cmd(['git','fetch','origin','main'],r)
        ensure(subprocess.run(['git','merge-base','--is-ancestor','origin/main','HEAD'],cwd=r).returncode==0,'Rebase the candidate branch onto current origin/main first: '+str(r))
    p=plan(repo,ci,args.domain,args.version)
    unused_version(repo,args.domain,args.version)
    profile=scope_members(repo,ci,'corpus:'+slug(args.regression_profile))
    ensure(any(x in profile for x in p['candidateMachines']),'Regression profile must include at least one actual machine from this domain')
    folder.mkdir(parents=True)
    write(folder/'plan.json',p)
    run=Run(folder);runid=str(uuid.uuid4());repo_inputs=input_snapshot(repo);ci_inputs=snapshot(ci,('config/ces-contracts/',))
    state={'schemaVersion':'1.0.0','runId':runid,'domain':args.domain,'version':args.version,'state':'PREPARING_NOT_APPROVED',
           'createdAt':now(),'machinesRepo':str(repo),'ciRepo':str(ci),'machinesOrigin':origin(repo),'ciOrigin':origin(ci),
           'machinesBranch':branch(repo),'ciBranch':branch(ci),'candidateCommit':p['candidateCommit'],
           'ciCandidateCommit':git(ci,'rev-parse','HEAD'),'regressionProfile':args.regression_profile,'scopeRunnerSHA256':filehash(runner),'scopeRunner':str(runner),
           'candidateMachines':p['candidateMachines'],'plan':p,'events':[]}
    write(folder/'state.json',state)
    try:
        for script in GENERATORS:run.python(script[:-3],script,'--write',repo=repo)
        # Remove only orphan ABoxes, never authored ontology/shapes/action maps.
        for ttl in (repo/'semantics/abox').glob('*/*.ttl'):
            source=repo/'machines/domains'/ttl.parent.name/(ttl.stem+'.json')
            if not source.exists():ttl.unlink()
        run.python('owl-generate','generate-owl.py','--all','--write','--strict-actions',repo=repo)
        run.python('owl-manifest','generate-owl.py','--manifest-write','--strict-actions',repo=repo)
        run.execute('engine-build-provenance',['python3',ci/'scripts/verify-build-provenance.py','--no-fetch'],ci)
        # Runner is reviewed project-specific orchestration, never arbitrary eval.
        for scope in p['cesScopes']:
            out=folder/'scopes'/scope.replace(':','-');out.mkdir(parents=True)
            request={'domain':args.domain,'scope':scope,'candidateMachines':p['candidateMachines'],
                     'testedMachines':scope_members(repo,ci,scope),'candidateCommit':p['candidateCommit'],
                     'instructions':'Boot/load exact scope using canonical CI orchestration; demonstrate current-source ISRE/OSRE parity and applicable integrations. Do not fabricate receipts.'}
            write(out/'request.json',request)
            run.execute('scope-'+scope.replace(':','-'),[runner,out/'request.json',out],ci)
            ensure(filehash(runner)==state['scopeRunnerSHA256'],'Scope runner changed during validation')
            receipt=read(out/'receipt.json');url=validate_scope_receipt(receipt,args.domain,scope,request['testedMachines'])
            # Bind artifacts to local bytes; forbid escaping the scope evidence folder.
            for artifact in receipt['artifacts']:
                path=(out/artifact['path']).resolve()
                ensure(path.is_relative_to(out) and path.is_file(),'Missing/out-of-scope evidence artifact')
                ensure(filehash(path)==artifact['sha256'],'Evidence artifact digest mismatch')
            with urlopen(url,timeout=15) as response:instances=json.load(response)
            write(out/'instance-registry.json',instances)
            run.execute('build-provenance-'+scope.replace(':','-'),['python3',ci/'scripts/verify-build-provenance.py','--no-fetch'],ci)
            kind,name=scope.split(':',1)
            run.execute('record-'+scope.replace(':','-'),['python3',ci/'scripts/record-ces-contracts.py','--registry',url,'--only' if kind=='domain' else '--corpus',name,'--write'],ci)
        run.python('cesgen-refresh','build-ces-contract-registry.py','--write',repo=repo)
        ces=read(repo/'domains/ces-contract-registry.json')['scopes']
        ensure(all(ces[s]['status']=='recorded' for s in p['cesScopes']),'A CES scope is missing/stale/unrecorded after refresh')
        env=dict(os.environ,STRICT_DOMAIN_CONTRACT='1')
        run.execute('strict-corpus',[BASH,repo/'scripts/validate-corpus.sh'],repo,env)
        run.execute('explicit-schema',['node',repo/'scripts/validate-schemas.mjs'],repo)
        run.execute('contracts',['python3','-m','unittest','discover','-s','tests/contracts','-p','*_test.py'],repo)
        run.execute('domain-reasoning',[BASH,repo/'scripts/reason-owl.sh',args.domain,'--reasoner','both'],repo)
        # Each release invocation reports/diffs the OLD semantic baseline before
        # publishing its refreshed candidate. Git review still decides admission.
        for domain in sorted(x.split(':',1)[1] for x in p['cesScopes'] if x.startswith('domain:')):
            run.execute('semantic-shard-'+domain,[BASH,repo/'scripts/reason-owl.sh',domain,'--reasoner','both','--release'],repo)
        run.execute('semantic-union',[BASH,repo/'scripts/reason-owl.sh','--all','--reasoner','both','--release'],repo)
        generated=folder/'deployment-artifacts';generated.mkdir()
        for name in ['lane-graph.ttl','decision-table.json']:
            shutil.copyfile(repo/'semantics/lanes'/name,generated/name)
        ensure(input_snapshot(repo)==repo_inputs,'Authored Machines inputs changed during gates; restart approval with a new run')
        ensure(snapshot(ci,('config/ces-contracts/',))==ci_inputs,'CI inputs changed during gates; restart approval with a new run')
        manifest=read(repo/'domains/domain-manifest.json');entry=manifest['domains'][args.domain]
        ensure(entry['currentMachineCount']==len(p['candidateMachines']),'Author/review the manifest machine count before admission')
        entry['status']='accepted';write(repo/'domains/domain-manifest.json',manifest)
        # Status changes can influence generated provenance; regenerate and recheck.
        for script in GENERATORS:run.python('admitted-'+script[:-3],script,'--write',repo=repo)
        run.python('admitted-owl-manifest','generate-owl.py','--manifest-write','--strict-actions',repo=repo)
        run.python('admitted-cesgen','build-ces-contract-registry.py','--write',repo=repo)
        run.execute('accepted-candidate-gate',[BASH,repo/'scripts/validate-corpus.sh'],repo,env)
        state.update(state='PREPARED_PENDING_GITHUB_REVIEW',finishedAt=now(),events=run.events,
                     machinesSnapshot=snapshot(repo),ciSnapshot=snapshot(ci),
                     scopeEvidence={str(x.relative_to(folder)):filehash(x) for base in ['scopes','deployment-artifacts'] for x in (folder/base).rglob('*') if x.is_file()})
        state['machinesSnapshotSHA256']=objecthash(state['machinesSnapshot']);state['ciSnapshotSHA256']=objecthash(state['ciSnapshot'])
        write(folder/'state.json',state)
        print('Prepared candidate only. No approval or merge. Submit with the same evidence directory.')
    except Exception as exc:
        state.update(state='FAILED_NOT_APPROVED',failedAt=now(),error=str(exc),events=run.events)
        write(folder/'state.json',state);raise

def verify_prepared(state,folder):
    ensure(state['state']=='PREPARED_PENDING_GITHUB_REVIEW','No successful prepared state')
    for key,root in [('machinesSnapshot',state['machinesRepo']),('ciSnapshot',state['ciRepo'])]:
        ensure(snapshot(Path(root))==state[key],'Tracked candidate changed since preparation: '+root)
    for event in state['events']:
        ensure(event['exitCode']==0 and filehash(folder/event['log'])==event['logSHA256'],'Gate log changed or failed')
    for rel,sha in state['scopeEvidence'].items():ensure(filehash(folder/rel)==sha,'Scope evidence changed')

def gh_json(repo,*argv):return json.loads(cmd(['gh',*argv],repo))
def publish_commit(repo,paths,message):
    if paths:cmd(['git','add','--',*paths],repo)
    if git(repo,'diff','--cached','--name-only'):cmd(['git','commit','-m',message],repo)
    cmd(['git','push','-u','origin',branch(repo)],repo)
    return git(repo,'rev-parse','HEAD')
def new_pr(repo,title,body):
    return cmd(['gh','pr','create','--draft','--base','main','--head',branch(repo),'--title',title,'--body-file',str(body)],repo)

def submit(args):
    folder=args.evidence.resolve();state=read(folder/'state.json');verify_prepared(state,folder)
    ensure(args.evidence_reviewed,'Review local logs before publishing them; then specify --evidence-reviewed')
    repo=Path(state['machinesRepo']);ci=Path(state['ciRepo'])
    ensure(branch(repo)==state['machinesBranch'] and branch(ci)==state['ciBranch'],'Branch identity changed')
    slug_=state['domain'];ver=state['version'];label=f'{slug_} {ver}'
    unused_version(repo,slug_,ver)
    # Persist publication progress, so a failed network call cannot be mistaken for approval.
    state['state']='PUBLISHING_NOT_APPROVED';write(folder/'state.json',state)
    ci_changes=git(ci,'diff','--name-only').splitlines()+[p for p in git(ci,'ls-files','--others','--exclude-standard').splitlines() if p.startswith('config/ces-contracts/')]
    ensure(all(p.startswith('config/ces-contracts/') for p in ci_changes),'Unrelated CI changes cannot be published by this workflow')
    ci_commit=publish_commit(ci,ci_changes,'Record domain approval CES evidence: '+label)
    state['ciEvidenceCommit']=ci_commit;write(folder/'state.json',state)
    ci_pr=None
    if git(ci,'rev-list','--count','origin/main..HEAD')!='0':
        body=folder/'ci-pr.md';body.write_text(f'Domain approval evidence for {label}.\n\nRun {state["runId"]}. CES scopes were re-recorded from canonical CI stimulus under 3-of-3 quorum. Review source and evidence together with the Machines approval PR. No clinical or agent-outcome claim follows from CES parity.\n')
        ci_pr=new_pr(ci,'Domain approval evidence: '+label,body)
    state['ciPR']=ci_pr;write(folder/'state.json',state)
    candidate_tag=f'domain-candidate/{slug_}/v{ver}/{state["runId"]}'
    archive=folder/'evidence.tar.gz'
    selected=[folder/'plan.json',folder/'events.json']+sorted((folder/'logs').rglob('*.log'))+sorted(p for base in ['scopes','deployment-artifacts'] for p in (folder/base).rglob('*') if p.is_file())
    with archive.open('wb') as target:
        with gzip.GzipFile(fileobj=target,mode='wb',mtime=0) as compressed:
            with tarfile.open(fileobj=compressed,mode='w|') as tar:
                for path in selected:
                    info=tarfile.TarInfo(str(path.relative_to(folder)));info.size=path.stat().st_size;info.mtime=0;info.mode=0o644
                    with path.open('rb') as source:tar.addfile(info,source)
    state.update(evidenceTag=candidate_tag,evidenceArchiveSHA256=filehash(archive),evidenceURL=f'https://github.com/{origin(repo)}/releases/tag/{candidate_tag}')
    write(folder/'state.json',state)
    ledger_path=f'domains/approvals/{slug_}/{ver}/{state["runId"]}.json'
    ledger={k:v for k,v in state.items() if k not in ['machinesSnapshot','ciSnapshot','scopeEvidence']}
    ledger.update(state='PREPARED_PENDING_GITHUB_REVIEW',ciEvidenceCommit=ci_commit,ciPR=ci_pr,
                  evidenceFiles={str(p.relative_to(folder)):filehash(p) for p in sorted(folder.rglob('*')) if p.is_file() and p.name not in ['state.json','ci-pr.md']})
    write(repo/ledger_path,ledger)
    cmd(['node',repo/'scripts/validate-schemas.mjs'],repo)
    changes=git(repo,'diff','--name-only').splitlines()+[p for p in git(repo,'ls-files','--others','--exclude-standard').splitlines() if any(p==d or p.startswith(d+'/') for d in DERIVED) or p.startswith('config/ces-contracts/')]+[ledger_path]
    ensure(all(p in DERIVED or any(p.startswith(x+'/') for x in DERIVED) or p=='domains/domain-manifest.json' or p==ledger_path for p in changes),'Unrelated Machines changes cannot be staged')
    sha=publish_commit(repo,changes,'Prepare domain admission '+label+' with auditable gate ledger')
    evidence_note=folder/'evidence-release.md';evidence_note.write_text(f'NOT APPROVED. Candidate gate evidence for {label}. Run {state["runId"]}. SHA256 {state["evidenceArchiveSHA256"]}. Ledger {ledger_path}.')
    cmd(['gh','release','create',candidate_tag,str(archive),'--target',sha,'--prerelease','--title',f'Candidate evidence (NOT APPROVED): {label}','--notes-file',str(evidence_note),'--latest=false'],repo)
    body=folder/'machines-pr.md';body.write_text(f'## Domain admission candidate: {label}\n\nCandidate source {state["candidateCommit"]}; gate run {state["runId"]}.\n\nLedger: `{ledger_path}`. CI evidence commit: {ci_commit}. CI evidence PR: {ci_pr or "unchanged existing evidence"}.\n\nCandidate evidence bundle: {state["evidenceURL"]} (SHA256 {state["evidenceArchiveSHA256"]}).\n\nAll recorded gates passed; raw logs remain in the operator evidence bundle with hashes in the ledger. Review the actual logs and integration receipts. Approval is pending GitHub review and merge, not asserted by this PR.\n\nRequired order: review both PRs; merge CI evidence first; merge this exact reviewed Machines candidate through main protection; run finalize for the post-merge tag/release receipt. No self-approval or automatic merge.\n')
    url=new_pr(repo,'Approve domain version: '+label,body)
    state.update(state='SUBMITTED_PENDING_GITHUB_REVIEW',machinesPR=url,machinesPRHead=sha,ledgerPath=ledger_path)
    write(folder/'state.json',state)
    print(url)

# Latest non-comment review per reviewer determines approval, bound to exact head.
def approved_reviewers(reviews,head,author):
    last={}
    for review in reviews:
        if review.get('state') in ['APPROVED','CHANGES_REQUESTED','DISMISSED']:
            last[review['user']['login']]=review
    ensure(not any(r['state']=='CHANGES_REQUESTED' for r in last.values()),'An active changes-requested review blocks approval')
    return [r for user,r in last.items() if user!=author and r['state']=='APPROVED' and r.get('commit_id')==head]

def merged_pr(repo,url,expected_head):
    view=gh_json(repo,'pr','view',url,'--json','number,url,state,headRefOid,baseRefName,mergeCommit,author,statusCheckRollup')
    ensure(view['state']=='MERGED' and view['baseRefName']=='main','PR must be merged into main through normal review')
    ensure(view['headRefOid']==expected_head,'PR head changed after tests; prepare a new approval run')
    reviews=gh_json(repo,'api',f'repos/{origin(repo)}/pulls/{view["number"]}/reviews','--paginate','--slurp')
    reviews=[r for page in reviews for r in page]
    approvals=approved_reviewers(reviews,expected_head,view['author']['login'])
    ensure(approvals,'Independent approval of the exact tested PR head is required')
    checks=view.get('statusCheckRollup') or []
    for c in checks:
        ensure(c.get('conclusion') in ['SUCCESS','SKIPPED','NEUTRAL'] or c.get('state')=='SUCCESS','A published check is pending or failed')
    return dict(view,approvalReviews=approvals)

def validate_bound_state(ledger,state):
    for key in ['runId','domain','version','candidateCommit','candidateMachines','ciEvidenceCommit','ciPR','evidenceArchiveSHA256','evidenceURL']:
        ensure(ledger.get(key)==state.get(key),'Local state disagrees with the Git-reviewed ledger: '+key)
    for key in ['machinesSnapshot','ciSnapshot']:
        ensure(objecthash(state[key])==ledger.get(key+'SHA256'),'Local snapshot disagrees with the Git-reviewed ledger: '+key)

def finalize(args):
    folder=args.evidence.resolve();state=read(folder/'state.json')
    ensure(state['state']=='SUBMITTED_PENDING_GITHUB_REVIEW','Finalize requires submitted evidence')
    repo=Path(state['machinesRepo']);ci=Path(state['ciRepo'])
    machines=merged_pr(repo,state['machinesPR'],state['machinesPRHead'])
    dependency=merged_pr(ci,state['ciPR'],state['ciEvidenceCommit']) if state.get('ciPR') else None
    for r in [repo,ci]:cmd(['git','fetch','origin','main'],r)
    merged=machines['mergeCommit']['oid'];cmd(['git','fetch','origin',merged],repo)
    expected_path=f'domains/approvals/{slug(state["domain"])}/{version(state["version"])}/{state["runId"]}.json'
    ensure(state['ledgerPath']==expected_path,'Noncanonical admission ledger path')
    ledger=json.loads(subprocess.check_output(['git','show',f'{merged}:{expected_path}'],cwd=repo))
    validate_bound_state(ledger,state)
    ensure(subprocess.run(['git','merge-base','--is-ancestor',merged,'origin/main'],cwd=repo).returncode==0,'Approval merge is not on origin/main')
    # An untested extra machine can change shared-vector results. Require the
    # complete tested tree, plus only this run's immutable candidate ledger.
    for key,root,ref in [('machinesSnapshot',repo,merged),('ciSnapshot',ci,dependency['mergeCommit']['oid'] if dependency else 'origin/main')]:
        if dependency and root==ci:
            cmd(['git','fetch','origin',ref],root)
            ensure(subprocess.run(['git','merge-base','--is-ancestor',ref,'origin/main'],cwd=root).returncode==0,'CI evidence merge is not on current origin/main')
        actual_paths=set(git(root,'ls-tree','-r','--name-only',ref).splitlines())
        expected_paths={rel for rel,sha in state[key].items() if sha!='DELETED'}
        if root==repo:expected_paths.add(state['ledgerPath'])
        ensure(actual_paths==expected_paths,'Merge introduced untested files or deletions; prepare/review a new run')
        for rel,sha in state[key].items():
            result=subprocess.run(['git','show',f'{ref}:{rel}'],cwd=root,capture_output=True)
            ensure((result.returncode!=0 if sha=='DELETED' else result.returncode==0 and digest(result.stdout)==sha),'Merged bytes differ from tested snapshot: '+rel)
    tag=f'domain/{state["domain"]}/v{state["version"]}'
    ensure(not subprocess.check_output(['git','ls-remote','--tags','origin',f'refs/tags/{tag}'],cwd=repo,text=True).strip(),'Version tag already exists; never move an approval tag')
    final={'schemaVersion':'1.0.0','state':'APPROVED_MERGED','approvedAt':now(),'domain':state['domain'],'version':state['version'],
           'runId':state['runId'],'machinesPR':machines,'ciPR':dependency,'mergeCommit':merged,'tag':tag,
           'candidateMachines':state['candidateMachines'],'preparedLedgerPath':state['ledgerPath'],
           'evidenceURL':state['evidenceURL'],'evidenceArchiveSHA256':state['evidenceArchiveSHA256'],
           'preparedLedgerSHA256':digest(subprocess.check_output(['git','show',f'{merged}:{state["ledgerPath"]}'],cwd=repo)),
           'tagSigning':'gpg' if args.sign_tag else 'unsigned-annotated','approvalBoundary':'GitHub independent review and merge, not operator name or script exit code'}
    write(folder/'approval.json',final)
    cmd(['git','tag','-s' if args.sign_tag else '-a',tag,merged,'-m',f'Approved {state["domain"]} {state["version"]}; run {state["runId"]}; PR {state["machinesPR"]}'],repo)
    cmd(['git','push','origin',f'refs/tags/{tag}'],repo)
    note=folder/'release.md';note.write_text(f'Approved version of {state["domain"]}.\n\nMachines PR: {state["machinesPR"]}\n\nCI evidence PR: {state.get("ciPR")}\n\nRun: {state["runId"]}\n\nLedger: `{state["ledgerPath"]}` at merge `{merged}`. `approval.json` captures the observed independent reviews, exact heads and merge commits. It does not claim clinical efficacy or authority beyond the tested domain acceptance.\n')
    cmd(['gh','release','create',tag,str(folder/'approval.json'),'--verify-tag','--title',f'{state["domain"]} {state["version"]} approved','--notes-file',str(note),'--latest=false'],repo)
    state.update(state='APPROVED_MERGED',approval=final);write(folder/'state.json',state)
    print(f'https://github.com/{origin(repo)}/releases/tag/{tag}')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='action',required=True)
    for mode in ['plan','prepare']:
        p=sub.add_parser(mode);p.add_argument('--repo',type=Path,default=MACHINES);p.add_argument('--ci',type=Path,default=MACHINES.parent/'RealityEngine_CI')
        p.add_argument('--domain',required=True,type=slug);p.add_argument('--version',required=True,type=version)
        if mode=='prepare':
            p.add_argument('--evidence',required=True,type=Path);p.add_argument('--scope-runner',required=True,type=Path);p.add_argument('--regression-profile',required=True,type=slug);p.add_argument('--allow-runtime-reset',action='store_true')
    for mode in ['submit','finalize']:
        p=sub.add_parser(mode);p.add_argument('--evidence',required=True,type=Path)
        if mode=='finalize':p.add_argument('--sign-tag',action='store_true')
        else:p.add_argument('--evidence-reviewed',action='store_true')
    args=parser.parse_args()
    if args.action=='plan':print(json.dumps(plan(args.repo.resolve(),args.ci.resolve(),args.domain,args.version),indent=2))
    else:
        state=read(args.evidence.resolve()/'state.json') if args.action!='prepare' else None
        root=args.repo.resolve() if args.action=='prepare' else Path(state['machinesRepo'])
        gitdir=Path(git(root,'rev-parse','--absolute-git-dir'))
        with (gitdir/'domain-approval.lock').open('w') as lock:
            try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise ValueError('Another domain approval workflow owns this checkout')
            globals()[args.action](args)
if __name__=='__main__':
    try:main()
    except (ValueError,OSError,subprocess.CalledProcessError) as exc:
        print('STOP: '+str(exc),file=sys.stderr);sys.exit(1)
