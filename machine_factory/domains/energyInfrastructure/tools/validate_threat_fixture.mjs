#!/usr/bin/env node
/** Offline synthetic threat schema profile; never operational threat assessment. */
import {readFileSync} from 'node:fs';
import {resolve,dirname,sep} from 'node:path';
import {fileURLToPath,domainToASCII} from 'node:url';
import {createHash} from 'node:crypto';
import Ajv2020 from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';
const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const read=p=>JSON.parse(readFileSync(p,'utf8'));
let cached;
function compareTimes(a,b) {
  const compare=(x,y)=>x===y?0:x<y?-1:1;
  const base=compare(a.slice(0,19),b.slice(0,19));
  const fraction=s=>s.slice(19,-1).replace(/^\./,'');
  const x=fraction(a),y=fraction(b),width=Math.max(x.length,y.length);
  return base||compare(x.padEnd(width,'0'),y.padEnd(width,'0'));
}
function compiler() {
  if(cached)return cached;
  const receipt=read(resolve(ROOT,'assets/stix-source-receipt.json'));
  if(receipt.commit!=='9af1db41b7b86c06324f899649ae83480134f66e'||receipt.license!=='BSD-3-Clause'||receipt.ragIndexed)throw Error('STIX source identity/rights boundary changed');
  const source=resolve(ROOT,'intake/public-models/stix21');
  const files=new Set();
  for(const entry of receipt.files) {
    const path=resolve(ROOT,entry.path);
    if(!path.startsWith(source+sep)||files.has(path)||createHash('sha256').update(readFileSync(path)).digest('hex')!==entry.sha256)throw Error('STIX source hash/path mismatch');
    files.add(path);
  }
  const ajv=new Ajv2020({allErrors:true,strict:false,allowUnionTypes:true,unicodeRegExp:false});addFormats(ajv);
  // Explicit bounded hostname check; no DNS, URI fetching or network discovery.
  ajv.addFormat('idn-hostname',value=>{
    const ascii=domainToASCII(value).replace(/\.$/,'');
    return ascii.length>0&&ascii.length<=253&&ascii.split('.').every(label=>/^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/i.test(label));
  });
  const catalog=read(resolve(ROOT,'assets/threat-class-catalog.json'));
  if(catalog.templates.length!==57||catalog.normativeCoverageComplete!==false)throw Error('Threat catalog coverage boundary changed');
  const objectSchemas=new Map();
  for(const t of catalog.templates) {
    const path=resolve(ROOT,t.schemaPath);
    if(!files.has(path))throw Error('Catalog schema outside source receipt');
    const schema=read(path);ajv.addSchema(schema);
    if(t.classKind==='STANDARD_DEFINED_CYBER_INFORMATION_OBJECT')objectSchemas.set(t.classId,schema.$id);
  }
  for(const t of catalog.templates)ajv.getSchema(t.schemaId); // Resolve every schema locally; missing refs fail closed.
  cached={ajv,objectSchemas};return cached;
}
export function validateThreatFixture(fixture) {
  const errors=[];const require=(ok,msg)=>{if(!ok)errors.push(msg);};
  if(!fixture||fixture.kind!=='SYNTHETIC_STIX_FIXTURE'||fixture.closedBundle!==true||Object.keys(fixture).sort().join(',')!=='bundle,closedBundle,kind')return ['Expected explicitly synthetic closed-bundle fixture'];
  const bundle=fixture.bundle;
  if(!bundle||bundle.type!=='bundle'||!Array.isArray(bundle.objects)||bundle.objects.length===0||bundle.objects.length>128)return ['Expected 1..128 objects in a synthetic STIX bundle'];
  if(Buffer.byteLength(JSON.stringify(fixture),'utf8')>1048576)return ['Synthetic fixture exceeds one MiB profile limit'];
  const {ajv,objectSchemas}=compiler();
  const bundleSchema=ajv.getSchema(objectSchemas.get('bundle'));
  if(!bundleSchema(bundle))errors.push('Bundle schema: '+ajv.errorsText(bundleSchema.errors));
  const ids=new Set();
  for(const object of bundle.objects) {
    if(!object||typeof object!=='object'){errors.push('Invalid object');continue;}
    require(typeof object.id==='string'&&!ids.has(object.id),'Missing/duplicate object identity');ids.add(object.id);
    require(object.spec_version==='2.1','Explicit STIX 2.1 version required by this profile');
    if(object.type==='course-of-action')require(!Object.hasOwn(object,'action'),'Reserved course-of-action action property is not an automation instruction');
    const id=objectSchemas.get(object.type);
    if(!id||object.type==='bundle'){errors.push('Unsupported top-level object type: '+object.type);continue;}
    const validate=ajv.getSchema(id);
    if(!validate(object))errors.push(object.type+' schema: '+ajv.errorsText(validate.errors));
    if(typeof object.created==='string'&&typeof object.modified==='string')require(compareTimes(object.created,object.modified)<=0,'Object modified precedes created');
    if(typeof object.valid_from==='string'&&typeof object.valid_until==='string')require(compareTimes(object.valid_from,object.valid_until)<0,'Indicator validity interval is empty/reversed');
  }
  function refs(value,depth=0) {
    if(depth>32){errors.push('Fixture nesting exceeds profile limit');return;}
    if(Array.isArray(value)){for(const v of value)refs(v,depth+1);return;}
    if(!value||typeof value!=='object')return;
    for(const [k,v] of Object.entries(value)) {
      if(k.endsWith('_ref'))require(typeof v==='string'&&ids.has(v),'Unresolved closed-bundle reference: '+k);
      if(k.endsWith('_refs'))require(Array.isArray(v)&&v.every(id=>typeof id==='string'&&ids.has(id)),'Unresolved closed-bundle references: '+k);
      refs(v,depth+1);
    }
  }
  refs(bundle.objects);
  return errors;
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  try {
    if(process.argv.length!==3)throw Error('Usage: node tools/validate_threat_fixture.mjs <synthetic-fixture.json>');
    const errors=validateThreatFixture(read(resolve(process.argv[2])));
    console.log(JSON.stringify({result:errors.length?'FAIL':'PASS',verificationType:'SYNTHETIC_STIX_SCHEMA_PROFILE_ONLY',normativeConformance:false,operationalThreatAssessment:false,controlAction:'DENY',errors},null,2));process.exitCode=errors.length?1:0;
  }catch(e){console.error(e.message);process.exitCode=1;}
}
