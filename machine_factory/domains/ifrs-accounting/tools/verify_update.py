import collections,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent/'ifrs-standard-coverage';DEEP=ROOT.parent/'ifrs-section-deep-review'
def read(p):return json.loads(p.read_text())
cat=read(ROOT/'document-asset-catalog.json')['assetTypes'];A={a['assetTypeId']:a for a in cat};duties=read(ROOT/'machine-document-duty-index.json')['machines'];controls={c['id'] for c in read(ROOT/'source-requirements.json')['controls']};errors=[]
expected={p.stem for p in (BASE/'machines/domains/ifrs-accounting').glob('*.json')};actual={p.stem for p in (ROOT/'machines/domains/ifrs-accounting').glob('*.json')};assert expected==actual and len(actual)==225
assert {a['sectionId'] for a in cat}=={f'{i:02d}' for i in range(36)}|{'A','B'}
assert len(A)==len(cat)==68
edges={a['assetTypeId']:a['dependencies'] for a in cat};seen=set();active=set()
def visit(aid):
 assert aid in A
 if aid in active:raise AssertionError('Dependency cycle '+aid)
 if aid in seen:return
 active.add(aid)
 for x in edges[aid]:visit(x)
 active.remove(aid);seen.add(aid)
for aid in A:visit(aid)
family_owners=collections.Counter()
for f in (ROOT/'families').glob('*.json'):
 data=read(f)
 for aid in data['accountableAssetTypeIds']:family_owners[aid]+=1
assert set(family_owners)==set(A) and all(v==1 for v in family_owners.values())
for aid,a in A.items():
 assert a['motivation'] and a['requiredFields'] and a['controlIds'];assert set(a['controlIds'])<=controls
 assert read(ROOT/'templates'/(aid+'.json'))['status']=='DRAFT_TEMPLATE_NOT_AN_ENTITY_STATEMENT'
fields=['id','arbiterRule','matchAlgorithm','outputMergeTransformation','perceptualMapping','sequences','inputSequences']
for mid in sorted(expected):
 new=read(ROOT/'machines/domains/ifrs-accounting'/(mid+'.json'))['machine'];old=read(BASE/'machines/domains/ifrs-accounting'/(mid+'.json'))['machine']
 for k in fields:assert new[k]==old[k],(mid,k)
 for k in ['sensorNormalization','arbitrationPolicy','outputEncoding','interconnections']:assert new['metadata'][k]==old['metadata'][k],(mid,k)
 a=read(ROOT/'agents/ifrs-accounting'/(mid+'.oc-agent.json'));b=read(BASE/'agents/ifrs-accounting'/(mid+'.oc-agent.json'))
 for k in ['agentBinding','responseMapping','openclaw']:assert a[k]==b[k],(mid,k)
 assert a['reasoning']['outputContract']==b['reasoning']['outputContract']
 refs={x['assetTypeId'] for x in new['metadata']['documentAssetWorkflow']['duties']};assert refs<=set(A)
 assert refs==set(a['governance']['documentAssetDutyRefs'])
 assert new['metadata']['governance']['runbook']==a['governance']['runbook']
 resolution=read(ROOT/'runbook-resolution.json')['runbooks'][a['governance']['runbook']]
 assert hashlib.sha256((ROOT/resolution['path']).read_bytes()).hexdigest()==resolution['sha256']
 binding=a['documentWorkflowBinding'];owned=set(binding['ownedAssetTypeIds']);requested=set(binding['requestOnlyAssetTypeIds']);assert not owned&requested and owned|requested==refs
 assert all(A[x]['ownerName']==binding['actorOwnerName'] for x in owned)
 assert all(A[x]['ownerName']!=binding['actorOwnerName'] for x in requested)
 for x in refs:assert x in a['reasoning']['systemPrompt']
 assert 'approve-own-or-other-draft' in binding['forbiddenOperations']
 assert 'post-journal' in binding['forbiddenOperations']
 assert new['metadata']['arbitrationPolicy']['resolvedRule']=='PRECEDENCE'
 assert new['metadata']['arbitrationPolicy']['withinRank']=='MAX'
summary={'status':'PASS','assetTypes':len(A),'sourceSections':38,'machines':225,'agents':225,'families':len(list((ROOT/'families').glob('*.json'))),'documentDutyLinks':sum(len(m['dutyAssetTypeIds']) for m in duties),'controlReferencesResolved':len(controls),'oneAccountableFamilyPerAsset':True,'documentGraphAcyclic':True,'nativeExecutionEncodingAndArbitrationUnchanged':True,'peBindingAndCompletionUnchanged':True,'documentBindingSeparate':True,'scope':'Static assembly and invariance checks; no financial accounting or live engine acceptance proof.'}
print(json.dumps(summary))
