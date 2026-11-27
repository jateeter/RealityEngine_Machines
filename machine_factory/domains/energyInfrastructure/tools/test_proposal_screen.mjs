import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,mkdtempSync,mkdirSync,copyFileSync,writeFileSync,rmSync,cpSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {screenStorageProposal} from './screen_storage_proposal.mjs';
const fixture=JSON.parse(readFileSync(new URL('../assets/storage-proposal-screen.json',import.meta.url),'utf8'));
const fresh=()=>structuredClone(fixture),f=(n,d='1')=>({numerator:n,denominator:d});
const denied=r=>{assert.equal(r.controlAction,'DENY');assert.equal(r.operationallyAuthorized,false);assert.equal(r.executionPathAvailable,false);assert.equal(r.carbonObjectiveQualified,false);};
test('independent constant-discharge oracle: 5 - (2*0.25/0.8) = 4.375',()=>{
 const r=screenStorageProposal(fixture);assert.equal(r.eligibleForFurtherSimulation,true);assert.deepEqual(r.calculations.nextStoredKWh,f('35','8'));assert.deepEqual(r.calculations.netImportKw,f('0'));assert.equal(r.claimedCarbonReductionUsed,false);denied(r);
});
test('charging preserves loss direction: 5 + 2*0.25*0.9 = 5.45',()=>{
 const d=fresh();d.proposal.storagePowerKw='-2';const r=screenStorageProposal(d);assert.equal(r.eligibleForFurtherSimulation,true);assert.deepEqual(r.calculations.nextStoredKWh,f('109','20'));assert.deepEqual(r.calculations.netImportKw,f('4'));denied(r);
});
test('idle proposal does not change energy',()=>{
 const d=fresh();d.proposal.storagePowerKw='0';const r=screenStorageProposal(d);assert.equal(r.eligibleForFurtherSimulation,true);assert.deepEqual(r.calculations.nextStoredKWh,f('5'));assert.deepEqual(r.calculations.netImportKw,f('2'));denied(r);
});
test('exact power/export/step boundaries are inclusive',()=>{
 const d=fresh();d.proposal.storagePowerKw='4';d.state.previousStorageKw='1';const r=screenStorageProposal(d);assert.equal(r.eligibleForFurtherSimulation,true);assert.deepEqual(r.calculations.netImportKw,f('-2'));denied(r);
});
for(const [name,mutate,reason] of [
 ['reserve despite claimed carbon benefit',d=>{d.state.storedEnergyKWh='3.1';d.proposal.claimedCarbonReductionPercent='100';},'RESERVE_VIOLATION'],
 ['capacity overflow',d=>{d.state.storedEnergyKWh='9.9';d.proposal.storagePowerKw='-2';},'CAPACITY_VIOLATION'],
 ['initial envelope violation',d=>d.state.storedEnergyKWh='11','INITIAL_ENERGY_OUTSIDE_ENVELOPE'],
 ['discharge power excess',d=>d.proposal.storagePowerKw='4.000001','STORAGE_POWER_LIMIT'],
 ['charge power excess',d=>d.proposal.storagePowerKw='-4.000001','STORAGE_POWER_LIMIT'],
 ['step change excess',d=>d.state.previousStorageKw='-2','POWER_STEP_LIMIT'],
 ['interval excess',d=>d.proposal.intervalHours='0.5','INTERVAL_LIMIT'],
 ['critical shedding',d=>d.proposal.criticalServedKw='1','CRITICAL_LOAD_NOT_PRESERVED'],
 ['invented critical service',d=>d.proposal.criticalServedKw='3','CRITICAL_LOAD_NOT_PRESERVED'],
 ['below generic critical demand',d=>{d.state.criticalDemandKw='1';d.proposal.criticalServedKw='1';},'CRITICAL_LOAD_NOT_PRESERVED'],
 ['import excess',d=>d.state.otherDemandKw='8','IMPORT_LIMIT'],
 ['export excess',d=>d.state.pvGenerationKw='5','EXPORT_LIMIT'],
 ['wrong target',d=>d.proposal.storageAssetId='fixture.battery-pack','WRONG_STORAGE_TARGET'],
 ['stale state revision',d=>d.proposal.stateRevision='old','REVISION_BINDING_MISMATCH'],
 ['stale topology revision',d=>d.proposal.topologyRevision='old','REVISION_BINDING_MISMATCH'],
 ['stale profile revision',d=>d.proposal.profileSHA256='0'.repeat(64),'REVISION_BINDING_MISMATCH'],
 ['expired proposal',d=>d.proposal.expiresAt=d.evaluationAt,'PROPOSAL_NOT_CURRENT'],
 ['future proposal',d=>d.proposal.issuedAt='2026-01-01T00:30:01.500Z','PROPOSAL_NOT_CURRENT'],
 ['proposal before state receipt',d=>d.proposal.issuedAt='2026-01-01T00:30:00.050Z','PROPOSAL_PREDATES_STATE_RECEIPT'],
 ['stale state',d=>d.state.observedAt='2026-01-01T00:29:58.999Z','STALE_STATE'],
 ['unknown state',d=>{d.state.quality='UNKNOWN';d.state.storedEnergyKWh=null;},'STATE_QUALITY_NOT_GOOD'],
 ['bad state',d=>d.state.quality='BAD','STATE_QUALITY_NOT_GOOD'],
 ['grid outage',d=>d.state.gridAvailable=false,'UNSUPPORTED_GRID_MODE'],
 ['open PCC',d=>d.state.pcc='OPEN','UNSUPPORTED_GRID_MODE'],
 ['island mode',d=>d.state.mode='ISLANDED','UNSUPPORTED_GRID_MODE'],
 ['blocked protection',d=>d.state.protectiveInterlocks='BLOCKED','PROTECTION_NOT_HEALTHY'],
 ['unknown protection',d=>d.state.protectiveInterlocks='UNKNOWN','PROTECTION_NOT_HEALTHY'],
 ['blocked risk',d=>d.state.riskDisposition='BLOCKED','RISK_NOT_CLEAR'],
 ['unknown risk',d=>d.state.riskDisposition='UNKNOWN','RISK_NOT_CLEAR']
])test('excludes '+name,()=>{const d=fresh();mutate(d);const r=screenStorageProposal(d);assert.equal(r.eligibleForFurtherSimulation,false);assert.ok(r.reasons.includes(reason));denied(r);});
test('unknown and stale state produce no numeric fallback',()=>{
 for(const mutate of [d=>{d.state.quality='UNKNOWN';d.state.storedEnergyKWh=null;},d=>d.state.observedAt='2026-01-01T00:00:00.000Z']){const d=fresh();mutate(d);const r=screenStorageProposal(d);assert.equal(r.calculations,null);denied(r);}
});
test('freshness includes the exact generic limit',()=>{const d=fresh();d.state.observedAt='2026-01-01T00:29:59.000Z';assert.equal(screenStorageProposal(d).eligibleForFurtherSimulation,true);});
const invalid=[
 ['projection traversal',d=>d.sourceProjection='/etc/passwd'],['projection hash drift',d=>d.sourceProjectionSHA256='0'.repeat(64)],
 ['profile traversal',d=>d.profilePath='/etc/passwd'],['profile hash drift',d=>d.profileSHA256='0'.repeat(64)],
 ['wrong source primary',d=>d.storageAssetId='fixture.battery-pack'],['wrong scenario',d=>d.referenceScenarioId='REF02_ISLAND_RESTORE'],
 ['wrong units',d=>d.proposal.powerUnit='W'],['model approval injection',d=>d.proposal.operatingApproval='invented'],['priority override',d=>d.proposal.force=true],
 ['role escalation',d=>d.proposal.origin='OPERATOR'],['GOOD missing energy',d=>d.state.storedEnergyKWh=null],
 ['negative critical demand',d=>d.state.criticalDemandKw='-1'],['numeric power',d=>d.proposal.storagePowerKw=2],['nonfinite power',d=>d.proposal.storagePowerKw='NaN'],
 ['scientific encoding',d=>d.proposal.storagePowerKw='2e0'],['excess precision',d=>d.proposal.storagePowerKw='0.0000001'],['oversized decimal',d=>d.proposal.storagePowerKw='9'.repeat(65)],
 ['zero interval',d=>d.proposal.intervalHours='0'],['impossible carbon claim',d=>d.proposal.claimedCarbonReductionPercent='101'],
 ['invalid calendar date',d=>d.evaluationAt='2026-02-30T00:30:01Z'],['receipt in future',d=>d.state.receivedAt='2026-01-01T00:30:02Z'],['receipt before observation',d=>d.state.receivedAt='2026-01-01T00:29:59Z'],
 ['invalid expiry window',d=>d.proposal.expiresAt=d.proposal.issuedAt],['invented engineering approval',d=>d.engineeringReview='APPROVED'],['control enable',d=>d.controlAction='ALLOW'],['case execution claim',d=>d.behavioralCasesRun=1]
];
for(const [name,mutate] of invalid)test('rejects '+name,()=>{const d=fresh();mutate(d);assert.throws(()=>screenStorageProposal(d));});
test('profile tampering and engineering approval claims fail closed',t=>{
 const root=mkdtempSync(join(tmpdir(),'energy-screen-'));t.after(()=>rmSync(root,{recursive:true,force:true}));
 for(const folder of ['assets','examples'])cpSync(new URL('../'+folder,import.meta.url),join(root,folder),{recursive:true});
 mkdirSync(join(root,'acceptance'));copyFileSync(new URL('../acceptance/cases.json',import.meta.url),join(root,'acceptance/cases.json'));
 const path=join(root,'assets/generic-storage-screen-profile.json'),p=JSON.parse(readFileSync(path,'utf8'));p.status='ENGINEERING_APPROVED';writeFileSync(path,JSON.stringify(p));
 assert.throws(()=>screenStorageProposal(fixture,root),/profile hash/);
 const d=fresh();d.profileSHA256=createHash('sha256').update(readFileSync(path)).digest('hex');d.proposal.profileSHA256=d.profileSHA256;assert.throws(()=>screenStorageProposal(d,root),/generic screen profile/);
});
