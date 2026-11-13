#!/usr/bin/env python3
"""Offline package/semantic integrity checks; no model, service or care action."""
import argparse,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def digest(data): return hashlib.sha256(data).hexdigest()
def canonical(data): return digest(json.dumps(data,sort_keys=True,separators=(',',':')).encode())
def check(ok,message):
 if not ok: raise ValueError(message)
def load(path): return json.loads((ROOT/path).read_text())
def allowed(record,rules):
 path=record.get('path','')
 return (record.get('role',record.get('documentRole'))==rules['allowedRole']
  and record.get('collection')==rules['allowedCollection'] and record.get('synthetic') is False
  and path.startswith(tuple(rules['allowedRoots'])) and '..' not in Path(path).parts
  and not Path(path).is_absolute() and path.endswith('.md'))
def verify(repo=None):
 manifest=load('asset-manifest.json'); entries=manifest['assets']
 actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='asset-manifest.json'}
 check(actual=={e['path'] for e in entries},'Asset file inventory drift')
 check(len(entries)==len(actual),'Duplicate inventory path')
 for e in entries:
  check(digest((ROOT/e['path']).read_bytes())==e['sha256'],'Checksum mismatch: '+e['path'])
  if e['path'].endswith('.json'):load(e['path'])
 for p in ROOT.rglob('*.md'):
  for link in re.findall(r'\]\(([^)]+)\)',p.read_text()):
   if '://' not in link and not link.startswith('#'):
    check((p.parent/link.split('#')[0]).exists(),'Broken link: '+str(p)+' '+link)
 rules=load('acceptance/contract-rules.json')
 for path,keys in rules['requiredTopLevel'].items():
  check(set(keys)<=load(path).keys(),'Missing contract fields: '+path)
 inv=load('semantic-inventory.json'); machines=inv['machines']
 check(inv['domain']=='health-personal' and inv['machineCount']==len(machines)==43,'Domain/coverage mismatch')
 check(len({m['path'] for m in machines})==43,'Duplicate machine path')
 check(sum(len(m['sequenceSummary']) for m in machines)==172,'CES count mismatch')
 grouped=[stem for values in inv['groups'].values() for stem in values]
 check(len(grouped)==len(set(grouped))==43 and len(inv['groups'])==10,'Group partition mismatch')
 check(set(grouped)=={Path(m['path']).stem for m in machines},'Group membership mismatch')
 for m in machines:
  check((ROOT/m['guidancePath']).is_file(),'Missing guidance')
  check(m['group'] in inv['groups'] and Path(m['path']).stem in inv['groups'][m['group']],'Wrong grouping')
  check(m['arbiterRule']=='PASSTHROUGH','Arbitration drift')
 if repo is None:
  candidate=ROOT.parents[2]
  if (candidate/'machines/domains/health-personal').is_dir():repo=candidate
 compared=0
 if repo:
  repo=Path(repo).resolve(); source=repo/'machines/domains/health-personal'
  check({p.relative_to(repo).as_posix() for p in source.glob('*.json')}=={m['path'] for m in machines},'Source inventory drift')
  for m in machines:
   p=repo/m['path'];check(digest(p.read_bytes())==m['sha256'],'Source bytes changed: '+m['path'])
   native=json.loads(p.read_text())['machine']
   check(canonical(native)==m['semanticContractSHA256'],'Native semantics changed: '+m['path'])
   check([canonical(s) for s in native.get('sequences',[])]==[s['contractSHA256'] for s in m['sequenceSummary']],'CES semantics changed')
   compared+=1
 assets=load('document-asset-catalog.json')['assetTypes']; ids={a['assetTypeId'] for a in assets}
 check(len(ids)==len(assets)==6,'Asset type count')
 for a in assets:
  check((ROOT/a['template']).is_file(),'Template missing')
  check(bool(a['ownerRole']) and len(a['requiredFields'])==len(set(a['requiredFields'])),'Invalid owner/fields')
  text=(ROOT/a['template']).read_text()
  check(all('{{'+f+'}}' in text for f in a['requiredFields']),'Template required field missing')
 deps=load('document-dependencies.json')['dependencies'];check(set(deps)==ids,'Dependency scope')
 visited=set()
 def walk(n,stack):
  check(n not in stack,'Dependency cycle')
  if n in visited:return
  check(n in ids,'Unknown dependency')
  for d in deps[n]:walk(d,stack|{n})
  visited.add(n)
 for n in deps:walk(n,set())
 ingest=load('ingestion-manifest.json'); docs=ingest['documents']
 check(ingest['domain']=='health-personal' and ingest['deploymentStatus']=='STAGED_ONLY_NOT_INGESTED','Ingestion status')
 check(ingest['totalDocuments']==len(docs) and len({d['documentId'] for d in docs})==len(docs),'RAG inventory')
 expected={p.relative_to(ROOT).as_posix() for base in rules['allowedRoots'] for p in (ROOT/base).glob('*.md')}
 check({d['path'] for d in docs}==expected,'RAG allowlist coverage')
 for d in docs:
  check(allowed(d,rules) and d['indexed'] is False,'Unsafe ingestion item')
  check(d['contentSHA256']==digest((ROOT/d['path']).read_bytes()),'RAG hash drift')
 fixtures=load('acceptance/policy-fixtures.json')['fixtures']
 for case in fixtures:check(allowed(case['record'],rules)==case['expected'],'Policy fixture: '+case['id'])
 cases=load('acceptance/cases.json')['cases'];check(len({c['caseId'] for c in cases})==len(cases),'Duplicate case ID')
 check(all(c['requiredEvidence'] and c['expected'] for c in cases),'Acceptance evidence missing')
 check(all(c['executionStatus'] in ['NOT_RUN','PACKAGE_CHECK_ONLY'] for c in cases),'Unsubstantiated acceptance status')
 return {'status':'PASS','scope':'STATIC_PACKAGE_AND_SOURCE_INTEGRITY_ONLY','payloadAssets':len(entries),'machines':43,'sourceHashesCompared':compared,'CESs':172,'documentaryGroups':10,'assetTypes':6,'allowlistedDocuments':len(docs),'policyFixtures':len(fixtures),'designedAcceptanceCases':len(cases),'liveAcceptance':'NOT_RUN','clinicalReview':'NOT_PERFORMED'}
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--repo');args=parser.parse_args()
 try:print(json.dumps(verify(args.repo),indent=2))
 except (ValueError,KeyError,FileNotFoundError) as exc:raise SystemExit('FAIL: '+str(exc))
