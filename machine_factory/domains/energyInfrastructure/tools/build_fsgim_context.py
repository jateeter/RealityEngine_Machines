#!/usr/bin/env python3
"""Build the owner-selected FSGIM context; supplementary IRIs are not normative mappings."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
PINS={'fsgim.ttl':'68c1dba2b5fecdb2018cf1682fa09ae5afbb377ede03fa01fe1d1d304497c9e6','LICENSE':'b130ae7bdd91784819cacf31960c5c8cdc7a44e64c631613c90ae2e616105762','README.md':'a16cc6cdde55b381b5aa2aafc6eae678c089a5ca238c102e1d01683b3a623bf8','ASHRAE-Model-License.txt':'1e4936eceaa731286cbe2b57a3bb2c396e40136b10fc19f32d649815e81e032e'}
CONCEPTS={'Device':'fsgim-device:Device','EnergyManager':'fsgim-energy_manager_component:EM','Meter':'fsgim-meter_component:Meter','Load':'fsgim-load_component:Load','Generator':'fsgim-generator_component:Generator'}
# These are authored functional projections, not inferred normative equivalences.
ROLES={
 'utility-grid':('EXTERNAL_SERVICE',[],'PCC_AC'),
 'pcc-switch':('SUPPORTING_DEVICE_ASSET',[],'PCC_AC'),
 'transformer':('SUPPORTING_DEVICE_ASSET',[],'PCC_AC'),
 'solar-array':('ENERGY_BEHAVIOR_PATTERN',['Generator'],'PV_AC'),
 'solar-inverter':('ENERGY_BEHAVIOR_PATTERN',['Generator'],'PV_AC'),
 'battery-pack':('ENERGY_BEHAVIOR_PATTERN',['Load','Generator'],'STORAGE_AC'),
 'battery-inverter':('ENERGY_BEHAVIOR_PATTERN',['Load','Generator'],'STORAGE_AC'),
 'protection-controller':('SUPPORTING_DEVICE_ASSET',[],None),
 'meter':('ENERGY_BEHAVIOR_PATTERN',['Meter'],'EXPLICIT_METER_SCOPE'),
 'clock':('SUPPORTING_DEVICE_ASSET',[],None),
 'critical-load':('ENERGY_BEHAVIOR_PATTERN',['Load'],'CRITICAL_LOAD_AC'),
 'flexible-load':('ENERGY_BEHAVIOR_PATTERN',['Load'],'FLEXIBLE_LOAD_AC'),
 'evse':('ENERGY_BEHAVIOR_PATTERN',['Load'],'EV_AC'),
 'ev':('ENERGY_BEHAVIOR_PATTERN',['Load'],'EV_AC'),
 'demand-response-peer':('EXTERNAL_SERVICE',[],None),
 'microgrid-controller':('ENERGY_BEHAVIOR_PATTERN',['EnergyManager'],None),
 'threat-feed':('SUPPORTING_INFORMATION',[],None),
 'carbon-provider':('PROJECT_EXTENSION',[],None),
 'market-peer':('EXTERNAL_SERVICE',[],None)}
CATALOGS={'assets/asset-class-catalog.json':'ENERGY_INFORMATION_MODEL_REQUIRES_FUNCTION_BINDING','assets/device-class-catalog.json':'DEVICE_TYPE_FACET_REQUIRES_FUNCTION_BINDING','assets/threat-class-catalog.json':'CYBER_INFORMATION_SUPPORT_NOT_ENERGY_FUNCTION','assets/taxii-resource-catalog.json':'THREAT_TRANSPORT_SUPPORT_NOT_ENERGY_FUNCTION'}

def render(root):
    receipt=json.loads((root/'assets/fsgim-source-receipt.json').read_text())
    impl=receipt['supplementaryImplementation']
    if receipt['selectedReference']!='ANSI/ASHRAE/NEMA Standard 201-2016 (RA2026), Facility Smart Grid Information Model':raise ValueError('Unverified selected FSGIM reference')
    if receipt['standardId']!='OP23' or impl['commit']!='1759521d70e8535fdd261f2f6e53cb97079db1af' or impl['license']!='BSD-3-Clause' or receipt['ragIndexed'] or receipt['externalImportsLoaded']:raise ValueError('FSGIM source/rights/execution boundary changed')
    archive=receipt['officialModelArchive']
    if archive['state']!='DOWNLOAD_BLOCKED_BY_BROWSER_CHALLENGE_NOT_COLLECTED' or archive['sha256'] is not None or archive['ra2026ModelEquivalenceVerified']:raise ValueError('Unverified normative model collection/equivalence claim')
    expected={'intake/fsgim-context/'+name:sha for name,sha in PINS.items()}
    actual={p.relative_to(root).as_posix() for p in (root/'intake/fsgim-context').rglob('*') if p.is_file() and p.name!='.DS_Store'}
    if actual!=set(expected)|{'intake/fsgim-context/.gitattributes'}:raise ValueError('Unlisted FSGIM source artifact; rights/provenance review required')
    if len(receipt['files'])!=4 or {f['path'] for f in receipt['files']}!=set(expected):raise ValueError('FSGIM source inventory mismatch')
    for f in receipt['files']:
        path=root/f['path']
        if f['sha256']!=expected[f['path']] or hashlib.sha256(path.read_bytes()).hexdigest()!=expected[f['path']] or path.stat().st_size!=f['bytes']:raise ValueError('FSGIM source hash mismatch')
    text=(root/'intake/fsgim-context/fsgim.ttl').read_text()
    prefixes=dict(re.findall(r'^@prefix ([\w-]+): <([^>]+)> \.$',text,re.M))
    concepts={}
    for name,qname in CONCEPTS.items():
        prefix,local=qname.split(':')
        match=re.search(r'^'+re.escape(qname)+r'\n(.*?)^\.\s*$',text,re.M|re.S)
        if not match or 'a owl:Class ;' not in match[1] or 'a sh:NodeShape ;' not in match[1]:raise ValueError('Supplementary FSGIM class declaration missing: '+name)
        concepts[name]={'supplementaryClassIRI':prefixes[prefix]+local,'sourceQName':qname,'sourceLine':text[:match.start()].count('\n')+1,'authority':'SUPPLEMENTARY_2016_IMPLEMENTATION_NOT_NORMATIVE_UML'}
    scope=json.loads((root/'examples/reference-microgrids.json').read_text())
    if {r['id'] for r in scope['assetRoles']}!=set(ROLES):raise ValueError('Unmapped reference asset role')
    actual={p.relative_to(root).as_posix() for p in (root/'assets').glob('*-class-catalog.json')}|{p.relative_to(root).as_posix() for p in (root/'assets').glob('*-resource-catalog.json')}
    if actual!=set(CATALOGS):raise ValueError('Asset catalog missing FSGIM applicability disposition')
    role_rows=[]
    for role in scope['assetRoles']:
        disposition,functions,boundary=ROLES[role['id']]
        role_rows.append({'roleId':role['id'],'contextDisposition':disposition,'functionConcepts':functions,
            'deviceConcept':'Device' if disposition in ['ENERGY_BEHAVIOR_PATTERN','SUPPORTING_DEVICE_ASSET'] else None,
            'conditionalFunctions':[{'concept':'Generator','condition':'BIDIRECTIONAL_CAPABILITY_AND_REVIEWED_PROFILE_REQUIRED'}] if role['id'] in ['ev','evse'] else [],
            'accountingGroup':boundary,'electricalBoundaryReviewRequired':True,
            'mappingStatus':'PROJECT_FUNCTIONAL_PROJECTION_NOT_NORMATIVE_EQUIVALENCE',
            'hardwareRepresentation':role['hardwareRepresentation'],'controlAuthorityGranted':False})
    source_rows=[]
    for rel in ['assets/asset-class-catalog.json','assets/device-class-catalog.json']:
        for t in json.loads((root/rel).read_text())['templates']:
            source_rows.append({'sourceCatalog':rel,'sourceTemplateId':t['templateId'],'sourceClassId':t['classId'],
                'contextStandardId':'OP23','deviceContextConcept':'Device',
                'mappingRelation':'SOURCE_TYPE_OR_INFORMATION_FACET_SUPPORTS_INSTANCE_BINDING_NOT_CLASS_EQUIVALENCE',
                'functionAssignment':'REQUIRED_FROM_REVIEWED_ASSET_INSTANCE_NOT_INFERRED_FROM_TYPE_NAME',
                'nativeIdentifiersAndSemanticsPreserved':True})
    return {'schemaVersion':'1.0.0','standardId':'OP23','selectedReference':receipt['selectedReference'],
        'status':'OWNER_SELECTED_INTEGRATION_CONTEXT_PROVISIONAL_CROSSWALKS',
        'normativeEquivalenceVerified':False,'sourceReceipt':'assets/fsgim-source-receipt.json',
        'concepts':concepts,'roleMappings':role_rows,'sourceClassBindings':source_rows,
        'assetFamilyPatterns':[
            {'family':'Electrical consumers: HVAC, lighting, appliances, industrial and ICT equipment','concepts':['Device','Load']},
            {'family':'Electrical sources: PV, wind and dispatchable generation','concepts':['Device','Generator']},
            {'family':'Bidirectional storage and capability-qualified vehicles','concepts':['Device','Load','Generator']},
            {'family':'Electricity measurement and declared measurement boundaries','concepts':['Device','Meter']},
            {'family':'Energy management and facility aggregation','concepts':['Device','EnergyManager']},
            {'family':'Passive distribution, protection and communications support','concepts':['Device']},
            {'family':'Weather, market, carbon and threat information','concepts':[],'disposition':'CONTEXT_INPUT_OR_PROJECT_EXTENSION_NOT_AUTOMATIC_ENERGY_FUNCTION'}],
        'catalogDispositions':[{'path':path,'disposition':disposition} for path,disposition in CATALOGS.items()],
        'opcuaDIBridge':{'deviceIdentityFacetTemplate':'opcua-di-ns1-i1002','deviceTypeIsAbstract':True,
            'relationship':'IDENTITY_AND_CAPABILITY_FACET_OF_FSGIM_DEVICE_NOT_EQUIVALENT_CLASS',
            'sourceMemberCandidates':['Manufacturer','Model','SerialNumber','ProductInstanceUri'],
            'propertyEquivalenceVerified':False,'concreteDerivedTypeAndInstanceBindingsRequired':True,
            'sourceAndProjectIdentifiers':'Preserve namespace URI, NodeId, equipment identifiers and project asset ID as scoped aliases; do not assume string equality proves identity.'},
        'accountingRules':['A device may expose several energy functions; storage has charge Load and discharge Generator roles with explicit modes.',
            'PV, storage and EV conversion-chain members share an accounting group; do not sum multiple views of the same flow.',
            'Choose explicit PCC/submeter boundaries, units, signs, time windows and aggregation hierarchy before computing facility totals.',
            'Do not infer zero losses or energy consumption for supporting/passive devices without measurements.',
            'External services and threat records are not automatically energy functions; model their host equipment separately if energy-accounted.'],
        'carbonExtension':{'namespace':'urn:realityengine:energyInfrastructure:carbon-context:1','normativeFSGIMClassClaim':False,
            'metric':'electricity carbon intensity','unit':'gCO2e/kWh','meterConcept':'Meter','decisionConcept':'EnergyManager',
            'requiredBindings':['quantityAndGasBasis','electricalAndGeographicBoundary','intervalAndTimezone','locationMarketOrMarginalMethod','sourceVersionAndRights','qualityFreshnessAndUncertainty'],
            'missingData':'UNKNOWN_NOT_ZERO','safetyPrecedence':'Carbon objectives cannot override protection, operating constraints or approved authority.'},
        'executionBoundary':{'networkExecution':False,'ragIndexing':False,'externalSHACLImportsLoaded':False,'runtimeTypeRegistration':False,'controlAction':'DENY','behavioralCasesRun':0},
        'remaining':['Acquire/verify the official UML archive and applicable reaffirmation/errata mapping','Review exact properties, multiplicities, units, inheritance and conformance blocks','Instantiate typed device/function bindings and actual protocol adapters','Verify simulation, runtime behavior and authentic admission evidence']}

def check(root):
    try:return [] if render(root)==json.loads((root/'assets/fsgim-integration-context.json').read_text()) else ['FSGIM integration context/source coverage mismatch']
    except (OSError,ValueError,KeyError,TypeError,IndexError) as e:return [str(e)]

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');args=p.parse_args()
    if args.write:(ROOT/'assets/fsgim-integration-context.json').write_text(json.dumps(render(ROOT),indent=2)+'\n')
    errors=check(ROOT);print(json.dumps({'result':'FAIL' if errors else 'PASS','context':'ASHRAE201_FSGIM','normativeEquivalenceVerified':False,'errors':errors}));raise SystemExit(bool(errors))
