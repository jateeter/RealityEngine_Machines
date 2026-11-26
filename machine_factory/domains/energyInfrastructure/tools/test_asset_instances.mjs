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

const referenceNames=['ref01_connected','ref02_island_restore','ref03_flex_ev'];
const referenceFixtures=referenceNames.map(name=>JSON.parse(readFileSync(new URL(`../assets/reference-instances/${name}.json`,import.meta.url),'utf8')));
const topology=d=>d.documents.find(x=>x.templateId==='generic-document-topology');
for(const f of referenceFixtures)test(`validates ${f.referenceScenarioId} topology`,()=>assert.deepEqual(validateInstances(f),[]));
for(const f of referenceFixtures)test(`accepts reordered undirected edges for ${f.referenceScenarioId}`,()=>{
  const d=structuredClone(f);
  topology(d).fields.connections.value=topology(d).fields.connections.value.reverse().map(e=>({from:e.to,to:e.from}));
  assert.deepEqual(validateInstances(d),[]);
});
const topologyNegatives=[
 ['missing expected edge',d=>topology(d).fields.connections.value.pop()],
 ['duplicate reversed edge',d=>{const e=topology(d).fields.connections.value[0];topology(d).fields.connections.value.push({from:e.to,to:e.from});}],
 ['orphan edge endpoint',d=>topology(d).fields.connections.value[0].to='absent'],
 ['self edge',d=>{const e=topology(d).fields.connections.value[0];e.to=e.from;}],
 ['missing bus',d=>topology(d).fields.nodes.value.pop()],
 ['extra asset role',d=>{const a=structuredClone(d.assets[0]);a.id='extra';d.assets.push(a);}],
 ['wrong voltage assumption',d=>topology(d).fields.voltageBases.value['bus.local-ac-bus'].value=240],
 ['false normative voltage',d=>topology(d).fields.voltageBases.value['bus.local-ac-bus'].basis='NORMATIVE'],
 ['invented grounding',d=>topology(d).fields.grounding.value='approved'],
 ['invented normative mapping',d=>topology(d).fields.sourceClassMappings.value={fake:'class'}],
 ['missing topology document',d=>d.documents=d.documents.filter(x=>x.templateId!=='generic-document-topology')],
 ['wrong scenario case scope',d=>d.caseIds.push('AC43')],
 ['duplicate topology document',d=>{const doc=structuredClone(topology(d));doc.id='extra.topology';d.documents.push(doc);}],
 ['nonarray connections',d=>topology(d).fields.connections.value=null],
 ['reordered duplicate source binding',d=>{const a=inverter(d);const p=structuredClone(a.properties[0]);p.name='reordered';p.sourcePoint={pointer:p.sourcePoint.pointer,templateId:p.sourcePoint.templateId};a.properties.push(p);}]
];
for(const [name,mutate] of topologyNegatives)test(`rejects ${name}`,()=>{const d=structuredClone(referenceFixtures[0]);mutate(d);assert.ok(validateInstances(d).length);});

test('rejects a substituted primary integration context',()=>{
  const d=structuredClone(fixture);d.integrationContextStandardId='OP17';assert.ok(validateInstances(d).length);
});
test('rejects missing FSGIM context linkage',()=>{
  const d=structuredClone(fixture);delete d.integrationContextArtifact;assert.ok(validateInstances(d).length);
});
test('rejects the older context-free fixture revision',()=>{
  const d=structuredClone(fixture);d.schemaVersion='1.0.0';assert.ok(validateInstances(d).length);
});
