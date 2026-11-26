#!/usr/bin/env node
/** Offline selected-point decoding, not Modbus transport or complete device conformance. */
import {readFileSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {isDeepStrictEqual} from 'node:util';
import {evaluatePowerSnapshot} from './validate_power_snapshot.mjs';
const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const read=p=>JSON.parse(readFileSync(p,'utf8'));
const hash=b=>createHash('sha256').update(b).digest('hex');

export function decodeSunSpecPower(modelId,blockHex,root=ROOT) {
 if(![103,203].includes(modelId))throw Error('Unsupported SunSpec model');
 const profile=read(resolve(root,'assets/sunspec-power-profile.json'));
 if(profile.schemaVersion!=='1.0.0'||profile.kind!=='OFFLINE_SUNSPEC_POWER_SUBSET'||!Array.isArray(profile.models)||profile.models.length!==2||new Set(profile.models.map(m=>m.modelId)).size!==2)throw Error('Unsupported profile inventory');
 const expectedPath=`intake/public-models/sunspec/model_${modelId}.json`;
 const model=profile.models.find(m=>m.modelId===modelId);
 const receipt=read(resolve(root,'assets/source-receipt.json'));
 const bytes=readFileSync(resolve(root,expectedPath));
 if(!model||model.sourcePath!==expectedPath||model.sourceSHA256!==hash(bytes)||
    receipt.files.find(f=>f.path===expectedPath)?.sha256!==hash(bytes)||
    profile.modelCommit!==receipt.commit)throw Error('Pinned model provenance mismatch');
 const source=JSON.parse(bytes);let offset=0;const points=new Map();
 for(const [i,p] of source.group.points.entries()){points.set(p.name,{offset,pointer:`/group/points/${i}`,p});offset+=p.size;}
 const w=points.get('W'),sf=points.get('W_SF');
 if(!w||!sf||w.p.type!=='int16'||w.p.size!==1||w.p.units!=='W'||w.p.sf!=='W_SF'||sf.p.type!=='sunssf'||sf.p.size!==1||
    model.registerCount!==offset||model.powerOffset!==w.offset||model.scaleOffset!==sf.offset||model.powerPointer!==w.pointer||model.scalePointer!==sf.pointer||
    profile.byteOrder!=='BIG_ENDIAN'||profile.missingInt16!==32768||profile.missingScaleFactor!==32768||!isDeepStrictEqual(profile.scaleRange,[-10,10])||profile.controlAction!=='DENY'||profile.peerVerified!==false||profile.normativeFsgimPropertyEquivalence!==false)throw Error('Unsupported or drifted selected-point profile');
 if(typeof blockHex!=='string'||!/^([0-9a-fA-F]{4})+$/.test(blockHex)||blockHex.length!==4*offset)throw Error('Invalid/truncated/extra register block');
 const block=Buffer.from(blockHex,'hex');
 if(block.readUInt16BE(0)!==modelId||block.readUInt16BE(2)!==offset-2)throw Error('Model ID/length header mismatch');
 const rawWord=block.readUInt16BE(w.offset*2),scaleWord=block.readUInt16BE(sf.offset*2),reasons=[];
 if(rawWord===32768)reasons.push('POWER_NOT_IMPLEMENTED');
 if(scaleWord===32768)reasons.push('SCALE_NOT_IMPLEMENTED');
 const exponent=block.readInt16BE(sf.offset*2);
 if(scaleWord!==32768&&(exponent< -10||exponent>10))throw Error('SunSpec scale factor outside selected range');
 return {modelId,sourceSHA256:model.sourceSHA256,rawValue:reasons.length?null:block.readInt16BE(w.offset*2),scaleExponent:reasons.length?null:exponent,unit:'W',quality:reasons.length?'UNKNOWN':'GOOD',reasons};
}

export function evaluateSunSpecReplay(replay,root=ROOT) {
 // This replay intentionally supports one generic fixture and two selected boundaries only.
 const keys=['schemaVersion','kind','sourceSnapshot','sourceSnapshotSHA256','blocks','networkExecution','behavioralCasesRun','controlAction'];
 if(!replay||!isDeepStrictEqual(Object.keys(replay).sort(),keys.sort())||replay.schemaVersion!=='1.0.0'||replay.kind!=='SYNTHETIC_REGISTER_BLOCK_REPLAY'||replay.sourceSnapshot!=='assets/power-snapshots/generic.json'||replay.networkExecution!==false||replay.behavioralCasesRun!==0||replay.controlAction!=='DENY'||!Array.isArray(replay.blocks)||replay.blocks.length!==2)throw Error('Unsupported replay scope/claims');
 const bytes=readFileSync(resolve(root,replay.sourceSnapshot));
 if(hash(bytes)!==replay.sourceSnapshotSHA256)throw Error('Snapshot hash mismatch');
 const snapshot=JSON.parse(bytes),baseline=evaluatePowerSnapshot(snapshot,root);
 if(baseline.errors.length)throw Error('Invalid source snapshot: '+baseline.errors.join('; '));
 const seen=new Set(),decoded=[];
 for(const b of replay.blocks) {
  if(!b||!isDeepStrictEqual(Object.keys(b).sort(),['blockHex','boundaryId','modelId'])||seen.has(b.boundaryId)||!['PV_AC','FACILITY_PCC'].includes(b.boundaryId)||b.modelId!==(b.boundaryId==='PV_AC'?103:203))throw Error('Unsupported/duplicate boundary-model mapping');
  seen.add(b.boundaryId);const d=decodeSunSpecPower(b.modelId,b.blockHex,root);decoded.push({boundaryId:b.boundaryId,...d});
  const sample=snapshot.samples.find(s=>s.boundaryId===b.boundaryId);
  sample.rawValue=d.rawValue;sample.scaleExponent=d.scaleExponent??0;sample.unit=d.unit;sample.quality=d.quality;
  sample.sourceIdentity={sourceSystemId:'synthetic.sunspec-block-replay',namespaceUri:'urn:energy:synthetic:sunspec',identifier:`${b.boundaryId}/model/${b.modelId}/W`};
 }
 const result=evaluatePowerSnapshot(snapshot,root);
 return {verificationType:'OFFLINE_SELECTED_REGISTER_REPLAY_ONLY',networkExecution:false,controlAction:'DENY',behavioralCasesRun:0,decoded,...result};
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
 try {
  if(process.argv.length!==3)throw Error('Usage: node tools/decode_sunspec_power.mjs <replay.json>');
  const result=evaluateSunSpecReplay(read(resolve(process.argv[2])));
  console.log(JSON.stringify({result:result.errors.length?'FAIL':'PASS',...result},null,2));process.exitCode=result.errors.length?1:0;
 }catch(e){console.error(e.message);process.exitCode=1;}
}
