#!/usr/bin/env python3
"""Reproduce synthetic reference topologies; no power-flow or admission claim."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def build(root):
    scope=json.loads((root/'examples/reference-microgrids.json').read_text())
    base=json.loads((root/'assets/generic-instance-fixture.json').read_text())
    result={}
    for scenario in scope['scenarios']:
        fixture=deepcopy(base)
        fixture['referenceScenarioId']=scenario['id']
        fixture['requireAllGenericTemplates']=False
        fixture['caseIds']=scenario['caseIds']
        fixture['assets']=[a for a in fixture['assets'] if a['roleId'] in scenario['assetRoleIds']]
        ids={a['roleId']:a['id'] for a in fixture['assets']}
        buses={'bus.'+id for id in scenario['electricalConnectivity']['busIds']}
        def endpoint(id):return ids[id] if id in ids else 'bus.'+id
        for doc in fixture['documents']:
            doc['assetRefs']=list(ids.values())
            if doc['templateId']=='generic-document-topology':
                fields=doc['fields']
                fields['nodes']['value']=list(ids.values())+sorted(buses)
                fields['connections']['value']=[{'from':endpoint(a),'to':endpoint(b)} for a,b in scenario['electricalConnectivity']['edges']]
                fields['voltageBases']['value']={id:scenario['nominalReference']['localVoltage'] for id in sorted(buses)}
                for field in ['nodes','connections','voltageBases']:
                    fields[field]['provenance']['reference']='examples/reference-microgrids.json scenario '+scenario['id']+'; generic assumptions, not physical design or normative limits'
            if doc['templateId']=='generic-document-evidence-record':
                doc['fields']['caseId']['value']=scenario['caseIds'][0]
        result[scenario['id'].lower()+'.json']=fixture
    return result

def check(root):
    expected=build(root)
    folder=root/'assets/reference-instances'
    errors=[]
    if {p.name for p in folder.glob('*.json')}!=set(expected):errors.append('Reference fixture inventory mismatch')
    for name,data in expected.items():
        path=folder/name
        if not path.is_file() or json.loads(path.read_text())!=data:errors.append('Reference fixture drift: '+name)
    return errors

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--write',action='store_true');args=parser.parse_args()
    if args.write:
        (ROOT/'assets/reference-instances').mkdir(exist_ok=True)
        for name,data in build(ROOT).items():(ROOT/'assets/reference-instances'/name).write_text(json.dumps(data,indent=2)+'\n')
    errors=check(ROOT)
    print(json.dumps({'result':'FAIL' if errors else 'PASS','referenceTopologies':3,'behavioralCasesRun':0,'errors':errors}))
    raise SystemExit(bool(errors))
