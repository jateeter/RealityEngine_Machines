import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,mkdtempSync,mkdirSync,copyFileSync,writeFileSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {decodeSunSpecPower,evaluateSunSpecReplay} from './decode_sunspec_power.mjs';
const replay=JSON.parse(readFileSync(new URL('../assets/sunspec-power-replay.json',import.meta.url),'utf8'));
const block=n=>replay.blocks.find(b=>b.modelId===n).blockHex;
const word=(hex,offset,value)=>{const b=Buffer.from(hex,'hex');b.writeUInt16BE(value,2*offset);return b.toString('hex');};
for(const [model,count,w,sf] of [[103,52,14,15],[203,107,18,22]]) {
 test(`model ${model} decodes independently specified signed register positions`,()=>{
  // Independent vectors deliberately use literal offsets rather than the generated profile.
  const bytes=Buffer.alloc(count*2);bytes.writeUInt16BE(model,0);bytes.writeUInt16BE(count-2,2);
  bytes.writeInt16BE(-12345,w*2);bytes.writeInt16BE(-2,sf*2);
  const d=decodeSunSpecPower(model,bytes.toString('hex'));
  assert.equal(d.rawValue,-12345);assert.equal(d.scaleExponent,-2);assert.equal(d.unit,'W');assert.equal(d.quality,'GOOD');
 });
 for(const [label,offset] of [['power',w],['scale',sf]])test(`model ${model} excludes unimplemented ${label}`,()=>{
  const d=decodeSunSpecPower(model,word(block(model),offset,0x8000));assert.equal(d.quality,'UNKNOWN');assert.equal(d.rawValue,null);assert.equal(d.scaleExponent,null);
 });
 for(const [value,expected] of [[0,0],[0x7fff,32767],[0x8001,-32767],[0xffff,-1]])test(`model ${model} signed vector ${value}`,()=>assert.equal(decodeSunSpecPower(model,word(block(model),w,value)).rawValue,expected));
 for(const v of [-10,10])test(`model ${model} accepts scale edge ${v}`,()=>assert.equal(decodeSunSpecPower(model,word(block(model),sf,v&0xffff)).scaleExponent,v));
 for(const v of [-11,11])test(`model ${model} rejects scale outside range ${v}`,()=>assert.throws(()=>decodeSunSpecPower(model,word(block(model),sf,v&0xffff))));
 for(const [label,mutate] of [
  ['wrong ID',h=>word(h,0,999)],['wrong length',h=>word(h,1,count)],
  ['truncation',h=>h.slice(0,-4)],['extra register',h=>h+'0000'],['partial word',h=>h.slice(0,-2)],['nonhex',h=>'zzzz'+h.slice(4)],
  ['little endian header',h=>{const b=Buffer.from(h,'hex');b.swap16();return b.toString('hex');}]
 ])test(`model ${model} rejects ${label}`,()=>assert.throws(()=>decodeSunSpecPower(model,mutate(block(model)))));
}
test('rejects unsupported model and non-string bytes',()=>{assert.throws(()=>decodeSunSpecPower(101,block(103)));assert.throws(()=>decodeSunSpecPower(103,{}));});
test('register blocks feed the FSGIM accounting snapshot with explicit polarity',()=>{
 const r=evaluateSunSpecReplay(replay);assert.deepEqual(r.errors,[]);assert.equal(r.observations.find(o=>o.boundaryId==='PV_AC').wattsNetImportPositive,'-2500');assert.equal(r.observations.find(o=>o.boundaryId==='FACILITY_PCC').wattsNetImportPositive,'1250');assert.equal(r.controlAction,'DENY');
});
test('unimplemented source flows through as null, never zero',()=>{
 const d=structuredClone(replay);d.blocks[0].blockHex=word(d.blocks[0].blockHex,14,0x8000);
 const r=evaluateSunSpecReplay(d);assert.deepEqual(r.errors,[]);const o=r.observations.find(o=>o.boundaryId==='PV_AC');assert.equal(o.eligible,false);assert.equal(o.wattsNetImportPositive,null);
});
test('SunSpec scale edges survive exact decimal snapshot normalization',()=>{
 for(const [sf,expected] of [[-10,'-0.0000025'],[10,'-250000000000000']]){
  const d=structuredClone(replay);d.blocks[0].blockHex=word(d.blocks[0].blockHex,15,sf&0xffff);const r=evaluateSunSpecReplay(d);assert.deepEqual(r.errors,[]);assert.equal(r.observations.find(o=>o.boundaryId==='PV_AC').wattsNetImportPositive,expected);
 }
});
for(const [label,mutate] of [
 ['path traversal',d=>d.sourceSnapshot='/etc/passwd'],['source drift',d=>d.sourceSnapshotSHA256='0'.repeat(64)],
 ['missing block',d=>d.blocks.pop()],['duplicate boundary',d=>d.blocks[1]=structuredClone(d.blocks[0])],
 ['wrong boundary model',d=>d.blocks[0].modelId=203],['unsupported boundary',d=>d.blocks[0].boundaryId='STORAGE_AC'],
 ['network claim',d=>d.networkExecution=true],['control claim',d=>d.controlAction='ALLOW'],['behavioral case claim',d=>d.behavioralCasesRun=1],['extra field',d=>d.peerReceipt='fabricated']
])test('rejects replay '+label,()=>{const d=structuredClone(replay);mutate(d);assert.throws(()=>evaluateSunSpecReplay(d));});
test('source provenance and profile drift are rejected independently',t=>{
 const root=mkdtempSync(join(tmpdir(),'energy-sunspec-'));t.after(()=>rmSync(root,{recursive:true,force:true}));
 mkdirSync(join(root,'assets'));mkdirSync(join(root,'intake/public-models/sunspec'),{recursive:true});
 for(const path of ['assets/sunspec-power-profile.json','assets/source-receipt.json','intake/public-models/sunspec/model_103.json'])copyFileSync(new URL('../'+path,import.meta.url),join(root,path));
 const p=join(root,'assets/sunspec-power-profile.json'),original=readFileSync(p,'utf8');
 const d=JSON.parse(original);d.models[0].powerOffset=13;writeFileSync(p,JSON.stringify(d));assert.throws(()=>decodeSunSpecPower(103,block(103),root));
 writeFileSync(p,original);writeFileSync(join(root,'intake/public-models/sunspec/model_103.json'),'{}');assert.throws(()=>decodeSunSpecPower(103,block(103),root));
});
