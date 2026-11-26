#!/usr/bin/env python3
"""Reproduce draft FSGIM function projections; never instantiate a normative device."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCES={'generic.json':'assets/generic-instance-fixture.json','ref01_connected.json':'assets/reference-instances/ref01_connected.json','ref02_island_restore.json':'assets/reference-instances/ref02_island_restore.json','ref03_flex_ev.json':'assets/reference-instances/ref03_flex_ev.json'}
PRIMARY_ROLES={'PV_AC':'solar-inverter','STORAGE_AC':'battery-inverter','EV_AC':'evse','CRITICAL_LOAD_AC':'critical-load','FLEXIBLE_LOAD_AC':'flexible-load'}

def build(root):
    context=json.loads((root/'assets/fsgim-integration-context.json').read_text())
    roles={r['roleId']:r for r in context['roleMappings']}
    scope=json.loads((root/'examples/reference-microgrids.json').read_text())
    hardware={r['id'] for r in scope['assetRoles'] if r['kind'] in ['hardware','electrical']}
    catalog=json.loads((root/'assets/device-class-catalog.json').read_text())
    device=next(t for t in catalog['templates'] if t['templateId']==context['opcuaDIBridge']['deviceIdentityFacetTemplate'])
    result={}
    for name,path in SOURCES.items():
        fixture=json.loads((root/path).read_text());bindings=[];groups={}
        meters=[a['id'] for a in fixture['assets'] if 'Meter' in roles[a['roleId']]['functionConcepts']]
        if len(meters)!=1:raise ValueError('Facility meter assignment requires explicit policy review')
        for asset in fixture['assets']:
            role=roles[asset['roleId']];functions=[]
            for concept in role['functionConcepts']:
                gate=None
                if asset['roleId'] in ['battery-pack','battery-inverter']:gate='CHARGING' if concept=='Load' else 'DISCHARGING'
                functions.append({'projectionId':'projection.'+asset['id']+'.'+concept,'concept':concept,
                    'supplementaryClassIRI':context['concepts'][concept]['supplementaryClassIRI'],
                    'requiredOperatingMode':gate,'active':False})
            facet=None
            if asset['roleId'] in hardware and role['deviceConcept']=='Device':
                facet={'sourceTemplateId':device['templateId'],'sourceClassId':device['classId'],'sourceIsAbstract':device['isAbstract'],
                    'runtimeNodeInstantiation':False,'derivedRuntimeTypeId':None,'peerMappingReceipt':None}
            binding={'assetId':asset['id'],'roleId':asset['roleId'],'sourceAliases':[],
                'mappingStatus':'DRAFT_PROJECT_PROJECTION_NOT_NORMATIVE_EQUIVALENCE',
                'deviceInstanceStatus':'NOT_INSTANTIATED','functions':functions,'accountingGroup':role['accountingGroup'],
                'genericBidirectionalCapability':False,'opcuaDITypeFacet':facet}
            bindings.append(binding)
            if any(f['concept'] in ['Load','Generator'] for f in functions):groups.setdefault(role['accountingGroup'],[]).append(asset)
        group_rows=[]
        for group,members in groups.items():
            primary=next((a['id'] for a in members if a['roleId']==PRIMARY_ROLES.get(group)),None)
            if not primary:raise ValueError('Accounting primary needs explicit policy review: '+str(group))
            group_rows.append({'id':group,'memberAssetIds':[a['id'] for a in members],'primaryViewAssetId':primary,
                'boundaryStatus':'GENERIC_ASSUMPTION_REQUIRES_ENGINEERING_REVIEW','measurementBinding':None})
        result[name]={'schemaVersion':'1.0.0','kind':'SYNTHETIC_FSGIM_FUNCTION_PROJECTION','standardId':'OP23',
            'sourceFixture':path,'sourceFixtureSHA256':hashlib.sha256((root/path).read_bytes()).hexdigest(),
            'normativeEquivalenceVerified':False,'bindings':bindings,
            'accounting':{'facilityNetMeterAssetId':meters[0],'facilityMeterAssignment':'DRAFT_PCC_NET_ASSUMPTION_REQUIRES_REVIEW',
                'resourceViewsAddedToFacilityNet':False,'resourceGroups':group_rows},
            'execution':{'networkExecution':False,'runtimeTypeRegistration':False,'controlAction':'DENY','simulatorVersion':None,'measuredIntegrationReceipt':None,'behavioralCasesRun':0}}
    return result

def check(root):
    try:
        expected=build(root);folder=root/'assets/function-bindings';errors=[]
        if {p.name for p in folder.glob('*.json')}!=set(expected):errors.append('FSGIM projection inventory mismatch')
        for name,data in expected.items():
            p=folder/name
            if not p.is_file() or json.loads(p.read_text())!=data:errors.append('FSGIM projection/source drift: '+name)
        return errors
    except (OSError,ValueError,KeyError,TypeError,StopIteration) as e:return [str(e)]

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');args=p.parse_args()
    if args.write:
        (ROOT/'assets/function-bindings').mkdir(exist_ok=True)
        for name,data in build(ROOT).items():(ROOT/'assets/function-bindings'/name).write_text(json.dumps(data,indent=2)+'\n')
    errors=check(ROOT);print(json.dumps({'result':'FAIL' if errors else 'PASS','draftProjections':4,'normativeEquivalenceVerified':False,'errors':errors}));raise SystemExit(bool(errors))
