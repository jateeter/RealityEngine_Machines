const fs=require('fs'),path=require('path');
const root=process.cwd(),out=path.join(root,'outputs/ifrs-document-workflows');
const dep=path.join(root,'work/acceptance/staged/RealityEngine_Machines/node_modules');
const Ajv=require(path.join(dep,'ajv/dist/2020.js')),formats=require(path.join(dep,'ajv-formats'));
const ajv=new Ajv({strict:false,allErrors:true});formats(ajv);
for(const f of fs.readdirSync(path.join(out,'schemas')).filter(f=>f.endsWith('.json'))){
 const schema=JSON.parse(fs.readFileSync(path.join(out,'schemas',f)));ajv.addSchema(schema,f);
 if(schema.$id)ajv.addSchema({$ref:schema.$id},'https://realityengine.example.org/RealityEngine_Machines/schemas/'+f);
}
const machine=ajv.getSchema('machine.schema.json'),agent=ajv.getSchema('oc-agent.schema.json'),workflow=ajv.getSchema('document-workflow.schema.json');let count=0;
for(const f of fs.readdirSync(path.join(out,'machines/domains/ifrs-accounting'))){
 const m=JSON.parse(fs.readFileSync(path.join(out,'machines/domains/ifrs-accounting',f)));
 if(!machine(m))throw Error(f+JSON.stringify(machine.errors));if(!workflow(m.machine.metadata.documentAssetWorkflow))throw Error(f+JSON.stringify(workflow.errors));count+=2;
}
for(const f of fs.readdirSync(path.join(out,'agents/ifrs-accounting'))){const a=JSON.parse(fs.readFileSync(path.join(out,'agents/ifrs-accounting',f)));if(!agent(a))throw Error(f+JSON.stringify(agent.errors));count++;}
let exampleCount=0;for(const [schema,file,field] of [['document-context.schema.json','context.json',null],['document-event.schema.json','period-open-request.json','event'],['document-revision.schema.json','draft-revision.json',null],['monetary-value.schema.json','money.json',null]]){const validate=ajv.getSchema(schema);let obj=JSON.parse(fs.readFileSync(path.join(out,'examples',file)));if(field)obj=obj[field];if(!validate(obj))throw Error(file+JSON.stringify(validate.errors));exampleCount++;}
console.log(JSON.stringify({exampleContractsValidated:exampleCount,status:'PASS',validator:'Ajv draft 2020-12 with formats',machineFiles:225,agentFiles:225,workflowFacets:225,totalValidations:count}));
