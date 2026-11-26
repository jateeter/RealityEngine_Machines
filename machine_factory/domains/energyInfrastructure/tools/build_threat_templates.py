#!/usr/bin/env python3
"""Reproduce source-backed threat information classes; no conformance claim."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT=Path(__file__).resolve().parents[1]
SDOS='attack-pattern campaign course-of-action grouping identity incident indicator infrastructure intrusion-set location malware malware-analysis note observed-data opinion report threat-actor tool vulnerability'.split()
SCOS='artifact autonomous-system directory domain-name email-addr email-message file ipv4-addr ipv6-addr mac-addr mutex network-traffic process software url user-account windows-registry-key x509-certificate'.split()
CLAUSES={**{'sdos/'+name+'.json':'4.'+str(i+1) for i,name in enumerate(SDOS)},**{'observables/'+name+'.json':'6.'+str(i+1) for i,name in enumerate(SCOS)},'sros/relationship.json':'5.1','sros/sighting.json':'5.2','common/language-content.json':'7.1','common/marking-definition.json':'7.2.1','common/extension-definition.json':'7.3','common/bundle.json':'8'}

def pointer(data,fragment):
    if not fragment:return data
    if not fragment.startswith('/'):raise ValueError('Unsupported schema anchor: '+fragment)
    for part in fragment[1:].split('/'):
        key=unquote(part).replace('~1','/').replace('~0','~')
        data=data[int(key)] if isinstance(data,list) else data[key]
    return data

def render(root):
    receipt=json.loads((root/'assets/stix-source-receipt.json').read_text())
    source=root/'intake/public-models/stix21'
    if receipt['commit']!='9af1db41b7b86c06324f899649ae83480134f66e' or receipt['license']!='BSD-3-Clause' or receipt['ragIndexed'] or receipt['schemaAuthority']!='NON_NORMATIVE_OASIS_TC_OPEN_REPOSITORY':raise ValueError('STIX source identity/rights boundary changed')
    if receipt['repository']!='https://github.com/oasis-open/cti-stix2-json-schemas' or receipt['schemaCount']!=57 or receipt['licenseFile']!='intake/public-models/stix21/LICENSE':raise ValueError('STIX source receipt metadata mismatch')
    if receipt['normativeReference']['url']!='https://docs.oasis-open.org/cti/stix/v2.1/os/stix-v2.1-os.html' or receipt['normativeReference']['storedNormativeText'] is not False:raise ValueError('Unsupported normative source claim')
    actual={p.relative_to(root).as_posix() for p in source.rglob('*') if p.is_file()}
    if actual!={r['path'] for r in receipt['files']}:raise ValueError('STIX source inventory mismatch')
    for entry in receipt['files']:
        p=root/entry['path']
        if not p.resolve().is_relative_to(source.resolve()) or hashlib.sha256(p.read_bytes()).hexdigest()!=entry['sha256']:raise ValueError('STIX source hash/path mismatch')
    folder=source/'schemas';schemas={p.relative_to(folder).as_posix():json.loads(p.read_text()) for p in sorted(folder.rglob('*.json'))}
    if len(schemas)!=57 or not set(CLAUSES)<=set(schemas):raise ValueError('STIX schema/class inventory mismatch')
    templates=[]
    for rel,schema in schemas.items():
        refs=[];required=[]
        def walk(value,location=''):
            if isinstance(value,dict):
                if '$ref' in value:
                    uri=urlsplit(value['$ref'])
                    if uri.scheme or uri.netloc or uri.query:raise ValueError('Nonlocal schema reference: '+value['$ref'])
                    target=((folder/rel).parent/unquote(uri.path)).resolve() if uri.path else (folder/rel).resolve()
                    if not target.is_relative_to(folder.resolve()):raise ValueError('Escaping schema reference')
                    targetRel=target.relative_to(folder.resolve()).as_posix()
                    pointer(schemas[targetRel],unquote(uri.fragment))
                    refs.append({'pointer':location+'/$ref','target':targetRel,'fragment':uri.fragment})
                if 'required' in value:required.append({'pointer':location+'/required','properties':value['required']})
                for k,v in value.items():walk(v,location+'/'+k.replace('~','~0').replace('/','~1'))
            elif isinstance(value,list):
                for i,v in enumerate(value):walk(v,location+'/'+str(i))
        walk(schema)
        clause=CLAUSES.get(rel)
        templates.append({'templateId':'stix21-'+rel.removesuffix('.json').replace('/','-'),'classId':schema.get('title',Path(rel).stem),
            'classKind':'STANDARD_DEFINED_CYBER_INFORMATION_OBJECT' if clause else 'SUPPORTING_SCHEMA_NOT_TOP_LEVEL_OBJECT',
            'definitionStatus':'STUB_WITH_LIMITED_METADATA' if rel in ['sdos/course-of-action.json','sdos/incident.json'] else ('TOP_LEVEL_OBJECT_OR_CONTAINER' if clause else 'SUPPORTING_SCHEMA'),
            'standardId':'SC16','edition':'STIX 2.1 OASIS Standard 2021-06-10','clause':clause,
            'normativeURL':receipt['normativeReference']['url'] if clause else None,
            'schemaPath':(folder/rel).relative_to(root).as_posix(),'schemaId':schema['$id'],
            'schemaAuthority':'NON_NORMATIVE','requiredDeclarations':required,'references':refs,
            'instance':{'payload':None,'synthetic':True,'authority':'ANALYST_REVIEW_ONLY','automaticControlAction':'DENY','executionReceipt':None},
            'limitations':'Schema requirements/conditionals and references remain in the unmodified source. No physical asset equivalence, TAXII transport, pattern-language validity, semantic conformance or admission claim.'})
    return {'schemaVersion':'1.0.0','status':'PARTIAL_SC16_STIX_OBJECT_SCHEMA_COVERAGE_TAXII_PENDING','sourceReceipt':'assets/stix-source-receipt.json',
        'normativeCoverageComplete':False,'schemaCount':57,'topLevelObjectAndContainerCount':len(CLAUSES),'supportingSchemaCount':57-len(CLAUSES),'templates':templates,
        'remaining':['TAXII edition/services/classes and peer integration','Nested extension/type normative class review','Full prose requirements, errata applicability and STIX semantic/pattern validation','Cross-standard mappings and secure threat assessment integration','Authentic runtime and admission evidence']}

def check(root):
    try:return [] if render(root)==json.loads((root/'assets/threat-class-catalog.json').read_text()) else ['Threat class catalog/source mismatch']
    except (OSError,ValueError,KeyError,TypeError,IndexError) as e:return [str(e)]

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');args=p.parse_args()
    if args.write:(ROOT/'assets/threat-class-catalog.json').write_text(json.dumps(render(ROOT),indent=2)+'\n')
    errors=check(ROOT);print(json.dumps({'result':'FAIL' if errors else 'PASS','schemaTemplates':57,'topLevelObjectAndContainerTemplates':43,'normativeCoverageComplete':False,'errors':errors}));raise SystemExit(bool(errors))
