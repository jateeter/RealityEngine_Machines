import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {validateFunctionBindings} from './validate_function_bindings.mjs';
const read=name=>JSON.parse(readFileSync(new URL('../assets/function-bindings/'+name,import.meta.url),'utf8'));
const names=['generic.json','ref01_connected.json','ref02_island_restore.json','ref03_flex_ev.json'];
const fixture=read(names[0]);
const binding=(d,role)=>d.bindings.find(b=>b.roleId===role);
const context=JSON.parse(readFileSync(new URL('../assets/fsgim-integration-context.json',import.meta.url),'utf8'));
for(const name of names)test(`validates draft function bindings for ${name}`,()=>assert.deepEqual(validateFunctionBindings(read(name)),[]));
test('scoped aliases may reuse an identifier across distinct source systems',()=>{
 const d=structuredClone(fixture);binding(d,'meter').sourceAliases=[{sourceSystemId:'server.A',namespaceUri:'urn:fixture:ua',identifier:'i=100'}];binding(d,'solar-inverter').sourceAliases=[{sourceSystemId:'server.B',namespaceUri:'urn:fixture:ua',identifier:'i=100'}];assert.deepEqual(validateFunctionBindings(d),[]);
});
test('capability-qualified EV generation can be declared only as inactive draft projection',()=>{
 const d=structuredClone(fixture),b=binding(d,'ev');b.genericBidirectionalCapability=true;b.functions.push({projectionId:'projection.ev.optionalGenerator',concept:'Generator',supplementaryClassIRI:context.concepts.Generator.supplementaryClassIRI,requiredOperatingMode:'DISCHARGING',active:false});assert.deepEqual(validateFunctionBindings(d),[]);
});
const bad=[
 ['malformed alias namespace URI',d=>binding(d,'meter').sourceAliases=[{sourceSystemId:'fixture.server',namespaceUri:'not a URI',identifier:'i=100'}]],
 ['missing source asset binding',d=>d.bindings.pop()],
 ['duplicate asset binding',d=>d.bindings.push(structuredClone(d.bindings[0]))],
 ['wrong asset/role association',d=>d.bindings[0].roleId='meter'],
 ['unknown source fixture path',d=>d.sourceFixture='/etc/passwd'],
 ['source hash drift',d=>d.sourceFixtureSHA256='0'.repeat(64)],
 ['missing storage generation role',d=>{const b=binding(d,'battery-pack');b.functions=b.functions.filter(f=>f.concept!=='Generator');}],
 ['storage charge/discharge reversal',d=>binding(d,'battery-pack').functions[0].requiredOperatingMode='DISCHARGING'],
 ['unsupported source class IRI',d=>binding(d,'meter').functions[0].supplementaryClassIRI=context.concepts.Load.supplementaryClassIRI],
 ['unqualified EV generation',d=>binding(d,'ev').functions.push({projectionId:'projection.ev.badGenerator',concept:'Generator',supplementaryClassIRI:context.concepts.Generator.supplementaryClassIRI,requiredOperatingMode:'DISCHARGING',active:false})],
 ['active draft function',d=>binding(d,'battery-pack').functions[0].active=true],
 ['duplicate function identity',d=>binding(d,'battery-inverter').functions[0].projectionId=binding(d,'battery-pack').functions[0].projectionId],
 ['duplicate source alias across assets',d=>{const a={sourceSystemId:'fixture.server',namespaceUri:'urn:fixture:ua',identifier:'i=100'};binding(d,'meter').sourceAliases=[a];binding(d,'solar-inverter').sourceAliases=[structuredClone(a)];}],
 ['missing physical DI facet',d=>binding(d,'meter').opcuaDITypeFacet=null],
 ['type NodeId namespace collapse',d=>binding(d,'meter').opcuaDITypeFacet.sourceClassId='i=1002'],
 ['false concrete DeviceType',d=>binding(d,'meter').opcuaDITypeFacet.sourceIsAbstract=false],
 ['abstract node instantiated directly',d=>binding(d,'meter').opcuaDITypeFacet.runtimeNodeInstantiation=true],
 ['invented derived runtime type',d=>binding(d,'meter').opcuaDITypeFacet.derivedRuntimeTypeId='fake.runtime.type'],
 ['external utility forced into DI DeviceType',d=>binding(d,'utility-grid').opcuaDITypeFacet=structuredClone(binding(d,'meter').opcuaDITypeFacet)],
 ['missing accounting group',d=>d.accounting.resourceGroups.pop()],
 ['duplicate accounting group',d=>d.accounting.resourceGroups.push(structuredClone(d.accounting.resourceGroups[0]))],
 ['wrong conversion-chain grouping',d=>binding(d,'battery-pack').accountingGroup='PV_AC'],
 ['primary accounting view outside group',d=>d.accounting.resourceGroups[0].primaryViewAssetId=binding(d,'critical-load').assetId],
 ['partial accounting membership',d=>d.accounting.resourceGroups[0].memberAssetIds.pop()],
 ['resource totals added to PCC net',d=>d.accounting.resourceViewsAddedToFacilityNet=true],
 ['non-meter used as facility meter',d=>d.accounting.facilityNetMeterAssetId=binding(d,'solar-inverter').assetId],
 ['fabricated measured integration receipt',d=>d.execution.measuredIntegrationReceipt='invented'],
 ['normative equivalence claimed',d=>d.normativeEquivalenceVerified=true],
 ['control action enabled',d=>d.execution.controlAction='ALLOW']
];
for(const [name,mutate] of bad)test(`rejects ${name}`,()=>{const d=structuredClone(fixture);mutate(d);assert.ok(validateFunctionBindings(d).length);});
