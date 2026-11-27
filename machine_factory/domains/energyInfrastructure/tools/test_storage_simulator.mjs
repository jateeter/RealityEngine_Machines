import test from 'node:test';
import assert from 'node:assert/strict';
import {StorageComponentSimulator,runStorageComponentScenario} from './simulate_storage_component.mjs';
const req=(id,power)=>({id,storagePowerKw:power});
test('independent held-interval energy and signed SunSpec power readback',()=>{
 const s=new StorageComponentSimulator();
 assert.equal(s.observe().storedEnergyKWh,'5.000000');
 let r=s.step(req('a','2'));assert.equal(r.applied,true);assert.equal(r.observation.storedEnergyKWh,'4.375000');assert.equal(r.observation.power.rawValue,0);
 r=s.step(req('b','0'));assert.equal(r.observation.storedEnergyKWh,'4.375000');assert.equal(r.observation.power.rawValue,2000);
 r=s.step(req('c','3'));assert.equal(r.observation.storedEnergyKWh,'3.437500');assert.equal(r.observation.power.rawValue,-1000);
 const block=Buffer.from(r.observation.blockHex,'hex');assert.equal(block.length,214);assert.equal(block.readUInt16BE(0),203);assert.equal(block.readUInt16BE(2),105);assert.equal(block.readInt16BE(36),-1000);assert.equal(block.readInt16BE(44),0);
 assert.equal(r.controlAction,'DENY');assert.equal(r.carriedCarbonGCO2e,null);assert.equal(r.behavioralCasesRun,0);
});
test('charging increases stored energy with .9 efficiency',()=>{
 const s=new StorageComponentSimulator(),r=s.step(req('charge','-2'));
 assert.equal(r.applied,true);assert.equal(r.observation.storedEnergyKWh,'5.450000');assert.equal(r.observation.power.rawValue,4000);
});
test('10 W minimum resolution has exact integer mWh state',()=>{
 const r=new StorageComponentSimulator().step(req('small','0.01'));
 assert.equal(r.observation.storedEnergyKWh,'4.996875');assert.equal(r.observation.power.rawValue,1990);
});
test('replays return immutable original receipt without changing current state',()=>{
 const s=new StorageComponentSimulator(),a=s.step(req('a','2'));
 a.observation.storedEnergyKWh='tampered';s.step(req('b','0'));const before=s.observe();
 const replay=s.step(req('a','2'));assert.equal(replay.replayed,true);assert.equal(replay.observation.storedEnergyKWh,'4.375000');assert.deepEqual(s.observe(),before);
 assert.throws(()=>s.step(req('a','1')),/Conflicting replay/);assert.deepEqual(s.observe(),before);
});
test('reserve rejection leaves energy, clock, readback and revision unchanged',()=>{
 const s=new StorageComponentSimulator();s.step(req('a','2'));s.step(req('b','3'));const before=s.observe();
 const r=s.step(req('c','3'));assert.equal(r.applied,false);assert.ok(r.screen.reasons.includes('RESERVE_VIOLATION'));assert.deepEqual(s.observe(),before);
 assert.equal(s.step(req('c','3')).replayed,true);assert.deepEqual(s.observe(),before);
});
for(const [fault,reason] of [['TELEMETRY_UNKNOWN','STATE_QUALITY_NOT_GOOD'],['PROTECTION_BLOCKED','PROTECTION_NOT_HEALTHY'],['RISK_UNKNOWN','RISK_NOT_CLEAR']])test(`${fault} latches and blocks state advance`,()=>{
 const s=new StorageComponentSimulator(),before=s.injectFault(fault),r=s.step(req('held','2'));
 assert.equal(r.applied,false);assert.ok(r.screen.reasons.includes(reason));assert.equal(r.screen.calculations,null);assert.deepEqual(s.observe(),before);
 assert.deepEqual(s.injectFault(fault),before);
 if(fault==='TELEMETRY_UNKNOWN'){assert.equal(before.storedEnergyKWh,null);assert.equal(before.power.rawValue,null);assert.equal(before.power.quality,'UNKNOWN');}
});
for(const request of [null,{},req('../x','2'),req('a',2),req('a','0.001'),req('a','1e2'),req('a','NaN'),{...req('a','2'),endpoint:'https://device.invalid'}])test(`reject invalid request ${JSON.stringify(request)}`,()=>{
 const s=new StorageComponentSimulator(),before=s.observe();assert.throws(()=>s.step(request));assert.deepEqual(s.observe(),before);
});
test('unsupported faults cannot change state',()=>{const s=new StorageComponentSimulator(),before=s.observe();assert.throws(()=>s.injectFault('CLEAR'));assert.deepEqual(s.observe(),before);});
test('bounded receipt history refuses new IDs without eviction or re-execution',()=>{
 const s=new StorageComponentSimulator();for(let i=0;i<100;i++)s.step(req(`rejected${i}`,'99'));
 const before=s.observe();assert.throws(()=>s.step(req('overflow','0')),/limit/);assert.equal(s.step(req('rejected0','99')).replayed,true);assert.deepEqual(s.observe(),before);
});
test('scenario reproduces deterministic component-only events',()=>{
 const a=runStorageComponentScenario();assert.deepEqual(a,runStorageComponentScenario());assert.deepEqual(a.events.filter(e=>'applied' in e).map(e=>e.applied),[true,true,true,true,false,false]);
 assert.equal(a.result,'COMPONENT_SIMULATION_ONLY_NOT_DOMAIN_ACCEPTANCE');
});
