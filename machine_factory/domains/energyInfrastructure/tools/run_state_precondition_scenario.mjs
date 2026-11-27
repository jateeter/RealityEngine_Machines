#!/usr/bin/env node
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {isDeepStrictEqual} from 'node:util';
import {StorageExecutionJournal} from './storage_execution_journal.mjs';
const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'..');
export function runStatePreconditionScenario(root=ROOT){
 const j=new StorageExecutionJournal('synthetic.state.precondition.1',root),first=j.stateToken();
 const accepted=j.step({id:'first',storagePowerKw:'2',expectedStateSHA256:first.expectedStateSHA256});
 const before=j.observe(),stale=j.step({id:'stale',storagePowerKw:'0',expectedStateSHA256:first.expectedStateSHA256});
 if(stale.applied||stale.meterInterval!==null||!isDeepStrictEqual(before,j.observe()))throw Error('Stale state advanced simulation');
 const current=j.stateToken(),fresh=j.step({id:'fresh',storagePowerKw:'0',expectedStateSHA256:current.expectedStateSHA256});
 const restored=StorageExecutionJournal.restore(j.export(),root);
 if(!accepted.applied||!fresh.applied||!isDeepStrictEqual(restored.observe(),j.observe()))throw Error('State-bound reconstruction failed');
 return {result:'STATE_PRECONDITION_COMPONENT_SIMULATION_ONLY',simulationOnly:true,controlAction:'DENY',behavioralCasesRun:0,firstToken:first,accepted,stale,fresh,journal:j.export(),reconstructedObservation:restored.observe()};
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{if(process.argv.length!==2)throw Error('Usage: node tools/run_state_precondition_scenario.mjs');console.log(JSON.stringify(runStatePreconditionScenario(),null,2));}
 catch(e){console.error(e.message);process.exitCode=1;}
}
