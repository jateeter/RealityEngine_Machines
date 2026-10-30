#!/usr/bin/env python3
"""Local reference document lifecycle and deterministic task outbox.

No LLM, native dispatch, financial calculations, posting, publication or identity
verification is implemented here. Production connectors must preserve the same
version/evidence guards and authenticate reviewer decisions at their boundary.
"""
import argparse,contextlib,datetime,fcntl,hashlib,json,os,uuid
from pathlib import Path

class ConflictError(ValueError):pass
class EvidenceError(ValueError):pass

def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def hashed(x):return hashlib.sha256(canonical(x).encode()).hexdigest()
def empty(v):return v is None or v=='' or v==[] or v=={}

def scope(context):
 for k in ['entityId','period','factsFingerprint','sourceFingerprint','policyFingerprint']:
  if not isinstance(context.get(k),str) or not context[k].strip():raise EvidenceError('Missing context '+k)
 return {k:context[k] for k in ['entityId','period','factsFingerprint','sourceFingerprint','policyFingerprint']}

def asset_key(context,asset_id):return hashed({'entityId':context['entityId'],'period':context['period'],'assetTypeId':asset_id})

def input_fingerprint(context,upstream):return hashed({'scope':scope(context),'upstream':upstream})

class Store:
 def __init__(self,path,catalog):
  self.root=Path(path);self.root.mkdir(parents=True,exist_ok=True)
  data=json.loads(Path(catalog).read_text()) if isinstance(catalog,(Path,str)) else catalog
  self.catalog={a['assetTypeId']:a for a in data['assetTypes']}
  self._validate_catalog()
 def _validate_catalog(self):
  seen=set();active=set()
  def visit(a):
   if a not in self.catalog:raise EvidenceError('Unknown dependency '+a)
   if a in active:raise EvidenceError('Document dependency cycle '+a)
   if a in seen:return
   active.add(a)
   for dep in self.catalog[a]['dependencies']:visit(dep)
   active.remove(a);seen.add(a)
  for a in self.catalog:visit(a)
 @contextlib.contextmanager
 def locked(self):
  with (self.root/'.lock').open('a') as f:
   fcntl.flock(f,fcntl.LOCK_EX)
   try:yield
   finally:fcntl.flock(f,fcntl.LOCK_UN)
 def _path(self,context,aid):return self.root/'assets'/asset_key(context,aid)
 def _read(self,p,default=None):return json.loads(p.read_text()) if p.exists() else default
 def _write(self,p,data):
  p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.'+uuid.uuid4().hex+'.tmp');tmp.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n');os.replace(tmp,p)
 def _event(self,data):
  data={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),**data}
  with (self.root/'events.jsonl').open('a') as f:f.write(canonical(data)+'\n')
 def head(self,context,aid):return self._read(self._path(context,aid)/'head.json')
 def revision(self,context,aid,revision):return self._read(self._path(context,aid)/f'v{revision}.json')
 def _upstream(self,context,aid):
  refs=[];na=context.get('notApplicableAssets',{})
  for dep in self.catalog[aid]['dependencies']:
   decision=na.get(dep)
   if decision:
    if not all(decision.get(k) for k in ['basis','reviewerName','evidenceRefs']):raise EvidenceError('Unreviewed non-applicability '+dep)
    refs.append({'assetTypeId':dep,'status':'NOT_APPLICABLE','decisionFingerprint':hashed(decision)})
   else:
    h=self.head(context,dep)
    refs.append({'assetTypeId':dep,'revision':h['revision'] if h else None,'contentHash':h['contentHash'] if h else None,'status':h['status'] if h else 'MISSING'})
  return refs
 def draft(self,context,aid,content,evidence_refs,expected_revision=0,change_reason=''):
  scope(context)
  if aid not in self.catalog:raise EvidenceError('Unknown asset type '+aid)
  if not isinstance(content,dict) or not isinstance(evidence_refs,list):raise EvidenceError('Typed object content and evidence reference list required')
  # Source document references are inputs; no synthetic issuer evidence is created.
  with self.locked():
   folder=self._path(context,aid);old=self.head(context,aid);up=self._upstream(context,aid);fingerprint=input_fingerprint(context,up)
   revision_content={'assetTypeId':aid,'entityId':context['entityId'],'period':context['period'],'content':content,'evidenceRefs':evidence_refs,'upstreamRefs':up,'inputFingerprint':fingerprint}
   content_hash=hashed(revision_content)
   if old and old['contentHash']==content_hash:return old # Retry cannot clear STALE or approve.
   actual=old['revision'] if old else 0
   if actual!=expected_revision:raise ConflictError(f'Expected revision {expected_revision}, found {actual}')
   number=actual+1
   if old and not change_reason:raise EvidenceError('Revision change reason required')
   p=folder/f'v{number}.json'
   if p.exists():raise ConflictError('Immutable revision already exists')
   record={**revision_content,'revision':number,'contentHash':content_hash,'changeReason':change_reason,'previousRevision':actual or None,'ownerName':self.catalog[aid]['ownerName']}
   self._write(p,record)
   head={k:record[k] for k in ['assetTypeId','entityId','period','revision','contentHash','inputFingerprint']};head.update(status='DRAFT',review=None)
   self._write(folder/'head.json',head);self._event({'type':'DRAFT_CREATED','assetKey':asset_key(context,aid),'revision':number,'previousRevision':actual or None})
   if old:
    self._event({'type':'REVISION_SUPERSEDED','assetKey':asset_key(context,aid),'revision':actual,'supersededBy':number})
    self._invalidate(context,[aid],include_roots=False,reason='upstream revision changed')
   return head
 def _invalidate(self,context,roots,include_roots=True,reason='inputs changed'):
  for x in roots:
   if x not in self.catalog:raise EvidenceError('Unknown changed asset '+x)
  impacted=set(roots);changed=True
  while changed:
   changed=False
   for aid,a in self.catalog.items():
    if aid not in impacted and set(a['dependencies'])&impacted:impacted.add(aid);changed=True
  marked=[]
  for aid in sorted(impacted if include_roots else impacted-set(roots)):
   h=self.head(context,aid)
   if h and h['status']!='STALE':
    h.update(status='STALE',review=None,staleReason=reason);self._write(self._path(context,aid)/'head.json',h);marked.append(aid)
    self._event({'type':'ASSET_STALE','assetKey':asset_key(context,aid),'revision':h['revision'],'reason':reason})
  return marked
 def invalidate(self,context,roots,reason):
  scope(context)
  with self.locked():return self._invalidate(context,roots,reason=reason)
 def _validate_approval(self,context,aid,h,review):
  if h['status']=='STALE':raise EvidenceError('Stale revision must be reassessed and revised')
  r=self.revision(context,aid,h['revision']);a=self.catalog[aid]
  for k in a['requiredFields']:
   if k not in r['content'] or empty(r['content'][k]):raise EvidenceError('Unresolved required field '+k)
   value=r['content'][k]
   if isinstance(value,dict) and value.get('status')=='NOT_APPLICABLE' and not all(value.get(x) for x in ['basis','reviewerName','evidenceRefs']):raise EvidenceError('Unsupported field non-applicability '+k)
  if not r['evidenceRefs']:raise EvidenceError('Authentic evidence references required')
  if r['inputFingerprint']!=input_fingerprint(context,self._upstream(context,aid)):raise EvidenceError('Inputs or upstream heads changed')
  for dep in self._upstream(context,aid):
   if dep['status'] not in {'APPROVED','NOT_APPLICABLE'}:raise EvidenceError('Unapproved upstream dependency '+dep['assetTypeId'])
  for k in ['reviewerName','ownerName','evidenceChecked','citationsChecked','reconciliationsChecked','unresolvedItems','revision','contentHash']:
   if k not in review:raise EvidenceError('Review missing '+k)
  if review['ownerName']!=a['ownerName']:raise EvidenceError('Wrong accountable owner')
  if not isinstance(review['reviewerName'],str) or not review['reviewerName'].strip() or review['reviewerName']==review['ownerName']:raise EvidenceError('Independent reviewer name required')
  if review['reviewerName']!=a['reviewerName']:raise EvidenceError('Reviewer does not match assigned role/name')
  if review['revision']!=h['revision'] or review['contentHash']!=h['contentHash']:raise ConflictError('Review targets another revision')
  if not all(review[k] is True for k in ['evidenceChecked','citationsChecked','reconciliationsChecked']):raise EvidenceError('Unverified evidence citations or reconciliations')
  if review['unresolvedItems']!=[]:raise EvidenceError('Unresolved review items block approval')
  rag=review.get('ragReceipt')
  if not isinstance(rag,dict) or not all(rag.get(k) for k in ['interactionId','sourceHash','sourceFingerprint','indexSnapshot','verifiedPassageRefs']):raise EvidenceError('RAG receipt provenance incomplete')
  if rag.get('citationVerified') is not True:raise EvidenceError('RAG citation verification required')
  if rag['sourceFingerprint']!=context['sourceFingerprint'] or rag['indexSnapshot']!=context.get('indexSnapshot'):raise EvidenceError('RAG source/index context mismatch')
  if aid in {'COMPLIANCE-REVIEW','STATEMENT-BUNDLE'} and context.get('unresolvedRequirements',None)!=[]:raise EvidenceError('Unresolved or unassessed accounting requirements block final bundle/compliance approval')
 def request_review(self,context,aid,expected_revision):
  scope(context)
  with self.locked():
   h=self.head(context,aid)
   if not h or h['revision']!=expected_revision:raise ConflictError('Review request targets another revision')
   if h['status'] not in {'DRAFT','IN_REVIEW'}:raise EvidenceError('Only a current draft may enter review')
   if h['inputFingerprint']!=input_fingerprint(context,self._upstream(context,aid)):raise EvidenceError('Inputs changed before review')
   h['status']='IN_REVIEW';self._write(self._path(context,aid)/'head.json',h);self._event({'type':'REVIEW_REQUESTED','assetKey':asset_key(context,aid),'revision':h['revision']});return h
 def approve(self,context,aid,review):
  scope(context)
  with self.locked():
   h=self.head(context,aid)
   if not h:raise EvidenceError('No draft to review')
   if h['status']!='IN_REVIEW':raise EvidenceError('Exact revision must first be submitted for review')
   self._validate_approval(context,aid,h,review)
   h.update(status='APPROVED',review=review);self._write(self._path(context,aid)/'head.json',h);self._event({'type':'REVISION_APPROVED','assetKey':asset_key(context,aid),'revision':h['revision'],'reviewerName':review['reviewerName']})
   return h
 def reconcile_event(self,context,event,applicable_asset_ids):
  scope(context)
  allowed={'period-opened','period-close-requested','facts-changed','upstream-revised','policy-changed','edition-changed','review-rejected','contradictory-evidence','source-citation-failed','authorisation-received','recognizer-observed'}
  if event.get('type') not in allowed:raise EvidenceError('Unknown maintenance event')
  if event.get('entityId')!=context['entityId'] or event.get('period')!=context['period']:raise EvidenceError('Event belongs to another entity/period')
  for aid in applicable_asset_ids:
   if aid not in self.catalog:raise EvidenceError('Unknown applicable asset '+aid)
  if event['type']=='recognizer-observed' and (not event.get('machineId') or not event.get('observationRef') or event.get('changedAssetTypeIds')):raise EvidenceError('Native observation needs identity/provenance and cannot assert accounting fact changes')
  with self.locked():
   roots=event.get('changedAssetTypeIds',[])
   for aid in roots:
    if aid not in self.catalog:raise EvidenceError('Unknown changed asset '+aid)
   if event['type'] in {'facts-changed','policy-changed','edition-changed','contradictory-evidence','source-citation-failed','review-rejected'}:
    self._invalidate(context,roots or applicable_asset_ids,reason=event['type'])
   elif event['type']=='upstream-revised':self._invalidate(context,roots,include_roots=False,reason=event['type'])
   existing=self._read(self.root/'outbox.json',{});result=[]
   # Version drift is discovered even if the event producer mislabeled a close event.
   for aid in applicable_asset_ids:
    h=self.head(context,aid)
    if h and h['inputFingerprint']!=input_fingerprint(context,self._upstream(context,aid)):
     self._invalidate(context,[aid],reason='observed-input-fingerprint-change')
   for tid,task in existing.items():
    if task['entityId']!=context['entityId'] or task['period']!=context['period'] or task['status']!='OPEN':continue
    aid=task['assetTypeId'];h=self.head(context,aid);fp=input_fingerprint(context,self._upstream(context,aid))
    if task['inputFingerprint']!=fp:task['status']='SUPERSEDED';task['supersededByFingerprint']=fp
    elif task['action']=='ASSESS_DOCUMENT_IMPACT':continue
    elif h and (h['status']=='APPROVED' or task['action']=='CREATE_DRAFT_AND_REQUEST_EVIDENCE'):
     task['status']='DONE';task['completionRef']={'assetTypeId':aid,'revision':h['revision'],'contentHash':h['contentHash']}
    elif h and h['status']=='STALE' and task['action']=='COMPLETE_RECONCILE_AND_REQUEST_REVIEW':task['status']='SUPERSEDED'

   for aid in sorted(set(applicable_asset_ids)):
    a=self.catalog[aid];h=self.head(context,aid);up=self._upstream(context,aid);fp=input_fingerprint(context,up)
    if event['type']=='recognizer-observed':action='ASSESS_DOCUMENT_IMPACT'
    elif not h:action='CREATE_DRAFT_AND_REQUEST_EVIDENCE'
    elif h['status']=='STALE' or h['inputFingerprint']!=fp:action='REASSESS_AND_REVISE'
    elif h['status']!='APPROVED':action='COMPLETE_RECONCILE_AND_REQUEST_REVIEW'
    else:continue
    payload={'entityId':context['entityId'],'period':context['period'],'assetTypeId':aid,'action':action,'inputFingerprint':fp}
    if event['type']=='recognizer-observed':payload['observationFingerprint']=hashed(event['observationRef']);payload['requestedByMachine']=event['machineId']
    tid=hashed(payload);task={'taskId':tid,**payload,'ownerName':a['ownerName'],'reviewerName':a['reviewerName'],'motivation':a['motivation'],'requiredFields':a['requiredFields'],'upstreamRefs':up,'status':'OPEN','generatedBy':'reference-document-workflow','noAutoRelease':True}
    if tid not in existing:existing[tid]=task;self._event({'type':'TASK_CREATED','taskId':tid,'eventId':event.get('eventId')})
    result.append(existing[tid])
   self._write(self.root/'outbox.json',existing);return result
 def observe_machine(self,context,machine,envelope):
  m=machine.get('machine',machine)
  if envelope.get('machineId')!=m['id']:raise EvidenceError('Machine observation identity mismatch')
  if envelope.get('sequenceId') not in {s['id'] for s in m['sequences']}:raise EvidenceError('Unknown observed sequence')
  vector=envelope.get('outputVector')
  if not isinstance(vector,list) or len(vector)!=m['perceptualMapping']['output']['length'] or any(type(x) not in (int,float) or x not in {0,0.5,1} for x in vector):raise EvidenceError('Observation violates existing bounded nominal output encoding')
  if not envelope.get('providerRef'):raise EvidenceError('Observation provider provenance required')
  duty_ids=[d['assetTypeId'] for d in m['metadata']['documentAssetWorkflow']['duties']]
  event={'type':'recognizer-observed','entityId':context['entityId'],'period':context['period'],'machineId':m['id'],'observationRef':{k:envelope[k] for k in ['machineId','sequenceId','outputVector','providerRef']}}
  return self.reconcile_event(context,event,duty_ids)
 def resolve_assessment(self,context,task_id,resolution):
  scope(context)
  with self.locked():
   outbox=self._read(self.root/'outbox.json',{});task=outbox.get(task_id)
   if not task or task['action']!='ASSESS_DOCUMENT_IMPACT':raise EvidenceError('No assessment task')
   if task['entityId']!=context['entityId'] or task['period']!=context['period']:raise EvidenceError('Wrong assessment scope')
   if task['status']!='OPEN':raise ConflictError('Assessment is not open')
   aid=task['assetTypeId'];current=input_fingerprint(context,self._upstream(context,aid))
   if current!=task['inputFingerprint']:raise ConflictError('Assessment inputs changed')
   if resolution.get('ownerName')!=self.catalog[aid]['ownerName'] or not resolution.get('basis') or not resolution.get('evidenceRefs'):raise EvidenceError('Named owner, source basis and authentic evidence references required')
   disposition=resolution.get('disposition')
   if disposition not in {'NO_DOCUMENT_CHANGE','REFRESH_REQUIRED','UNRESOLVED'}:raise EvidenceError('Unknown assessment disposition')
   task['resolution']=resolution
   if disposition!='UNRESOLVED':task['status']='DONE'
   if disposition=='REFRESH_REQUIRED':self._invalidate(context,[aid],reason='verified observation impact requires refresh')
   outbox[task_id]=task;self._write(self.root/'outbox.json',outbox);self._event({'type':'ASSESSMENT_DISPOSITION','taskId':task_id,'disposition':disposition});return task
 def render(self,context,aid):
  h=self.head(context,aid)
  if not h:raise EvidenceError('No document revision')
  r=self.revision(context,aid,h['revision']);a=self.catalog[aid]
  if h['inputFingerprint']!=input_fingerprint(context,self._upstream(context,aid)):h={**h,'status':'STALE'}
  text=f"# {a['title']}\n\n**{h['status']} — revision {h['revision']}; not an issued financial statement.**\n\nEntity: {context['entityId']}\n\nPeriod: {context['period']}\n\nPurpose: {a['motivation']}\n\n"
  for field in a['requiredFields']:
   v=r['content'].get(field);text+=f"## {field}\n\n"+('UNRESOLVED — verified content/evidence required.' if empty(v) else json.dumps(v,indent=2,ensure_ascii=False))+'\n\n'
  return text+'## Provenance\n\n'+json.dumps({'contentHash':h['contentHash'],'evidenceRefs':r['evidenceRefs'],'upstreamRefs':r['upstreamRefs'],'review':h['review']},indent=2)+'\n'

def main():
 ap=argparse.ArgumentParser();ap.add_argument('command',choices=['plan','observe','resolve-assessment','draft','request-review','approve','render']);ap.add_argument('--catalog',type=Path,default=Path(__file__).resolve().parents[1]/'document-asset-catalog.json');ap.add_argument('--store',type=Path,required=True);ap.add_argument('--context',type=Path,required=True);ap.add_argument('--request',type=Path,required=True);ap.add_argument('--machine',type=Path);a=ap.parse_args();store=Store(a.store,a.catalog);context=json.loads(a.context.read_text());request=json.loads(a.request.read_text())
 if a.command=='plan':result=store.reconcile_event(context,request['event'],request['applicableAssetTypeIds'])
 elif a.command=='observe':
  if not a.machine:ap.error('--machine is required for observe')
  result=store.observe_machine(context,json.loads(a.machine.read_text()),request)
 elif a.command=='resolve-assessment':result=store.resolve_assessment(context,request['taskId'],request['resolution'])
 elif a.command=='draft':result=store.draft(context,request['assetTypeId'],request['content'],request['evidenceRefs'],request.get('expectedRevision',0),request.get('changeReason',''))
 elif a.command=='request-review':result=store.request_review(context,request['assetTypeId'],request['expectedRevision'])
 elif a.command=='approve':result=store.approve(context,request['assetTypeId'],request['review'])
 else:print(store.render(context,request['assetTypeId']));return
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
