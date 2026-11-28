#!/usr/bin/env node
/** Offline held-interval component surrogate; no device or transport access. */
import {readFileSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {assessRisk} from './assess_risk.mjs';
import {screenStorageProposal} from './screen_storage_proposal.mjs';
import {decodeMeterEnergy,evaluateMeterInterval} from './evaluate_meter_interval.mjs';
import {decodeSunSpecPower} from './decode_sunspec_power.mjs';
const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const hash=b=>createHash('sha256').update(b).digest('hex');
const canonical=x=>Array.isArray(x)?'['+x.map(canonical).join(',')+']':x!==null&&typeof x==='object'?'{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canonical(x[k])).join(',')+'}':JSON.stringify(x);
const require=(ok,msg)=>{if(!ok)throw Error(msg);};
const decimal=m=>{const sign=m<0?'-':'';m=Math.abs(m);return sign+`${Math.floor(m/1000000)}.${String(m%1000000).padStart(6,'0')}`;};
const clone=x=>structuredClone(x);
const SCOPE={simulationOnly:true,controlAction:'DENY',behavioralCasesRun:0,carriedCarbonGCO2e:null};

export class StorageComponentSimulator {
 #root; #template; #energy=5000000; #previous='0'; #time=Date.parse('2026-11-25T00:00:00.000Z');
 #evaluationOffsetMs=0; #maxStateAgeMs=2000; #revision=0; #faults=new Set(); #receipts=new Map(); #profile; #provenance; #risk='CLEAR'; #runId; #meter; #imported=1000000; #exported=100000;
 constructor(root=ROOT,runId='synthetic.storage.component.scenario.1') {
  require(typeof runId==='string'&&/^[a-zA-Z0-9_.-]{1,80}$/.test(runId),'Invalid synthetic run ID');this.#runId=runId;
  this.#root=root;
  const templateBytes=readFileSync(resolve(root,'assets/storage-proposal-screen.json'));
  this.#template=JSON.parse(templateBytes);
  require(this.#template.state.criticalDemandKw==='2'&&this.#template.state.otherDemandKw==='1'&&this.#template.state.pvGenerationKw==='1','Unsupported simulator load/generation assumptions');
  const profileBytes=readFileSync(resolve(root,'assets/generic-storage-screen-profile.json'));
  const p=JSON.parse(profileBytes);this.#maxStateAgeMs=p.maxStateAgeMs;
  require(p.chargeEfficiency==='0.9'&&p.dischargeEfficiency==='0.8','Unsupported simulator efficiencies');
  require(hash(profileBytes)===this.#template.profileSHA256,'Simulator profile binding mismatch');
  this.#profile=JSON.parse(readFileSync(resolve(root,'assets/sunspec-power-profile.json'))).models.find(m=>m.modelId===203);
  this.#meter=JSON.parse(readFileSync(resolve(root,'assets/meter-energy-profile.json')));
  this.#provenance={version:'energy-storage-component/0.6.0',implementationSHA256:hash(readFileSync(fileURLToPath(import.meta.url))),templateSHA256:hash(templateBytes),profileSHA256:hash(profileBytes)};
  // Validate source bindings, profile, and pinned model before exposing any observation.
  require(screenStorageProposal(this.#frame('bootstrap','0'),root).eligibleForFurtherSimulation,'Invalid simulator bootstrap');this.observe();
 }
 #fresh(){return this.#evaluationOffsetMs+1000<=this.#maxStateAgeMs;}
 #effectiveRisk(){return this.#risk==='BLOCKED'?'BLOCKED':this.#faults.has('RISK_UNKNOWN')?'UNKNOWN':this.#risk;}
 #frame(id,power) {
  const f=clone(this.#template),iso=offset=>new Date(this.#time+offset).toISOString();
  const s=f.state,q=f.proposal;
  Object.assign(s,{observedAt:iso(0),receivedAt:iso(100),stateRevision:`sim.${this.#revision}`,topologyRevision:'sim.connected.1',storedEnergyKWh:decimal(this.#energy),previousStorageKw:this.#previous,
   quality:this.#faults.has('TELEMETRY_UNKNOWN')||!this.#fresh()?'UNKNOWN':'GOOD',protectiveInterlocks:this.#faults.has('PROTECTION_BLOCKED')?'BLOCKED':'HEALTHY',riskDisposition:this.#effectiveRisk()});
  if(s.quality==='UNKNOWN')for(const key of ['storedEnergyKWh','previousStorageKw','criticalDemandKw','otherDemandKw','pvGenerationKw'])s[key]=null;
  Object.assign(q,{id,issuedAt:iso(this.#evaluationOffsetMs+500),expiresAt:iso(this.#evaluationOffsetMs+2000),stateRevision:s.stateRevision,topologyRevision:s.topologyRevision,storagePowerKw:power,intervalHours:'0.25',criticalServedKw:'2',claimedCarbonReductionPercent:'0'});
  f.evaluationAt=iso(this.#evaluationOffsetMs+1000);return f;
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
  const unknown=this.#faults.has('TELEMETRY_UNKNOWN')||!this.#fresh();
  const readback=this.#readback(2000-Math.round(Number(this.#previous)*1000),this.#imported,this.#exported,unknown);
  return {...SCOPE,simulationRunId:this.#runId,provenance:clone(this.#provenance),observedAt:new Date(this.#time).toISOString(),receivedAt:new Date(this.#time+100).toISOString(),evaluationAt:new Date(this.#time+this.#evaluationOffsetMs+1000).toISOString(),stateAgeMs:this.#evaluationOffsetMs+1000,stateFresh:this.#fresh(),dataExclusionReasons:[...(!this.#fresh()?['STALE_STATE']:[]),...(this.#faults.has('TELEMETRY_UNKNOWN')?['TELEMETRY_UNKNOWN']:[])],stateRevision:`sim.${this.#revision}`,storedEnergyKWh:unknown?null:decimal(this.#energy),riskDisposition:this.#effectiveRisk(),faults:[...this.#faults].sort(),selectedPoints:['W','W_SF','TotWhImp','TotWhExp','TotWh_SF'],...readback};
 }
 stateToken(){
  const observation=this.observe(),sourceManifestSHA256=hash(readFileSync(resolve(this.#root,'asset-manifest.json')));
  return {simulationRunId:this.#runId,stateRevision:observation.stateRevision,sourceManifestSHA256,
   expectedStateSHA256:hash(canonical({observation,sourceManifestSHA256})),simulationOnly:true,controlAction:'DENY'};
 }
 #interval(start,end,time) {
  const endpoint=(observation,t)=>({observedAt:new Date(t).toISOString(),receivedAt:new Date(t+100).toISOString(),counterEpochId:this.#runId,sourceIdentity:{sourceSystemId:'synthetic.storage.component',namespaceUri:'urn:energy:synthetic:sunspec',identifier:'REF01.pcc.203'},quality:'GOOD',blockHex:observation.blockHex});
  const input={schemaVersion:'1.0.0',kind:'SYNTHETIC_METER_ENERGY_INTERVAL',sourceProjection:this.#template.sourceProjection,sourceProjectionSHA256:this.#template.sourceProjectionSHA256,meterAssetId:'fixture.meter',boundaryId:'FACILITY_PCC',modelId:203,start:endpoint(start,this.#time),end:endpoint(end,time),evaluationAt:new Date(time+this.#evaluationOffsetMs+1000).toISOString(),maxAgeMs:2000,maxIntervalMs:900000,synthetic:true,engineeringReview:'PENDING',controlAction:'DENY',behavioralCasesRun:0};
  return {input,result:evaluateMeterInterval(input,this.#root)};
 }
 applyRiskAssessment(input) {
  require(input&&Buffer.byteLength(JSON.stringify(input))<=16384&&Array.isArray(input.findings)&&input.findings.length<=16&&input.findings.every(f=>typeof f.id==='string'&&f.id.length<=80),'Risk simulation input bound exceeded');
  const before=this.#effectiveRisk(),prior=before==='BLOCKED'?'BLOCKED':'UNKNOWN';
  require(input.evaluationAt===new Date(this.#time+this.#evaluationOffsetMs+1000).toISOString()&&input.context?.topologyRevision==='sim.connected.1'&&input.context?.electricalMode==='GRID_CONNECTED'&&input.priorRiskDisposition===prior,'Risk/simulation clock, topology, mode or prior binding mismatch');
  require(input.sourceProjection===this.#template.sourceProjection&&input.sourceProjectionSHA256===this.#template.sourceProjectionSHA256,'Risk/simulation projection binding mismatch');
  const assessment=assessRisk(input,this.#root);
  require(Buffer.byteLength(JSON.stringify(assessment))<=8192,'Risk simulation receipt bound exceeded');
  // Only tighten synthetic posture; this entrypoint cannot grant clearance or alter electrical state.
  const next=before==='BLOCKED'?'BLOCKED':assessment.riskDisposition;
  if(next!==this.#risk){this.#risk=next;this.#revision++;}
  return {...SCOPE,previousRiskDisposition:before,riskDisposition:this.#effectiveRisk(),assessment,observation:this.observe()};
 }
 advanceEvaluationClock(deltaMs) {
  require(Number.isSafeInteger(deltaMs)&&deltaMs>0&&deltaMs<=3600000&&this.#evaluationOffsetMs+deltaMs<=3600000,'Invalid/excessive evaluation clock advance');
  this.#evaluationOffsetMs+=deltaMs;this.#revision++;
  return {...SCOPE,clockAdvanceType:'LOGICAL_EVALUATION_ONLY',evaluationClockAdvancedMs:deltaMs,plantClockAdvanced:false,observation:this.observe()};
 }
 injectFault(fault) {
  require(['TELEMETRY_UNKNOWN','PROTECTION_BLOCKED','RISK_UNKNOWN'].includes(fault),'Unsupported simulated fault');
  if(!this.#faults.has(fault)){this.#faults.add(fault);this.#revision++;}return this.observe();
 }
 step(request) {
  require(request&&['id,storagePowerKw','expectedStateSHA256,id,storagePowerKw'].includes(Object.keys(request).sort().join(',')),'Unsupported simulator request fields');
  const {id,storagePowerKw:power}=request;
  require(typeof id==='string'&&/^[a-zA-Z0-9_.-]{1,80}$/.test(id),'Invalid simulator request ID');
  require(typeof power==='string'&&/^-?(0|[1-9]\d?)(\.\d{1,2})?$/.test(power),'Expected bounded power decimal at 10 W resolution');
  const bound=Object.hasOwn(request,'expectedStateSHA256');
  require(!bound||(typeof request.expectedStateSHA256==='string'&&/^[0-9a-f]{64}$/.test(request.expectedStateSHA256)),'Invalid expected state digest');
  const intent=hash(JSON.stringify({power,expectedStateSHA256:bound?request.expectedStateSHA256:null}));
  if(this.#receipts.has(id)){
   const old=this.#receipts.get(id);require(old.intent===intent,'Conflicting replay intent');
   return {...clone(old.receipt),replayed:true};
  }
  require(this.#receipts.size<100,'Simulator request limit reached');
  const screen=screenStorageProposal(this.#frame(id,power),this.#root);
  const actual=bound?this.stateToken().expectedStateSHA256:null;
  const stateBinding=bound?{mode:'EXPECTED_STATE_SNAPSHOT',expectedSHA256:request.expectedStateSHA256,evaluatedSHA256:actual,matched:actual===request.expectedStateSHA256}:null;
  if(bound&&!stateBinding.matched){screen.eligibleForFurtherSimulation=false;screen.reasons.unshift('EXPECTED_STATE_CHANGED');screen.calculations=null;}
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
  const receipt={...SCOPE,id,applied:screen.eligibleForFurtherSimulation,replayed:false,stateBinding,screen,meterInterval,observation:this.observe()};
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
