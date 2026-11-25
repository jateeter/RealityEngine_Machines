import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {validateThreatFixture} from './validate_threat_fixture.mjs';
const fixture=JSON.parse(readFileSync(new URL('../assets/synthetic-threat-fixture.json',import.meta.url),'utf8'));
test('all 57 schemas compile offline and the closed synthetic bundle validates',()=>assert.deepEqual(validateThreatFixture(fixture),[]));
test('timestamp precision differences do not invent a reversed interval',()=>{
  const d=structuredClone(fixture);d.bundle.objects[0].created='2026-11-25T00:00:00.0000Z';
  assert.deepEqual(validateThreatFixture(d),[]);
});
const bad=[
 ['oversized UTF-8 fixture',d=>d.bundle.objects[0].description='😀'.repeat(300000)],
 ['reserved automated course of action',d=>{const o=d.bundle.objects[1];o.type='course-of-action';o.id='course-of-action--00000000-0000-4000-8000-000000000002';o.action={command:'trip'};d.bundle.objects[3].source_ref=o.id;}],
 ['non-synthetic envelope',d=>d.kind='LIVE'],
 ['open bundle',d=>d.closedBundle=false],
 ['missing required object property',d=>delete d.bundle.objects[1].name],
 ['wrong object ID type',d=>d.bundle.objects[1].id='vulnerability--00000000-0000-4000-8000-000000000002'],
 ['duplicate identity',d=>d.bundle.objects.push(structuredClone(d.bundle.objects[0]))],
 ['unresolved target',d=>d.bundle.objects[3].target_ref='vulnerability--00000000-0000-4000-8000-000000000099'],
 ['unresolved creator',d=>d.bundle.objects[1].created_by_ref='identity--00000000-0000-4000-8000-000000000099'],
 ['wrong explicit version',d=>d.bundle.objects[0].spec_version='2.0'],
 ['unknown object type',d=>d.bundle.objects[0].type='x-unreviewed'],
 ['backdated modification',d=>d.bundle.objects[0].modified='2026-11-24T00:00:00.000Z'],
 ['reversed submillisecond timestamp',d=>{d.bundle.objects[0].created='2026-11-25T00:00:00.0001Z';d.bundle.objects[0].modified='2026-11-25T00:00:00.0000Z';}],
 ['empty bundle',d=>d.bundle.objects=[]],
 ['oversized object count',d=>d.bundle.objects=Array(129).fill(d.bundle.objects[0])],
 ['action authority in envelope',d=>d.controlAction='ALLOW'],
 ['nested bundle',d=>d.bundle.objects.push({type:'bundle',id:'bundle--00000000-0000-4000-8000-000000000099',spec_version:'2.1',objects:[]})]
];
for(const [name,mutate] of bad)test(`rejects ${name}`,()=>{const d=structuredClone(fixture);mutate(d);assert.ok(validateThreatFixture(d).length);});

for(const name of ['gateway.example','münchen.example'])test(`accepts bounded hostname ${name}`,()=>{
  const d=structuredClone(fixture);d.bundle.objects.push({type:'domain-name',spec_version:'2.1',id:'domain-name--00000000-0000-4000-8000-000000000006',value:name});
  assert.deepEqual(validateThreatFixture(d),[]);
});
for(const name of ['-invalid.example','bad..example'])test(`rejects malformed hostname ${name}`,()=>{
  const d=structuredClone(fixture);d.bundle.objects.push({type:'domain-name',spec_version:'2.1',id:'domain-name--00000000-0000-4000-8000-000000000006',value:name});
  assert.ok(validateThreatFixture(d).length);
});
