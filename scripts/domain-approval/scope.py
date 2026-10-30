#!/usr/bin/env python3
"""Canonical development-scope boot/parity driver plus a required integration gate."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
BASH='/opt/homebrew/bin/bash'
def write(path,data):Path(path).write_text(json.dumps(data,indent=2)+'\n')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def run(label,argv,cwd,out,env):
    log=out/(label+'.log')
    with log.open('wb') as stream:subprocess.run([str(x) for x in argv],cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT,check=True)
    return {'path':log.name,'sha256':sha(log)}
def main():
    if len(sys.argv)!=3:raise ValueError('usage: run-scope.sh request.json output-directory')
    request=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();d=json.loads(request.read_text());ci=Path.cwd()
    if ci.name!='RealityEngine_CI' or not (ci/'startUniverse.sh').is_file():raise ValueError('Run with the canonical sibling CI checkout as cwd')
    hook=Path(os.environ.get('DOMAIN_INTEGRATION_RUNNER','')).resolve()
    if not hook.is_file() or not os.access(hook,os.X_OK):raise ValueError('Set DOMAIN_INTEGRATION_RUNNER to a reviewed executable domain integration suite; there is no pass-by-default hook')
    manifest=out/'scope-corpus.txt';manifest.write_text('\n'.join(sorted(d['testedMachines']))+'\n')
    env=dict(os.environ,MACHINE_CORPUS_WORK_DIR=str(out/'materialized-corpus'))
    artifacts=[]
    artifacts.append(run('stop',[BASH,ci/'stopUniverse.sh','--all'],ci,out,env))
    artifacts.append(run('boot',[BASH,ci/'startUniverse.sh','--engines=cpp:1,lsp:1,scala:1','--machine-load=runtime','--machine-corpus=standard-deployment',f'--machine-corpus-manifest={manifest}','--pe-source-bootstrap=auto','--no-openclaw','--no-local-ai','--fresh'],ci,out,env))
    # Resolve free/fixed port identity through the existing CI resolver.
    sys.path.insert(0,str(ci/'scripts/lib'));from registry_url import registry_url
    url=registry_url();env['RE_REGISTRY_URL']=url
    artifacts.append(run('machine-sets',['python3',ci/'scripts/regression-machine-set-parity.py','--registry',url,'--out',out/'machine-sets.json'],ci,out,env))
    artifacts.append(run('trajectories',['python3',ci/'scripts/regression-trajectory-parity.py','--registry',url,'--out',out/'trajectories.json'],ci,out,env))
    # Real domain/provider/tool assertions belong to its owning CI suite. The hook
    # receives native scope+fingerprints and must write integration.json/evidence.
    hook_before=sha(hook)
    artifacts.append(run('domain-integration',[hook,request,out],ci,out,env))
    if sha(hook)!=hook_before:raise ValueError('Integration gate changed during the run')
    evidence=json.loads((out/'integration.json').read_text())
    if evidence.get('result')!='PASS' or not evidence.get('artifacts'):raise ValueError('Integration hook must supply passing assertions with evidence artifacts')
    for item in evidence['artifacts']:
        p=(out/item['path']).resolve()
        if not p.is_relative_to(out) or not p.is_file() or sha(p)!=item['sha256']:raise ValueError('Invalid integration artifact')
    artifacts+=evidence['artifacts']
    artifacts += [{'path':name,'sha256':sha(out/name)} for name in ['scope-corpus.txt','machine-sets.json','trajectories.json','integration.json']]
    write(out/'receipt.json',{'domain':d['domain'],'scope':d['scope'],'testedMachines':d['testedMachines'],
        'result':'PASS','checks':{'isreParity':'PASS','osreParity':'PASS','domainIntegration':'PASS'},
        'engines':['cpp','lsp','scala'],'instanceRegistryURL':url,'integrationGateSHA256':hook_before,'artifacts':artifacts})
if __name__=='__main__':
    try:main()
    except (ValueError,OSError,subprocess.CalledProcessError) as exc:raise SystemExit('STOP: '+str(exc))
