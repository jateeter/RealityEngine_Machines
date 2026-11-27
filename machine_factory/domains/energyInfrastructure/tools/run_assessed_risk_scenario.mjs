#!/usr/bin/env node
/** Compose existing conservative risk assessment with source-bound offline execution. */
import {readFileSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {isDeepStrictEqual} from 'node:util';
import {StorageExecutionJournal} from './storage_execution_journal.mjs';
const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'..');
export function runAssessedRiskScenario(root=ROOT){
 const journal=new StorageExecutionJournal('synthetic.assessed-risk.1',root);
 const input=JSON.parse(readFileSync(resolve(root,'assets/risk-assessment-fixture.json')));
 input.context.topologyRevision='sim.connected.1';input.previousContext.topologyRevision='sim.connected.1';
 input.feed.complete=true;input.findings[0].applicability='AFFECTED';
 const before=journal.observe(),risk=journal.applyRiskAssessment(input),held=journal.step({id:'after-risk',storagePowerKw:'2'});
 const reconstructed=StorageExecutionJournal.restore(journal.export(),root);
 if(risk.riskDisposition!=='BLOCKED'||held.applied||held.meterInterval!==null||!isDeepStrictEqual(reconstructed.observe(),journal.observe()))throw Error('Risk/execution scenario invariant failed');
 return {result:'ASSESSED_RISK_COMPONENT_COMPOSITION_ONLY',simulationOnly:true,controlAction:'DENY',behavioralCasesRun:0,before,risk,held,journal:journal.export(),reconstructedObservation:reconstructed.observe()};
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{if(process.argv.length!==2)throw Error('Usage: node tools/run_assessed_risk_scenario.mjs');console.log(JSON.stringify(runAssessedRiskScenario(),null,2));}
 catch(e){console.error(e.message);process.exitCode=1;}
}
