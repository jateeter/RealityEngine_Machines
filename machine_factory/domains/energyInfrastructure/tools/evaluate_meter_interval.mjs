#!/usr/bin/env node
/** Offline counter-difference semantics, never carbon accounting or operational approval. */
import {readFileSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {isDeepStrictEqual} from 'node:util';
import Ajv2020 from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';
import {validateFunctionBindings} from './validate_function_bindings.mjs';
const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const read=p=>JSON.parse(readFileSync(p,'utf8'));
const hash=b=>createHash('sha256').update(b).digest('hex');
const require=(ok,msg)=>{if(!ok)throw Error(msg);};
const keys=(o,expected)=>o&&typeof o==='object'&&!Array.isArray(o)&&isDeepStrictEqual(Object.keys(o).sort(),expected.split(' ').sort());
const ajv=new Ajv2020({strict:false});addFormats(ajv);
const validTime=ajv.compile({type:'string',format:'date-time',pattern:'^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d{3})?Z$'});
const time=s=>{require(validTime(s)&&Number.isFinite(Date.parse(s)),'Invalid or unsupported UTC timestamp');return Date.parse(s);};
const validIdentity=ajv.compile({type:'object',additionalProperties:false,required:['sourceSystemId','namespaceUri','identifier'],properties:{sourceSystemId:{type:'string',minLength:1},namespaceUri:{type:'string',format:'uri'},identifier:{type:'string',minLength:1}}});

export function decodeMeterEnergy(blockHex,root=ROOT) {
 const profile=read(resolve(root,'assets/meter-energy-profile.json'));
 const path='intake/public-models/sunspec/model_203.json',bytes=readFileSync(resolve(root,path));
 const receipt=read(resolve(root,'assets/source-receipt.json'));
 require(profile.schemaVersion==='1.0.0'&&profile.kind==='OFFLINE_METER_ENERGY_SUBSET'&&profile.modelId===203&&profile.sourcePath===path&&profile.sourceSHA256===hash(bytes)&&receipt.files.find(f=>f.path===path)?.sha256===hash(bytes)&&profile.modelCommit===receipt.commit,'Pinned meter source mismatch');
 require(profile.byteOrder==='BIG_ENDIAN'&&profile.notAccumulated===0&&profile.missingScaleFactor===32768&&isDeepStrictEqual(profile.scaleRange,[-10,10])&&profile.normativeFsgimPropertyEquivalence===false&&profile.peerVerified===false&&profile.controlAction==='DENY','Unsupported meter profile');
 const source=JSON.parse(bytes);let count=0;const points=new Map();
 for(const [i,p] of source.group.points.entries()){points.set(p.name,{offset:count,pointer:`/group/points/${i}`,definition:p});count+=p.size;}
 require(count===profile.registerCount&&keys(profile.points,'TotWhImp TotWhExp TotWh_SF'),'Meter profile inventory mismatch');
 for(const n of ['TotWhImp','TotWhExp','TotWh_SF'])require(isDeepStrictEqual(points.get(n),profile.points[n]),'Meter point definition/offset drift');
 for(const n of ['TotWhImp','TotWhExp']){const p=points.get(n).definition;require(p.type==='acc32'&&p.size===2&&p.units==='Wh'&&p.sf==='TotWh_SF','Unsupported energy counter definition');}
 require(points.get('TotWh_SF').definition.type==='sunssf'&&points.get('TotWh_SF').definition.size===1,'Unsupported energy scale definition');
 require(typeof blockHex==='string'&&/^([0-9a-fA-F]{4})+$/.test(blockHex)&&blockHex.length===count*4,'Malformed/truncated/extra meter block');
 const b=Buffer.from(blockHex,'hex');require(b.readUInt16BE(0)===203&&b.readUInt16BE(2)===count-2,'Meter ID/length mismatch');
 const imported=b.readUInt32BE(points.get('TotWhImp').offset*2),exported=b.readUInt32BE(points.get('TotWhExp').offset*2),sf=b.readInt16BE(points.get('TotWh_SF').offset*2),reasons=[];
 if(imported===0)reasons.push('IMPORT_NOT_ACCUMULATED');if(exported===0)reasons.push('EXPORT_NOT_ACCUMULATED');
 if(sf===-32768)reasons.push('ENERGY_SCALE_NOT_IMPLEMENTED');else require(sf>=-10&&sf<=10,'Energy scale outside range');
 return {rawImported:imported===0?null:imported,rawExported:exported===0?null:exported,scaleExponent:sf===-32768?null:sf,reasons};
}
function decimal(n,exponent) {
 const v=BigInt(n);if(exponent>=0)return (v*10n**BigInt(exponent)).toString();
 const s=v.toString().padStart(1-exponent,'0');return (s.slice(0,exponent)+'.'+s.slice(exponent)).replace(/0+$/,'').replace(/\.$/,'');
}
export function evaluateMeterInterval(input,root=ROOT) {
 require(keys(input,'schemaVersion kind sourceProjection sourceProjectionSHA256 meterAssetId boundaryId modelId start end evaluationAt maxAgeMs maxIntervalMs synthetic engineeringReview controlAction behavioralCasesRun'),'Unsupported interval fields');
 require(input.schemaVersion==='1.0.0'&&input.kind==='SYNTHETIC_METER_ENERGY_INTERVAL'&&input.sourceProjection==='assets/function-bindings/generic.json'&&input.boundaryId==='FACILITY_PCC'&&input.modelId===203&&input.synthetic===true&&input.engineeringReview==='PENDING'&&input.controlAction==='DENY'&&input.behavioralCasesRun===0,'Unsupported interval scope/claims');
 require(Number.isSafeInteger(input.maxAgeMs)&&input.maxAgeMs>0&&input.maxAgeMs<=3600000&&Number.isSafeInteger(input.maxIntervalMs)&&input.maxIntervalMs>0&&input.maxIntervalMs<=86400000,'Invalid generic time policy');
 const bytes=readFileSync(resolve(root,input.sourceProjection));require(hash(bytes)===input.sourceProjectionSHA256,'Interval projection hash mismatch');
 const p=JSON.parse(bytes);require(!validateFunctionBindings(p,root).length,'Invalid source function projection');
 require(input.meterAssetId===p.accounting.facilityNetMeterAssetId&&p.bindings.some(b=>b.assetId===input.meterAssetId&&b.functions.some(f=>f.concept==='Meter')),'Interval meter is not selected PCC Meter');
 const evaluation=time(input.evaluationAt),readings=[];
 for(const r of [input.start,input.end]) {
  require(keys(r,'observedAt receivedAt counterEpochId sourceIdentity quality blockHex')&&validIdentity(r.sourceIdentity)&&typeof r.counterEpochId==='string'&&r.counterEpochId.length>0&&['GOOD','BAD','UNKNOWN'].includes(r.quality),'Invalid meter reading metadata');
  const observed=time(r.observedAt),received=time(r.receivedAt);require(observed<=received&&received<=evaluation,'Meter timestamps out of order');
  readings.push({observed,received,...decodeMeterEnergy(r.blockHex,root)});
 }
 require(isDeepStrictEqual(input.start.sourceIdentity,input.end.sourceIdentity),'Meter source identity changed');
 require(input.start.counterEpochId===input.end.counterEpochId,'Counter epoch changed; interval must be split');
 const [a,b]=readings,duration=b.observed-a.observed;
 require(duration>0&&duration<=input.maxIntervalMs&&a.received<=b.received,'Invalid or overlong counter interval');
 const reasons=[...new Set([...a.reasons,...b.reasons])];
 if(input.start.quality!=='GOOD'||input.end.quality!=='GOOD')reasons.push('SOURCE_QUALITY_NOT_GOOD');
 if(evaluation-b.observed>input.maxAgeMs)reasons.push('STALE_INTERVAL_END');
 if(a.scaleExponent!==b.scaleExponent)reasons.push('ENERGY_SCALE_CHANGED');
 if((a.rawImported!==null&&b.rawImported!==null&&b.rawImported<a.rawImported)||(a.rawExported!==null&&b.rawExported!==null&&b.rawExported<a.rawExported))reasons.push('COUNTER_DISCONTINUITY_RESET_OR_ROLLOVER');
 const eligible=!reasons.length;
 return {verificationType:'SYNTHETIC_COUNTER_INTERVAL_ONLY',eligible,reasons,durationMs:duration,
  importedWh:eligible?decimal(b.rawImported-a.rawImported,b.scaleExponent):null,
  exportedWh:eligible?decimal(b.rawExported-a.rawExported,b.scaleExponent):null,
  importedKWh:eligible?decimal(b.rawImported-a.rawImported,b.scaleExponent-3):null,
  exportedKWh:eligible?decimal(b.rawExported-a.rawExported,b.scaleExponent-3):null,
  carbonIntensity:null,carbonStatus:'NOT_COMPUTED_NO_EMISSIONS_FACTOR',controlAction:'DENY',behavioralCasesRun:0};
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
 try {
  if(process.argv.length!==3)throw Error('Usage: node tools/evaluate_meter_interval.mjs <interval.json>');
  console.log(JSON.stringify({result:'PASS',...evaluateMeterInterval(read(resolve(process.argv[2])))},null,2));
 }catch(e){console.error(e.message);process.exitCode=1;}
}
