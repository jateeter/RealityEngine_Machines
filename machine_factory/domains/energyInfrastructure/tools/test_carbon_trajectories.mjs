import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {evaluateCarbonTrajectories,trajectoryDigest} from './evaluate_carbon_trajectories.mjs';
const fixture=JSON.parse(readFileSync(new URL('../assets/carbon-trajectories.json',import.meta.url),'utf8'));
const fresh=()=>structuredClone(fixture),f=n=>({numerator:n,denominator:'1'});
const seal=r=>{r.snapshotDigest=trajectoryDigest(r.ledger);};
test('canonical object key order matches an independent SHA-256 vector',()=>{
 assert.equal(trajectoryDigest({b:2,a:1}),'43258cff783fe7036d8a43033f830adfc60ec037382473548ac742b888292777');assert.equal(trajectoryDigest({b:2,a:1}),trajectoryDigest({a:1,b:2}));
});
test('correction changes reporting without rewriting original decision reference',()=>{
 const r=evaluateCarbonTrajectories(fixture);assert.deepEqual(r.observedRevisions[0].intensityGCO2ePerKWh,f('325'));assert.deepEqual(r.observedRevisions[1].intensityGCO2ePerKWh,f('350'));assert.deepEqual(r.observedRevisions[1].allocatedEmissionsGCO2e,f('1750'));assert.deepEqual(r.decisionReferences[0].intensityGCO2ePerKWh,f('325'));assert.equal(r.decisionReferences[0].actionExecuted,false);assert.equal(r.seriesCombined,false);assert.equal(r.targetAdopted,false);assert.equal(r.draftTargets[0].usableForControl,false);assert.equal(r.forecasts[0].series,'SYNTHETIC_FORECAST_NOT_OBSERVATION');
});
test('unknown correction remains unknown without erasing the original',()=>{
 const d=fresh(),r=d.observedRevisions[1];r.ledger.rows[0].factor.quality='UNKNOWN';r.ledger.rows[0].factor.intensity=null;seal(r);
 const out=evaluateCarbonTrajectories(d);assert.equal(out.observedRevisions[1].eligible,false);assert.equal(out.observedRevisions[1].intensityGCO2ePerKWh,null);assert.equal(out.observedRevisions[1].intensityStatus,'UNKNOWN_INPUT');assert.deepEqual(out.decisionReferences[0].intensityGCO2ePerKWh,f('325'));
});
test('unknown forecast is null, not zero or an observation',()=>{
 const d=fresh();d.forecasts[0].quality='UNKNOWN';d.forecasts[0].intensity=null;const r=evaluateCarbonTrajectories(d);assert.equal(r.forecasts[0].eligible,false);assert.equal(r.forecasts[0].intensity,null);assert.deepEqual(r.observedRevisions[0].intensityGCO2ePerKWh,f('325'));
});
test('observations-only archive needs no invented forecast, target or decision',()=>{
 const d=fresh();d.forecasts=[];d.draftTargets=[];d.decisionReferences=[];const r=evaluateCarbonTrajectories(d);assert.equal(r.observedRevisions.length,2);assert.deepEqual(r.draftTargets,[]);
});
test('known zero forecast is distinct from missing data',()=>{
 const d=fresh();d.forecasts[0].intensity='0';assert.equal(evaluateCarbonTrajectories(d).forecasts[0].intensity,'0');
});
test('corrections flag dependent accounting for requalification',()=>{
 assert.equal(evaluateCarbonTrajectories(fixture).dependentAccountingRequalificationRequired,true);
 const d=fresh();d.observedRevisions=d.observedRevisions.slice(0,1);assert.equal(evaluateCarbonTrajectories(d).dependentAccountingRequalificationRequired,false);
});
test('long-delayed correction remains unknown under current freshness policy',()=>{
 const d=fresh(),r=d.observedRevisions[1];d.evaluationAt='2026-01-01T02:05:00.000Z';r.ledger.evaluationAt='2026-01-01T02:00:01.000Z';
 for(const row of r.ledger.rows){row.meterInterval.evaluationAt=r.ledger.evaluationAt;row.factor.revision='fixture-v2';row.factor.issuedAt='2026-01-01T02:00:00.000Z';row.factor.validUntil='2026-01-01T03:00:00.000Z';}seal(r);
 const out=evaluateCarbonTrajectories(d);assert.equal(out.observedRevisions[1].eligible,false);assert.equal(out.observedRevisions[1].intensityGCO2ePerKWh,null);assert.deepEqual(out.decisionReferences[0].intensityGCO2ePerKWh,f('325'));
});
const bad=[
 ['unallowlisted source',d=>d.sourceLedger='/etc/passwd'],['source hash',d=>d.sourceLedgerSHA256='0'.repeat(64)],
 ['missing observation baseline',d=>d.observedRevisions=[]],['corrupt digest',d=>d.observedRevisions[1].snapshotDigest='0'.repeat(64)],
 ['broken parent',d=>d.observedRevisions[1].parentSnapshotDigest='0'.repeat(64)],['parent on baseline',d=>d.observedRevisions[0].parentSnapshotDigest='0'.repeat(64)],
 ['revision reordering',d=>d.observedRevisions.reverse()],['duplicate identity',d=>d.forecasts[0].id=d.observedRevisions[0].id],
 ['rewritten baseline with recomputed digest',d=>{const r=d.observedRevisions[0];r.ledger.rows[0].factor.intensity='200';seal(r);}],
 ['factor changed without new label',d=>{const r=d.observedRevisions[1];r.ledger.rows[0].factor.revision='fixture-v1';seal(r);}],
 ['revised meter evidence',d=>{const r=d.observedRevisions[1],i=r.ledger.rows[1].meterInterval,b=Buffer.from(i.end.blockHex,'hex');b.writeUInt32BE(155000,92);i.end.blockHex=b.toString('hex');seal(r);}],
 ['revision unavailable at archive time',d=>d.evaluationAt='2026-01-01T00:35:00.000Z'],
 ['decision points to future correction',d=>d.decisionReferences[0].observedSnapshotDigest=d.observedRevisions[1].snapshotDigest],
 ['decision points to forecast',d=>d.decisionReferences[0].observedSnapshotDigest=d.forecasts[0].id],
 ['decision points to target',d=>d.decisionReferences[0].observedSnapshotDigest=d.draftTargets[0].id],
 ['fabricated executed action',d=>d.decisionReferences[0].actionExecuted=true],['decision enables control',d=>d.decisionReferences[0].controlAction='ALLOW'],
 ['forecast relabeled observation',d=>d.forecasts[0].sourceType='OBSERVED'],['forecast basis relabeled observation',d=>d.forecasts[0].basis.dataRole='SYNTHETIC_OBSERVATION'],
 ['forecast vintage after interval begins',d=>d.forecasts[0].issuedAt='2026-01-01T00:30:01.000Z'],['forecast inverted window',d=>d.forecasts[0].intervalEnd=d.forecasts[0].intervalStart],
 ['forecast wrong units',d=>d.forecasts[0].basis.factorUnit='kgCO2e/kWh'],['forecast nonfinite value',d=>d.forecasts[0].intensity='NaN'],
 ['target adopted by fixture',d=>d.draftTargets[0].status='APPROVED'],['invented target owner',d=>d.draftTargets[0].owner='invented owner'],['invented target approval',d=>d.draftTargets[0].approvalReceipt='fake'],
 ['target wrong basis',d=>d.draftTargets[0].basis.signalType='MARGINAL'],['target undefined baseline',d=>d.draftTargets[0].baselineSnapshotDigest='0'.repeat(64)],
 ['target future baseline',d=>d.draftTargets[0].baselineSnapshotDigest=d.observedRevisions[1].snapshotDigest],['target inverted period',d=>d.draftTargets[0].intervalEnd=d.draftTargets[0].intervalStart],
 ['negative target',d=>d.draftTargets[0].intensity='-1'],['numeric target',d=>d.draftTargets[0].intensity=300],
 ['invalid date',d=>d.evaluationAt='2026-02-30T00:45:00Z'],['non-UTC date',d=>d.evaluationAt='2026-01-01T00:45:01+01:00'],
 ['control claim',d=>d.controlAction='ALLOW'],['case execution claim',d=>d.behavioralCasesRun=1],['review claim',d=>d.engineeringReview='APPROVED']
];
for(const [name,mutate] of bad)test('rejects '+name,()=>{const d=fresh();mutate(d);assert.throws(()=>evaluateCarbonTrajectories(d));});
test('unchanged factor content cannot be presented as a new reporting revision',()=>{
 const d=fresh(),r=d.observedRevisions[1];r.ledger.rows[0].factor=structuredClone(d.observedRevisions[0].ledger.rows[0].factor);seal(r);assert.throws(()=>evaluateCarbonTrajectories(d),/Empty reporting revision/);
});
test('old source revision label cannot be reused for different content',()=>{
 const d=fresh(),r=structuredClone(d.observedRevisions[1]);r.id='report.v3';r.parentSnapshotDigest=d.observedRevisions[1].snapshotDigest;r.ledger.evaluationAt='2026-01-01T00:42:01.000Z';for(const row of r.ledger.rows)row.meterInterval.evaluationAt=r.ledger.evaluationAt;r.ledger.rows[0].factor.revision='fixture-v1';r.ledger.rows[0].factor.intensity='250';r.ledger.rows[0].factor.issuedAt='2026-01-01T00:42:00.000Z';seal(r);d.observedRevisions.push(r);assert.throws(()=>evaluateCarbonTrajectories(d),/label reused/);
});
