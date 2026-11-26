#!/usr/bin/env python3
"""Reproduce EI04 public-model templates; no upstream code or controls execute."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def render(root):
    receipt = json.loads((root/'assets/source-receipt.json').read_text())
    if receipt['commit'] != '90b4a331dcca1d6eac69c1bead952fddcc5852e0' or receipt['license'] != 'Apache-2.0' or receipt['ragIndexed']:
        raise ValueError('Source identity/license/ingestion boundary changed')
    source = root/'intake/public-models/sunspec'
    actual = {p.relative_to(root).as_posix() for p in source.iterdir() if p.is_file()}
    if actual != {f['path'] for f in receipt['files']}:
        raise ValueError('Source inventory mismatch')
    for f in receipt['files']:
        path = root/f['path']
        if not path.resolve().is_relative_to(source.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != f['sha256']:
            raise ValueError('Source hash/path mismatch: '+f['path'])
    models = []
    for path in sorted(source.glob('model_*.json')):
        data = json.loads(path.read_text())
        points = []
        def walk(group, pointer):
            for i, point in enumerate(group.get('points', [])):
                points.append({'sourcePointer':pointer+'/points/'+str(i), 'definition':point})
            for i, child in enumerate(group.get('groups', [])):
                walk(child, pointer+'/groups/'+str(i))
        walk(data['group'], '/group')
        models.append({'classId':'SUNSPEC_MODEL_'+str(data['id']), 'templateId':'sunspec-model-'+str(data['id']),
            'classKind':'PUBLIC_INFORMATION_MODEL_NOT_ASSERTED_PHYSICAL_TAXONOMY',
            'standardId':'OP08', 'edition':receipt['commit'], 'clause':'model_'+str(data['id'])+'.json#/group',
            'sourcePath':path.relative_to(root).as_posix(), 'groupDefinition':data['group'], 'properties':points,
            'crossStandardMappings':[{'reference':s,'relation':'UPSTREAM_POINT_ANNOTATION_NOT_EQUIVALENCE_OR_CONFORMANCE'} for s in sorted({s for p in points for s in p['definition'].get('standards',[])})],
            'instantiation':{'hardwareMode':'SIMULATED_REQUIRED_HARDWARE','genericAllowedForAllCases':True,
                'instanceId':None,'topologyBindings':[],'authorityBindings':[], 'operatingLimits':None,
                'uncertaintyModel':None,'faultModel':None,'simulatorVersion':None,'caseBindings':[],
                'securityPolicy':'Default deny. RW metadata grants no authority. Deterministic authorization, safety envelope, approval and readback required before commands.',
                'state':'UNBOUND_TEMPLATE_NOT_EXECUTABLE','limitations':'No normative limits inferred; enum states and access metadata preserved verbatim. No simulator or admission evidence.'}})
    if len(models)!=112 or len({m['classId'] for m in models})!=112:
        raise ValueError('Expected 112 unique source models')
    standards=json.loads((root/'standards-inventory.json').read_text())['standards']
    roles=json.loads((root/'examples/reference-microgrids.json').read_text())['assetRoles']
    cases=json.loads((root/'acceptance/cases.json').read_text())['cases']
    documents = {
        'topology':['nodes','connections','terminalIds','voltageBases','grounding','sourceClassMappings'],
        'utility-profile':['pccId','interconnectionEnvelope','islandingRules','exportLimits','protectionCoordination','profileEdition'],
        'equipment-capability':['assetId','ratingsWithUnits','modes','interfaces','commands','observations','firmwareDigest','limitations'],
        'calibration':['sensorId','quantity','unit','range','uncertainty','clockQuality','method','syntheticReference'],
        'hazard-analysis':['hazardId','initiatingEvents','consequences','likelihoodBasis','safeguards','residualRisk','riskOwner'],
        'operating-procedure':['procedureId','preconditions','authority','steps','interlocks','abortConditions','recovery','readback'],
        'evidence-record':['caseId','candidateDigest','simulatorDigest','policyDigest','inputDigest','expectedOracle','tolerances','observedReadback','result','authenticReviewerReceipt']}
    return {'schemaVersion':'1.0.0','status':'PARTIAL_PUBLIC_MODEL_TEMPLATES_NORMATIVE_COVERAGE_PENDING',
        'sourceReceipt':'assets/source-receipt.json','normativeCoverageComplete':False,'templates':models,
        'genericRoleTemplates':[{'templateId':'generic-role-'+r['id'],'classKind':'PROJECT_FUNCTIONAL_ROLE_NOT_NORMATIVE_CLASS',
            'referenceRoleId':r['id'],'function':r['function'],'hardwareRepresentation':r['hardwareRepresentation'],
            'genericAllowedForAllCases':True,'normativeClassBindings':[], 'propertiesWithUnits':[],
            'modes':[], 'interfaces':[], 'commands':[], 'observations':[], 'topology':[], 'authority':[],
            'securityAndDynamicRisk':{'policyDigest':None,'threatAssessmentReceipt':None,'defaultCommandDecision':'DENY'},
            'parametersConstraintsUncertaintyFaults':None,'simulatorVersion':None,'caseBindings':[],
            'state':'UNBOUND_TEMPLATE_NOT_EXECUTABLE'} for r in roles],
        'genericDocumentTemplates':[{'templateId':'generic-document-'+kind,'classKind':'PROJECT_DOCUMENT_FIXTURE_NOT_NORMATIVE_CLASS',
            'synthetic':True,'genericAllowedCaseIds':[c['id'] for c in cases],
            'fields':{field:None for field in fields},'sourceProvenance':[],
            'reviewStatus':'UNPOPULATED_UNREVIEWED','authenticEvidence':False,
            'limitation':'A generic fixture cannot substitute for actual software execution, reviewer identity or admission approval.'}
            for kind,fields in documents.items()],
        'standardCoverage':[{'standardId':s['id'],'reference':s['reference'],
            'disposition':{'OP08':'PUBLIC_MODEL_SNAPSHOT_COVERED_NORMATIVE_REVIEW_PENDING','SC16':'PARTIAL_STIX_TAXII_CLASS_REVIEW_INTEGRATION_PENDING','OP17':'PARTIAL_OPCUA_DI_TYPES_CORE_MQTT_PENDING','OP23':'OWNER_SELECTED_FSGIM_CONTEXT_NORMATIVE_MAPPING_PENDING'}.get(s['id'],'NORMATIVE_CLASS_REVIEW_PENDING'),
            'relatedClassCatalog':{'SC16':'assets/threat-class-catalog.json','OP17':'assets/device-class-catalog.json','OP23':'assets/fsgim-integration-context.json'}.get(s['id']),
            **({'relatedResourceCatalog':'assets/taxii-resource-catalog.json'} if s['id']=='SC16' else {}),
            'primarySources':s['primarySources'],'requiredNextStep':'Freeze lawful exact edition/profile; enumerate classes with clause locators or substantiate no taxonomy; map every applicable class to template.',
            'fulfillmentReceipt':None} for s in standards]}

def check(root):
    try:
        expected=render(root)
        actual=json.loads((root/'assets/asset-class-catalog.json').read_text())
        return [] if expected==actual else ['Asset catalog differs from source-derived templates/coverage']
    except (ValueError,KeyError,OSError,TypeError) as exc:
        return [str(exc)]

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--write',action='store_true');args=parser.parse_args()
    if args.write:
        (ROOT/'assets/asset-class-catalog.json').write_text(json.dumps(render(ROOT),indent=2)+'\n')
    errors=check(ROOT)
    print(json.dumps({'result':'FAIL' if errors else 'PASS','publicModels':112,'normativeCoverageComplete':False,'errors':errors}))
    raise SystemExit(bool(errors))
