import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,mkdtempSync,mkdirSync,copyFileSync,writeFileSync,rmSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {decodeMeterEnergy,evaluateMeterInterval} from './evaluate_meter_interval.mjs';
const fixture=JSON.parse(readFileSync(new URL('../assets/meter-energy-interval.json',import.meta.url),'utf8'));
const fresh=()=>structuredClone(fixture);
const register=(hex,offset,value,width=2)=>{const b=Buffer.from(hex,'hex');if(width===4)b.writeUInt32BE(value,offset*2);else b.writeUInt16BE(value,offset*2);return b.toString('hex');};
test('independent 32-bit vectors preserve high and low word order',()=>{
 const b=Buffer.alloc(214);b.writeUInt16BE(203,0);b.writeUInt16BE(105,2);b.writeUInt32BE(0x12345678,46*2);b.writeUInt32BE(0xfedcba98,38*2);b.writeInt16BE(-2,54*2);
 const d=decodeMeterEnergy(b.toString('hex'));assert.equal(d.rawImported,0x12345678);assert.equal(d.rawExported,0xfedcba98);assert.equal(d.scaleExponent,-2);assert.deepEqual(d.reasons,[]);
});
test('separate imported/exported interval quantities and no carbon claim',()=>{
 const r=evaluateMeterInterval(fixture);assert.equal(r.eligible,true);assert.equal(r.durationMs,900000);assert.equal(r.importedWh,'1250');assert.equal(r.exportedWh,'250');assert.equal(r.importedKWh,'1.25');assert.equal(r.exportedKWh,'0.25');assert.equal(r.carbonIntensity,null);assert.equal(r.controlAction,'DENY');
});
test('unchanged nonzero counters give a valid zero delta',()=>{
 const d=fresh();d.end.blockHex=d.start.blockHex;const r=evaluateMeterInterval(d);assert.equal(r.eligible,true);assert.equal(r.importedWh,'0');assert.equal(r.exportedWh,'0');assert.equal(r.carbonIntensity,null);
});
test('all-ones acc32 is a valid value, not an unsigned sentinel',()=>assert.equal(decodeMeterEnergy(register(fixture.end.blockHex,46,0xffffffff,4)).rawImported,4294967295));
for(const [sf,expected] of [[-10,'0.00000125'],[10,'125000000000000']])test('exact interval scale edge '+sf,()=>{
 const d=fresh();for(const name of ['start','end'])d[name].blockHex=register(d[name].blockHex,54,sf&0xffff);const r=evaluateMeterInterval(d);assert.equal(r.eligible,true);assert.equal(r.importedWh,expected);
});
for(const [label,mutate,reason] of [
 ['import not accumulated',d=>d.end.blockHex=register(d.end.blockHex,46,0,4),'IMPORT_NOT_ACCUMULATED'],
 ['export not accumulated',d=>d.start.blockHex=register(d.start.blockHex,38,0,4),'EXPORT_NOT_ACCUMULATED'],
 ['unimplemented scale',d=>d.end.blockHex=register(d.end.blockHex,54,0x8000),'ENERGY_SCALE_NOT_IMPLEMENTED'],
 ['import decrease',d=>d.end.blockHex=register(d.end.blockHex,46,99999,4),'COUNTER_DISCONTINUITY_RESET_OR_ROLLOVER'],
 ['export decrease',d=>d.end.blockHex=register(d.end.blockHex,38,9999,4),'COUNTER_DISCONTINUITY_RESET_OR_ROLLOVER'],
 ['apparent wrap',d=>{d.start.blockHex=register(d.start.blockHex,46,0xffffffff,4);d.end.blockHex=register(d.end.blockHex,46,1,4);},'COUNTER_DISCONTINUITY_RESET_OR_ROLLOVER'],
 ['scale change',d=>d.end.blockHex=register(d.end.blockHex,54,0),'ENERGY_SCALE_CHANGED'],
 ['bad source status',d=>d.start.quality='BAD','SOURCE_QUALITY_NOT_GOOD'],
 ['unknown source status',d=>d.end.quality='UNKNOWN','SOURCE_QUALITY_NOT_GOOD'],
 ['stale interval end',d=>d.maxAgeMs=999,'STALE_INTERVAL_END']
])test('excludes '+label,()=>{
 const d=fresh();mutate(d);const r=evaluateMeterInterval(d);assert.equal(r.eligible,false);assert.ok(r.reasons.includes(reason));for(const k of ['importedWh','exportedWh','importedKWh','exportedKWh','carbonIntensity'])assert.equal(r[k],null);
});
test('freshness includes the exact end-time limit and does not expire the interval start',()=>{
 const d=fresh();d.maxAgeMs=1000;assert.equal(evaluateMeterInterval(d).eligible,true);
});
const invalid=[
 ['unallowlisted path',d=>d.sourceProjection='/etc/passwd'],['source hash',d=>d.sourceProjectionSHA256='0'.repeat(64)],
 ['wrong meter',d=>d.meterAssetId='invented'],['resource boundary',d=>d.boundaryId='PV_AC'],['wrong model',d=>d.modelId=103],
 ['changed source',d=>d.end.sourceIdentity.identifier='other-meter'],['changed epoch',d=>d.end.counterEpochId='synthetic.epoch.2'],
 ['invalid source namespace',d=>d.end.sourceIdentity.namespaceUri='not-a-uri'],['missing epoch',d=>delete d.start.counterEpochId],
 ['unknown quality',d=>d.start.quality='TRUSTED'],['invalid time',d=>d.start.observedAt='yesterday'],
 ['leap second',d=>d.end.observedAt='2026-01-01T00:14:60Z'],['invalid calendar date',d=>d.start.observedAt='2026-02-30T00:00:00Z'],
 ['non-UTC time',d=>d.start.observedAt='2026-01-01T00:00:00+01:00'],
 ['future receipt',d=>d.end.receivedAt='2026-01-01T00:15:02.000Z'],['receipt before source',d=>d.end.receivedAt='2026-01-01T00:14:59.000Z'],
 ['zero duration',d=>d.end.observedAt=d.start.observedAt],['reversed duration',d=>d.start.observedAt='2026-01-01T00:16:00Z'],
 ['overlong interval',d=>d.maxIntervalMs=899999],['invalid TTL',d=>d.maxAgeMs=0],['unbounded interval',d=>d.maxIntervalMs=86400001],
 ['truncated block',d=>d.end.blockHex=d.end.blockHex.slice(0,-4)],['wrong ID',d=>d.end.blockHex=register(d.end.blockHex,0,103)],
 ['wrong length',d=>d.end.blockHex=register(d.end.blockHex,1,106)],['extra register',d=>d.end.blockHex+='0000'],
 ['nonhex block',d=>d.end.blockHex='zzzz'+d.end.blockHex.slice(4)],['scale out of range',d=>d.end.blockHex=register(d.end.blockHex,54,11)],
 ['control claim',d=>d.controlAction='ALLOW'],['real data claim',d=>d.synthetic=false],['approved review claim',d=>d.engineeringReview='APPROVED'],
 ['case execution claim',d=>d.behavioralCasesRun=1],['invented emissions factor',d=>d.emissionsFactor=0]
];
for(const [label,mutate] of invalid)test('rejects '+label,()=>{const d=fresh();mutate(d);assert.throws(()=>evaluateMeterInterval(d));});
test('source and selected point profile tampering fail closed',t=>{
 const root=mkdtempSync(join(tmpdir(),'energy-interval-'));t.after(()=>rmSync(root,{recursive:true,force:true}));
 mkdirSync(join(root,'assets'));mkdirSync(join(root,'intake/public-models/sunspec'),{recursive:true});
 for(const p of ['assets/source-receipt.json','assets/meter-energy-profile.json','intake/public-models/sunspec/model_203.json'])copyFileSync(new URL('../'+p,import.meta.url),join(root,p));
 const path=join(root,'assets/meter-energy-profile.json'),original=readFileSync(path,'utf8'),d=JSON.parse(original);d.points.TotWhImp.offset=38;writeFileSync(path,JSON.stringify(d));assert.throws(()=>decodeMeterEnergy(fixture.start.blockHex,root));
 writeFileSync(path,original);writeFileSync(join(root,'intake/public-models/sunspec/model_203.json'),'{}');assert.throws(()=>decodeMeterEnergy(fixture.start.blockHex,root));
});
