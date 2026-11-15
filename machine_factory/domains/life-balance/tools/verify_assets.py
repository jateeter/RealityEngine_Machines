#!/usr/bin/env python3
"""Verify package integrity, not runtime/clinical acceptance. Standard library only."""
from pathlib import Path
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]
def load(name):return json.loads((ROOT/name).read_text())
manifest=load('asset-manifest.json')
actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='asset-manifest.json'}
assert actual=={e['path'] for e in manifest['assets']}, 'File inventory mismatch'
for e in manifest['assets']:
 p=ROOT/e['path']; assert hashlib.sha256(p.read_bytes()).hexdigest()==e['sha256'],p
 if p.suffix=='.json':json.loads(p.read_text())
for p in ROOT.rglob('*.md'):
 for link in re.findall(r'\]\(([^)]+)\)',p.read_text()):
  if '://' not in link and not link.startswith('#'):assert (p.parent/link.split('#')[0]).exists(),(p,link)
families=load('family-catalog.json')['families']; assert len(families)==10
family_ids={f['familyId'] for f in families}
duties=load('machine-document-duty-index.json');assert duties['machineCount']==len(duties['machines'])==110
assert len({m['machinePath'] for m in duties['machines']})==110
for m in duties['machines']:
 assert m['familyId'] in family_ids
 for k in ['guidancePath','interactionTemplate']:assert (ROOT/m[k]).is_file()
# If installed in the repository, also compare exact runtime machine inventory.
repo=ROOT.parents[2]
corpus=repo/'machines/domains/life-balance'
if corpus.is_dir():assert {m['machinePath'] for m in duties['machines']}=={p.relative_to(repo).as_posix() for p in corpus.glob('*.json')}
assets=load('document-asset-catalog.json')['assetTypes'];ids={a['assetTypeId'] for a in assets}
for a in assets:assert (ROOT/a['template']).is_file()
deps=load('document-dependencies.json')['dependencies'];assert set(deps)==ids
visited=set()
def visit(n,stack):
 assert n not in stack, 'Dependency cycle'
 if n in visited:return
 assert n in ids
 for d in deps[n]:visit(d,stack|{n})
 visited.add(n)
for n in deps:visit(n,set())
ingest=load('ingestion-manifest.json');assert ingest['totalDocuments']==len(ingest['documents'])
assert len({d['documentId'] for d in ingest['documents']})==len(ingest['documents'])
for d in ingest['documents']:
 assert d['path'].startswith(('documents/workflow/','families/'))
 assert d['indexed'] is False
 assert hashlib.sha256((ROOT/d['path']).read_bytes()).hexdigest()==d['contentSHA256']
result={'status':'PASS','scope':'STATIC_PACKAGE_INTEGRITY_ONLY','assetCount':len(actual),'machineDuties':110,'familyCards':10,'ingestionDocuments':len(ingest['documents']),'documentAssetTypes':len(assets),'liveAcceptance':'NOT_RUN','clinicalSourceReview':'NOT_PERFORMED'}
print(json.dumps(result,indent=2))
