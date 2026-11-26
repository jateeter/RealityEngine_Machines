import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,mkdtempSync,mkdirSync,copyFileSync,writeFileSync,rmSync,cpSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {evaluateStorageCarbon} from './evaluate_storage_carbon.mjs';
const fixture=JSON.parse(readFileSync(new URL('../assets/storage-carbon-allocation.json',import.meta.url),'utf8'));
const fresh=()=>structuredClone(fixture),f=(n,d='1')=>({numerator:n,denominator:d});
test('independent mixed-charge/loss oracle preserves emissions into discharge',()=>{
 const r=evaluateStorageCarbon(fixture);
 assert.deepEqual(r.chargedInputKWh,f('2'));assert.deepEqual(r.chargedEmissionsGCO2e,f('500'));
 assert.deepEqual(r.deliveredAcKWh,f('17','25'));assert.deepEqual(r.deliveredAllocatedGCO2e,f('250'));
 assert.deepEqual(r.remainingStoredKWh,f('17','20'));assert.deepEqual(r.remainingCarriedGCO2e,f('250'));
 assert.deepEqual(r.chargeConversionLossKWh,f('3','10'));assert.deepEqual(r.dischargeConversionLossKWh,f('17','100'));
 assert.deepEqual(r.deliveredIntensityGCO2ePerKWh,f('6250','17'));
 assert.equal(r.additionalInventoryEmissions,false);assert.equal(r.energyAllocationConserved,true);assert.equal(r.emissionsAllocationConserved,true);
 assert.equal(r.steps[0].sourceRowId,'interval.1');assert.equal(r.sourceLedgerSHA256,fixture.sourceLedgerSHA256);assert.equal(r.controlAction,'DENY');
});
test('full depletion empties energy and carbon pools exactly',()=>{
 const d=fresh();d.events[2].removedStoredKWh='1.7';d.events[2].deliveredAcKWh='1.36';const r=evaluateStorageCarbon(d);
 assert.deepEqual(r.remainingStoredKWh,f('0'));assert.deepEqual(r.remainingCarriedGCO2e,f('0'));assert.deepEqual(r.deliveredAllocatedGCO2e,f('500'));assert.deepEqual(r.dischargeConversionLossKWh,f('17','50'));
});
test('charge-only inventory does not invent a discharge intensity',()=>{
 const d=fresh();d.events.pop();const r=evaluateStorageCarbon(d);assert.deepEqual(r.remainingStoredKWh,f('17','10'));assert.deepEqual(r.remainingCarriedGCO2e,f('500'));assert.deepEqual(r.deliveredAllocatedGCO2e,f('0'));assert.equal(r.deliveredIntensityGCO2ePerKWh,null);
});
test('lossless single-source result retains the charging intensity',()=>{
 const d=fresh();d.events.splice(1,1);d.events[0].storedKWh='1';d.events[1].removedStoredKWh='1';d.events[1].deliveredAcKWh='1';const r=evaluateStorageCarbon(d);assert.deepEqual(r.deliveredIntensityGCO2ePerKWh,f('100'));assert.deepEqual(r.chargeConversionLossKWh,f('0'));assert.deepEqual(r.dischargeConversionLossKWh,f('0'));
});
test('multiple withdrawals preserve exact fractional allocation',()=>{
 const d=fresh();d.events.push({...d.events[2],id:'discharge.2',at:'2026-01-01T01:00:00.000Z'});const r=evaluateStorageCarbon(d);assert.deepEqual(r.deliveredAllocatedGCO2e,f('500'));assert.deepEqual(r.remainingStoredKWh,f('0'));assert.deepEqual(r.remainingCarriedGCO2e,f('0'));
});
test('small positive allocations retain exact decimal quantities',()=>{
 const d=fresh();d.events=d.events.slice(0,1);d.events[0].inputAcKWh='0.0000000000001';d.events[0].storedKWh='0.0000000000001';const r=evaluateStorageCarbon(d);assert.deepEqual(r.remainingStoredKWh,f('1','10000000000000'));assert.deepEqual(r.remainingCarriedGCO2e,f('1','100000000000'));
});
const invalid=[
 ['unallowlisted source',d=>d.sourceLedger='/etc/passwd'],['source hash mismatch',d=>d.sourceLedgerSHA256='0'.repeat(64)],
 ['wrong storage asset',d=>d.storageAssetId='invented'],['unknown initial inventory',d=>d.initialInventory.status='UNKNOWN'],
 ['untraced initial energy',d=>d.initialInventory.storedKWh='1'],['untraced initial carbon',d=>d.initialInventory.carriedGCO2e='1'],
 ['unreviewed alternate policy',d=>d.accountingPolicy='DISCHARGE_ZERO_CARBON'],['empty event list',d=>d.events=[]],
 ['duplicate identity',d=>d.events[1].id=d.events[0].id],['reordered events',d=>d.events.reverse()],['simultaneous events',d=>d.events[1].at=d.events[0].at],
 ['future discharge',d=>d.events[2].at='2026-01-01T01:00:02.000Z'],['evaluation before source ledger',d=>d.evaluationAt='2026-01-01T00:29:59.000Z'],['dispatch use',d=>d.accountingUse='DISPATCH'],
 ['invalid date',d=>d.events[0].at='2026-02-30T00:00:00Z'],['non-UTC date',d=>d.events[0].at='2026-01-01T00:15:00+01:00'],
 ['missing source row',d=>d.events[0].sourceRowId='invented'],['source time mismatch',d=>d.events[0].at='2026-01-01T00:15:01.000Z'],
 ['excess source import allocation',d=>d.events[0].inputAcKWh='1.26'],['charge creates energy',d=>d.events[0].storedKWh='1.01'],
 ['zero AC input',d=>d.events[0].inputAcKWh='0'],['zero stored charge',d=>d.events[0].storedKWh='0'],['negative charge',d=>d.events[0].inputAcKWh='-1'],
 ['numeric energy',d=>d.events[0].inputAcKWh=1],['nonfinite energy',d=>d.events[0].inputAcKWh='Infinity'],['exponent encoding',d=>d.events[0].inputAcKWh='1e0'],['excess precision',d=>d.events[0].inputAcKWh='0.00000000000001'],['oversized input',d=>d.events[0].inputAcKWh='9'.repeat(65)],
 ['discharge before charging',d=>d.events=[{...d.events[2],at:'2026-01-01T00:00:00.000Z'}]],['overdrawn pool',d=>d.events[2].removedStoredKWh='1.71'],
 ['discharge creates energy',d=>d.events[2].deliveredAcKWh='0.86'],['zero removed energy',d=>d.events[2].removedStoredKWh='0'],['pure loss without allocation policy',d=>d.events[2].deliveredAcKWh='0'],
 ['unsupported idle loss event',d=>d.events[2].type='IDLE_LOSS'],['fabricated factor override',d=>d.events[0].intensity='0'],['control claim',d=>d.controlAction='ALLOW'],['execution claim',d=>d.behavioralCasesRun=1],['review approval claim',d=>d.engineeringReview='APPROVED']
];
for(const [name,mutate] of invalid)test('rejects '+name,()=>{const d=fresh();mutate(d);assert.throws(()=>evaluateStorageCarbon(d));});
test('source ledger tampering is rejected before allocation',t=>{
 const root=mkdtempSync(join(tmpdir(),'energy-storage-'));t.after(()=>rmSync(root,{recursive:true,force:true}));mkdirSync(join(root,'assets'));
 copyFileSync(new URL('../assets/import-carbon-ledger.json',import.meta.url),join(root,'assets/import-carbon-ledger.json'));
 writeFileSync(join(root,'assets/import-carbon-ledger.json'),'{}');assert.throws(()=>evaluateStorageCarbon(fixture,root));
});
test('unknown source factors cannot become zero-carbon storage inventory',t=>{
 const root=mkdtempSync(join(tmpdir(),'energy-storage-unknown-'));t.after(()=>rmSync(root,{recursive:true,force:true}));
 for(const folder of ['assets','examples'])cpSync(new URL('../'+folder,import.meta.url),join(root,folder),{recursive:true});
 mkdirSync(join(root,'acceptance'));copyFileSync(new URL('../acceptance/cases.json',import.meta.url),join(root,'acceptance/cases.json'));
 mkdirSync(join(root,'intake/public-models/sunspec'),{recursive:true});copyFileSync(new URL('../intake/public-models/sunspec/model_203.json',import.meta.url),join(root,'intake/public-models/sunspec/model_203.json'));
 const path=join(root,'assets/import-carbon-ledger.json'),ledger=JSON.parse(readFileSync(path,'utf8'));
 ledger.rows[0].factor.quality='UNKNOWN';ledger.rows[0].factor.intensity=null;writeFileSync(path,JSON.stringify(ledger));
 const d=fresh();d.sourceLedgerSHA256=createHash('sha256').update(readFileSync(path)).digest('hex');
 assert.throws(()=>evaluateStorageCarbon(d,root),/Unusable source carbon ledger/);
});
