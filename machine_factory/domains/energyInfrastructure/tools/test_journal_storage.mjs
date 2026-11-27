import test from 'node:test';
import assert from 'node:assert/strict';
import {StorageExecutionJournal} from './storage_execution_journal.mjs';
import {evaluateJournalStorage} from './evaluate_journal_storage.mjs';
import {buildJournalStorageScenario} from './run_journal_storage_scenario.mjs';
const f=(n,d='1')=>({numerator:n,denominator:d});
function single(power){
 const x=buildJournalStorageScenario(),j=new StorageExecutionJournal('storage.single');j.step({id:'single',storagePowerKw:power});x.carbonLedger.journal=j.export();
 const e=j.export().events[0],factor=structuredClone(x.carbonLedger.factors[0].factor);factor.intervalStart=e.receipt.meterInterval.input.start.observedAt;factor.intervalEnd=e.receipt.meterInterval.input.end.observedAt;
 x.carbonLedger.factors=[{eventSHA256:e.eventSHA256,factor}];return x;
}
test('independent storage reconciliation closes energy balance including both conversion losses',()=>{
 const r=evaluateJournalStorage(buildJournalStorageScenario());
 assert.deepEqual(r.openingStoredKWh,f('5'));assert.deepEqual(r.chargedInputAcKWh,f('1','2'));assert.deepEqual(r.deliveredAcKWh,f('1','2'));
 assert.deepEqual(r.chargeConversionLossKWh,f('1','20'));assert.deepEqual(r.dischargeConversionLossKWh,f('1','8'));assert.deepEqual(r.lastAppliedStoredKWh,f('193','40'));assert.equal(r.energyAllocationConserved,true);assert.equal(r.steps.length,3);
 assert.deepEqual(r.steps[0].storedAfterKWh,f('109','20'));assert.deepEqual(r.steps[2].storedAfterKWh,f('193','40'));
});
test('new charging attribution is a subset of imports, never total inventory carbon',()=>{
 const r=evaluateJournalStorage(buildJournalStorageScenario());assert.deepEqual(r.newChargeAllocatedGCO2e,f('200'));assert.deepEqual(r.sourceImportAccounting.allocatedEmissionsGCO2e,f('500'));assert.equal(r.newChargeAllocationIsSubsetOfImportLedger,true);assert.equal(r.additionalInventoryEmissions,false);
 for(const key of ['openingCarriedGCO2e','deliveredAllocatedGCO2e','remainingCarriedGCO2e','deliveredIntensityGCO2ePerKWh'])assert.equal(r[key],null,key);
 assert.equal(r.carbonStatus,'UNKNOWN_OPENING_INVENTORY');assert.equal(r.facilityConsumptionIntensityQualified,false);assert.equal(r.controlAction,'DENY');assert.equal(r.operationallyAuthorized,false);assert.equal(r.behavioralCasesRun,0);
 for(const s of r.steps){assert.equal(s.remainingCarriedGCO2e,null);assert.equal(s.deliveredAllocatedGCO2e,null);}
});
test('current unknown telemetry is not replaced by the last historical energy state',()=>{
 const r=evaluateJournalStorage(buildJournalStorageScenario());assert.equal(r.currentObservedStoredKWh,null);assert.equal(r.currentObservationQuality,'UNKNOWN');assert.deepEqual(r.lastAppliedStoredKWh,f('193','40'));assert.equal(r.lastAppliedObservedAt,'2026-11-25T00:45:00.000Z');
});
for(const quality of ['missing','BAD','expired'])test(`${quality} factor leaves energy reconciliation intact and new attribution unknown`,()=>{
 const x=buildJournalStorageScenario(),q=x.carbonLedger.factors[0].factor;
 if(quality==='missing')q.intensity=null;else if(quality==='BAD')q.quality='BAD';else{q.issuedAt='2026-11-25T00:15:00.100Z';q.validUntil='2026-11-25T00:45:00.500Z';}
 const r=evaluateJournalStorage(x);assert.equal(r.energyAllocationConserved,true);assert.equal(r.newChargeAttributionEligible,false);assert.equal(r.newChargeAllocatedGCO2e,null);assert.equal(r.remainingCarriedGCO2e,null);assert.deepEqual(r.lastAppliedStoredKWh,f('193','40'));
});
test('idle does not turn unknown opening carbon into a known empty pool',()=>{
 const r=evaluateJournalStorage(single('0'));assert.deepEqual(r.lastAppliedStoredKWh,f('5'));assert.deepEqual(r.chargedInputAcKWh,f('0'));assert.deepEqual(r.newChargeAllocatedGCO2e,f('0'));assert.equal(r.openingCarbonStatus,'UNKNOWN_OPENING_INVENTORY');assert.equal(r.remainingCarriedGCO2e,null);
});
test('discharge without recorded charging still has unknown delivered carbon',()=>{
 const r=evaluateJournalStorage(single('2'));assert.deepEqual(r.lastAppliedStoredKWh,f('35','8'));assert.deepEqual(r.deliveredAcKWh,f('1','2'));assert.deepEqual(r.dischargeConversionLossKWh,f('1','8'));assert.equal(r.deliveredAllocatedGCO2e,null);assert.equal(r.deliveredIntensityGCO2ePerKWh,null);
});
test('charge-only calculation allocates conversion loss without manufacturing delivery',()=>{
 const r=evaluateJournalStorage(single('-2'));assert.deepEqual(r.lastAppliedStoredKWh,f('109','20'));assert.deepEqual(r.deliveredAcKWh,f('0'));assert.deepEqual(r.newChargeAllocatedGCO2e,f('200'));assert.equal(r.deliveredIntensityGCO2ePerKWh,null);
});
test('historical charge replay and held request cannot add inventory or charging emissions',()=>{
 const x=buildJournalStorageScenario(),r=evaluateJournalStorage(x);assert.equal(x.carbonLedger.journal.events[3].receipt.replayed,true);assert.equal(x.carbonLedger.journal.events.at(-1).receipt.applied,false);assert.equal(r.steps.length,3);assert.deepEqual(r.chargedInputAcKWh,f('1','2'));assert.deepEqual(r.newChargeAllocatedGCO2e,f('200'));
});
for(const [name,mutate] of [
 ['known-empty override',x=>x.initialInventory={status:'KNOWN_EMPTY_SYNTHETIC',storedKWh:'0',carriedGCO2e:'0'}],
 ['opening energy override',x=>x.openingStoredKWh='0'],
 ['opening mass override',x=>x.openingCarriedGCO2e='0'],
 ['unsupported policy',x=>x.accountingPolicy='ZERO_CARBON_STORAGE'],
 ['dispatch use',x=>x.accountingUse='DISPATCH'],
 ['false control',x=>x.controlAction='ALLOW'],
 ['false case claim',x=>x.behavioralCasesRun=43],
 ['tampered receipt',x=>x.carbonLedger.journal.events[0].receipt.observation.storedEnergyKWh='0'],
 ['source pin drift',x=>x.carbonLedger.journal.sourcePins.assetManifestSHA256='0'.repeat(64)],
 ['factor omission',x=>x.carbonLedger.factors.pop()],
 ['unqualified provider identity',x=>x.carbonLedger.factors[0].factor.providerId='REAL_PROVIDER']
])test(`reject ${name}`,()=>{const x=buildJournalStorageScenario();mutate(x);assert.throws(()=>evaluateJournalStorage(x));});
test('evaluation preserves its input including the journal',()=>{
 const x=buildJournalStorageScenario(),before=structuredClone(x);evaluateJournalStorage(x);assert.deepEqual(x,before);
});
