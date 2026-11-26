#!/usr/bin/env node
/** Draft synthetic allocation policy, not a storage controller or final inventory. */
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
const require=(ok,msg)=>{if(!ok)throw Error(msg);};
const keys=(o,s)=>o&&typeof o==='object'&&!Array.isArray(o)&&isDeepStrictEqual(Object.keys(o).sort(),s.split(' ').sort());
const ajv=new Ajv2020({strict:false});addFormats(ajv);
const date=ajv.compile({type:'string',format:'date-time',pattern:'^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d{3})?Z$'});
const time=s=>{require(date(s)&&Number.isFinite(Date.parse(s)),'Invalid allocation timestamp');return Date.parse(s);};
function rational(n,d=1n){require(n>=0n&&d>0n,'Invalid allocation rational');if(n===0n)return [0n,1n];let a=n,b=d;while(b){const t=a%b;a=b;b=t;}return [n/a,d/a];}
function parse(s){require(typeof s==='string'&&s.length<=64&&/^(0|[1-9]\d*)(\.\d{1,13})?$/.test(s),'Expected nonnegative bounded allocation decimal');const [a,b='']=s.split('.');return rational(BigInt(a+b),10n**BigInt(b.length));}
const decode=a=>rational(BigInt(a.numerator),BigInt(a.denominator));
const encode=a=>({numerator:a[0].toString(),denominator:a[1].toString()});
const add=(a,b)=>rational(a[0]*b[1]+b[0]*a[1],a[1]*b[1]);
const sub=(a,b)=>rational(a[0]*b[1]-b[0]*a[1],a[1]*b[1]);
const mul=(a,b)=>rational(a[0]*b[0],a[1]*b[1]);
const div=(a,b)=>{require(b[0]>0n,'Undefined allocation ratio');return rational(a[0]*b[1],a[1]*b[0]);};
const le=(a,b)=>a[0]*b[1]<=b[0]*a[1];
const ZERO=[0n,1n];

export function evaluateStorageCarbon(input,root=ROOT) {
 require(keys(input,'schemaVersion kind sourceLedger sourceLedgerSHA256 storageAssetId evaluationAt accountingUse initialInventory accountingPolicy events engineeringReview controlAction behavioralCasesRun'),'Unsupported storage allocation fields');
 require(input.schemaVersion==='1.0.0'&&input.kind==='SYNTHETIC_STORAGE_CARBON_ALLOCATION'&&input.sourceLedger==='assets/import-carbon-ledger.json'&&input.accountingUse==='RETROSPECTIVE_ONLY'&&input.accountingPolicy==='DRAFT_WELL_MIXED_POOL_ALL_CONVERSION_LOSS_EMISSIONS_TO_DELIVERY'&&input.engineeringReview==='PENDING'&&input.controlAction==='DENY'&&input.behavioralCasesRun===0,'Unsupported storage allocation scope/claims');
 require(isDeepStrictEqual(input.initialInventory,{status:'KNOWN_EMPTY_SYNTHETIC',storedKWh:'0',carriedGCO2e:'0'}),'Only explicitly known-empty synthetic inventory is supported');
 const bytes=readFileSync(resolve(root,input.sourceLedger));require(createHash('sha256').update(bytes).digest('hex')===input.sourceLedgerSHA256,'Storage source ledger hash mismatch');
 const ledger=JSON.parse(bytes),source=evaluateCarbonLedger(ledger,root);require(source.eligible,'Unusable source carbon ledger');
 const evaluation=time(input.evaluationAt);require(time(ledger.evaluationAt)<=evaluation,'Source ledger evaluated after allocation evaluation');
 const projection=read(resolve(root,ledger.rows[0].meterInterval.sourceProjection)); // already allowlisted and verified by source ledger
 require(projection.accounting.resourceGroups.some(g=>g.id==='STORAGE_AC'&&g.primaryViewAssetId===input.storageAssetId)&&projection.bindings.some(b=>b.assetId===input.storageAssetId&&['Load','Generator'].every(c=>b.functions.some(f=>f.concept===c&&!f.active))),'Storage must be the selected primary with inactive Load/Generator projections');
 require(Array.isArray(input.events)&&input.events.length>0&&input.events.length<=100,'Invalid allocation event count');
 const rows=new Map(ledger.rows.map(row=>[row.id,row])),used=new Map(),ids=new Set(),steps=[];
 let stored=ZERO,carried=ZERO,charged=ZERO,chargedMass=ZERO,delivered=ZERO,deliveredMass=ZERO,chargeLoss=ZERO,dischargeLoss=ZERO,lastTime=-Infinity;
 for(const e of input.events) {
  require(e&&typeof e.id==='string'&&e.id.length>0&&!ids.has(e.id),'Invalid/duplicate allocation identity');ids.add(e.id);
  const at=time(e.at);require(at>lastTime&&at<=evaluation,'Allocation events must be chronological and no later than evaluation');lastTime=at;
  let stepMass,stepIntensity=null;
  if(e.type==='CHARGE_ALLOCATION') {
   require(keys(e,'id type at sourceRowId inputAcKWh storedKWh'),'Unsupported charge allocation fields');
   const row=rows.get(e.sourceRowId);require(!!row&&at===time(row.factor.intervalEnd),'Charge must reference the exact source interval end');
   const one=evaluateCarbonLedger({...ledger,rows:[row]},root);require(one.eligible,'Unusable charging source');
   const ac=parse(e.inputAcKWh),delta=parse(e.storedKWh),budget=add(used.get(row.id)??ZERO,ac);
   require(ac[0]>0n&&delta[0]>0n&&le(delta,ac),'Invalid stored/input charge energy');
   require(le(budget,decode(one.importedKWh)),'Charging allocation exceeds source imported energy');used.set(row.id,budget);
   require(one.intensityGCO2ePerKWh!==null,'Charging factor undefined for zero import');
   stepMass=mul(ac,decode(one.intensityGCO2ePerKWh));stored=add(stored,delta);carried=add(carried,stepMass);
   charged=add(charged,ac);chargedMass=add(chargedMass,stepMass);chargeLoss=add(chargeLoss,sub(ac,delta));
  }else if(e.type==='DISCHARGE_ALLOCATION') {
   require(keys(e,'id type at removedStoredKWh deliveredAcKWh'),'Unsupported discharge allocation fields');
   const removed=parse(e.removedStoredKWh),ac=parse(e.deliveredAcKWh);
   require(removed[0]>0n&&ac[0]>0n&&le(ac,removed)&&le(removed,stored),'Invalid discharge energy or insufficient inventory');
   stepMass=mul(carried,div(removed,stored));stored=sub(stored,removed);carried=sub(carried,stepMass);
   delivered=add(delivered,ac);deliveredMass=add(deliveredMass,stepMass);dischargeLoss=add(dischargeLoss,sub(removed,ac));stepIntensity=div(stepMass,ac);
  }else throw Error('Unsupported storage event type');
  require(stored[0]!==0n||carried[0]===0n,'Empty pool cannot retain unallocated emissions');
  steps.push({id:e.id,type:e.type,at:e.at,sourceRowId:e.type==='CHARGE_ALLOCATION'?e.sourceRowId:null,storedKWh:encode(stored),carriedGCO2e:encode(carried),allocatedGCO2e:encode(stepMass),deliveredIntensityGCO2ePerKWh:stepIntensity?encode(stepIntensity):null});
 }
 const energyBalance=add(add(delivered,stored),add(chargeLoss,dischargeLoss));
 require(isDeepStrictEqual(energyBalance,charged)&&isDeepStrictEqual(add(deliveredMass,carried),chargedMass),'Allocation conservation failed');
 return {verificationType:'DRAFT_SYNTHETIC_STORAGE_ALLOCATION_ONLY',sourceLedgerSHA256:input.sourceLedgerSHA256,storageAssetId:input.storageAssetId,accountingPolicy:input.accountingPolicy,steps,chargedInputKWh:encode(charged),chargedEmissionsGCO2e:encode(chargedMass),deliveredAcKWh:encode(delivered),deliveredAllocatedGCO2e:encode(deliveredMass),chargeConversionLossKWh:encode(chargeLoss),dischargeConversionLossKWh:encode(dischargeLoss),remainingStoredKWh:encode(stored),remainingCarriedGCO2e:encode(carried),deliveredIntensityGCO2ePerKWh:delivered[0]?encode(div(deliveredMass,delivered)):null,energyAllocationConserved:true,emissionsAllocationConserved:true,additionalInventoryEmissions:false,controlAction:'DENY',behavioralCasesRun:0};
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
 try {
  if(process.argv.length!==3)throw Error('Usage: node tools/evaluate_storage_carbon.mjs <allocation.json>');
  console.log(JSON.stringify({result:'PASS',...evaluateStorageCarbon(read(resolve(process.argv[2])))},null,2));
 }catch(e){console.error(e.message);process.exitCode=1;}
}
