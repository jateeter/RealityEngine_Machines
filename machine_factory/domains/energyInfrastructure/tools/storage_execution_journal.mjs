#!/usr/bin/env node
/** Source-bound offline reconstruction, not authenticated durable delivery. */
import {readFileSync,realpathSync,lstatSync,openSync,readSync,closeSync,fstatSync,constants} from 'node:fs';
import {resolve,dirname,sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {isDeepStrictEqual} from 'node:util';
import {StorageComponentSimulator} from './simulate_storage_component.mjs';
const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const MAX_BYTES=1048576,MAX_EVENTS=128;
const require=(ok,msg)=>{if(!ok)throw Error(msg);};
const hash=b=>createHash('sha256').update(b).digest('hex');
function canonical(x){
 if(Array.isArray(x))return '['+x.map(canonical).join(',')+']';
 if(x!==null&&typeof x==='object')return '{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canonical(x[k])).join(',')+'}';
 return JSON.stringify(x);
}
const digest=x=>hash(canonical(x));
const keys=(o,list)=>o&&typeof o==='object'&&!Array.isArray(o)&&isDeepStrictEqual(Object.keys(o).sort(),list.split(' ').sort());
function sourcePins(root){
 const bytes=readFileSync(resolve(root,'asset-manifest.json')),m=JSON.parse(bytes),base=realpathSync(root);
 require(m.domain==='energyInfrastructure'&&Array.isArray(m.files)&&m.files.length>0&&m.files.length<=1000,'Invalid package asset manifest');
 const seen=new Set();
 for(const f of m.files){
  require(typeof f.path==='string'&&!seen.has(f.path),'Invalid/duplicate package path');seen.add(f.path);
  const path=resolve(root,f.path);
  require(path.startsWith(resolve(root)+sep)&&realpathSync(path).startsWith(base+sep)&&!lstatSync(path).isSymbolicLink(),'Invalid package path');
  const data=readFileSync(path);require(data.length===f.bytes&&hash(data)===f.sha256,'Package source drift: '+f.path);
 }
 for(const name of ['tools/storage_execution_journal.mjs','tools/simulate_storage_component.mjs','assets/storage-component-catalog.json'])require(seen.has(name),'Missing executable/catalog package pin');
 return {assetManifestSHA256:hash(bytes),journalImplementationSHA256:hash(readFileSync(fileURLToPath(import.meta.url)))};
}

export class StorageExecutionJournal {
 #sim; #header; #events=[]; #head;
 constructor(runId,root=ROOT){
  require(typeof runId==='string'&&/^[a-zA-Z0-9_.-]{1,80}$/.test(runId),'Invalid synthetic run ID');
  this.#header={schemaVersion:'1.0.0',kind:'SYNTHETIC_STORAGE_EXECUTION_JOURNAL',runId,sourcePins:sourcePins(root),simulationOnly:true,controlAction:'DENY',behavioralCasesRun:0};
  this.#head=digest(this.#header);this.#sim=new StorageComponentSimulator(root,runId);
 }
 observe(){return this.#sim.observe();}
 #append(operation,payload){
  require(this.#events.length<MAX_EVENTS,'Journal event limit reached');
  // Reserve space before mutating the simulator. Caller-controlled receipts are never accepted.
  require(Buffer.byteLength(JSON.stringify(this.export()))+Buffer.byteLength(JSON.stringify(payload))+20000<MAX_BYTES,'Journal byte limit reached');
  const receipt=operation==='STEP'?this.#sim.step(payload):operation==='RISK_ASSESSMENT'?this.#sim.applyRiskAssessment(payload):this.#sim.injectFault(payload);
  const body={sequence:this.#events.length+1,previousSHA256:this.#head,operation,payload:structuredClone(payload),receipt:structuredClone(receipt)};
  const event={...body,eventSHA256:digest(body)};this.#events.push(event);this.#head=event.eventSHA256;return structuredClone(receipt);
 }
 step(request){return this.#append('STEP',request);}
 injectFault(fault){return this.#append('FAULT',fault);}
 applyRiskAssessment(input){return this.#append('RISK_ASSESSMENT',input);}
 export(){return {...structuredClone(this.#header),events:structuredClone(this.#events),headSHA256:this.#head};}
 static restore(input,root=ROOT){
  require(keys(input,'schemaVersion kind runId sourcePins simulationOnly controlAction behavioralCasesRun events headSHA256'),'Unsupported journal fields');
  require(input.schemaVersion==='1.0.0'&&input.kind==='SYNTHETIC_STORAGE_EXECUTION_JOURNAL'&&input.simulationOnly===true&&input.controlAction==='DENY'&&input.behavioralCasesRun===0,'Unsupported journal claims');
  require(Array.isArray(input.events)&&input.events.length<=MAX_EVENTS&&Buffer.byteLength(JSON.stringify(input))<=MAX_BYTES,'Oversized journal');
  const restored=new StorageExecutionJournal(input.runId,root);
  require(isDeepStrictEqual(input.sourcePins,restored.#header.sourcePins),'Journal source pins changed');
  for(const e of input.events){
   require(keys(e,'sequence previousSHA256 operation payload receipt eventSHA256')&&['STEP','FAULT','RISK_ASSESSMENT'].includes(e.operation),'Invalid journal event');
   const {eventSHA256,...body}=e;
   require(e.sequence===restored.#events.length+1&&e.previousSHA256===restored.#head&&eventSHA256===digest(body),'Journal sequence/hash mismatch');
   const actual=restored.#append(e.operation,e.payload);
   require(isDeepStrictEqual(actual,e.receipt),'Journal receipt disagrees with reconstructed simulation');
  }
  require(restored.#head===input.headSHA256,'Journal head mismatch');return restored;
 }
}

export function parseStorageJournal(text,root=ROOT){
 require(typeof text==='string'&&Buffer.byteLength(text)<=MAX_BYTES,'Oversized journal text');
 return StorageExecutionJournal.restore(JSON.parse(text),root);
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{
  if(process.argv.length===4&&process.argv[2]==='--replay'){
   const fd=openSync(resolve(process.argv[3]),constants.O_RDONLY|constants.O_NONBLOCK);let bytes;
   try{const stat=fstatSync(fd);require(stat.isFile()&&stat.size<=MAX_BYTES,'Journal file must be a bounded regular file');bytes=Buffer.alloc(MAX_BYTES+1);let size=0,n;while(size<bytes.length&&(n=readSync(fd,bytes,size,bytes.length-size,null))>0)size+=n;require(size<=MAX_BYTES,'Oversized journal file');bytes=bytes.subarray(0,size);}finally{closeSync(fd);}
   const j=parseStorageJournal(bytes.toString('utf8'));console.log(JSON.stringify({result:'SIMULATION_RECONSTRUCTION_ONLY',observation:j.observe(),journalHeadSHA256:j.export().headSHA256},null,2));
  }else{
   require(process.argv.length===2,'Usage: node tools/storage_execution_journal.mjs [--replay journal.json]');
   const j=new StorageExecutionJournal('synthetic.journal.example.1');j.step({id:'discharge',storagePowerKw:'2'});j.step({id:'idle',storagePowerKw:'0'});console.log(JSON.stringify(j.export(),null,2));
  }
 }catch(e){console.error(e.message);process.exitCode=1;}
}
