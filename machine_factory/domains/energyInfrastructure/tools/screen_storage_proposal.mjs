#!/usr/bin/env node
/** Draft constant-power algebra only; no command authorization or execution path. */
import {readFileSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {isDeepStrictEqual} from 'node:util';
import Ajv2020 from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';
import {validateFunctionBindings} from './validate_function_bindings.mjs';
const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const read=p=>JSON.parse(readFileSync(p,'utf8'));
const hash=b=>createHash('sha256').update(b).digest('hex');
const require=(ok,msg)=>{if(!ok)throw Error(msg);};
const keys=(o,s)=>o&&typeof o==='object'&&!Array.isArray(o)&&isDeepStrictEqual(Object.keys(o).sort(),s.split(' ').sort());
const ajv=new Ajv2020({strict:false});addFormats(ajv);
const date=ajv.compile({type:'string',format:'date-time',pattern:'^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d{3})?Z$'});
const time=s=>{require(date(s)&&Number.isFinite(Date.parse(s)),'Invalid screen timestamp');return Date.parse(s);};
function frac(n,d=1n){require(d>0n,'Invalid rational');if(n===0n)return [0n,1n];let a=n<0n?-n:n,b=d;while(b){const t=a%b;a=b;b=t;}return [n/a,d/a];}
function parse(s,signed=false){require(typeof s==='string'&&s.length<=64&&(signed?/^-?(0|[1-9]\d*)(\.\d{1,6})?$/:/^(0|[1-9]\d*)(\.\d{1,6})?$/).test(s),'Expected bounded screen decimal');const negative=s.startsWith('-'),[a,b='']=(negative?s.slice(1):s).split('.');return frac(BigInt(a+b)*(negative?-1n:1n),10n**BigInt(b.length));}
const add=(a,b)=>frac(a[0]*b[1]+b[0]*a[1],a[1]*b[1]);
const neg=a=>[-a[0],a[1]],sub=(a,b)=>add(a,neg(b));
const mul=(a,b)=>frac(a[0]*b[0],a[1]*b[1]);
const div=(a,b)=>{require(b[0]>0n,'Invalid efficiency');return frac(a[0]*b[1],a[1]*b[0]);};
const le=(a,b)=>a[0]*b[1]<=b[0]*a[1],abs=a=>[a[0]<0n?-a[0]:a[0],a[1]];
const encode=a=>({numerator:a[0].toString(),denominator:a[1].toString()});
const ONE=[1n,1n],ZERO=[0n,1n];

export function screenStorageProposal(input,root=ROOT) {
 require(keys(input,'schemaVersion kind referenceScenarioId sourceProjection sourceProjectionSHA256 profilePath profileSHA256 storageAssetId evaluationAt state proposal engineeringReview controlAction behavioralCasesRun'),'Unsupported screen fields');
 require(input.schemaVersion==='1.0.0'&&input.kind==='SYNTHETIC_STORAGE_PROPOSAL_SCREEN'&&input.referenceScenarioId==='REF01_CONNECTED'&&input.sourceProjection==='assets/function-bindings/ref01_connected.json'&&input.profilePath==='assets/generic-storage-screen-profile.json'&&input.engineeringReview==='PENDING'&&input.controlAction==='DENY'&&input.behavioralCasesRun===0,'Unsupported screen scope/claims');
 const bytes=readFileSync(resolve(root,input.sourceProjection));require(hash(bytes)===input.sourceProjectionSHA256,'Screen projection hash mismatch');const projection=JSON.parse(bytes);require(!validateFunctionBindings(projection,root).length,'Invalid screen projection');
 require(projection.accounting.resourceGroups.some(g=>g.id==='STORAGE_AC'&&g.primaryViewAssetId===input.storageAssetId),'Wrong storage accounting primary');
 const profileBytes=readFileSync(resolve(root,input.profilePath));require(hash(profileBytes)===input.profileSHA256,'Screen profile hash mismatch');const p=JSON.parse(profileBytes);
 require(keys(p,'schemaVersion kind revision status powerUnit energyUnit intervalUnit capacityKWh reserveKWh maxChargeKw maxDischargeKw maxStepPowerChangeKw maxImportKw maxExportKw minCriticalDemandKw chargeEfficiency dischargeEfficiency maxIntervalHours maxStateAgeMs controlAction')&&p.schemaVersion==='1.0.0'&&p.kind==='DRAFT_GENERIC_STORAGE_SCREEN_PROFILE'&&typeof p.revision==='string'&&p.revision.length>0&&p.status==='NOT_ENGINEERING_APPROVED'&&p.powerUnit==='kW'&&p.energyUnit==='kWh'&&p.intervalUnit==='h'&&p.controlAction==='DENY','Unsupported generic screen profile');
 const limits={};for(const name of ['capacityKWh','reserveKWh','maxChargeKw','maxDischargeKw','maxStepPowerChangeKw','maxImportKw','maxExportKw','minCriticalDemandKw','chargeEfficiency','dischargeEfficiency','maxIntervalHours'])limits[name]=parse(p[name]);
 require(limits.capacityKWh[0]>0n&&le(limits.reserveKWh,limits.capacityKWh)&&limits.chargeEfficiency[0]>0n&&le(limits.chargeEfficiency,ONE)&&limits.dischargeEfficiency[0]>0n&&le(limits.dischargeEfficiency,ONE)&&limits.maxIntervalHours[0]>0n&&Number.isSafeInteger(p.maxStateAgeMs)&&p.maxStateAgeMs>0&&p.maxStateAgeMs<=3600000,'Invalid generic limits/efficiencies');
 const s=input.state,q=input.proposal;
 require(keys(s,'observedAt receivedAt quality stateRevision topologyRevision mode pcc gridAvailable protectiveInterlocks riskDisposition storedEnergyKWh criticalDemandKw otherDemandKw pvGenerationKw previousStorageKw')&&['GOOD','BAD','UNKNOWN'].includes(s.quality)&&['HEALTHY','BLOCKED','UNKNOWN'].includes(s.protectiveInterlocks)&&['CLEAR','BLOCKED','UNKNOWN'].includes(s.riskDisposition)&&typeof s.gridAvailable==='boolean','Invalid synthetic state fields');
 require(['stateRevision','topologyRevision'].every(k=>typeof s[k]==='string'&&s[k].length>0),'Missing state/topology identity');
 require(keys(q,'id origin issuedAt expiresAt stateRevision topologyRevision profileSHA256 storageAssetId powerUnit storagePowerKw intervalHours criticalServedKw claimedCarbonReductionPercent operatingApproval')&&typeof q.id==='string'&&q.id.length>0&&q.origin==='MODEL_PLANNER'&&q.powerUnit==='kW'&&q.operatingApproval===null,'Unsupported proposal identity/units/approval claim');
 const evaluation=time(input.evaluationAt),observed=time(s.observedAt),received=time(s.receivedAt),issued=time(q.issuedAt),expires=time(q.expiresAt);
 require(observed<=received&&received<=evaluation&&issued<expires,'Invalid screen time ordering');
 const power=parse(q.storagePowerKw,true),hours=parse(q.intervalHours),served=parse(q.criticalServedKw),claim=parse(q.claimedCarbonReductionPercent);
 require(hours[0]>0n&&le(claim,[100n,1n]),'Invalid proposal interval/carbon claim');
 const reasons=[],check=(ok,reason)=>{if(!ok)reasons.push(reason);};
 check(issued<=evaluation&&evaluation<expires,'PROPOSAL_NOT_CURRENT');check(issued>=received,'PROPOSAL_PREDATES_STATE_RECEIPT');
 check(q.stateRevision===s.stateRevision&&q.topologyRevision===s.topologyRevision&&q.profileSHA256===input.profileSHA256,'REVISION_BINDING_MISMATCH');check(q.storageAssetId===input.storageAssetId,'WRONG_STORAGE_TARGET');
 check(s.quality==='GOOD','STATE_QUALITY_NOT_GOOD');check(evaluation-observed<=p.maxStateAgeMs,'STALE_STATE');
 check(s.mode==='GRID_CONNECTED'&&s.pcc==='CLOSED'&&s.gridAvailable,'UNSUPPORTED_GRID_MODE');check(s.protectiveInterlocks==='HEALTHY','PROTECTION_NOT_HEALTHY');check(s.riskDisposition==='CLEAR','RISK_NOT_CLEAR');
 const values={};let missing=false;
 for(const name of ['storedEnergyKWh','criticalDemandKw','otherDemandKw','pvGenerationKw','previousStorageKw']){
  if(s[name]===null){require(s.quality!=='GOOD','GOOD state lacks required quantity');missing=true;}else values[name]=parse(s[name],name==='previousStorageKw');
 }
 let calculations=null;
 if(missing)reasons.push('MISSING_STATE_QUANTITY');
 // Unknown/stale/interlocked state never produces numeric screening results.
 if(!reasons.length) {
  const discharge=power[0]>=0n;
  const next=discharge?sub(values.storedEnergyKWh,div(mul(power,hours),limits.dischargeEfficiency)):add(values.storedEnergyKWh,mul(mul(abs(power),hours),limits.chargeEfficiency));
  const net=sub(sub(add(served,values.otherDemandKw),values.pvGenerationKw),power);
  check(le(hours,limits.maxIntervalHours),'INTERVAL_LIMIT');check(le(abs(power),discharge?limits.maxDischargeKw:limits.maxChargeKw),'STORAGE_POWER_LIMIT');
  check(le(abs(sub(power,values.previousStorageKw)),limits.maxStepPowerChangeKw),'POWER_STEP_LIMIT');
  check(le(limits.reserveKWh,values.storedEnergyKWh)&&le(values.storedEnergyKWh,limits.capacityKWh),'INITIAL_ENERGY_OUTSIDE_ENVELOPE');
  check(le(limits.reserveKWh,next),'RESERVE_VIOLATION');check(le(next,limits.capacityKWh),'CAPACITY_VIOLATION');
  check(le(limits.minCriticalDemandKw,values.criticalDemandKw)&&isDeepStrictEqual(served,values.criticalDemandKw),'CRITICAL_LOAD_NOT_PRESERVED');
  check(le(net,limits.maxImportKw),'IMPORT_LIMIT');check(le(neg(limits.maxExportKw),net),'EXPORT_LIMIT');
  calculations={nextStoredKWh:encode(next),netImportKw:encode(net)};
 }
 return {verificationType:'DRAFT_SYNTHETIC_PROPOSAL_SCREEN_ONLY',eligibleForFurtherSimulation:!reasons.length,reasons,calculations,claimedCarbonReductionUsed:false,carbonObjectiveQualified:false,engineeringApproved:false,operationallyAuthorized:false,executionPathAvailable:false,controlAction:'DENY',behavioralCasesRun:0};
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
 try {if(process.argv.length!==3)throw Error('Usage: node tools/screen_storage_proposal.mjs <screen.json>');console.log(JSON.stringify({result:'PASS',...screenStorageProposal(read(resolve(process.argv[2])))},null,2));}
 catch(e){console.error(e.message);process.exitCode=1;}
}
