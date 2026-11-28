#!/usr/bin/env node
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {isDeepStrictEqual} from 'node:util';
import {StorageExecutionJournal} from './storage_execution_journal.mjs';
import {reviewModelProposal} from './review_model_proposal.mjs';
const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'..');
export function buildModelReviewScenario(root=ROOT){
 const j=new StorageExecutionJournal('synthetic.model.review.1',root),journal=j.export();
 return {schemaVersion:'1.0.0',kind:'SYNTHETIC_MODEL_PROPOSAL_REVIEW',sourceClass:'SYNTHETIC_UNTRUSTED_MODEL_TEXT',reviewScope:'SIMULATION_REVIEW_ONLY',journal,
  modelResponseText:JSON.stringify({id:'model.proposal.1',storagePowerKw:'2',expectedStateSHA256:j.stateToken().expectedStateSHA256}),controlAction:'DENY',behavioralCasesRun:0};
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{if(process.argv.length!==2)throw Error('Usage: node tools/run_model_review_scenario.mjs');const input=buildModelReviewScenario(),before=structuredClone(input),result=reviewModelProposal(input);if(!isDeepStrictEqual(input,before))throw Error('Review mutated input');console.log(JSON.stringify({input,result},null,2));}
 catch(e){console.error(e.message);process.exitCode=1;}
}
