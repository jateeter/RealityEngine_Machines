#!/usr/bin/env node
/** Bounded synthetic factor restatement; hashes do not authenticate reporting history. */
import {readFileSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {isDeepStrictEqual} from 'node:util';
import Ajv2020 from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';
import {trajectoryDigest} from './evaluate_carbon_trajectories.mjs';
import {POLICY,evaluateJournalStorage} from './evaluate_journal_storage.mjs';
const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const require=(ok,msg)=>{if(!ok)throw Error(msg);};
const keys=(x,list)=>x&&typeof x==='object'&&!Array.isArray(x)&&isDeepStrictEqual(Object.keys(x).sort(),list.split(' ').sort());
const ajv=new Ajv2020({strict:false});addFormats(ajv);
const date=ajv.compile({type:'string',format:'date-time',pattern:'^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d{3})?Z$'});
const time=x=>{require(date(x)&&Number.isFinite(Date.parse(x)),'Invalid journal revision timestamp');return Date.parse(x);};
export function journalRevisionDigest(baselineLedgerDigest,revision){
 const {revisionDigest,...body}=revision;return trajectoryDigest({baselineLedgerDigest,...body});
}

export function evaluateJournalRevisions(input,root=ROOT){
 require(keys(input,'schemaVersion kind baselineLedger baselineLedgerDigest revisions evaluationAt asOf engineeringReview controlAction behavioralCasesRun'),'Unsupported journal revision fields');
 require(input.schemaVersion==='1.0.0'&&input.kind==='SYNTHETIC_JOURNAL_CARBON_REVISION_ARCHIVE'&&input.engineeringReview==='PENDING'&&input.controlAction==='DENY'&&input.behavioralCasesRun===0,'Unsupported journal revision scope/claims');
 require(Buffer.byteLength(JSON.stringify(input))<=2097152&&Array.isArray(input.revisions)&&input.revisions.length>0&&input.revisions.length<=10,'Invalid/oversized journal revision archive');
 require(input.baselineLedgerDigest===trajectoryDigest(input.baselineLedger),'Baseline ledger digest mismatch');
 const evaluation=time(input.evaluationAt),cutoff=time(input.asOf);require(cutoff<=evaluation,'As-of time exceeds archive evaluation');
 const base=input.baselineLedger,ids=new Set(),digests=new Set(),labels=new Map(),snapshots=[];let previous=null,selected=null;
 for(const r of input.revisions){
  require(keys(r,'id parentRevisionDigest revisionDigest evaluationAt factors')&&typeof r.id==='string'&&/^[a-zA-Z0-9_.-]{1,80}$/.test(r.id)&&!ids.has(r.id),'Invalid/duplicate journal revision identity');ids.add(r.id);
  const at=time(r.evaluationAt);require(at<=evaluation,'Revision not yet available');
  require(r.revisionDigest===journalRevisionDigest(input.baselineLedgerDigest,r)&&!digests.has(r.revisionDigest),'Revision digest mismatch/duplicate');digests.add(r.revisionDigest);
  if(previous===null){
   require(r.parentRevisionDigest===null&&r.evaluationAt===base.evaluationAt&&isDeepStrictEqual(r.factors,base.factors),'Baseline reporting snapshot was rewritten');
  }else{
   require(r.parentRevisionDigest===previous.revisionDigest&&at>time(previous.evaluationAt),'Broken/reordered journal revision chain');
   require(Array.isArray(r.factors)&&r.factors.length===previous.factors.length,'Revision changes factor coverage');let changed=false;
   for(const [i,f] of r.factors.entries()){
    const old=previous.factors[i];require(keys(f,'eventSHA256 factor')&&f.eventSHA256===old.eventSHA256,'Revision changes meter event binding/order');
    if(!isDeepStrictEqual(f.factor,old.factor)){
     changed=true;require(f.factor.revision!==old.factor.revision&&time(f.factor.issuedAt)>=time(old.factor.issuedAt),'Changed factor needs a new revision label and nondecreasing publication time');
    }
   }
   require(changed,'Empty factor restatement');
  }
  const ledger={...base,evaluationAt:r.evaluationAt,factors:r.factors};
  // The same immutable journal is used for every report; meter/storage state cannot be rewritten here.
  const storage=evaluateJournalStorage({schemaVersion:'1.0.0',kind:'SYNTHETIC_JOURNAL_STORAGE_RECONCILIATION',carbonLedger:ledger,accountingPolicy:POLICY,accountingUse:'RETROSPECTIVE_ONLY',engineeringReview:'PENDING',controlAction:'DENY',behavioralCasesRun:0},root);
  for(const f of r.factors){
   const key=JSON.stringify([f.eventSHA256,f.factor.providerId,f.factor.revision]),digest=trajectoryDigest(f.factor);
   require(!labels.has(key)||labels.get(key)===digest,'Source revision label reused for different factor content');labels.set(key,digest);
  }
  const carbon=storage.sourceImportAccounting;
  const snapshot={id:r.id,revisionDigest:r.revisionDigest,parentRevisionDigest:r.parentRevisionDigest,availableAt:r.evaluationAt,
   importedKWh:carbon.importedKWh,allocatedEmissionsGCO2e:carbon.allocatedEmissionsGCO2e,intensityGCO2ePerKWh:carbon.intensityGCO2ePerKWh,intensityStatus:carbon.intensityStatus,importAccountingEligible:carbon.eligible,
   newChargeAllocatedGCO2e:storage.newChargeAllocatedGCO2e,newChargeAttributionEligible:storage.newChargeAttributionEligible,
   lastAppliedStoredKWh:storage.lastAppliedStoredKWh,energyAllocationConserved:storage.energyAllocationConserved,
   storageCarbonStatus:storage.carbonStatus,deliveredAllocatedGCO2e:storage.deliveredAllocatedGCO2e,remainingCarriedGCO2e:storage.remainingCarriedGCO2e};
  snapshots.push(snapshot);if(at<=cutoff)selected=snapshot;previous=r;
 }
 return {verificationType:'SYNTHETIC_JOURNAL_FACTOR_RESTATEMENT_ONLY',baselineLedgerDigest:input.baselineLedgerDigest,journalHeadSHA256:base.journal.headSHA256,
  snapshots:snapshots.filter(s=>time(s.availableAt)<=cutoff),archiveRevisionCount:snapshots.length,asOf:input.asOf,selectedRevisionDigest:selected?.revisionDigest??null,
  selectedImportIntensityGCO2ePerKWh:selected?.intensityGCO2ePerKWh??null,selectedNewChargeAllocatedGCO2e:selected?.newChargeAllocatedGCO2e??null,
  selectedReportAvailable:selected!==null,storageRecomputedForEveryRevision:true,meterHistoryChanged:false,
  historyAuthenticated:false,forecastOrTargetSeriesIncluded:false,targetAdopted:false,providerQualified:false,facilityConsumptionIntensityQualified:false,operationallyAuthorized:false,
  simulationOnly:true,controlAction:'DENY',behavioralCasesRun:0};
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{if(process.argv.length!==3)throw Error('Usage: node tools/evaluate_journal_revisions.mjs <archive.json>');console.log(JSON.stringify({result:'PASS',...evaluateJournalRevisions(JSON.parse(readFileSync(resolve(process.argv[2]),'utf8')))},null,2));}
 catch(e){console.error(e.message);process.exitCode=1;}
}
