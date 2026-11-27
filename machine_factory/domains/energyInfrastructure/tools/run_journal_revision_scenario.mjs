#!/usr/bin/env node
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {buildJournalStorageScenario} from './run_journal_storage_scenario.mjs';
import {trajectoryDigest} from './evaluate_carbon_trajectories.mjs';
import {journalRevisionDigest,evaluateJournalRevisions} from './evaluate_journal_revisions.mjs';
const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'..');
export function buildJournalRevisionScenario(root=ROOT){
 const baselineLedger=buildJournalStorageScenario(root).carbonLedger,baselineLedgerDigest=trajectoryDigest(baselineLedger);
 const first={id:'original',parentRevisionDigest:null,revisionDigest:null,evaluationAt:baselineLedger.evaluationAt,factors:structuredClone(baselineLedger.factors)};first.revisionDigest=journalRevisionDigest(baselineLedgerDigest,first);
 const second={id:'corrected',parentRevisionDigest:first.revisionDigest,revisionDigest:null,evaluationAt:'2026-11-25T00:45:11.000Z',factors:structuredClone(first.factors)};
 Object.assign(second.factors[0].factor,{revision:'synthetic.storage.factor.1.r2',intensity:'300',issuedAt:'2026-11-25T00:45:10.000Z'});second.revisionDigest=journalRevisionDigest(baselineLedgerDigest,second);
 return {schemaVersion:'1.0.0',kind:'SYNTHETIC_JOURNAL_CARBON_REVISION_ARCHIVE',baselineLedger,baselineLedgerDigest,revisions:[first,second],evaluationAt:'2026-11-25T00:45:20.000Z',asOf:'2026-11-25T00:45:05.000Z',engineeringReview:'PENDING',controlAction:'DENY',behavioralCasesRun:0};
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{if(process.argv.length!==2)throw Error('Usage: node tools/run_journal_revision_scenario.mjs');const input=buildJournalRevisionScenario();console.log(JSON.stringify({input,result:evaluateJournalRevisions(input),latestReport:evaluateJournalRevisions({...input,asOf:input.evaluationAt})},null,2));}
 catch(e){console.error(e.message);process.exitCode=1;}
}
