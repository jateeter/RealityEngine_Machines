#!/usr/bin/env node
/** Historical storage energy reconciliation; unknown opening carbon stays unknown. */
import {readFileSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {isDeepStrictEqual} from 'node:util';
import {StorageExecutionJournal} from './storage_execution_journal.mjs';
import {StorageComponentSimulator} from './simulate_storage_component.mjs';
import {evaluateJournalCarbonLedger} from './evaluate_carbon_ledger.mjs';
const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'..');
export const POLICY='DRAFT_FIXED_REF01_INCREMENTAL_GRID_CHARGE_WITH_UNKNOWN_OPENING_CARBON';
const require=(ok,msg)=>{if(!ok)throw Error(msg);};
function rational(n,d=1n){require(n>=0n&&d>0n,'Invalid storage reconciliation rational');if(!n)return [0n,1n];let a=n,b=d;while(b){[a,b]=[b,a%b];}return [n/a,d/a];}
function parse(s){require(typeof s==='string'&&s.length<=64&&/^(0|[1-9]\d*)(\.\d{1,13})?$/.test(s),'Invalid storage reconciliation decimal');const [a,b='']=s.split('.');return rational(BigInt(a+b),10n**BigInt(b.length));}
const add=(a,b)=>rational(a[0]*b[1]+b[0]*a[1],a[1]*b[1]);
const sub=(a,b)=>rational(a[0]*b[1]-b[0]*a[1],a[1]*b[1]);
const mul=(a,b)=>rational(a[0]*b[0],a[1]*b[1]);
const div=(a,b)=>rational(a[0]*b[1],a[1]*b[0]);
const le=(a,b)=>a[0]*b[1]<=b[0]*a[1];
const encode=a=>({numerator:a[0].toString(),denominator:a[1].toString()});
const decode=a=>rational(BigInt(a.numerator),BigInt(a.denominator));
const ZERO=[0n,1n],QUARTER=[1n,4n];

export function evaluateJournalStorage(input,root=ROOT){
 require(input&&isDeepStrictEqual(Object.keys(input).sort(),'schemaVersion kind carbonLedger accountingPolicy accountingUse engineeringReview controlAction behavioralCasesRun'.split(' ').sort()),'Unsupported journal storage fields');
 require(input.schemaVersion==='1.0.0'&&input.kind==='SYNTHETIC_JOURNAL_STORAGE_RECONCILIATION'&&input.accountingPolicy===POLICY&&input.accountingUse==='RETROSPECTIVE_ONLY'&&input.engineeringReview==='PENDING'&&input.controlAction==='DENY'&&input.behavioralCasesRun===0,'Unsupported journal storage scope/claims');
 const carbon=evaluateJournalCarbonLedger(input.carbonLedger,root);
 const restored=StorageExecutionJournal.restore(input.carbonLedger.journal,root),journal=restored.export();
 const opening=new StorageComponentSimulator(root,journal.runId).observe();
 const events=journal.events.filter(e=>e.operation==='STEP'&&e.receipt.applied&&!e.receipt.replayed);
 require(isDeepStrictEqual(events.map(e=>e.eventSHA256),carbon.accountedEventSHA256),'Storage/carbon event binding mismatch');
 const template=JSON.parse(readFileSync(resolve(root,'assets/storage-proposal-screen.json')));
 let stored=parse(opening.storedEnergyKWh),charged=ZERO,delivered=ZERO,chargeLoss=ZERO,dischargeLoss=ZERO,chargeMass=ZERO;
 const initial=stored,steps=[];
 for(const [i,e] of events.entries()){
  const power=e.payload.storagePowerKw,negative=power.startsWith('-'),magnitude=parse(negative?power.slice(1):power),ac=mul(magnitude,QUARTER);
  const before=stored;let gain=ZERO,removed=ZERO,cLoss=ZERO,dLoss=ZERO,mass=ZERO;
  if(negative&&magnitude[0]>0n){
   gain=mul(ac,[9n,10n]);cLoss=sub(ac,gain);stored=add(stored,gain);charged=add(charged,ac);chargeLoss=add(chargeLoss,cLoss);
   // In fixed REF01, 3 kW demand minus 1 kW PV leaves positive residual load.
   // Charge input is incremental grid import under this explicitly draft allocation policy.
   require(le(ac,parse(e.receipt.meterInterval.result.importedKWh)),'Charge input exceeds source import budget');
   if(carbon.eligible){mass=mul(ac,parse(input.carbonLedger.factors[i].factor.intensity));chargeMass=add(chargeMass,mass);}
  }else if(magnitude[0]>0n){
   removed=div(ac,[4n,5n]);dLoss=sub(removed,ac);stored=sub(stored,removed);delivered=add(delivered,ac);dischargeLoss=add(dischargeLoss,dLoss);
  }
  require(isDeepStrictEqual(stored,parse(e.receipt.observation.storedEnergyKWh)),'Independent storage state reconciliation disagrees');
  steps.push({eventSHA256:e.eventSHA256,observedAt:e.receipt.observation.observedAt,
   storedBeforeKWh:encode(before),storedAfterKWh:encode(stored),chargeInputAcKWh:encode(negative?ac:ZERO),
   deliveredAcKWh:encode(negative?ZERO:ac),chargeConversionLossKWh:encode(cLoss),dischargeConversionLossKWh:encode(dLoss),
   newChargeAllocatedGCO2e:carbon.eligible?encode(mass):null,remainingCarriedGCO2e:null,deliveredAllocatedGCO2e:null});
 }
 require(isDeepStrictEqual(add(initial,charged),add(add(stored,delivered),add(chargeLoss,dischargeLoss))),'Storage energy conservation failed');
 if(carbon.eligible)require(le(chargeMass,decode(carbon.allocatedEmissionsGCO2e)),'Charging allocation exceeds import emissions');
 const current=restored.observe(),last=events.at(-1).receipt.observation;
 return {verificationType:'SOURCE_BOUND_SYNTHETIC_STORAGE_ENERGY_RECONCILIATION_ONLY',simulationOnly:true,
  journalHeadSHA256:journal.headSHA256,storageAssetId:template.storageAssetId,accountingPolicy:POLICY,steps,
  openingStoredKWh:encode(initial),openingCarbonStatus:'UNKNOWN_OPENING_INVENTORY',openingCarriedGCO2e:null,
  chargedInputAcKWh:encode(charged),deliveredAcKWh:encode(delivered),
  chargeConversionLossKWh:encode(chargeLoss),dischargeConversionLossKWh:encode(dischargeLoss),
  lastAppliedStoredKWh:encode(stored),lastAppliedObservedAt:last.observedAt,
  currentObservedStoredKWh:current.storedEnergyKWh,currentObservationQuality:current.power.quality,
  energyAllocationConserved:true,newChargeAttributionEligible:carbon.eligible,
  newChargeAllocatedGCO2e:carbon.eligible?encode(chargeMass):null,
  deliveredAllocatedGCO2e:null,remainingCarriedGCO2e:null,deliveredIntensityGCO2ePerKWh:null,
  carbonStatus:'UNKNOWN_OPENING_INVENTORY',newChargeAllocationIsSubsetOfImportLedger:true,additionalInventoryEmissions:false,
  sourceImportAccounting:carbon,facilityConsumptionIntensityQualified:false,operationallyAuthorized:false,
  controlAction:'DENY',behavioralCasesRun:0};
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{if(process.argv.length!==3)throw Error('Usage: node tools/evaluate_journal_storage.mjs <input.json>');console.log(JSON.stringify({result:'PASS',...evaluateJournalStorage(JSON.parse(readFileSync(resolve(process.argv[2]),'utf8')))},null,2));}
 catch(e){console.error(e.message);process.exitCode=1;}
}
