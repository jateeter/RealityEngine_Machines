#!/usr/bin/env node
/** Offline synthetic TAXII resource profile; never client/server conformance. */
import {readFileSync} from 'node:fs';
import {dirname,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import Ajv2020 from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';
import {validateThreatFixture} from './validate_threat_fixture.mjs';
const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const read=p=>JSON.parse(readFileSync(p,'utf8'));
const TAXII='application/taxii+json;version=2.1', STIX='application/stix+json;version=2.1';
const sourceHash=createHash('sha256').update(readFileSync(resolve(ROOT,'intake/taxii21/taxii-v2.1-os.html'))).digest('hex');
if(sourceHash!=='ae8cf71e9527a066ec3cbc8fff631c4832600aad01f521b274b1636919f1f420')throw Error('TAXII source hash mismatch');
const schema=read(resolve(ROOT,'assets/taxii-resource.schema.json'));
const ajv=new Ajv2020({allErrors:true,strict:false});addFormats(ajv);ajv.addSchema(schema);
const validators=new Map(Object.keys(schema.$defs).map(type=>[type,ajv.compile({$ref:schema.$id+'#/$defs/'+type})]));
export function validateTaxiiFixture(fixture) {
  const errors=[];const require=(ok,message)=>{if(!ok)errors.push(message);};
  if(!fixture||fixture.kind!=='SYNTHETIC_TAXII_FIXTURES'||Object.keys(fixture).sort().join(',')!=='kind,resources'||!Array.isArray(fixture.resources)||fixture.resources.length!==11)return ['Expected 11 explicitly synthetic resource/record fixtures'];
  if(Buffer.byteLength(JSON.stringify(fixture),'utf8')>1048576)return ['Fixture exceeds one MiB profile limit'];
  const seen=new Set();
  const secureURI=value=>{
    try {const u=new URL(value);return u.protocol==='https:'&&!u.username&&!u.password&&!u.hash&&!u.search;}catch{return false;}
  };
  function collection(value) {
    if(value?.media_types)require(value.media_types.every(type=>type===STIX),'Unsupported collection media type');
  }
  for(const entry of fixture.resources) {
    if(!entry||Object.keys(entry).sort().join(',')!=='payload,resourceType'){errors.push('Malformed resource fixture');continue;}
    const type=entry.resourceType,validate=validators.get(type);
    require(!seen.has(type),'Duplicate resource fixture: '+type);seen.add(type);
    if(!validate){errors.push('Unknown TAXII resource/record: '+type);continue;}
    if(!validate(entry.payload)){errors.push(type+' schema: '+ajv.errorsText(validate.errors));continue;}
    const p=entry.payload;
    if(type==='discovery') {
      for(const u of [...(p.api_roots??[]),...(p.default?[p.default]:[])])require(secureURI(u),'Profile requires explicit credential-free HTTPS API root URI');
      if(p.default)require(p.api_roots?.includes(p.default),'Default API root missing from advertised roots');
    }
    if(type==='api-root')require(p.versions.includes(TAXII),'Selected TAXII 2.1 media version absent');
    if(type==='status') {
      require(p.total_count===p.success_count+p.failure_count+p.pending_count,'Status counters do not reconcile');
      for(const [list,count] of [['successes','success_count'],['failures','failure_count'],['pendings','pending_count']])if(p[list])require(p[list].length===p[count],'Status detail/count mismatch: '+list);
      if(p.status==='complete')require(p.pending_count===0,'Complete status still has pending objects');
    }
    if(type==='collection')collection(p);
    if(type==='collections')for(const c of p.collections??[])collection(c);
    if(type==='manifest-record'&&p.media_type)require(p.media_type===STIX,'Unsupported manifest media type');
    if(type==='manifest')for(const record of p.objects??[])if(record.media_type)require(record.media_type===STIX,'Unsupported manifest media type');
    if(type==='error'&&p.http_status)require(/^[45]\d\d$/.test(p.http_status),'Invalid profile error HTTP status');
    if(type==='envelope'&&p.objects?.length) {
      const stix={kind:'SYNTHETIC_STIX_FIXTURE',closedBundle:true,bundle:{type:'bundle',id:'bundle--00000000-0000-4000-8000-000000000010',objects:p.objects}};
      errors.push(...validateThreatFixture(stix).map(e=>'envelope STIX: '+e));
    }
  }
  require([...validators.keys()].every(type=>seen.has(type)),'Missing TAXII resource/record coverage');
  return errors;
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  try {
    if(process.argv.length!==3)throw Error('Usage: node tools/validate_taxii_fixture.mjs <synthetic-fixture.json>');
    const errors=validateTaxiiFixture(read(resolve(process.argv[2])));
    console.log(JSON.stringify({result:errors.length?'FAIL':'PASS',verificationType:'SYNTHETIC_TAXII_RESOURCE_PROFILE_ONLY',clientServerConformance:false,networkExecution:false,controlAction:'DENY',errors},null,2));process.exitCode=errors.length?1:0;
  }catch(e){console.error(e.message);process.exitCode=1;}
}
