import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {evaluatePowerSnapshot} from './validate_power_snapshot.mjs';
const read=name=>JSON.parse(readFileSync(new URL('../assets/power-snapshots/'+name,import.meta.url),'utf8'));
const fixture=read('generic.json');
const sample=(d,boundary='FACILITY_PCC')=>d.samples.find(s=>s.boundaryId===boundary);
test('storage discharge uses its separate inactive Generator projection',()=>{
 const d=structuredClone(fixture),s=sample(d,'STORAGE_AC');
 const p=JSON.parse(readFileSync(new URL('../'+d.sourceProjection,import.meta.url),'utf8'));
 s.functionProjectionId=p.bindings.find(b=>b.assetId===s.assetId).functions.find(f=>f.concept==='Generator').projectionId;
 s.positiveDirection='EXPORT';
 const r=evaluatePowerSnapshot(d);assert.deepEqual(r.errors,[]);
 assert.equal(r.observations.find(o=>o.boundaryId==='STORAGE_AC').wattsNetImportPositive,'-1250');
});
for(const name of ['generic.json','ref01_connected.json','ref02_island_restore.json','ref03_flex_ev.json'])test('normalizes source-bound synthetic snapshot '+name,()=>{
 const result=evaluatePowerSnapshot(read(name));assert.deepEqual(result.errors,[]);
 for(const o of result.observations){assert.equal(o.eligible,true);assert.equal(o.wattsNetImportPositive,o.boundaryId==='PV_AC'?'-2500':'1250');}
});
for(const [raw,scale,unit,direction,expected] of [
 [123456,-6,'W','IMPORT','0.123456'],[1,-6,'kW','IMPORT','0.001'],
 [-123,-2,'W','EXPORT','1.23'],[0,-6,'W','EXPORT','0'],
 [9007199254740991,6,'kW','IMPORT','9007199254740991000000000'],
 [25,0,'W','EXPORT','-25']
])test(`exact decimal normalization ${raw}/${scale}/${unit}/${direction}`,()=>{
 const d=structuredClone(fixture);Object.assign(sample(d),{rawValue:raw,scaleExponent:scale,unit,positiveDirection:direction});
 const r=evaluatePowerSnapshot(d);assert.deepEqual(r.errors,[]);assert.equal(r.observations[0].wattsNetImportPositive,expected);
});
for(const quality of ['BAD','UNKNOWN'])test(quality+' is excluded even when a numeric value exists',()=>{
 const d=structuredClone(fixture);sample(d).quality=quality;sample(d).rawValue=0;
 const r=evaluatePowerSnapshot(d);assert.deepEqual(r.errors,[]);assert.equal(r.observations[0].eligible,false);assert.equal(r.observations[0].wattsNetImportPositive,null);assert.deepEqual(r.observations[0].reasons,['QUALITY_'+quality]);
});
test('unknown missing data stays null',()=>{
 const d=structuredClone(fixture);sample(d).quality='UNKNOWN';sample(d).rawValue=null;
 const r=evaluatePowerSnapshot(d);assert.deepEqual(r.errors,[]);assert.equal(r.observations[0].wattsNetImportPositive,null);assert.ok(r.observations[0].reasons.includes('MISSING_VALUE'));
});
test('freshness uses observation time, not a recent receipt',()=>{
 const d=structuredClone(fixture);sample(d).observedAt='2025-12-31T23:59:00.000Z';
 const r=evaluatePowerSnapshot(d);assert.deepEqual(r.errors,[]);assert.equal(r.observations[0].eligible,false);assert.equal(r.observations[0].wattsNetImportPositive,null);assert.deepEqual(r.observations[0].reasons,['STALE']);
});
test('freshness boundary is inclusive',()=>{
 const d=structuredClone(fixture);d.maxAgeMs=1000;assert.equal(evaluatePowerSnapshot(d).observations[0].eligible,true);
 d.maxAgeMs=999;assert.equal(evaluatePowerSnapshot(d).observations[0].eligible,false);
});
const bad=[
 ['source projection path traversal',d=>d.sourceProjection='/etc/passwd'],
 ['source hash mismatch',d=>d.sourceProjectionSHA256='0'.repeat(64)],
 ['missing boundary',d=>d.samples.pop()],
 ['duplicated boundary',d=>d.samples.push({...d.samples[0],id:'another'})],
 ['duplicated sample identity',d=>d.samples[1].id=d.samples[0].id],
 ['reused source point',d=>d.samples[1].sourceIdentity=structuredClone(d.samples[0].sourceIdentity)],
 ['unscoped source identity',d=>delete sample(d).sourceIdentity.namespaceUri],
 ['invalid namespace URI',d=>sample(d).sourceIdentity.namespaceUri='not-a-uri'],
 ['conversion-chain secondary used as primary',d=>sample(d,'STORAGE_AC').assetId=d.samples.find(s=>s.boundaryId==='PV_AC').assetId],
 ['unbound function identity',d=>sample(d).functionProjectionId='invented'],
 ['native normative property claim',d=>sample(d).propertyId='fsgim:ActivePower'],
 ['normative equivalence claimed',d=>d.normativePropertyEquivalence=true],
 ['unreviewed control enabled',d=>d.controlAction='ALLOW'],
 ['synthetic provenance removed',d=>sample(d).synthetic=false],
 ['fabricated case execution',d=>d.behavioralCasesRun=1],
 ['unsupported power unit',d=>sample(d).unit='kWh'],
 ['ambiguous polarity',d=>sample(d).positiveDirection='UNKNOWN'],
 ['fractional raw register',d=>sample(d).rawValue=0.5],
 ['unsafe integer',d=>sample(d).rawValue=9007199254740992],
 ['GOOD missing reading',d=>sample(d).rawValue=null],
 ['future observation',d=>sample(d).observedAt='2026-01-01T00:00:02.000Z'],
 ['future receipt',d=>sample(d).receivedAt='2026-01-01T00:00:02.000Z'],
 ['invalid timestamp',d=>sample(d).observedAt='yesterday'],
 ['unsupported leap second timestamp',d=>sample(d).observedAt='2025-12-31T23:59:60Z'],
 ['unqualified clock offset',d=>sample(d).observedAt='2026-01-01T00:00:00+01:00'],
 ['load sign reversed',d=>sample(d,'CRITICAL_LOAD_AC').positiveDirection='EXPORT'],
 ['generator sign reversed',d=>sample(d,'PV_AC').positiveDirection='IMPORT']
];
for(const [name,mutate] of bad)test('rejects '+name,()=>{
 const d=structuredClone(fixture);mutate(d);const r=evaluatePowerSnapshot(d);assert.ok(r.errors.length);
 assert.ok(r.observations.every(o=>!o.eligible&&o.wattsNetImportPositive===null));
});
