import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {validateInstances} from './validate_asset_instances.mjs';
const fixture=JSON.parse(readFileSync(new URL('../assets/generic-instance-fixture.json',import.meta.url),'utf8'));
const inverter=d=>d.assets.find(a=>a.roleId==='solar-inverter');
test('all 19 generic roles and seven document types validate with explicit draft status',()=>{
  assert.equal(fixture.requireAllGenericTemplates,true);
  assert.equal(fixture.assets.length,19);assert.equal(fixture.documents.length,7);assert.equal(fixture.caseIds.length,43);
  assert.deepEqual(validateInstances(fixture),[]);
});
const negatives=[
 ['unknown enum value',d=>inverter(d).properties.find(p=>p.name==='ConnSt').value=999],
 ['duplicate source binding',d=>{const p=structuredClone(inverter(d).properties[0]);p.name='alias';inverter(d).properties.push(p);}],
 ['missing unit',d=>delete inverter(d).properties[0].unit],
 ['altered source unit',d=>inverter(d).properties[0].unit='kW'],
 ['out of range raw integer',d=>inverter(d).properties[0].value=40000],
 ['fractional raw integer',d=>inverter(d).properties[0].value=0.5],
 ['boolean raw integer',d=>inverter(d).properties[0].value=true],
 ['missing scale factor',d=>inverter(d).properties.splice(1,1)],
 ['unknown model',d=>inverter(d).properties[0].sourcePoint.templateId='absent'],
 ['unknown source pointer',d=>inverter(d).properties[0].sourcePoint.pointer='/group/points/999999'],
 ['missing raw encoding',d=>delete inverter(d).properties[0].valueEncoding],
 ['duplicate instance id',d=>d.assets[1].id=d.assets[0].id],
 ['missing role template',d=>d.assets.pop()],
 ['orphan role',d=>d.assets[0].roleId='absent'],
 ['unknown topology reference',d=>d.assets[0].topologyLinks=['absent']],
 ['unknown document asset reference',d=>d.documents[0].assetRefs.push('absent')],
 ['unknown authority role',d=>d.assets[0].authorityRoleIds=['invented']],
 ['missing document',d=>d.documents.pop()],
 ['missing required document field',d=>delete d.documents[0].fields.nodes],
 ['unknown topology node',d=>d.documents[0].fields.nodes.value.push('absent')],
 ['fabricated review',d=>d.documents[0].authenticEvidence=true],
 ['fabricated simulator',d=>d.assets[0].simulation.version='fiction'],
 ['command authority enabled',d=>d.assets[0].commandDecision='ALLOW'],
 ['unknown case',d=>d.caseIds.push('AC999')],
 ['invented execution result',d=>d.documents.find(x=>x.templateId==='generic-document-evidence-record').fields.result.value='PASS'],
 ['nonfinite number',d=>inverter(d).properties[0].value=Infinity],
 ['unproven provenance',d=>inverter(d).properties[0].provenance.kind='NORMATIVE_REQUIREMENT']
];
for(const [name,mutate] of negatives)test(`rejects ${name}`,()=>{const d=structuredClone(fixture);mutate(d);assert.ok(validateInstances(d).length);});
