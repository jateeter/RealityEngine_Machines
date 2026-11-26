#!/usr/bin/env node
/** Synthetic revision/series integrity only; hashes are not signatures or action receipts. */
import {readFileSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {isDeepStrictEqual} from 'node:util';
import Ajv2020 from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';
import {evaluateCarbonLedger} from './evaluate_carbon_ledger.mjs';
const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const read=p=>JSON.parse(readFileSync(p,'utf8'));
const hash=b=>createHash('sha256').update(b).digest('hex');
const require=(ok,msg)=>{if(!ok)throw Error(msg);};
const keys=(o,s)=>o&&typeof o==='object'&&!Array.isArray(o)&&isDeepStrictEqual(Object.keys(o).sort(),s.split(' ').sort());
function canonical(v){if(Array.isArray(v))return '['+v.map(canonical).join(',')+']';if(v!==null&&typeof v==='object')return '{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}';return JSON.stringify(v);}
export const trajectoryDigest=value=>hash(canonical(value));
const ajv=new Ajv2020({strict:false});addFormats(ajv);
const date=ajv.compile({type:'string',format:'date-time',pattern:'^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d{3})?Z$'});
const time=s=>{require(date(s)&&Number.isFinite(Date.parse(s)),'Invalid trajectory timestamp');return Date.parse(s);};
const decimal=s=>typeof s==='string'&&s.length<=64&&/^(0|[1-9]\d*)(\.\d{1,12})?$/.test(s);

export function evaluateCarbonTrajectories(input,root=ROOT) {
 require(keys(input,'schemaVersion kind sourceLedger sourceLedgerSHA256 evaluationAt observedRevisions forecasts draftTargets decisionReferences engineeringReview controlAction behavioralCasesRun'),'Unsupported trajectory fields');
 require(input.schemaVersion==='1.0.0'&&input.kind==='SYNTHETIC_CARBON_TRAJECTORY_ARCHIVE'&&input.sourceLedger==='assets/import-carbon-ledger.json'&&input.engineeringReview==='PENDING'&&input.controlAction==='DENY'&&input.behavioralCasesRun===0,'Unsupported trajectory scope/claims');
 const bytes=readFileSync(resolve(root,input.sourceLedger));require(hash(bytes)===input.sourceLedgerSHA256,'Trajectory source hash mismatch');
 const base=JSON.parse(bytes);evaluateCarbonLedger(base,root);const evaluation=time(input.evaluationAt);
 for(const list of [input.observedRevisions,input.forecasts,input.draftTargets,input.decisionReferences])require(Array.isArray(list)&&list.length<=100,'Invalid trajectory series size');
 require(input.observedRevisions.length>0,'Missing observed revision baseline');
 const ids=new Set(),snapshots=new Map(),factorLabels=new Map(),observed=[];let previous=null;
 const identity=id=>{require(typeof id==='string'&&id.length>0&&!ids.has(id),'Invalid/duplicate archive identity');ids.add(id);};
 for(const r of input.observedRevisions) {
  require(keys(r,'id parentSnapshotDigest snapshotDigest ledger'),'Unsupported revision fields');identity(r.id);
  const result=evaluateCarbonLedger(r.ledger,root),digest=trajectoryDigest(r.ledger),at=time(r.ledger.evaluationAt);
  require(r.snapshotDigest===digest&&!snapshots.has(digest),'Revision digest mismatch/duplicate');
  require(at<=evaluation,'Observed revision is not yet available');
  if(previous===null)require(r.parentSnapshotDigest===null&&digest===trajectoryDigest(base),'Original ledger snapshot was rewritten');
  else {
   require(r.parentSnapshotDigest===previous.snapshotDigest&&at>time(previous.ledger.evaluationAt),'Broken/reordered revision chain');
   require(r.ledger.sourceInterval===base.sourceInterval&&r.ledger.sourceIntervalSHA256===base.sourceIntervalSHA256&&isDeepStrictEqual(r.ledger.basis,base.basis)&&r.ledger.rows.length===base.rows.length,'Revision changes accounting source/scope');
   let changed=false;
   for(const [i,row] of r.ledger.rows.entries()) {
    const old=previous.ledger.rows[i];
    const stable=v=>{const copy=structuredClone(v);delete copy.evaluationAt;return copy;};
    require(row.id===old.id&&isDeepStrictEqual(stable(row.meterInterval),stable(old.meterInterval)),'Factor revision changed meter evidence');
    if(!isDeepStrictEqual(row.factor,old.factor)) {
     changed=true;require(row.factor.revision!==old.factor.revision&&time(row.factor.issuedAt)>=time(old.factor.issuedAt),'Changed factor needs a new revision label and nondecreasing publication time');
    }
   }
   require(changed,'Empty reporting revision');
  }
  for(const row of r.ledger.rows) {
   const key=JSON.stringify([row.id,row.factor.providerId,row.factor.revision]),factorDigest=trajectoryDigest(row.factor);
   require(!factorLabels.has(key)||factorLabels.get(key)===factorDigest,'Source revision label reused for different factor content');factorLabels.set(key,factorDigest);
  }
  snapshots.set(digest,{at,result});observed.push({id:r.id,snapshotDigest:digest,parentSnapshotDigest:r.parentSnapshotDigest,availableAt:r.ledger.evaluationAt,eligible:result.eligible,intensityGCO2ePerKWh:result.intensityGCO2ePerKWh,allocatedEmissionsGCO2e:result.allocatedEmissionsGCO2e,intensityStatus:result.intensityStatus});previous=r;
 }
 const basisFor=role=>({...base.basis,dataRole:role});
 const forecasts=[];
 for(const f of input.forecasts) {
  require(keys(f,'id sourceType basis issuedAt intervalStart intervalEnd quality intensity'),'Unsupported forecast fields');identity(f.id);
  require(f.sourceType==='SYNTHETIC_FORECAST'&&isDeepStrictEqual(f.basis,basisFor('SYNTHETIC_FORECAST')),'Forecast basis/role mismatch');
  require(time(f.issuedAt)<time(f.intervalStart)&&time(f.intervalStart)<time(f.intervalEnd)&&time(f.issuedAt)<=evaluation,'Invalid forecast vintage/window');
  require(['GOOD','BAD','UNKNOWN'].includes(f.quality)&&(f.intensity===null||decimal(f.intensity)),'Invalid forecast quality/value');
  const eligible=f.quality==='GOOD'&&f.intensity!==null;
  forecasts.push({id:f.id,issuedAt:f.issuedAt,intervalStart:f.intervalStart,intervalEnd:f.intervalEnd,eligible,intensity:eligible?f.intensity:null,series:'SYNTHETIC_FORECAST_NOT_OBSERVATION'});
 }
 const targets=[];
 for(const t of input.draftTargets) {
  require(keys(t,'id sourceType basis baselineSnapshotDigest issuedAt intervalStart intervalEnd intensity status owner approvalReceipt'),'Unsupported target fields');identity(t.id);
  require(t.sourceType==='SYNTHETIC_TARGET_EXAMPLE'&&isDeepStrictEqual(t.basis,basisFor('SYNTHETIC_TARGET'))&&t.status==='DRAFT_EXAMPLE_NOT_ADOPTED'&&t.owner===null&&t.approvalReceipt===null,'Target is an unadopted synthetic example only');
  const baseline=snapshots.get(t.baselineSnapshotDigest);
  require(baseline?.result.eligible&&baseline.result.intensityGCO2ePerKWh!==null&&baseline.at<=time(t.issuedAt),'Target baseline unavailable or undefined');
  require(time(t.issuedAt)<=evaluation&&time(t.issuedAt)<=time(t.intervalStart)&&time(t.intervalStart)<time(t.intervalEnd)&&decimal(t.intensity),'Invalid draft target window/value');
  targets.push({id:t.id,baselineSnapshotDigest:t.baselineSnapshotDigest,intensity:t.intensity,status:t.status,usableForControl:false});
 }
 const references=[];
 for(const d of input.decisionReferences) {
  require(keys(d,'id at observedSnapshotDigest actionExecuted controlAction'),'Unsupported decision reference fields');identity(d.id);
  const snapshot=snapshots.get(d.observedSnapshotDigest);
  require(snapshot?.result.eligible&&snapshot.at<=time(d.at)&&time(d.at)<=evaluation&&d.actionExecuted===false&&d.controlAction==='DENY','Unavailable snapshot or fabricated action reference');
  references.push({id:d.id,observedSnapshotDigest:d.observedSnapshotDigest,intensityGCO2ePerKWh:snapshot.result.intensityGCO2ePerKWh,actionExecuted:false});
 }
 return {verificationType:'SYNTHETIC_TRAJECTORY_REVISION_INTEGRITY_ONLY',observedRevisions:observed,forecasts,draftTargets:targets,decisionReferences:references,dependentAccountingRequalificationRequired:observed.length>1,seriesCombined:false,targetAdopted:false,controlAction:'DENY',behavioralCasesRun:0};
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
 try {
  if(process.argv.length!==3)throw Error('Usage: node tools/evaluate_carbon_trajectories.mjs <archive.json>');
  console.log(JSON.stringify({result:'PASS',...evaluateCarbonTrajectories(read(resolve(process.argv[2])))},null,2));
 }catch(e){console.error(e.message);process.exitCode=1;}
}
