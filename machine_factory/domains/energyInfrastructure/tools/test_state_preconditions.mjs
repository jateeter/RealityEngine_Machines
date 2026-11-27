import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,mkdtempSync,cpSync,appendFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {StorageComponentSimulator} from './simulate_storage_component.mjs';
import {StorageExecutionJournal} from './storage_execution_journal.mjs';
import {runStatePreconditionScenario} from './run_state_precondition_scenario.mjs';
import {buildJournalStorageScenario} from './run_journal_storage_scenario.mjs';
import {evaluateJournalStorage} from './evaluate_journal_storage.mjs';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const bound=(s,id,power='0')=>({id,storagePowerKw:power,expectedStateSHA256:s.stateToken().expectedStateSHA256});
test('state inspection is stable, run scoped and read-only',()=>{
 const s=new StorageExecutionJournal('precondition.inspect'),before=s.export(),a=s.stateToken();assert.deepEqual(a,s.stateToken());assert.deepEqual(s.export(),before);assert.equal(a.simulationRunId,'precondition.inspect');assert.equal(a.controlAction,'DENY');assert.match(a.expectedStateSHA256,/^[0-9a-f]{64}$/);
});
test('matching precondition advances once and changes the state digest',()=>{
 const s=new StorageExecutionJournal('precondition.fresh'),request=bound(s,'fresh','2'),r=s.step(request);assert.equal(r.applied,true);assert.equal(r.stateBinding.matched,true);assert.equal(r.observation.storedEnergyKWh,'4.375000');assert.notEqual(s.stateToken().expectedStateSHA256,request.expectedStateSHA256);
});
test('two intents prepared from the same state cannot both advance',()=>{
 const s=new StorageExecutionJournal('precondition.race'),a=bound(s,'first','2'),b={...a,id:'second',storagePowerKw:'0'};s.step(a);const before=s.observe(),r=s.step(b);assert.equal(r.applied,false);assert.equal(r.stateBinding.matched,false);assert.ok(r.screen.reasons.includes('EXPECTED_STATE_CHANGED'));assert.equal(r.screen.calculations,null);assert.equal(r.meterInterval,null);assert.deepEqual(s.observe(),before);
});
test('a failed precondition is retained; changed intent needs a new request ID',()=>{
 const s=new StorageExecutionJournal('precondition.retry'),old=bound(s,'stale');s.step(bound(s,'advance','2'));const r=s.step(old),before=s.observe();assert.equal(r.applied,false);assert.equal(s.step(old).replayed,true);assert.deepEqual(s.observe(),before);assert.throws(()=>s.step(bound(s,'stale')),/Conflicting replay/);assert.equal(s.step(bound(s,'new-id')).applied,true);
});
test('accepted historical replay bypasses fresh comparison without re-executing',()=>{
 const s=new StorageExecutionJournal('precondition.replay'),request=bound(s,'original','2');s.step(request);s.step(bound(s,'later'));const before=s.observe(),r=s.step(request);assert.equal(r.replayed,true);assert.equal(r.applied,true);assert.equal(r.controlAction,'DENY');assert.deepEqual(s.observe(),before);
});
for(const firstBound of [true,false])test(`bound/unbound intent cannot reuse one ID (${firstBound})`,()=>{
 const s=new StorageExecutionJournal('precondition.intent'),request=bound(s,'same');s.step(firstBound?request:{id:'same',storagePowerKw:'0'});assert.throws(()=>s.step(firstBound?{id:'same',storagePowerKw:'0'}:bound(s,'same')),/Conflicting replay/);
});
for(const value of [null,0,'','0'.repeat(63),'G'.repeat(64),'0'.repeat(65)])test(`reject malformed digest ${JSON.stringify(value)}`,()=>{
 const s=new StorageExecutionJournal('precondition.invalid'),before=s.export();assert.throws(()=>s.step({id:'bad',storagePowerKw:'0',expectedStateSHA256:value}));assert.deepEqual(s.export(),before);
});
test('a different run label cannot reuse a state token',()=>{
 const a=new StorageExecutionJournal('precondition.A'),b=new StorageExecutionJournal('precondition.B'),request=bound(a,'wrong-run');assert.equal(b.step(request).applied,false);
});
for(const fault of ['TELEMETRY_UNKNOWN','PROTECTION_BLOCKED','RISK_UNKNOWN'])test(`${fault} invalidates a snapshot and still holds a fresh one`,()=>{
 const s=new StorageExecutionJournal('precondition.fault'),request=bound(s,'old');s.injectFault(fault);const before=s.observe(),r=s.step(request);assert.equal(r.applied,false);assert.equal(r.stateBinding.matched,false);assert.deepEqual(s.observe(),before);const fresh=s.step(bound(s,'fresh'));assert.equal(fresh.stateBinding.matched,true);assert.equal(fresh.applied,false);assert.equal(fresh.meterInterval,null);
});
test('source-bound assessed risk change invalidates a previously captured state',()=>{
 const s=new StorageExecutionJournal('precondition.risk'),request=bound(s,'before-risk'),risk=JSON.parse(readFileSync(resolve(root,'assets/risk-assessment-fixture.json')));risk.context.topologyRevision='sim.connected.1';risk.previousContext.topologyRevision='sim.connected.1';risk.findings[0].applicability='AFFECTED';s.applyRiskAssessment(risk);assert.equal(s.step(request).stateBinding.matched,false);const fresh=s.step(bound(s,'after-risk'));assert.equal(fresh.stateBinding.matched,true);assert.equal(fresh.applied,false);
});
test('reconstruction preserves state tokens and stale request decisions',()=>{
 const a=runStatePreconditionScenario(),s=StorageExecutionJournal.restore(a.journal);assert.deepEqual(s.observe(),a.reconstructedObservation);assert.equal(s.step(a.journal.events[1].payload).replayed,true);assert.equal(s.step(a.journal.events[1].payload).applied,false);assert.equal(s.step(bound(s,'continue')).applied,true);
});
test('conditional steps feed existing carbon/storage accounting without counting rejected intents',()=>{
 const a=runStatePreconditionScenario(),x=buildJournalStorageScenario();x.carbonLedger.journal=a.journal;x.carbonLedger.evaluationAt='2026-11-25T00:30:01.000Z';
 const events=a.journal.events.filter(e=>e.receipt.applied&&!e.receipt.replayed);
 x.carbonLedger.factors=events.map((e,i)=>({eventSHA256:e.eventSHA256,factor:{...structuredClone(x.carbonLedger.factors[i].factor),intervalStart:e.receipt.meterInterval.input.start.observedAt,intervalEnd:e.receipt.meterInterval.input.end.observedAt,issuedAt:x.carbonLedger.evaluationAt}}));
 const r=evaluateJournalStorage(x);assert.equal(r.steps.length,2);assert.equal(r.energyAllocationConserved,true);assert.deepEqual(r.lastAppliedStoredKWh,{numerator:'35',denominator:'8'});assert.deepEqual(r.sourceImportAccounting.importedKWh,{numerator:'1',denominator:'2'});assert.equal(r.deliveredAllocatedGCO2e,null);
});
test('sealed manifest change invalidates standalone precondition and journal source context',()=>{
 const temp=mkdtempSync(resolve(tmpdir(),'energy-precondition-'));try{
  const copy=resolve(temp,'package');cpSync(root,copy,{recursive:true});const sim=new StorageComponentSimulator(copy,'manifest.change'),request=bound(sim,'before');const j=new StorageExecutionJournal('manifest.journal',copy),jRequest=bound(j,'before');appendFileSync(resolve(copy,'asset-manifest.json'),'\n');
  const before=sim.observe();assert.equal(sim.step(request).applied,false);assert.deepEqual(sim.observe(),before);const saved=j.export();assert.throws(()=>j.step(jRequest),/source package changed/);assert.deepEqual(j.export(),saved);
 }finally{rmSync(temp,{recursive:true,force:true});}
});
test('unsealed package-byte drift is rejected by journal token acquisition',()=>{
 const temp=mkdtempSync(resolve(tmpdir(),'energy-precondition-drift-'));try{const copy=resolve(temp,'package');cpSync(root,copy,{recursive:true});const j=new StorageExecutionJournal('package.drift',copy),before=j.export();appendFileSync(resolve(copy,'README.md'),'\nchanged');assert.throws(()=>j.stateToken(),/Package source drift/);assert.deepEqual(j.export(),before);}finally{rmSync(temp,{recursive:true,force:true});}
});
