import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {StorageExecutionJournal} from './storage_execution_journal.mjs';
import {runObservationAgeScenario} from './run_observation_age_scenario.mjs';
import {buildJournalStorageScenario} from './run_journal_storage_scenario.mjs';
import {evaluateJournalStorage} from './evaluate_journal_storage.mjs';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const bound=(j,id,power='0')=>({id,storagePowerKw:power,expectedStateSHA256:j.stateToken().expectedStateSHA256});
test('initial source age and clocks are explicit',()=>{
 const s=new StorageExecutionJournal('age.initial'),o=s.observe();assert.equal(o.stateAgeMs,1000);assert.equal(o.stateFresh,true);assert.equal(o.observedAt,'2026-11-25T00:00:00.000Z');assert.equal(o.receivedAt,'2026-11-25T00:00:00.100Z');assert.equal(o.evaluationAt,'2026-11-25T00:00:01.000Z');assert.deepEqual(o.dataExclusionReasons,[]);
});
test('freshness boundary is inclusive and new interval retains acquisition evaluation delay',()=>{
 const s=new StorageExecutionJournal('age.boundary');s.advanceEvaluationClock(1000);assert.equal(s.observe().stateAgeMs,2000);assert.equal(s.observe().stateFresh,true);const r=s.step(bound(s,'at-limit'));assert.equal(r.applied,true);assert.equal(r.meterInterval.input.evaluationAt,'2026-11-25T00:15:02.000Z');assert.equal(r.meterInterval.result.eligible,true);
});
test('one millisecond beyond the age limit excludes data and holds even a matching snapshot',()=>{
 const s=new StorageExecutionJournal('age.stale'),before=s.observe(),r=s.advanceEvaluationClock(1001),o=s.observe();assert.equal(r.plantClockAdvanced,false);assert.equal(o.observedAt,before.observedAt);assert.equal(o.receivedAt,before.receivedAt);assert.equal(o.evaluationAt,'2026-11-25T00:00:02.001Z');assert.equal(o.stateAgeMs,2001);assert.equal(o.stateFresh,false);assert.equal(o.storedEnergyKWh,null);assert.equal(o.power.rawValue,null);assert.equal(o.energy.rawImported,null);assert.ok(o.dataExclusionReasons.includes('STALE_STATE'));
 const held=s.step(bound(s,'stale'));assert.equal(held.stateBinding.matched,true);assert.equal(held.applied,false);assert.equal(held.screen.calculations,null);assert.ok(held.screen.reasons.includes('STALE_STATE'));assert.equal(held.meterInterval,null);assert.deepEqual(s.observe(),o);
});
test('evaluation clock advance invalidates an earlier snapshot without plant evolution',()=>{
 const s=new StorageExecutionJournal('age.pin'),request=bound(s,'old'),before=s.observe();s.advanceEvaluationClock(1);const after=s.observe();assert.equal(after.storedEnergyKWh,before.storedEnergyKWh);assert.equal(after.blockHex,before.blockHex);assert.equal(after.observedAt,before.observedAt);assert.equal(s.step(request).stateBinding.matched,false);
});
for(const delta of [0,-1,0.5,NaN,Infinity,'1',null,3600001])test(`reject invalid clock delta ${String(delta)}`,()=>{
 const s=new StorageExecutionJournal('age.invalid'),before=s.export(),o=s.observe();assert.throws(()=>s.advanceEvaluationClock(delta));assert.deepEqual(s.export(),before);assert.deepEqual(s.observe(),o);
});
test('cumulative clock horizon is bounded with no backward reset',()=>{
 const s=new StorageExecutionJournal('age.cap');s.advanceEvaluationClock(3600000);const before=s.export();assert.throws(()=>s.advanceEvaluationClock(1));assert.deepEqual(s.export(),before);assert.equal(s.observe().stateFresh,false);
});
test('telemetry failure and expiry have distinct exclusion reasons',()=>{
 const s=new StorageExecutionJournal('age.fault');s.injectFault('TELEMETRY_UNKNOWN');assert.equal(s.observe().stateFresh,true);s.advanceEvaluationClock(1001);assert.deepEqual(s.observe().dataExclusionReasons,['STALE_STATE','TELEMETRY_UNKNOWN']);assert.equal(s.observe().power.quality,'UNKNOWN');
});
test('risk assessment must bind the advanced evaluation clock',()=>{
 const s=new StorageExecutionJournal('age.risk');s.advanceEvaluationClock(500);const x=JSON.parse(readFileSync(resolve(root,'assets/risk-assessment-fixture.json')));x.context.topologyRevision='sim.connected.1';x.previousContext.topologyRevision='sim.connected.1';const before=s.export();assert.throws(()=>s.applyRiskAssessment(x),/clock/);assert.deepEqual(s.export(),before);x.evaluationAt='2026-11-25T00:00:01.500Z';assert.equal(s.applyRiskAssessment(x).riskDisposition,'UNKNOWN');
});
test('journal reconstruction preserves expiry and cannot restore freshness',()=>{
 const a=runObservationAgeScenario(),r=StorageExecutionJournal.restore(a.journal);assert.deepEqual(r.observe(),a.reconstructedObservation);assert.equal(r.observe().stateFresh,false);assert.equal(r.step(bound(r,'still-stale')).applied,false);assert.equal(r.step(a.journal.events[2].payload).replayed,true);
});
test('historical accepted replay after expiry does not execute or refresh the observation',()=>{
 const s=new StorageExecutionJournal('age.replay'),request=bound(s,'before','2');s.step(request);s.advanceEvaluationClock(1001);const before=s.observe(),r=s.step(request);assert.equal(r.applied,true);assert.equal(r.replayed,true);assert.equal(r.controlAction,'DENY');assert.deepEqual(s.observe(),before);assert.equal(s.observe().storedEnergyKWh,null);
});
test('historical carbon/storage accounting excludes clock/held events and preserves current unknown',()=>{
 const a=runObservationAgeScenario(),x=buildJournalStorageScenario();x.carbonLedger.journal=a.journal;x.carbonLedger.evaluationAt='2026-11-25T00:15:02.001Z';const e=a.journal.events[0];x.carbonLedger.factors=[{eventSHA256:e.eventSHA256,factor:{...structuredClone(x.carbonLedger.factors[0].factor),intervalStart:e.receipt.meterInterval.input.start.observedAt,intervalEnd:e.receipt.meterInterval.input.end.observedAt,issuedAt:x.carbonLedger.evaluationAt}}];
 const r=evaluateJournalStorage(x);assert.equal(r.steps.length,1);assert.equal(r.energyAllocationConserved,true);assert.deepEqual(r.lastAppliedStoredKWh,{numerator:'35',denominator:'8'});assert.equal(r.currentObservedStoredKWh,null);assert.equal(r.currentObservationQuality,'UNKNOWN');assert.deepEqual(r.sourceImportAccounting.importedKWh,{numerator:'0',denominator:'1'});assert.equal(r.sourceImportAccounting.intensityGCO2ePerKWh,null);
});
test('source-bound clock records reject tampering and unsupported resets',()=>{
 const x=runObservationAgeScenario().journal;x.events[1].payload=-1;assert.throws(()=>StorageExecutionJournal.restore(x));x.events[1].operation='EVALUATION_CLOCK_RESET';assert.throws(()=>StorageExecutionJournal.restore(x));
});
test('clock events remain subject to the journal event bound before mutation',()=>{
 const s=new StorageExecutionJournal('age.events');for(let i=0;i<128;i++)s.advanceEvaluationClock(1);const before=s.observe();assert.throws(()=>s.advanceEvaluationClock(1),/event limit/);assert.deepEqual(s.observe(),before);
});
