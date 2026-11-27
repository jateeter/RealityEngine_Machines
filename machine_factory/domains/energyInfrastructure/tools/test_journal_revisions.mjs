import test from 'node:test';
import assert from 'node:assert/strict';
import {trajectoryDigest} from './evaluate_carbon_trajectories.mjs';
import {journalRevisionDigest,evaluateJournalRevisions} from './evaluate_journal_revisions.mjs';
import {buildJournalRevisionScenario} from './run_journal_revision_scenario.mjs';
const f=(n,d='1')=>({numerator:n,denominator:d});
const rehash=x=>{for(const r of x.revisions)r.revisionDigest=journalRevisionDigest(x.baselineLedgerDigest,r);};
test('factor correction recomputes import and charge attribution without changing meter/storage energy',()=>{
 const x=buildJournalRevisionScenario();x.asOf=x.evaluationAt;const r=evaluateJournalRevisions(x),[a,b]=r.snapshots;
 assert.deepEqual(a.allocatedEmissionsGCO2e,f('500'));assert.deepEqual(b.allocatedEmissionsGCO2e,f('400'));
 assert.deepEqual(a.intensityGCO2ePerKWh,f('1000','3'));assert.deepEqual(b.intensityGCO2ePerKWh,f('800','3'));
 assert.deepEqual(a.newChargeAllocatedGCO2e,f('200'));assert.deepEqual(b.newChargeAllocatedGCO2e,f('150'));assert.deepEqual(a.lastAppliedStoredKWh,b.lastAppliedStoredKWh);assert.deepEqual(b.lastAppliedStoredKWh,f('193','40'));
 for(const s of r.snapshots){assert.equal(s.energyAllocationConserved,true);assert.equal(s.deliveredAllocatedGCO2e,null);assert.equal(s.remainingCarriedGCO2e,null);assert.equal(s.storageCarbonStatus,'UNKNOWN_OPENING_INVENTORY');}
 assert.equal(r.storageRecomputedForEveryRevision,true);assert.equal(r.meterHistoryChanged,false);assert.equal(r.historyAuthenticated,false);assert.equal(r.controlAction,'DENY');assert.equal(r.behavioralCasesRun,0);
});
test('as-of selection returns no later correction quantities',()=>{
 const x=buildJournalRevisionScenario(),r=evaluateJournalRevisions(x);assert.equal(r.archiveRevisionCount,2);assert.equal(r.snapshots.length,1);assert.equal(r.selectedRevisionDigest,x.revisions[0].revisionDigest);assert.deepEqual(r.selectedNewChargeAllocatedGCO2e,f('200'));assert.deepEqual(r.selectedImportIntensityGCO2ePerKWh,f('1000','3'));
});
test('as-of exactly at correction selects corrected report',()=>{
 const x=buildJournalRevisionScenario();x.asOf=x.revisions[1].evaluationAt;const r=evaluateJournalRevisions(x);assert.equal(r.selectedRevisionDigest,x.revisions[1].revisionDigest);assert.deepEqual(r.selectedNewChargeAllocatedGCO2e,f('150'));
});
test('as-of before first report returns unavailable, not zero or latest',()=>{
 const x=buildJournalRevisionScenario();x.asOf='2026-11-25T00:45:00.000Z';const r=evaluateJournalRevisions(x);assert.equal(r.snapshots.length,0);assert.equal(r.selectedReportAvailable,false);assert.equal(r.selectedRevisionDigest,null);assert.equal(r.selectedImportIntensityGCO2ePerKWh,null);
});
test('unknown latest correction stays unknown without falling back to eligible prior report',()=>{
 const x=buildJournalRevisionScenario();x.revisions[1].factors[0].factor.intensity=null;rehash(x);x.asOf=x.evaluationAt;
 const r=evaluateJournalRevisions(x);assert.equal(r.selectedRevisionDigest,x.revisions[1].revisionDigest);assert.equal(r.selectedImportIntensityGCO2ePerKWh,null);assert.equal(r.selectedNewChargeAllocatedGCO2e,null);assert.deepEqual(r.snapshots[0].newChargeAllocatedGCO2e,f('200'));assert.equal(r.snapshots[1].importAccountingEligible,false);
});
for(const [name,mutate] of [
 ['baseline digest',x=>x.baselineLedgerDigest='0'.repeat(64)],
 ['baseline factor rewrite',x=>{x.revisions[0].factors[0].factor.intensity='0';rehash(x);}],
 ['snapshot hash',x=>x.revisions[1].revisionDigest='0'.repeat(64)],
 ['parent link',x=>{x.revisions[1].parentRevisionDigest='0'.repeat(64);rehash(x);}],
 ['order',x=>x.revisions.reverse()],
 ['duplicate identity',x=>{x.revisions[1].id=x.revisions[0].id;rehash(x);}],
 ['no factor change',x=>{x.revisions[1].factors=structuredClone(x.revisions[0].factors);rehash(x);}],
 ['reused adjacent factor label',x=>{x.revisions[1].factors[0].factor.revision=x.revisions[0].factors[0].factor.revision;rehash(x);}],
 ['backdated publication',x=>{x.revisions[1].factors[0].factor.issuedAt='2026-11-25T00:45:00.000Z';rehash(x);}],
 ['meter event replacement',x=>{x.revisions[1].factors[0].eventSHA256='0'.repeat(64);rehash(x);}],
 ['missing factor',x=>{x.revisions[1].factors.pop();rehash(x);}],
 ['new meter journal in revision',x=>{x.revisions[1].journal=structuredClone(x.baselineLedger.journal);rehash(x);}],
 ['future correction',x=>{x.revisions[1].evaluationAt='2026-11-25T00:45:21.000Z';rehash(x);}],
 ['as-of beyond evaluation',x=>x.asOf='2026-11-25T00:45:21.000Z'],
 ['too many revisions',x=>x.revisions=Array(11).fill(x.revisions[0])],
 ['forecast mixing',x=>x.forecasts=[]],
 ['target adoption',x=>x.targetAdopted=true],
 ['authority',x=>x.controlAction='ALLOW'],
 ['false acceptance claim',x=>x.behavioralCasesRun=43]
])test(`reject ${name}`,()=>{const x=buildJournalRevisionScenario();mutate(x);assert.throws(()=>evaluateJournalRevisions(x));});
test('nonadjacent reuse of an old revision label with different content is rejected',()=>{
 const x=buildJournalRevisionScenario(),third=structuredClone(x.revisions[1]);third.id='third';third.parentRevisionDigest=x.revisions[1].revisionDigest;third.evaluationAt='2026-11-25T00:45:16.000Z';Object.assign(third.factors[0].factor,{revision:x.revisions[0].factors[0].factor.revision,intensity:'250',issuedAt:'2026-11-25T00:45:15.000Z'});third.revisionDigest=journalRevisionDigest(x.baselineLedgerDigest,third);x.revisions.push(third);assert.throws(()=>evaluateJournalRevisions(x),/label reused/);
});
test('source journal tampering cannot be made valid by rehashing the baseline archive',()=>{
 const x=buildJournalRevisionScenario();x.baselineLedger.journal.events[0].receipt.observation.storedEnergyKWh='0';x.baselineLedgerDigest=trajectoryDigest(x.baselineLedger);rehash(x);assert.throws(()=>evaluateJournalRevisions(x));
});
test('evaluation preserves all original reporting and meter evidence',()=>{
 const x=buildJournalRevisionScenario(),before=structuredClone(x);evaluateJournalRevisions(x);assert.deepEqual(x,before);
});
