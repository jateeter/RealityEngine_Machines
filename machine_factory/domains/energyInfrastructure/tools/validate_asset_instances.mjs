#!/usr/bin/env node
/** Validate synthetic asset fixtures, never operational readiness or admission. */
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {resolve,dirname} from 'node:path';
import Ajv2020 from 'ajv/dist/2020.js';
const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const read=p=>JSON.parse(readFileSync(p,'utf8'));

export function validateInstances(bundle,root=ROOT) {
  const errors=[];
  const schema=read(resolve(root,'assets/asset-instance.schema.json'));
  const ajv=new Ajv2020({allErrors:true,strict:false});
  const validate=ajv.compile(schema);
  if(!validate(bundle)) return validate.errors.map(e=>`${e.instancePath}: ${e.message}`);
  const catalog=read(resolve(root,'assets/asset-class-catalog.json'));
  const scope=read(resolve(root,'examples/reference-microgrids.json'));
  const cases=new Set(read(resolve(root,'acceptance/cases.json')).cases.map(c=>c.id));
  const roles=new Map(catalog.genericRoleTemplates.map(t=>[t.templateId,t]));
  const docs=new Map(catalog.genericDocumentTemplates.map(t=>[t.templateId,t]));
  const models=new Map(catalog.templates.map(t=>[t.templateId,t]));
  const authority=new Set(scope.authorityRoles.map(r=>r.id));
  const ids=new Set();
  const require=(ok,msg)=>{if(!ok)errors.push(msg);};
  for(const item of [...bundle.assets,...bundle.documents]) {
    require(!ids.has(item.id),`Duplicate instance identity: ${item.id}`);ids.add(item.id);
  }
  const assetIds=new Set(bundle.assets.map(a=>a.id));
  for(const c of bundle.caseIds) require(cases.has(c),`Unknown case: ${c}`);
  for(const asset of bundle.assets) {
    const t=roles.get(asset.templateId);
    require(!!t,`Unknown role template: ${asset.templateId}`);
    if(t) require(t.referenceRoleId===asset.roleId,`Role/template mismatch: ${asset.id}`);
    for(const id of asset.topologyLinks) require(assetIds.has(id)&&id!==asset.id,`Invalid topology reference: ${asset.id} -> ${id}`);
    for(const id of asset.authorityRoleIds) require(authority.has(id),`Unknown authority role: ${id}`);
    const names=new Set();
    const pointBindings=new Set();
    for(const p of asset.properties) {
      require(!names.has(p.name),`Duplicate property: ${asset.id}/${p.name}`);names.add(p.name);
      require(typeof p.value!=='number'||Number.isFinite(p.value),`Nonfinite property: ${p.name}`);
      if(!p.sourcePoint)continue;
      const binding=JSON.stringify(p.sourcePoint);
      require(!pointBindings.has(binding),`Duplicate source-point binding: ${asset.id}/${p.name}`);pointBindings.add(binding);
      require(p.valueEncoding==='RAW_REGISTER',`Explicit raw-register encoding required: ${p.name}`);
      const model=models.get(p.sourcePoint.templateId);
      const point=model?.properties.find(v=>v.sourcePointer===p.sourcePoint.pointer)?.definition;
      require(!!point,`Unknown model point: ${p.name}`);
      if(!point)continue;
      require(p.unit===(point.units??'1'),`Source unit mismatch: ${p.name}`);
      // Values here are raw point values, before SunSpec scale-factor conversion.
      const type=point.type;
      const bits=Number(type.match(/(16|32|64)$/)?.[1]);
      if(['uint16','uint32','uint64','int16','int32','int64','sunssf','enum16','enum32','bitfield16','bitfield32','acc16','acc32','acc64','count','pad'].includes(type)) {
        const width=bits||16; const signed=type.startsWith('int')||type==='sunssf';
        require(Number.isSafeInteger(p.value),`Raw integer required (64-bit values beyond safe JSON integers unsupported): ${p.name}`);
        require(p.value>=(signed?-(2**(width-1)):0)&&p.value<=(signed?2**(width-1)-1:2**width-1),`Raw integer range: ${p.name}`);
      } else if(type==='float32') {
        require(typeof p.value==='number'&&Number.isFinite(p.value)&&Math.abs(p.value)<=3.4028234663852886e38,`Raw float32 range: ${p.name}`);
      } else if(type==='string') {
        require(typeof p.value==='string'&&Buffer.byteLength(p.value,'utf8')<=2*point.size,`Source string capacity: ${p.name}`);
      } else {
        require(false,`Point type requires explicit encoder support: ${type}`);
      }
      if(type.startsWith('enum')&&point.symbols?.length)require(point.symbols.some(s=>s.value===p.value),`Unknown enum value: ${p.name}`);
      if(Object.hasOwn(point,'value'))require(p.value===point.value,`Source constant mismatch: ${p.name}`);
      if(point.sf) {
        const sibling=p.sourcePoint.pointer.replace(/\/points\/\d+$/,'/points/');
        const sf=model.properties.find(q=>q.sourcePointer.startsWith(sibling)&&q.sourcePointer.slice(sibling.length).match(/^\d+$/)&&q.definition.name===point.sf);
        require(!!sf&&asset.properties.some(q=>q.sourcePoint?.templateId===model.templateId&&q.sourcePoint?.pointer===sf.sourcePointer),`Missing same-group scale-factor binding: ${p.name}`);
      }
    }
  }
  for(const doc of bundle.documents) {
    const t=docs.get(doc.templateId);
    require(!!t,`Unknown document template: ${doc.templateId}`);
    if(t)require(JSON.stringify(Object.keys(doc.fields).sort())===JSON.stringify(Object.keys(t.fields).sort()),`Document field coverage: ${doc.id}`);
    for(const ref of doc.assetRefs)require(assetIds.has(ref),`Unknown document asset: ${ref}`);
    if(doc.templateId==='generic-document-topology') {
      const nodes=doc.fields.nodes?.value;
      require(Array.isArray(nodes)&&nodes.length===new Set(nodes).size&&nodes.every(id=>assetIds.has(id)),`Invalid topology document nodes: ${doc.id}`);
    }
    if(doc.templateId==='generic-document-evidence-record') {
      require(bundle.caseIds.includes(doc.fields.caseId?.value),`Evidence case outside bundle scope: ${doc.id}`);
      for(const field of ['candidateDigest','simulatorDigest','policyDigest','inputDigest','observedReadback','authenticReviewerReceipt','result'])
        require(doc.fields[field]?.value===null,`Synthetic evidence cannot assert execution/approval: ${field}`);
    }
  }
  if(bundle.requireAllGenericTemplates) {
    require([...roles.keys()].every(id=>bundle.assets.some(a=>a.templateId===id)),'Missing generic role template coverage');
    require([...docs.keys()].every(id=>bundle.documents.some(d=>d.templateId===id)),'Missing generic document template coverage');
  }
  return errors;
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  try {
    if(process.argv.length!==3)throw Error('Usage: node tools/validate_asset_instances.mjs <fixture.json>');
    const errors=validateInstances(read(resolve(process.argv[2])));
    console.log(JSON.stringify({result:errors.length?'FAIL':'PASS',verificationType:'SYNTHETIC_FIXTURE_STRUCTURE_ONLY',behavioralCasesRun:0,errors},null,2));
    process.exitCode=errors.length?1:0;
  } catch(e) {console.error(e.message);process.exitCode=1;}
}
