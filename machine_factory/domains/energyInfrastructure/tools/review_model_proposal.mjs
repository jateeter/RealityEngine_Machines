#!/usr/bin/env node
/** Strict untrusted proposal data, evaluated on an offline clone with no command authority. */
import {readFileSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {isDeepStrictEqual} from 'node:util';
import {StorageExecutionJournal} from './storage_execution_journal.mjs';
const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const require=(ok,msg)=>{if(!ok)throw Error(msg);};
const keys=(o,list)=>o&&typeof o==='object'&&!Array.isArray(o)&&isDeepStrictEqual(Object.keys(o).sort(),list.split(' ').sort());

export function parseFlatModelProposal(text){
 require(typeof text==='string'&&Buffer.byteLength(text)<=4096,'Unsupported model text size/type');
 let i=0;const fields=new Map(),space=()=>{while(/[ \t\r\n]/.test(text[i]??'\0'))i++;};
 const string=()=>{
  const pattern=/"(?:[^"\\\u0000-\u001f]|\\(?:["\\/bfnrt]|u[0-9a-fA-F]{4}))*"/y;pattern.lastIndex=i;
  const m=pattern.exec(text);require(m,'Expected JSON string');i=pattern.lastIndex;return JSON.parse(m[0]);
 };
 space();require(text[i++]==='{','Expected flat JSON object');space();
 if(text[i]!=='}')for(;;){
  const key=string();require(!fields.has(key),'Duplicate model proposal key');space();require(text[i++]===':','Expected colon');space();const value=string();fields.set(key,value);space();
  if(text[i]==='}')break;require(text[i++]===',','Expected comma');space();require(text[i]!=='}','Trailing comma');
 }
 require(text[i++]==='}','Expected closing object');space();require(i===text.length,'Trailing model response content');
 const proposal=Object.fromEntries(fields);
 require(keys(proposal,'id storagePowerKw expectedStateSHA256'),'Unsupported model proposal fields');
 require(/^[a-zA-Z0-9_.-]{1,80}$/.test(proposal.id)&&/^-?(0|[1-9]\d?)(\.\d{1,2})?$/.test(proposal.storagePowerKw)&&/^[0-9a-f]{64}$/.test(proposal.expectedStateSHA256),'Invalid model proposal values');
 return proposal;
}

export function reviewModelProposal(input,root=ROOT){
 require(keys(input,'schemaVersion kind sourceClass reviewScope journal modelResponseText controlAction behavioralCasesRun'),'Unsupported proposal review fields');
 require(input.schemaVersion==='1.0.0'&&input.kind==='SYNTHETIC_MODEL_PROPOSAL_REVIEW'&&input.sourceClass==='SYNTHETIC_UNTRUSTED_MODEL_TEXT'&&input.reviewScope==='SIMULATION_REVIEW_ONLY'&&input.controlAction==='DENY'&&input.behavioralCasesRun===0,'Unsupported proposal review scope/claims');
 const result={verificationType:'UNTRUSTED_MODEL_DATA_SIMULATION_REVIEW_ONLY',reviewDisposition:'ABSTAIN_INVALID_MODEL_DATA',reason:'INVALID_OR_UNSUPPORTED_MODEL_JSON',
  modelResponseTrust:'UNTRUSTED_DATA_NOT_INSTRUCTIONS',sourceJournalValidated:false,sourceHistoryAuthenticated:false,sourceJournalHeadSHA256:null,candidateReceipt:null,hypotheticalStepApplied:false,
  originalJournalMutated:false,actionExecuted:false,modelCalled:false,providerAuthenticated:false,toolPermissionsGranted:[],readyForOperationalUse:false,
  simulationOnly:true,controlAction:'DENY',behavioralCasesRun:0};
 let proposal,clone;
 try{proposal=parseFlatModelProposal(input.modelResponseText);}catch{return result;}
 try{clone=StorageExecutionJournal.restore(input.journal,root);}catch{return {...result,reviewDisposition:'ABSTAIN_INVALID_SOURCE_HISTORY',reason:'SOURCE_HISTORY_NOT_RECONSTRUCTIBLE'};}
 result.sourceJournalValidated=true;result.sourceJournalHeadSHA256=clone.export().headSHA256;
 let receipt;try{receipt=clone.step(proposal);}catch{return {...result,reviewDisposition:'HOLD_SIMULATION_PROPOSAL',reason:'SIMULATION_INTENT_REJECTED'};}
 // This clone is discarded; neither the supplied history nor any physical entity is changed.
 return {...result,reviewDisposition:receipt.replayed?'HISTORICAL_REQUEST_REPLAY':receipt.applied?'SIMULATION_CANDIDATE_ONLY':'HOLD_SIMULATION_PROPOSAL',
  reason:receipt.replayed?'NO_NEW_CANDIDATE_FROM_REPLAY':receipt.applied?'INDEPENDENT_AUTHORIZATION_STILL_REQUIRED':'SIMULATION_SCREEN_HELD',candidateReceipt:receipt,hypotheticalStepApplied:receipt.applied&&!receipt.replayed};
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{if(process.argv.length!==3)throw Error('Usage: node tools/review_model_proposal.mjs <review.json>');console.log(JSON.stringify(reviewModelProposal(JSON.parse(readFileSync(resolve(process.argv[2]),'utf8'))),null,2));}
 catch(e){console.error(e.message);process.exitCode=1;}
}
