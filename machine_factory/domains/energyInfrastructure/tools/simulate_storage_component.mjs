#!/usr/bin/env node
/** Offline held-interval component surrogate; no device or transport access. */
import {readFileSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {screenStorageProposal} from './screen_storage_proposal.mjs';
import {decodeMeterEnergy,evaluateMeterInterval} from './evaluate_meter_interval.mjs';
import {decodeSunSpecPower} from './decode_sunspec_power.mjs';
const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const hash=b=>createHash('sha256').update(b).digest('hex');
const require=(ok,msg)=>{if(!ok)throw Error(msg);};
const decimal=m=>{const sign=m<0?'-':'';m=Math.abs(m);return sign+`${Math.floor(m/1000000)}.${String(m%1000000).padStart(6,'0')}`;};
const clone=x=>structuredClone(x);
const SCOPE={simulationOnly:true,controlAction:'DENY',behavioralCasesRun:0,carriedCarbonGCO2e:null};

export class StorageComponentSimulator {
 #root; #template; #energy=5000000; #previous='0'; #time=Date.parse('2026-01-01T00:00:00.000Z');
 #revision=0; #faults=new Set(); #receipts=new Map(); #profile; #provenance; #meter; #imported=1000000; #exported=100000;
 constructor(root=ROOT) {
  this.#root=root;
  const templateBytes=readFileSync(resolve(root,'assets/storage-proposal-screen.json'));
  this.#template=JSON.parse(templateBytes);
  require(this.#template.state.criticalDemandKw==='2'&&this.#template.state.otherDemandKw==='1'&&this.#template.state.pvGenerationKw==='1','Unsupported simulator load/generation assumptions');
  const profileBytes=readFileSync(resolve(root,'assets/generic-storage-screen-profile.json'));
  const p=JSON.parse(profileBytes);
  require(p.chargeEfficiency==='0.9'&&p.dischargeEfficiency==='0.8','Unsupported simulator efficiencies');
  require(hash(profileBytes)===this.#template.profileSHA256,'Simulator profile binding mismatch');
  this.#profile=JSON.parse(readFileSync(resolve(root,'assets/sunspec-power-profile.json'))).models.find(m=>m.modelId===203);
  this.#meter=JSON.parse(readFileSync(resolve(root,'assets/meter-energy-profile.json')));
  this.#provenance={version:'energy-storage-component/0.2.0',implementationSHA256:hash(readFileSync(fileURLToPath(import.meta.url))),templateSHA256:hash(templateBytes),profileSHA256:hash(profileBytes)};
  // Validate source bindings, profile, and pinned model before exposing any observation.
  require(screenStorageProposal(this.#frame('bootstrap','0'),root).eligibleForFurtherSimulation,'Invalid simulator bootstrap');this.observe();
 }
 #frame(id,power) {
  const f=clone(this.#template),iso=offset=>new Date(this.#time+offset).toISOString();
  const s=f.state,q=f.proposal;
  Object.assign(s,{observedAt:iso(0),receivedAt:iso(100),stateRevision:`sim.${this.#revision}`,topologyRevision:'sim.connected.1',storedEnergyKWh:decimal(this.#energy),previousStorageKw:this.#previous,
   quality:this.#faults.has('TELEMETRY_UNKNOWN')?'UNKNOWN':'GOOD',protectiveInterlocks:this.#faults.has('PROTECTION_BLOCKED')?'BLOCKED':'HEALTHY',riskDisposition:this.#faults.has('RISK_UNKNOWN')?'UNKNOWN':'CLEAR'});
  if(s.quality==='UNKNOWN')for(const key of ['storedEnergyKWh','previousStorageKw','criticalDemandKw','otherDemandKw','pvGenerationKw'])s[key]=null;
  Object.assign(q,{id,issuedAt:iso(500),expiresAt:iso(2000),stateRevision:s.stateRevision,topologyRevision:s.topologyRevision,storagePowerKw:power,intervalHours:'0.25',criticalServedKw:'2',claimedCarbonReductionPercent:'0'});
  f.evaluationAt=iso(1000);return f;
 }
 #readback(watts,imported,exported,unknown=false) {
  const m=this.#profile,e=this.#meter,block=Buffer.alloc(m.registerCount*2);
  block.writeUInt16BE(203,0);block.writeUInt16BE(m.registerCount-2,2);
  block.writeUInt16BE(unknown?32768:watts&65535,m.powerOffset*2);block.writeUInt16BE(unknown?32768:0,m.scaleOffset*2);
  block.writeUInt32BE(unknown?0:imported,e.points.TotWhImp.offset*2);
  block.writeUInt32BE(unknown?0:exported,e.points.TotWhExp.offset*2);
  block.writeInt16BE(unknown?-32768:-2,e.points.TotWh_SF.offset*2);
  const blockHex=block.toString('hex'),power=decodeSunSpecPower(203,blockHex,this.#root),energy=decodeMeterEnergy(blockHex,this.#root);
  require(unknown?power.quality==='UNKNOWN'&&energy.scaleExponent===null&&energy.rawImported===null&&energy.rawExported===null:power.quality==='GOOD'&&power.rawValue===watts&&power.scaleExponent===0&&energy.rawImported===imported&&energy.rawExported===exported&&energy.scaleExponent===-2&&!energy.reasons.length,'Simulator readback mismatch');
  return {blockHex,power,energy};
 }
 observe() {
  const unknown=this.#faults.has('TELEMETRY_UNKNOWN');
  const readback=this.#readback(2000-Math.round(Number(this.#previous)*1000),this.#imported,this.#exported,unknown);
  return {...SCOPE,provenance:clone(this.#provenance),observedAt:new Date(this.#time).toISOString(),stateRevision:`sim.${this.#revision}`,storedEnergyKWh:unknown?null:decimal(this.#energy),faults:[...this.#faults].sort(),selectedPoints:['W','W_SF','TotWhImp','TotWhExp','TotWh_SF'],...readback};
 }
 #interval(start,end,time) {
  const endpoint=(observation,t)=>({observedAt:new Date(t).toISOString(),receivedAt:new Date(t+100).toISOString(),counterEpochId:'synthetic.storage.component.scenario.1',sourceIdentity:{sourceSystemId:'synthetic.storage.component',namespaceUri:'urn:energy:synthetic:sunspec',identifier:'REF01.pcc.203'},quality:'GOOD',blockHex:observation.blockHex});
  const input={schemaVersion:'1.0.0',kind:'SYNTHETIC_METER_ENERGY_INTERVAL',sourceProjection:this.#template.sourceProjection,sourceProjectionSHA256:this.#template.sourceProjectionSHA256,meterAssetId:'fixture.meter',boundaryId:'FACILITY_PCC',modelId:203,start:endpoint(start,this.#time),end:endpoint(end,time),evaluationAt:new Date(time+1000).toISOString(),maxAgeMs:2000,maxIntervalMs:900000,synthetic:true,engineeringReview:'PENDING',controlAction:'DENY',behavioralCasesRun:0};
  return {input,result:evaluateMeterInterval(input,this.#root)};
 }
 injectFault(fault) {
  require(['TELEMETRY_UNKNOWN','PROTECTION_BLOCKED','RISK_UNKNOWN'].includes(fault),'Unsupported simulated fault');
  if(!this.#faults.has(fault)){this.#faults.add(fault);this.#revision++;}return this.observe();
 }
 step(request) {
  require(request&&Object.keys(request).sort().join(',')==='id,storagePowerKw','Unsupported simulator request fields');
  const {id,storagePowerKw:power}=request;
  require(typeof id==='string'&&/^[a-zA-Z0-9_.-]{1,80}$/.test(id),'Invalid simulator request ID');
  require(typeof power==='string'&&/^-?(0|[1-9]\d?)(\.\d{1,2})?$/.test(power),'Expected bounded power decimal at 10 W resolution');
  const intent=hash(JSON.stringify({power}));
  if(this.#receipts.has(id)){
   const old=this.#receipts.get(id);require(old.intent===intent,'Conflicting replay intent');
   return {...clone(old.receipt),replayed:true};
  }
  require(this.#receipts.size<100,'Simulator request limit reached');
  const screen=screenStorageProposal(this.#frame(id,power),this.#root);
  let meterInterval=null;
  if(screen.eligibleForFurtherSimulation){
   const watts=Math.round(Number(power)*1000);
   // Independent integer mWh plant surrogate: 900 s, charge eta .9, discharge eta .8.
   const next=this.#energy+(watts>=0?-watts*625/2:-watts*225);
   require(Number.isSafeInteger(next)&&next>=0,'Unsupported simulator energy precision');
   const rational=screen.calculations.nextStoredKWh;
   require(BigInt(next)*BigInt(rational.denominator)===BigInt(rational.numerator)*1000000n,'Independent state prediction disagrees');
   const net=screen.calculations.netImportKw;
   require(BigInt(2000-watts)*BigInt(net.denominator)===BigInt(net.numerator)*1000n,'Independent grid prediction disagrees');
   // 900 seconds = .25 h; raw energy resolution is .01 Wh, hence 25 raw/W.
   const netWatts=2000-watts,imported=this.#imported+Math.max(netWatts,0)*25,exported=this.#exported+Math.max(-netWatts,0)*25;
   require([imported,exported].every(n=>Number.isSafeInteger(n)&&n>0&&n<=0xffffffff),'Counter overflow; no guessed rollover');
   const candidate=this.#readback(netWatts,imported,exported);
   meterInterval=this.#interval(this.observe(),candidate,this.#time+900000);
   require(meterInterval.result.eligible,'Candidate interval rejected');
   this.#energy=next;this.#previous=power;this.#time+=900000;this.#revision++;
   this.#imported=imported;this.#exported=exported;
  }
  const receipt={...SCOPE,id,applied:screen.eligibleForFurtherSimulation,replayed:false,screen,meterInterval,observation:this.observe()};
  this.#receipts.set(id,{intent,receipt:clone(receipt)});return receipt;
 }
}

export function runStorageComponentScenario(root=ROOT) {
 const sim=new StorageComponentSimulator(root),events=[];
 for(const request of [{id:'discharge',storagePowerKw:'2'},{id:'discharge',storagePowerKw:'2'},{id:'idle',storagePowerKw:'0'},{id:'export',storagePowerKw:'3'},{id:'reserve',storagePowerKw:'3'}])events.push(sim.step(request));
 events.push({injectedFault:'TELEMETRY_UNKNOWN',observation:sim.injectFault('TELEMETRY_UNKNOWN')});
 events.push(sim.step({id:'fault-hold',storagePowerKw:'0'}));
 return {result:'COMPONENT_SIMULATION_ONLY_NOT_DOMAIN_ACCEPTANCE',...SCOPE,events};
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{require(process.argv.length===2,'Usage: node tools/simulate_storage_component.mjs');console.log(JSON.stringify(runStorageComponentScenario(),null,2));}
 catch(e){console.error(e.message);process.exitCode=1;}
}
