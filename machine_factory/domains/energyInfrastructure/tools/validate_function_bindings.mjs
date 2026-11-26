#!/usr/bin/env node
/** Draft function projection validation; no normative model or device execution. */
import {readFileSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import Ajv2020 from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';
import {validateInstances} from './validate_asset_instances.mjs';
const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const read=p=>JSON.parse(readFileSync(p,'utf8'));
export function validateFunctionBindings(projection,root=ROOT) {
 const errors=[];const require=(ok,msg)=>{if(!ok)errors.push(msg);};
 const ajv=new Ajv2020({allErrors:true,strict:false});addFormats(ajv);
 const schema=ajv.compile(read(resolve(root,'assets/fsgim-function-binding.schema.json')));
 if(!schema(projection))return schema.errors.map(e=>`${e.instancePath}: ${e.message}`);
 const sourcePath=resolve(root,projection.sourceFixture); // schema allowlists the four source fixtures
 require(createHash('sha256').update(readFileSync(sourcePath)).digest('hex')===projection.sourceFixtureSHA256,'Projection source fixture hash mismatch');
 const source=read(sourcePath);errors.push(...validateInstances(source,root).map(e=>'source fixture: '+e));
 const context=read(resolve(root,'assets/fsgim-integration-context.json'));
 const deviceCatalog=read(resolve(root,'assets/device-class-catalog.json'));
 const scope=read(resolve(root,'examples/reference-microgrids.json'));
 const physical=new Set(scope.assetRoles.filter(r=>['hardware','electrical'].includes(r.kind)).map(r=>r.id));
 const assets=new Map(source.assets.map(a=>[a.id,a]));
 const roles=new Map(context.roleMappings.map(r=>[r.roleId,r]));
 const types=new Map(deviceCatalog.templates.map(t=>[t.templateId,t]));
 const bound=new Set(),functionIds=new Set(),aliases=new Map(),flowGroups=new Map();
 for(const b of projection.bindings) {
  const asset=assets.get(b.assetId),role=roles.get(b.roleId);
  require(!bound.has(b.assetId),'Duplicate asset binding: '+b.assetId);bound.add(b.assetId);
  require(!!asset&&asset.roleId===b.roleId,'Asset/role binding mismatch: '+b.assetId);
  if(!asset||!role){errors.push('Unknown source role');continue;}
  require(b.accountingGroup===role.accountingGroup,'Accounting group differs from context: '+b.assetId);
  const present=new Set();
  for(const f of b.functions) {
   require(!functionIds.has(f.projectionId),'Duplicate function projection identity');functionIds.add(f.projectionId);
   require(!present.has(f.concept),'Duplicate function concept: '+b.assetId);present.add(f.concept);
   require(f.supplementaryClassIRI===context.concepts[f.concept]?.supplementaryClassIRI,'Wrong supplementary function IRI');
   const conditional=role.conditionalFunctions.some(c=>c.concept===f.concept);
   require(role.functionConcepts.includes(f.concept)||(conditional&&b.genericBidirectionalCapability),'Unsupported/unqualified function: '+b.roleId+'/'+f.concept);
   const storage=['battery-pack','battery-inverter'].includes(b.roleId);
   const expectedGate=storage?(f.concept==='Load'?'CHARGING':'DISCHARGING'):(conditional?'DISCHARGING':null);
   require(f.requiredOperatingMode===expectedGate,'Function mode gate mismatch: '+b.assetId+'/'+f.concept);
  }
  require(role.functionConcepts.every(c=>present.has(c)),'Missing required context function: '+b.assetId);
  require(!b.genericBidirectionalCapability||role.conditionalFunctions.some(c=>c.concept==='Generator'),'Bidirectional capability not supported by this role profile');
  for(const alias of b.sourceAliases) {
   const key=JSON.stringify([alias.sourceSystemId,alias.namespaceUri,alias.identifier]);
   require(!aliases.has(key),'Duplicate scoped source alias: '+b.assetId);aliases.set(key,b.assetId);
  }
  const facet=b.opcuaDITypeFacet;
  if(physical.has(b.roleId)&&role.deviceConcept==='Device') {
   require(!!facet,'Missing hardware DI identity facet: '+b.assetId);
   if(facet) {
    const type=types.get(facet.sourceTemplateId);
    require(type?.templateId===context.opcuaDIBridge.deviceIdentityFacetTemplate,'Wrong DI identity facet type');
    require(!!type&&facet.sourceClassId===type.classId&&facet.sourceIsAbstract===type.isAbstract,'DI namespace/class/abstract metadata mismatch');
   }
  } else require(facet===null,'Software/external role cannot silently assert a physical DI instance');
  if(b.functions.some(f=>['Load','Generator'].includes(f.concept))) {
   require(typeof b.accountingGroup==='string','Energy-flow function needs an accounting group');
   if(!flowGroups.has(b.accountingGroup))flowGroups.set(b.accountingGroup,new Set());flowGroups.get(b.accountingGroup).add(b.assetId);
  }
 }
 require(bound.size===assets.size&&[...assets.keys()].every(id=>bound.has(id)),'Incomplete source asset binding coverage');
 const net=projection.accounting.facilityNetMeterAssetId;
 require(projection.bindings.some(b=>b.assetId===net&&b.functions.some(f=>f.concept==='Meter')),'Facility net meter is not a Meter function binding');
 const groups=new Set();
 for(const g of projection.accounting.resourceGroups) {
  require(!groups.has(g.id),'Duplicate resource accounting group');groups.add(g.id);
  const expected=flowGroups.get(g.id);
  require(!!expected&&g.memberAssetIds.length===expected.size&&g.memberAssetIds.every(id=>expected.has(id)),'Resource group membership mismatch: '+g.id);
  require(g.memberAssetIds.includes(g.primaryViewAssetId),'Accounting primary is outside its group');
  require(g.primaryViewAssetId!==net,'Facility net meter cannot also be a resource contribution');
 }
 require(groups.size===flowGroups.size&&[...flowGroups.keys()].every(id=>groups.has(id)),'Missing resource accounting group');
 return errors;
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
 try {
  if(process.argv.length!==3)throw Error('Usage: node tools/validate_function_bindings.mjs <projection.json>');
  const errors=validateFunctionBindings(read(resolve(process.argv[2])));
  console.log(JSON.stringify({result:errors.length?'FAIL':'PASS',verificationType:'DRAFT_FSGIM_FUNCTION_BINDINGS_ONLY',normativeConformance:false,networkExecution:false,behavioralCasesRun:0,errors},null,2));process.exitCode=errors.length?1:0;
 }catch(e){console.error(e.message);process.exitCode=1;}
}
