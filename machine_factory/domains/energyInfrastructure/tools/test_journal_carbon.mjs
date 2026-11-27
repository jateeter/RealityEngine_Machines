import test from 'node:test';
import assert from 'node:assert/strict';
import {StorageExecutionJournal} from './storage_execution_journal.mjs';
import {evaluateJournalCarbonLedger} from './evaluate_carbon_ledger.mjs';
import {buildJournalCarbonScenario} from './run_journal_carbon_scenario.mjs';
const fraction=(n,d='1')=>({numerator:n,denominator:d});
test('journal imports weight factors exactly; exports remain separate with no credit',()=>{
 const input=buildJournalCarbonScenario(),r=evaluateJournalCarbonLedger(input);
 assert.equal(r.eligible,true);assert.deepEqual(r.importedKWh,fraction('3','4'));assert.deepEqual(r.exportedKWhSeparate,fraction('1','4'));assert.deepEqual(r.allocatedEmissionsGCO2e,fraction('250'));assert.deepEqual(r.intensityGCO2ePerKWh,fraction('1000','3'));
 assert.equal(r.rows.length,3);assert.equal(r.exportCreditApplied,false);assert.equal(r.providerQualified,false);assert.equal(r.storageCarbonInventoryKnown,false);assert.equal(r.facilityConsumptionIntensityQualified,false);assert.equal(r.operationallyAuthorized,false);assert.equal(r.controlAction,'DENY');assert.equal(r.behavioralCasesRun,0);
 assert.equal(input.journal.events.length,6);assert.equal(input.journal.events[1].receipt.replayed,true);assert.equal(input.journal.events.at(-1).receipt.applied,false);
});
test('archival evaluation preserves acquisition-time freshness rather than rewriting clocks',()=>{
 const input=buildJournalCarbonScenario(),before=structuredClone(input),first=input.journal.events[0].receipt.meterInterval.input;
 assert.equal(first.maxAgeMs,2000);assert.notEqual(first.evaluationAt,input.evaluationAt);assert.equal(evaluateJournalCarbonLedger(input).eligible,true);assert.deepEqual(input,before);
});
for(const [label,mutate] of [
 ['missing factor',x=>x.factors.pop()],
 ['extra replay factor',x=>x.factors.push({eventSHA256:x.journal.events[1].eventSHA256,factor:x.factors[0].factor})],
 ['replay binding',x=>x.factors[0].eventSHA256=x.journal.events[1].eventSHA256],
 ['wrong event order',x=>x.factors.reverse()],
 ['modified journal',x=>x.journal.events[0].receipt.meterInterval.result.importedKWh='99'],
 ['changed source pin',x=>x.journal.sourcePins.assetManifestSHA256='0'.repeat(64)],
 ['mixed basis',x=>x.factors[1].factor.basis.reportingBasis='MARKET_BASED'],
 ['wrong factor interval',x=>x.factors[0].factor.intervalEnd='2026-11-25T00:14:00.000Z'],
 ['future issue',x=>x.factors[0].factor.issuedAt='2026-11-25T00:46:00.000Z'],
 ['issue before interval end',x=>x.factors[0].factor.issuedAt='2026-11-25T00:14:00.000Z'],
 ['report before acquisition',x=>x.evaluationAt='2026-11-25T00:00:00.000Z'],
 ['forecast dispatch use',x=>x.accountingUse='DISPATCH'],
 ['real provider claim',x=>x.factors[0].factor.providerId='REAL_PROVIDER'],
 ['control claim',x=>x.controlAction='ALLOW'],
 ['unknown supplied quantity',x=>x.importedKWh='1'],
 ['behavioral claim',x=>x.behavioralCasesRun=43]
])test(`reject ${label}`,()=>{const x=buildJournalCarbonScenario();mutate(x);assert.throws(()=>evaluateJournalCarbonLedger(x));});
for(const [label,mutate] of [
 ['unknown factor',x=>x.factors[0].factor.intensity=null],
 ['bad factor quality',x=>x.factors[0].factor.quality='BAD'],
 ['expired factor',x=>{x.factors[0].factor.issuedAt='2026-11-25T00:15:00.100Z';x.factors[0].factor.validUntil='2026-11-25T00:45:00.500Z';}]
])test(`${label} produces null aggregate quantities`,()=>{
 const x=buildJournalCarbonScenario();mutate(x);const r=evaluateJournalCarbonLedger(x);assert.equal(r.eligible,false);assert.equal(r.importedKWh,null);assert.equal(r.allocatedEmissionsGCO2e,null);assert.equal(r.intensityGCO2ePerKWh,null);assert.equal(r.intensityStatus,'UNKNOWN_INPUT');
});
test('zero imported energy leaves intensity undefined and does not subtract exports',()=>{
 const x=buildJournalCarbonScenario(),j=new StorageExecutionJournal('carbon.zero');j.step({id:'balanced',storagePowerKw:'2'});j.step({id:'export',storagePowerKw:'3'});x.journal=j.export();
 x.factors=x.journal.events.map((e,i)=>({eventSHA256:e.eventSHA256,factor:{...structuredClone(x.factors[i].factor),intervalStart:e.receipt.meterInterval.input.start.observedAt,intervalEnd:e.receipt.meterInterval.input.end.observedAt}}));
 const r=evaluateJournalCarbonLedger(x);assert.equal(r.eligible,true);assert.deepEqual(r.importedKWh,fraction('0'));assert.deepEqual(r.exportedKWhSeparate,fraction('1','4'));assert.deepEqual(r.allocatedEmissionsGCO2e,fraction('0'));assert.equal(r.intensityGCO2ePerKWh,null);assert.equal(r.intensityStatus,'UNDEFINED_ZERO_IMPORTED_ENERGY');
});
test('journal without applied intervals cannot manufacture accounting energy',()=>{
 const x=buildJournalCarbonScenario(),j=new StorageExecutionJournal('carbon.none');j.injectFault('RISK_UNKNOWN');j.step({id:'held',storagePowerKw:'0'});x.journal=j.export();x.factors=[];assert.throws(()=>evaluateJournalCarbonLedger(x),/no supported applied/);
});
