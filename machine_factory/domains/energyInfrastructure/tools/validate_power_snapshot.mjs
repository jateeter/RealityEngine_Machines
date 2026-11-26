#!/usr/bin/env node
/** Offline project semantics only: exact decimal watts, no energy integration or control. */
import {readFileSync} from 'node:fs';
import {resolve, dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import Ajv2020 from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';
import {validateFunctionBindings} from './validate_function_bindings.mjs';
const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const read=p=>JSON.parse(readFileSync(p,'utf8'));

// Integer source values and decimal scale factors avoid binary floating-point rounding.
function watts(sample) {
 let n=BigInt(sample.rawValue)*(sample.positiveDirection==='EXPORT'?-1n:1n);
 const exponent=sample.scaleExponent+(sample.unit==='kW'?3:0);
 if(exponent>=0)return (n*10n**BigInt(exponent)).toString();
 const sign=n<0n?'-':'';if(n<0n)n=-n;
 const digits=n.toString().padStart(1-exponent,'0');
 return (sign+digits.slice(0,exponent)+'.'+digits.slice(exponent)).replace(/0+$/,'').replace(/\.$/,'');
}

export function evaluatePowerSnapshot(snapshot,root=ROOT) {
 const errors=[],observations=[];
 const ajv=new Ajv2020({allErrors:true,strict:false});addFormats(ajv);
 const validate=ajv.compile(read(resolve(root,'assets/active-power-snapshot.schema.json')));
 if(!validate(snapshot))return {errors:validate.errors.map(e=>`${e.instancePath}: ${e.message}`),observations};
 // The schema allowlists paths before any caller-controlled path is read.
 const path=resolve(root,snapshot.sourceProjection),bytes=readFileSync(path);
 if(createHash('sha256').update(bytes).digest('hex')!==snapshot.sourceProjectionSHA256)errors.push('Projection hash mismatch');
 const projection=JSON.parse(bytes);errors.push(...validateFunctionBindings(projection,root));
 const bindings=new Map(projection.bindings.map(b=>[b.assetId,b]));
 const boundaries=new Map(projection.accounting.resourceGroups.map(g=>[g.id,g.primaryViewAssetId]));
 boundaries.set('FACILITY_PCC',projection.accounting.facilityNetMeterAssetId);
 const ids=new Set(),seenBoundaries=new Set(),aliases=new Set();
 const evaluation=Date.parse(snapshot.evaluationAt);
 for(const s of snapshot.samples) {
  if(ids.has(s.id))errors.push('Duplicate sample identity');ids.add(s.id);
  if(seenBoundaries.has(s.boundaryId))errors.push('Duplicate boundary snapshot; do not sum conversion-chain views');seenBoundaries.add(s.boundaryId);
  if(boundaries.get(s.boundaryId)!==s.assetId)errors.push('Measurement is not the selected boundary primary');
  const b=bindings.get(s.assetId),f=b?.functions.find(f=>f.projectionId===s.functionProjectionId);
  if(!f||!['Meter','Load','Generator'].includes(f.concept))errors.push('Unknown or unsupported function projection');
  if(s.boundaryId==='FACILITY_PCC'&&f?.concept!=='Meter')errors.push('Facility measurement requires Meter');
  if(s.boundaryId!=='FACILITY_PCC'&&f?.concept==='Meter')errors.push('Resource measurement requires Load or Generator');
  const key=JSON.stringify([s.sourceIdentity.sourceSystemId,s.sourceIdentity.namespaceUri,s.sourceIdentity.identifier]);
  if(aliases.has(key))errors.push('Source point reused across accounting boundaries');aliases.add(key);
  const observed=Date.parse(s.observedAt),received=Date.parse(s.receivedAt);
  const invalidTime=![observed,received,evaluation].every(Number.isFinite)||observed>received||received>evaluation;
  if(invalidTime)errors.push('Snapshot timestamps unsupported or out of order');
  if(s.quality==='GOOD'&&s.rawValue===null)errors.push('GOOD sample has no value');
  const reasons=[];
  if(s.quality!=='GOOD')reasons.push('QUALITY_'+s.quality);
  if(s.rawValue===null)reasons.push('MISSING_VALUE');
  if(evaluation-observed>snapshot.maxAgeMs)reasons.push('STALE');
  if(invalidTime)reasons.push('INVALID_TIME');
  const value=reasons.length?null:watts(s);
  if(value!==null&&((f?.concept==='Load'&&value.startsWith('-'))||(f?.concept==='Generator'&&!value.startsWith('-')&&value!=='0')))errors.push('Function direction disagrees with signed active power');
  observations.push({id:s.id,boundaryId:s.boundaryId,eligible:!reasons.length,wattsNetImportPositive:value,reasons});
 }
 if(seenBoundaries.size!==boundaries.size||[...boundaries.keys()].some(b=>!seenBoundaries.has(b)))errors.push('Incomplete accounting boundary snapshot');
 // Fail the entire batch closed if any structural/source/semantic error occurred.
 if(errors.length)for(const o of observations){o.eligible=false;o.wattsNetImportPositive=null;o.reasons.push('INVALID_SNAPSHOT');}
 return {errors,observations};
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
 try {
  if(process.argv.length!==3)throw Error('Usage: node tools/validate_power_snapshot.mjs <snapshot.json>');
  const result=evaluatePowerSnapshot(read(resolve(process.argv[2])));
  console.log(JSON.stringify({result:result.errors.length?'FAIL':'PASS',verificationType:'SYNTHETIC_SNAPSHOT_SEMANTICS_ONLY',controlAction:'DENY',behavioralCasesRun:0,...result},null,2));process.exitCode=result.errors.length?1:0;
 }catch(e){console.error(e.message);process.exitCode=1;}
}
