import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {StorageComponentSimulator} from './simulate_storage_component.mjs';
import {StorageExecutionJournal} from './storage_execution_journal.mjs';
import {runAssessedRiskScenario} from './run_assessed_risk_scenario.mjs';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
function fixture(){const x=JSON.parse(readFileSync(resolve(root,'assets/risk-assessment-fixture.json')));x.context.topologyRevision='sim.connected.1';x.previousContext.topologyRevision='sim.connected.1';return x;}
const unchangedElectrical=(a,b)=>{
 for(const k of ['storedEnergyKWh','blockHex','observedAt','power','energy','faults'])assert.deepEqual(b[k],a[k],k);
};
test('fresh affected finding blocks simulation without changing electrical state',()=>{
 const s=new StorageComponentSimulator(),before=s.observe(),x=fixture();x.feed.complete=true;x.findings[0].applicability='AFFECTED';
 const r=s.applyRiskAssessment(x);assert.equal(r.assessment.findings[0].usable,true);assert.equal(r.riskDisposition,'BLOCKED');unchangedElectrical(before,s.observe());
 const held=s.step({id:'blocked','storagePowerKw':'2'});assert.equal(held.applied,false);assert.equal(held.meterInterval,null);assert.equal(held.screen.calculations,null);assert.ok(held.screen.reasons.includes('RISK_NOT_CLEAR'));unchangedElectrical(before,s.observe());
 assert.equal(r.controlAction,'DENY');assert.equal(r.assessment.operatingAuthorityGranted,false);
});
for(const mode of ['unknown','empty','not-affected','bad-feed','context-change'])test(`${mode} yields UNKNOWN and holds without clearance`,()=>{
 const s=new StorageComponentSimulator(),before=s.observe(),x=fixture();
 if(mode==='empty')x.findings=[];
 if(mode==='not-affected')x.findings[0].applicability='NOT_AFFECTED';
 if(mode==='bad-feed')x.feed.quality='BAD';
 if(mode==='context-change')x.context.credentialRevision='synthetic.rotated';
 const r=s.applyRiskAssessment(x);assert.equal(r.riskDisposition,'UNKNOWN');assert.equal(r.assessment.clearanceSupported,false);unchangedElectrical(before,s.observe());assert.equal(s.step({id:'hold',storagePowerKw:'0'}).applied,false);
});
test('a blocked posture cannot be downgraded by later not-affected assertion or unknown fault',()=>{
 const s=new StorageComponentSimulator(),x=fixture();x.findings[0].applicability='AFFECTED';s.applyRiskAssessment(x);
 const next=fixture();next.priorRiskDisposition='BLOCKED';next.findings[0].applicability='NOT_AFFECTED';
 assert.equal(s.applyRiskAssessment(next).riskDisposition,'BLOCKED');assert.equal(s.injectFault('RISK_UNKNOWN').riskDisposition,'BLOCKED');
});
for(const [label,mutate] of [
 ['wrong clock',x=>x.evaluationAt='2026-11-25T00:15:01.000Z'],
 ['wrong topology',x=>x.context.topologyRevision='other.topology'],
 ['wrong mode',x=>x.context.electricalMode='RECOVERY'],
 ['wrong prior',x=>x.priorRiskDisposition='BLOCKED'],
 ['wrong projection',x=>x.sourceProjection='assets/function-bindings/generic.json'],
 ['wrong source hash',x=>x.sourceProjectionSHA256='0'.repeat(64)],
 ['false authority',x=>x.controlAction='ALLOW'],
 ['finding count',x=>x.findings=Array(17).fill(x.findings[0])],
 ['oversized finding id',x=>x.findings[0].id='x'.repeat(81)],
 ['oversized input',x=>x.extra='x'.repeat(16385)]
])test(`invalid ${label} cannot mutate simulation`,()=>{
 const s=new StorageComponentSimulator(),before=s.observe(),x=fixture();mutate(x);assert.throws(()=>s.applyRiskAssessment(x));assert.deepEqual(s.observe(),before);
});
test('journal reconstructs assessed block, held request and original denied replay',()=>{
 const j=new StorageExecutionJournal('risk.restore'),x=fixture();x.findings[0].applicability='AFFECTED';j.applyRiskAssessment(x);const held=j.step({id:'held',storagePowerKw:'2'});
 assert.equal(j.export().events[0].operation,'RISK_ASSESSMENT');const r=StorageExecutionJournal.restore(j.export());assert.deepEqual(r.observe(),j.observe());const replay=r.step({id:'held',storagePowerKw:'2'});assert.equal(replay.replayed,true);assert.equal(replay.applied,false);assert.deepEqual(replay.meterInterval,held.meterInterval);
 assert.equal(r.step({id:'new',storagePowerKw:'0'}).applied,false);
});
test('invalid assessed risk does not append to journal',()=>{
 const j=new StorageExecutionJournal('risk.invalid'),before=j.export(),x=fixture();x.context.topologyRevision='other';assert.throws(()=>j.applyRiskAssessment(x));assert.deepEqual(j.export(),before);
});
test('stale risk evidence after an applied interval holds rather than clears',()=>{
 const s=new StorageComponentSimulator();s.step({id:'advance',storagePowerKw:'0'});const x=fixture();x.evaluationAt='2026-11-25T00:15:01.000Z';x.findings[0].applicability='AFFECTED';const r=s.applyRiskAssessment(x);assert.equal(r.riskDisposition,'UNKNOWN');assert.ok(r.assessment.reasons.includes('THREAT_FEED_UNUSABLE_OR_STALE'));assert.equal(s.step({id:'after-stale',storagePowerKw:'0'}).applied,false);
});
test('risk scenario composes assessor, hold and reconstruction deterministically',()=>{
 const a=runAssessedRiskScenario();assert.deepEqual(a,runAssessedRiskScenario());assert.equal(a.risk.riskDisposition,'BLOCKED');assert.equal(a.held.applied,false);assert.equal(a.reconstructedObservation.riskDisposition,'BLOCKED');assert.equal(a.behavioralCasesRun,0);
});
