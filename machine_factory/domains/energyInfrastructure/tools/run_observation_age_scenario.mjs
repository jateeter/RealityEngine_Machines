#!/usr/bin/env node
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {isDeepStrictEqual} from 'node:util';
import {StorageExecutionJournal} from './storage_execution_journal.mjs';
const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'..');
export function runObservationAgeScenario(root=ROOT){
 const j=new StorageExecutionJournal('synthetic.observation.age.1',root);
 const applied=j.step({id:'before-age',storagePowerKw:'2',expectedStateSHA256:j.stateToken().expectedStateSHA256});
 const age=j.advanceEvaluationClock(1001),before=j.observe();
 const held=j.step({id:'stale-observation',storagePowerKw:'0',expectedStateSHA256:j.stateToken().expectedStateSHA256});
 const restored=StorageExecutionJournal.restore(j.export(),root);
 if(!applied.applied||age.plantClockAdvanced||held.applied||held.meterInterval!==null||!held.screen.reasons.includes('STALE_STATE')||!isDeepStrictEqual(before,j.observe())||!isDeepStrictEqual(restored.observe(),before))throw Error('Observation-age invariant failed');
 return {result:'LOGICAL_OBSERVATION_AGE_COMPONENT_ONLY',simulationOnly:true,controlAction:'DENY',behavioralCasesRun:0,applied,age,held,journal:j.export(),reconstructedObservation:restored.observe()};
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{if(process.argv.length!==2)throw Error('Usage: node tools/run_observation_age_scenario.mjs');console.log(JSON.stringify(runObservationAgeScenario(),null,2));}
 catch(e){console.error(e.message);process.exitCode=1;}
}
