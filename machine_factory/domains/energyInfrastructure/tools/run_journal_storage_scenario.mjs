#!/usr/bin/env node
import {readFileSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {StorageExecutionJournal} from './storage_execution_journal.mjs';
import {POLICY,evaluateJournalStorage} from './evaluate_journal_storage.mjs';
const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'..');
export function buildJournalStorageScenario(root=ROOT){
 const j=new StorageExecutionJournal('synthetic.journal.storage.1',root);
 for(const [id,storagePowerKw] of [['charge','-2'],['idle','0'],['discharge','2'],['charge','-2']])j.step({id,storagePowerKw});
 j.injectFault('TELEMETRY_UNKNOWN');j.step({id:'held',storagePowerKw:'0'});
 const journal=j.export(),basis=JSON.parse(readFileSync(resolve(root,'assets/import-carbon-ledger.json'))).basis;
 const events=journal.events.filter(e=>e.operation==='STEP'&&e.receipt.applied&&!e.receipt.replayed),evaluationAt='2026-11-25T00:45:01.000Z';
 const factors=events.map((e,i)=>({eventSHA256:e.eventSHA256,factor:{providerId:'SYNTHETIC_PROVIDER',revision:`synthetic.storage.factor.${i+1}`,basis:structuredClone(basis),intervalStart:e.receipt.meterInterval.input.start.observedAt,intervalEnd:e.receipt.meterInterval.input.end.observedAt,issuedAt:evaluationAt,validUntil:'2026-11-25T01:45:01.000Z',quality:'GOOD',rights:'SYNTHETIC_FIXTURE_ONLY',intensity:['400','200','900'][i]}}));
 const carbonLedger={schemaVersion:'1.0.0',kind:'SYNTHETIC_JOURNAL_IMPORT_CARBON_LEDGER',journal,evaluationAt,basis,factors,accountingUse:'RETROSPECTIVE_ONLY',engineeringReview:'PENDING',controlAction:'DENY',behavioralCasesRun:0};
 return {schemaVersion:'1.0.0',kind:'SYNTHETIC_JOURNAL_STORAGE_RECONCILIATION',carbonLedger,accountingPolicy:POLICY,accountingUse:'RETROSPECTIVE_ONLY',engineeringReview:'PENDING',controlAction:'DENY',behavioralCasesRun:0};
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{if(process.argv.length!==2)throw Error('Usage: node tools/run_journal_storage_scenario.mjs');const input=buildJournalStorageScenario();console.log(JSON.stringify({input,result:evaluateJournalStorage(input)},null,2));}
 catch(e){console.error(e.message);process.exitCode=1;}
}
