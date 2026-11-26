#!/usr/bin/env node
/** Exact synthetic retrospective accounting, never a dispatch or compliance approval. */
import {readFileSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {isDeepStrictEqual} from 'node:util';
import Ajv2020 from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';
import {evaluateMeterInterval} from './evaluate_meter_interval.mjs';
const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const read=p=>JSON.parse(readFileSync(p,'utf8'));
const require=(ok,msg)=>{if(!ok)throw Error(msg);};
const keys=(o,s)=>o&&typeof o==='object'&&!Array.isArray(o)&&isDeepStrictEqual(Object.keys(o).sort(),s.split(' ').sort());
const ajv=new Ajv2020({strict:false});addFormats(ajv);
const date=ajv.compile({type:'string',format:'date-time',pattern:'^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d{3})?Z$'});
const time=s=>{require(date(s)&&Number.isFinite(Date.parse(s)),'Invalid carbon timestamp');return Date.parse(s);};
function rational(n,d=1n){if(n===0n)return [0n,1n];let a=n,b=d;while(b){const t=a%b;a=b;b=t;}return [n/a,d/a];}
function parse(s,precision=12){require(typeof s==='string'&&s.length<=64&&/^(0|[1-9]\d*)(\.\d+)?$/.test(s),'Expected nonnegative bounded decimal string');const [a,b='']=s.split('.');require(b.length<=precision,'Unsupported decimal precision');return rational(BigInt(a+b),10n**BigInt(b.length));}
const add=(a,b)=>rational(a[0]*b[1]+b[0]*a[1],a[1]*b[1]);
const mul=(a,b)=>rational(a[0]*b[0],a[1]*b[1]);
const encode=a=>({numerator:a[0].toString(),denominator:a[1].toString()});
const BASIS={gasBasis:'CO2e',gwpBasis:'SYNTHETIC_GWP_BASIS',emissionsScope:'DIRECT',energyBoundary:'IMPORTED_ELECTRICITY_AT_PCC',signalType:'ATTRIBUTIONAL_AVERAGE',reportingBasis:'LOCATION_BASED',geography:'SYNTHETIC_ZONE',factorUnit:'gCO2e/kWh',dataRole:'SYNTHETIC_OBSERVATION'};

export function evaluateCarbonLedger(input,root=ROOT) {
 require(keys(input,'schemaVersion kind sourceInterval sourceIntervalSHA256 evaluationAt basis rows accountingUse engineeringReview controlAction behavioralCasesRun'),'Unsupported ledger fields');
 require(input.schemaVersion==='1.0.0'&&input.kind==='SYNTHETIC_IMPORT_CARBON_LEDGER'&&input.sourceInterval==='assets/meter-energy-interval.json'&&input.accountingUse==='RETROSPECTIVE_ONLY'&&input.engineeringReview==='PENDING'&&input.controlAction==='DENY'&&input.behavioralCasesRun===0,'Unsupported ledger scope/claims');
 require(isDeepStrictEqual(input.basis,BASIS),'Unsupported or incompatible accounting basis');
 const bytes=readFileSync(resolve(root,input.sourceInterval));require(createHash('sha256').update(bytes).digest('hex')===input.sourceIntervalSHA256,'Ledger source interval hash mismatch');
 const base=JSON.parse(bytes);evaluateMeterInterval(base,root);
 require(Array.isArray(input.rows)&&input.rows.length>0&&input.rows.length<=100,'Invalid ledger row count');
 const evaluation=time(input.evaluationAt),ids=new Set(),reasons=[],receipts=[];let previous=null;
 let imported=[0n,1n],exported=[0n,1n],mass=[0n,1n];
 for(const row of input.rows) {
  require(keys(row,'id meterInterval factor')&&typeof row.id==='string'&&row.id.length>0&&!ids.has(row.id),'Invalid/duplicate ledger row');ids.add(row.id);
  const interval=row.meterInterval,f=row.factor;
  const energy=evaluateMeterInterval(interval,root);
  require(interval.evaluationAt===input.evaluationAt,'Interval/ledger evaluation times differ');
  require(interval.meterAssetId===base.meterAssetId&&interval.sourceProjection===base.sourceProjection&&interval.sourceProjectionSHA256===base.sourceProjectionSHA256&&isDeepStrictEqual(interval.start.sourceIdentity,base.start.sourceIdentity),'Meter/projection differs from ledger source');
  if(previous)require(isDeepStrictEqual(previous,interval.start),'Intervals overlap, have a gap or lack continuous endpoint evidence');
  previous=interval.end;
  require(keys(f,'providerId revision basis intervalStart intervalEnd issuedAt validUntil quality rights intensity'),'Unsupported factor fields');
  require(f.providerId==='SYNTHETIC_PROVIDER'&&typeof f.revision==='string'&&f.revision.length>0&&f.rights==='SYNTHETIC_FIXTURE_ONLY','Unsupported provider/revision/rights');
  require(isDeepStrictEqual(f.basis,input.basis),'Factor accounting basis mismatch');
  require(time(f.intervalStart)===time(interval.start.observedAt)&&time(f.intervalEnd)===time(interval.end.observedAt),'Factor interval mismatch');
  require(time(f.issuedAt)>=time(f.intervalEnd)&&time(f.issuedAt)<=evaluation&&time(f.validUntil)>=time(f.issuedAt),'Invalid retrospective factor publication window');
  require(['GOOD','BAD','UNKNOWN'].includes(f.quality),'Unsupported factor quality');
  const factor=f.intensity===null?null:parse(f.intensity),rowReasons=[...energy.reasons];
  if(f.quality!=='GOOD')rowReasons.push('FACTOR_QUALITY_'+f.quality);
  if(factor===null)rowReasons.push('FACTOR_VALUE_MISSING');
  if(evaluation>time(f.validUntil))rowReasons.push('FACTOR_EXPIRED');
  receipts.push({id:row.id,providerId:f.providerId,revision:f.revision,eligible:!rowReasons.length,reasons:rowReasons});
  if(rowReasons.length){reasons.push(...rowReasons.map(r=>row.id+':'+r));continue;}
  const e=parse(energy.importedKWh,13);imported=add(imported,e);exported=add(exported,parse(energy.exportedKWh,13));mass=add(mass,mul(e,factor));
 }
 const eligible=!reasons.length,zero=imported[0]===0n;
 return {verificationType:'SYNTHETIC_IMPORTED_ELECTRICITY_ACCOUNTING_ONLY',eligible,reasons,rows:receipts,
  importedKWh:eligible?encode(imported):null,exportedKWhSeparate:eligible?encode(exported):null,
  allocatedEmissionsGCO2e:eligible?encode(mass):null,
  intensityGCO2ePerKWh:eligible&&!zero?encode(rational(mass[0]*imported[1],mass[1]*imported[0])):null,
  intensityStatus:!eligible?'UNKNOWN_INPUT':zero?'UNDEFINED_ZERO_IMPORTED_ENERGY':'EXACT_SYNTHETIC_RATIO',
  exportCreditApplied:false,controlAction:'DENY',behavioralCasesRun:0};
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
 try {
  if(process.argv.length!==3)throw Error('Usage: node tools/evaluate_carbon_ledger.mjs <ledger.json>');
  console.log(JSON.stringify({result:'PASS',...evaluateCarbonLedger(read(resolve(process.argv[2])))},null,2));
 }catch(e){console.error(e.message);process.exitCode=1;}
}
