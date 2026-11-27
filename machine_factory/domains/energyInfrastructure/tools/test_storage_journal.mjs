import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {mkdtempSync,writeFileSync,rmSync,readFileSync,mkdirSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {StorageExecutionJournal,parseStorageJournal} from './storage_execution_journal.mjs';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const req=(id,power)=>({id,storagePowerKw:power});
const create=()=>{const j=new StorageExecutionJournal('test.run.1');j.step(req('discharge','2'));j.step(req('idle','0'));return j;};
const canonical=x=>Array.isArray(x)?'['+x.map(canonical).join(',')+']':x!==null&&typeof x==='object'?'{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canonical(x[k])).join(',')+'}':JSON.stringify(x);
const digest=x=>createHash('sha256').update(canonical(x)).digest('hex');
test('reconstruction restores state, counters, clock, receipts and subsequent execution',()=>{
 const a=create(),b=parseStorageJournal(JSON.stringify(a.export()));assert.deepEqual(b.observe(),a.observe());
 const before=b.observe(),replay=b.step(req('idle','0'));assert.equal(replay.replayed,true);assert.deepEqual(b.observe(),before);
 assert.throws(()=>b.step(req('idle','1')),/Conflicting replay/);assert.deepEqual(b.observe(),before);
 assert.deepEqual(a.step(req('export','3')),b.step(req('export','3')));
});
test('fault latches and denied request receipts survive reconstruction',()=>{
 const j=create();j.injectFault('RISK_UNKNOWN');const held=j.step(req('held','0'));assert.equal(held.applied,false);
 const restored=StorageExecutionJournal.restore(j.export());assert.deepEqual(restored.observe(),j.observe());assert.equal(restored.step(req('held','0')).replayed,true);assert.equal(restored.step(req('new','0')).applied,false);
});
test('telemetry loss restores unknown readback without zero fallback',()=>{
 const j=create();j.injectFault('TELEMETRY_UNKNOWN');const r=StorageExecutionJournal.restore(j.export()).observe();assert.equal(r.storedEnergyKWh,null);assert.equal(r.energy.rawImported,null);assert.equal(r.power.rawValue,null);
});
test('exports and returned receipts cannot mutate stored journal',()=>{
 const j=create(),before=j.export(),x=j.export();x.events[0].receipt.applied=false;x.sourcePins.assetManifestSHA256='changed';assert.deepEqual(j.export(),before);
});
for(const [label,mutate] of [
 ['source pins',x=>x.sourcePins.assetManifestSHA256='0'.repeat(64)],
 ['head',x=>x.headSHA256='0'.repeat(64)],
 ['run identity',x=>x.runId='other.run'],
 ['sequence',x=>x.events[0].sequence=2],
 ['chain link',x=>x.events[1].previousSHA256='0'.repeat(64)],
 ['receipt',x=>x.events[0].receipt.observation.storedEnergyKWh='9.000000'],
 ['event removal',x=>x.events.shift()],
 ['truncated tail',x=>x.events.pop()],
 ['reordering',x=>x.events.reverse()],
 ['unknown field',x=>x.operatingApproval=true],
 ['control claim',x=>x.controlAction='ALLOW'],
 ['non-synthetic claim',x=>x.simulationOnly=false],
 ['behavioral case claim',x=>x.behavioralCasesRun=43],
 ['unknown operation',x=>x.events[0].operation='SEND_DEVICE_COMMAND']
])test(`reject altered ${label}`,()=>{const x=create().export();mutate(x);assert.throws(()=>StorageExecutionJournal.restore(x));});
test('recomputing hashes cannot make a false receipt match re-executed state',()=>{
 const x=create().export();x.events[0].receipt.observation.storedEnergyKWh='9.000000';
 for(let i=0;i<x.events.length;i++){const e=x.events[i];if(i)e.previousSHA256=x.events[i-1].eventSHA256;const {eventSHA256,...body}=e;e.eventSHA256=digest(body);}
 x.headSHA256=x.events.at(-1).eventSHA256;assert.throws(()=>StorageExecutionJournal.restore(x),/receipt disagrees/);
});
test('complete prefix is valid: hashes alone do not prove history completeness',()=>{
 const x=create().export();x.events.pop();x.headSHA256=x.events.at(-1).eventSHA256;const j=StorageExecutionJournal.restore(x);assert.equal(j.observe().storedEnergyKWh,'4.375000');assert.equal(j.export().events.length,1);
});
test('run label scopes meter epochs, without claiming global uniqueness',()=>{
 const a=new StorageExecutionJournal('run.A').step(req('a','0')),b=new StorageExecutionJournal('run.B').step(req('a','0'));
 assert.equal(a.meterInterval.input.end.counterEpochId,'run.A');assert.equal(b.meterInterval.input.end.counterEpochId,'run.B');
});
test('invalid request does not append a journal event',()=>{
 const j=create(),before=j.export();assert.throws(()=>j.step({...req('bad','2'),endpoint:'device'}));assert.deepEqual(j.export(),before);assert.throws(()=>j.injectFault('CLEAR'));assert.deepEqual(j.export(),before);
});
test('event bounds are checked before changing simulator state',()=>{
 const j=new StorageExecutionJournal('bounds');for(let i=0;i<128;i++)j.injectFault('RISK_UNKNOWN');const before=j.observe(),exported=j.export();assert.throws(()=>j.step(req('overflow','0')),/event limit/);assert.deepEqual(j.observe(),before);assert.deepEqual(j.export(),exported);
});
test('bounded parser rejects oversized and malformed input',()=>{
 assert.throws(()=>parseStorageJournal(' '.repeat(1048577)),/Oversized/);assert.throws(()=>parseStorageJournal('{'));
 const x=create().export();x.events=Array(129).fill(x.events[0]);assert.throws(()=>StorageExecutionJournal.restore(x),/Oversized/);
});
test('changed package bytes are rejected before simulation construction',()=>{
 const temp=mkdtempSync(resolve(tmpdir(),'energy-journal-drift-'));try{
  const manifest=JSON.parse(readFileSync(resolve(root,'asset-manifest.json'),'utf8'));
  writeFileSync(resolve(temp,'asset-manifest.json'),JSON.stringify(manifest));
  assert.equal(manifest.files[0].path,'PACKAGE_STATUS.md');writeFileSync(resolve(temp,'PACKAGE_STATUS.md'),'changed');
  assert.throws(()=>new StorageExecutionJournal('drift',temp),/Package source drift/);
 }finally{rmSync(temp,{recursive:true,force:true});}
});
test('package manifest cannot read outside its root',()=>{
 const temp=mkdtempSync(resolve(tmpdir(),'energy-journal-path-'));try{
  const sub=resolve(temp,'package');mkdirSync(sub);writeFileSync(resolve(temp,'outside.txt'),'outside');
  writeFileSync(resolve(sub,'asset-manifest.json'),JSON.stringify({domain:'energyInfrastructure',files:[{path:'../outside.txt',bytes:7,sha256:'unused'}]}));
  assert.throws(()=>new StorageExecutionJournal('escape',sub),/Invalid package path/);
 }finally{rmSync(temp,{recursive:true,force:true});}
});
test('fresh process CLI reconstructs a saved journal file',()=>{
 const temp=mkdtempSync(resolve(tmpdir(),'energy-journal-'));try{
  const script=resolve(root,'tools/storage_execution_journal.mjs'),a=spawnSync(process.execPath,[script],{encoding:'utf8',maxBuffer:2097152});assert.equal(a.status,0,a.stderr);
  const file=resolve(temp,'journal.json');writeFileSync(file,a.stdout);
  const b=spawnSync(process.execPath,[script,'--replay',file],{encoding:'utf8'});assert.equal(b.status,0,b.stderr);const result=JSON.parse(b.stdout);assert.equal(result.result,'SIMULATION_RECONSTRUCTION_ONLY');assert.equal(result.observation.storedEnergyKWh,'4.375000');assert.equal(result.observation.energy.rawImported,1050000);
  writeFileSync(file,' '.repeat(1048577));const c=spawnSync(process.execPath,[script,'--replay',file],{encoding:'utf8'});assert.notEqual(c.status,0);assert.equal(c.stdout,'');
 }finally{rmSync(temp,{recursive:true,force:true});}
});
