import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {validateTaxiiFixture} from './validate_taxii_fixture.mjs';
const fixture=JSON.parse(readFileSync(new URL('../assets/taxii-resource-fixtures.json',import.meta.url),'utf8'));
const resource=(d,type)=>d.resources.find(r=>r.resourceType===type).payload;
test('source-derived schema/catalog reproduce offline',()=>execFileSync('python3',[fileURLToPath(new URL('./build_taxii_templates.py',import.meta.url))]));
test('all nine resources and both records validate without network execution',()=>assert.deepEqual(validateTaxiiFixture(fixture),[]));
test('envelope next token stays opaque data',()=>{
 const d=structuredClone(fixture);const p=resource(d,'envelope');p.more=true;p.next='opaque cursor: https://not-fetched.example.invalid/';assert.deepEqual(validateTaxiiFixture(d),[]);
});
const bad=[
 ['non-synthetic envelope',d=>d.kind='LIVE'],
 ['missing resource',d=>d.resources.pop()],
 ['duplicate resource',d=>d.resources[1]=structuredClone(d.resources[0])],
 ['unknown resource',d=>d.resources[0].resourceType='unreviewed'],
 ['missing required title',d=>delete resource(d,'collection').title],
 ['wrong permission type',d=>resource(d,'collection').can_read='yes'],
 ['custom property outside selected profile',d=>resource(d,'collection').x_unreviewed='value'],
 ['unknown TAXII version',d=>resource(d,'api-root').versions=['application/taxii+json;version=2.0']],
 ['insecure discovery root',d=>resource(d,'discovery').api_roots=['http://example.invalid/']], // insecure-transport: negative-test
 ['credential-bearing discovery root',d=>{const p=resource(d,'discovery');p.default='https://user:secret@example.invalid/';p.api_roots=[p.default];}],
 ['unadvertised default',d=>resource(d,'discovery').default='https://other.example.invalid/'],
 ['negative counter',d=>resource(d,'status').total_count=-1],
 ['unsafe integer counter',d=>resource(d,'status').total_count=2**54],
 ['unreconciled counters',d=>resource(d,'status').total_count=2],
 ['wrong detail count',d=>resource(d,'status').successes.push(structuredClone(resource(d,'status-details')))],
 ['pending complete status',d=>{const p=resource(d,'status');p.total_count=2;p.pending_count=1;}],
 ['invalid status state',d=>resource(d,'status').status='approved'],
 ['invalid timestamp',d=>resource(d,'manifest-record').date_added='not-a-time'],
 ['unsupported collection media',d=>resource(d,'collection').media_types=['application/stix+json;version=2.0']],
 ['unsupported manifest media',d=>resource(d,'manifest').objects[0].media_type='application/unknown'],
 ['invalid error status',d=>resource(d,'error').http_status='200'],
 ['STIX bundle substituted for envelope objects',d=>resource(d,'envelope').objects=[{type:'bundle',id:'bundle--00000000-0000-4000-8000-000000000099',objects:[]}]],
 ['unresolved embedded STIX relationship',d=>resource(d,'envelope').objects[3].target_ref='vulnerability--00000000-0000-4000-8000-000000000099'],
 ['control authority in fixture envelope',d=>d.controlAction='ALLOW']
];
for(const [name,mutate] of bad)test(`rejects ${name}`,()=>{const d=structuredClone(fixture);mutate(d);assert.ok(validateTaxiiFixture(d).length);});
