import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {evaluateCarbonLedger} from './evaluate_carbon_ledger.mjs';
const fixture=JSON.parse(readFileSync(new URL('../assets/import-carbon-ledger.json',import.meta.url),'utf8'));
const fresh=()=>structuredClone(fixture),fraction=(n,d='1')=>({numerator:n,denominator:d});
const imp=(hex,value)=>{const b=Buffer.from(hex,'hex');b.writeUInt32BE(value,92);return b.toString('hex');};
const sf=(hex,value)=>{const b=Buffer.from(hex,'hex');b.writeUInt16BE(value&0xffff,108);return b.toString('hex');};
test('independent unequal-energy oracle: (1.25*100+3.75*400)/5 = 325, not 250',()=>{
 const r=evaluateCarbonLedger(fixture);assert.equal(r.eligible,true);assert.deepEqual(r.importedKWh,fraction('5'));assert.deepEqual(r.allocatedEmissionsGCO2e,fraction('1625'));assert.deepEqual(r.intensityGCO2ePerKWh,fraction('325'));assert.deepEqual(r.exportedKWhSeparate,fraction('3','4'));assert.equal(r.exportCreditApplied,false);assert.equal(r.controlAction,'DENY');
});
test('nonterminating weighted intensity stays an exact rational',()=>{
 const d=fresh();d.rows[0].meterInterval.end.blockHex=imp(d.rows[0].meterInterval.end.blockHex,120000);d.rows[1].meterInterval.start=structuredClone(d.rows[0].meterInterval.end);d.rows[1].meterInterval.end.blockHex=imp(d.rows[1].meterInterval.end.blockHex,130000);
 d.rows[0].factor.intensity='0';d.rows[1].factor.intensity='1';assert.deepEqual(evaluateCarbonLedger(d).intensityGCO2ePerKWh,fraction('1','3'));
});
test('known zero factors remain distinct from unknown factors',()=>{
 const d=fresh();for(const row of d.rows)row.factor.intensity='0';const r=evaluateCarbonLedger(d);assert.equal(r.eligible,true);assert.deepEqual(r.allocatedEmissionsGCO2e,fraction('0'));assert.deepEqual(r.intensityGCO2ePerKWh,fraction('0'));
});
test('zero imported energy gives undefined intensity, not zero intensity',()=>{
 const d=fresh();d.rows[0].meterInterval.end.blockHex=imp(d.rows[0].meterInterval.end.blockHex,100000);d.rows[1].meterInterval.start=structuredClone(d.rows[0].meterInterval.end);d.rows[1].meterInterval.end.blockHex=imp(d.rows[1].meterInterval.end.blockHex,100000);
 const r=evaluateCarbonLedger(d);assert.equal(r.eligible,true);assert.deepEqual(r.importedKWh,fraction('0'));assert.deepEqual(r.allocatedEmissionsGCO2e,fraction('0'));assert.equal(r.intensityGCO2ePerKWh,null);assert.equal(r.intensityStatus,'UNDEFINED_ZERO_IMPORTED_ENERGY');
});
test('smallest supported interval decimal remains exact',()=>{
 const d=fresh();d.rows=d.rows.slice(0,1);const i=d.rows[0].meterInterval;
 i.end.blockHex=imp(i.end.blockHex,100001);i.start.blockHex=sf(i.start.blockHex,-10);i.end.blockHex=sf(i.end.blockHex,-10);d.rows[0].factor.intensity='0.000000000001';
 const r=evaluateCarbonLedger(d);assert.deepEqual(r.importedKWh,fraction('1','10000000000000'));assert.deepEqual(r.allocatedEmissionsGCO2e,fraction('1','10000000000000000000000000'));
});
test('large decimal factors avoid floating-point overflow/rounding',()=>{
 const d=fresh();d.rows=d.rows.slice(0,1);d.rows[0].factor.intensity='9007199254740993';assert.deepEqual(evaluateCarbonLedger(d).allocatedEmissionsGCO2e,fraction('45035996273704965','4'));
});
test('factor revisions are carried in row results',()=>{
 const d=fresh();d.rows[1].factor.revision='fixture-v2';assert.equal(evaluateCarbonLedger(d).rows[1].revision,'fixture-v2');
});
for(const [label,mutate,reason] of [
 ['unknown factor',d=>{d.rows[1].factor.quality='UNKNOWN';d.rows[1].factor.intensity=null;},'FACTOR_VALUE_MISSING'],
 ['bad factor with numeric zero',d=>{d.rows[1].factor.quality='BAD';d.rows[1].factor.intensity='0';},'FACTOR_QUALITY_BAD'],
 ['expired factor',d=>d.rows[1].factor.validUntil='2026-01-01T00:30:00.900Z','FACTOR_EXPIRED'],
 ['unknown meter endpoint',d=>d.rows[1].meterInterval.end.quality='UNKNOWN','SOURCE_QUALITY_NOT_GOOD'],
 ['reset meter counter',d=>d.rows[1].meterInterval.end.blockHex=imp(d.rows[1].meterInterval.end.blockHex,1),'COUNTER_DISCONTINUITY_RESET_OR_ROLLOVER'],
 ['stale meter end',d=>d.rows[1].meterInterval.maxAgeMs=999,'STALE_INTERVAL_END']
])test('excludes entire ledger for '+label,()=>{
 const d=fresh();mutate(d);const r=evaluateCarbonLedger(d);assert.equal(r.eligible,false);assert.ok(r.reasons.some(s=>s.includes(reason)));for(const name of ['importedKWh','exportedKWhSeparate','allocatedEmissionsGCO2e','intensityGCO2ePerKWh'])assert.equal(r[name],null);assert.equal(r.intensityStatus,'UNKNOWN_INPUT');
});
const bad=[
 ['source traversal',d=>d.sourceInterval='/etc/passwd'],['source hash drift',d=>d.sourceIntervalSHA256='0'.repeat(64)],
 ['empty ledger',d=>d.rows=[]],['duplicate row identity',d=>d.rows[1].id=d.rows[0].id],['duplicate interval',d=>d.rows[1].meterInterval=structuredClone(d.rows[0].meterInterval)],
 ['reversed rows',d=>d.rows.reverse()],['interval gap',d=>d.rows[1].meterInterval.start.observedAt='2026-01-01T00:15:00.050Z'],
 ['counter continuity gap',d=>d.rows[1].meterInterval.start.blockHex=imp(d.rows[1].meterInterval.start.blockHex,112501)],
 ['different ledger evaluation',d=>d.rows[0].meterInterval.evaluationAt='2026-01-01T00:30:02.000Z'],
 ['other meter source',d=>{const i=d.rows[0].meterInterval;i.start.sourceIdentity.identifier='other';i.end.sourceIdentity.identifier='other';}],
 ['factor time mismatch',d=>d.rows[0].factor.intervalEnd='2026-01-01T00:14:59.000Z'],
 ['future publication',d=>d.rows[0].factor.issuedAt='2026-01-01T00:30:02.000Z'],['publication before observed period end',d=>d.rows[0].factor.issuedAt='2026-01-01T00:14:59.000Z'],['invalid validity window',d=>d.rows[0].factor.validUntil='2026-01-01T00:29:59.000Z'],
 ['unsupported provider',d=>d.rows[0].factor.providerId='REAL_PROVIDER'],['unqualified rights',d=>d.rows[0].factor.rights='UNKNOWN'],['missing revision',d=>d.rows[0].factor.revision=''],
 ['negative factor',d=>d.rows[0].factor.intensity='-1'],['numeric factor',d=>d.rows[0].factor.intensity=100],['nonfinite factor',d=>d.rows[0].factor.intensity='NaN'],['exponent factor',d=>d.rows[0].factor.intensity='1e2'],['oversized factor',d=>d.rows[0].factor.intensity='9'.repeat(65)],['unsupported precision',d=>d.rows[0].factor.intensity='0.0000000000001'],
 ['forecast used as observation',d=>d.rows[0].factor.basis.dataRole='FORECAST'],['marginal used as average',d=>d.rows[0].factor.basis.signalType='MARGINAL'],['lifecycle used as direct',d=>d.rows[0].factor.basis.emissionsScope='LIFECYCLE'],['CO2 used as CO2e',d=>d.rows[0].factor.basis.gasBasis='CO2'],['different GWP',d=>d.rows[0].factor.basis.gwpBasis='OTHER'],['market used as location',d=>d.rows[0].factor.basis.reportingBasis='MARKET_BASED'],['wrong geography',d=>d.rows[0].factor.basis.geography='OTHER'],['wrong unit',d=>d.rows[0].factor.basis.factorUnit='kgCO2e/MWh'],['different denominator',d=>d.rows[0].factor.basis.energyBoundary='DELIVERED_ELECTRICITY'],
 ['unsupported common basis',d=>{d.basis.gasBasis='CO2';for(const r of d.rows)r.factor.basis.gasBasis='CO2';}],
 ['export credit claim',d=>d.exportCreditApplied=true],['dispatch use',d=>d.accountingUse='DISPATCH'],['control claim',d=>d.controlAction='ALLOW'],['execution claim',d=>d.behavioralCasesRun=1]
];
for(const [label,mutate] of bad)test('rejects '+label,()=>{const d=fresh();mutate(d);assert.throws(()=>evaluateCarbonLedger(d));});
