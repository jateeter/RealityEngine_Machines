#!/usr/bin/env python3
"""Build and verify the EI02 seed disposition/allocation plan; never author runtime machines."""
import argparse
import hashlib
import json
from pathlib import Path
import re

def read(path):
    return json.loads(path.read_text())

def require(ok, message):
    if not ok:
        raise ValueError(message)

def build(root):
    decision = read(root / 'identity-decision.json')
    imports = read(root / 'machine-import-manifest.json')
    band = decision['nativeAllocation']
    rows = []
    for index, entry in enumerate(e for e in imports['files'] if e['path'].endswith('.json')):
        path = root / entry['path']
        require(hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256'], 'Historical clone hash changed: ' + entry['path'])
        machine = read(path)['machine']
        stem = path.stem
        match = re.fullmatch(r'ENX(\d+)_(.+)', stem)
        if match:
            target = 'ENI' + match[1] + '_' + match[2]
            code = 'ENI' + match[1]
            disposition = 'ADAPT'
            rationale = 'Adapt ' + machine['metadata'].get('operationalFocus', machine['name']) + ' to standards-derived generic assets, explicit quality/authority and new Source/agent contracts; the legacy CES is reference material, not accepted behavior.'
        elif re.fullmatch(r'EnergyEnx\d+Interconnect', stem):
            suffix = re.search(r'\d+', stem)[0]
            target = 'ENI_IC_' + suffix
            code = target
            disposition = 'REPLACE'
            rationale = 'Replace legacy family aggregation with reviewed new-domain truth tables, explicit output-to-input semantics and new scoped bus consumers.'
        else:
            require(stem == 'EnergyResilientCommunityMicrogridCommandCenterInterconnect', 'Undispositioned seed: ' + stem)
            target = 'ENI_IC_CommandCenter'
            code = target
            disposition = 'REPLACE'
            rationale = 'Replace the legacy command bus with new-domain governance, evidence freshness, authority and recovery semantics; no shared legacy lanes by default.'
        start = band['offset'] + index * band['blockLength']
        windows = {kind: {'offset': start + layout['relativeOffset'], 'length': layout['length']} for kind, layout in band['blockLayout'].items()}
        source = machine['perceptualMapping']
        require(source['input']['length'] <= windows['input']['length'] and source['output']['length'] <= windows['output']['length'], 'Seed exceeds declared capacity: ' + stem)
        rows.append({'sourceFile': entry['path'], 'sourceSHA256': entry['sha256'], 'sourceName': machine['name'],
                     'disposition': disposition, 'rationale': rationale, 'implementationIssue': 'EI08',
                     'targetDomain': decision['canonicalDomain'], 'targetStem': target, 'targetId': target,
                     'targetCode': code, 'targetFile': target + '.json', 'targetName': 'Energy Infrastructure / ' + machine['name'],
                     'blockIndex': index, 'block': {'offset': start, 'length': band['blockLength']},
                     'candidateWindows': windows, 'sourceWindows': source,
                     'state': 'PLANNED_NOT_AUTHORED', 'rewiringRequired': ['category/tags/IDs', 'Sources and quality predicates', 'agents and completion mapping', 'triggers and governance', 'semantic identities and bus transfer/arbitration'],
                     'compatibilityAlias': None})
    require(len(rows) == band['seedBlockCount'] == imports['machineCount'] == 187, 'Seed disposition coverage changed')
    return {'schemaVersion': '1.0.0', 'domain': 'energyInfrastructure', 'canonicalDomain': decision['canonicalDomain'],
            'status': 'IDENTITY_ALLOCATION_PLAN_NOT_RUNTIME_PAYLOAD', 'workstreamId': 'EI02',
            'sourceCommit': imports['sourceCommit'], 'sourceImportManifestSHA256': hashlib.sha256((root / 'machine-import-manifest.json').read_bytes()).hexdigest(),
            'nativeAllocation': band, 'dispositions': rows, 'behavioralCasesRun': 0}

def interval_objects(value):
    if isinstance(value, dict):
        if isinstance(value.get('offset'), int) and isinstance(value.get('length'), int):
            yield value['offset'], value['length']
        for child in value.values():
            yield from interval_objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from interval_objects(child)

def validate(plan, decision, imports, *, existing_stems=(), existing_names=(), existing_prefixes=(), occupied=(), factory_aliases=None):
    errors = []
    def check(ok, message):
        if not ok:
            errors.append(message)
    rows = plan['dispositions']
    check(decision['canonicalDomain'] == plan['canonicalDomain'] == 'energy-infrastructure', 'Canonical identity mismatch')
    check(decision['factoryFolder'] == 'energyInfrastructure' and decision['migrationMode'] == 'COEXIST', 'Factory/coexistence decision changed')
    if factory_aliases is not None:
        check(factory_aliases.get(decision['canonicalDomain']) == decision['factoryFolder'], 'Factory mapping/identity decision mismatch')
    check(decision['status'] == 'ARCHITECTURE_DECISION_NOT_DOMAIN_ADMISSION' and decision['behavioralCasesRun'] == 0 and not decision['candidateMachinesAuthored'], 'False identity/admission execution claim')
    check(plan['status'] == 'IDENTITY_ALLOCATION_PLAN_NOT_RUNTIME_PAYLOAD' and plan['behavioralCasesRun'] == 0, 'False runtime payload claim')
    expected = {e['path']: e for e in imports['files'] if e['path'].endswith('.json')}
    check(len(rows) == len(expected) == 187 and {r['sourceFile'] for r in rows} == set(expected), 'Incomplete/duplicate187-machine disposition coverage')
    for key in ['targetStem', 'targetId', 'targetCode', 'targetName', 'targetFile']:
        check(len({r[key].casefold() for r in rows}) == len(rows), 'Duplicate target identity: ' + key)
    stems = {s.casefold() for s in existing_stems}
    names = {s.casefold() for s in existing_names}
    prefixes = {s.casefold() for s in existing_prefixes}
    check(decision['codePrefix'].casefold() not in prefixes, 'Code prefix collision')
    band = plan['nativeAllocation']
    check(band == decision['nativeAllocation'] and band['status'] == 'FACTORY_PLAN_NOT_ACTIVE_RESERVATION', 'Native plan/activation mismatch')
    check(band['length'] == band['blockLength'] * band['blockCount'] and band['seedBlockCount'] + band['extensionBlockCount'] == band['blockCount'], 'Invalid native capacity arithmetic')
    start, end = band['offset'], band['offset'] + band['length']
    for offset, length in occupied:
        check(not (start < offset + length and offset < end), f'Native allocation collision: [{offset},{offset + length})')
    for index, row in enumerate(rows):
        check(row['disposition'] in ['ADAPT', 'REPLACE', 'RETAIN_REFERENCE', 'EXCLUDE'] and bool(row['rationale']), 'Missing reviewed disposition')
        check(row['sourceFile'] in expected and row['sourceSHA256'] == expected.get(row['sourceFile'], {}).get('sha256'), 'Source provenance mismatch')
        check(row['state'] == 'PLANNED_NOT_AUTHORED' and row['targetDomain'] == decision['canonicalDomain'] and row['compatibilityAlias'] is None, 'Unreviewed machine migration')
        check(row['targetId'] == row['targetStem'] and row['targetFile'] == row['targetStem'] + '.json' and row['targetStem'].startswith(decision['codePrefix']) and row['targetCode'].startswith(decision['codePrefix']), 'Deployment ID/stem/prefix mismatch')
        check(row['targetStem'].casefold() not in stems and row['targetName'].casefold() not in names, 'Existing machine identity collision')
        block = row['block']
        check(row['blockIndex'] == index and block == {'offset': start + index * band['blockLength'], 'length': band['blockLength']} and block['offset'] + block['length'] <= end, 'Overlapping/out-of-band machine block')
        used = []
        for kind, window in row['candidateWindows'].items():
            layout = band['blockLayout'][kind]
            check(window == {'offset': block['offset'] + layout['relativeOffset'], 'length': layout['length']}, 'Window/layout mismatch')
            check(window['length'] > 0 and block['offset'] <= window['offset'] and window['offset'] + window['length'] <= block['offset'] + block['length'], 'Window exceeds block')
            for offset, length in used:
                check(not (window['offset'] < offset + length and offset < window['offset'] + window['length']), 'Intra-block overlap')
            used.append((window['offset'], window['length']))
        check(set(row['candidateWindows']) == {'input', 'output', 'routing'}, 'Missing candidate window')
    return errors

def current_occupancy(repo, root, canonical):
    stems, names, prefixes, windows = [], [], [], []
    manifest = read(repo / 'domains/domain-manifest.json')
    for domain, entry in manifest['domains'].items():
        if domain != canonical:
            prefixes.extend(entry['codePrefixes'])
    for path in sorted((repo / 'machines/domains').rglob('*.json')):
        if canonical in path.relative_to(repo / 'machines/domains').parts:
            continue
        machine = read(path).get('machine')
        if machine:
            stems.append(path.stem)
            names.append(machine['name'])
            windows.extend(interval_objects(machine.get('perceptualMapping', {})))
            code = machine.get('metadata', {}).get('tagging', {}).get('machineCode') or path.stem
            prefix = re.match(r'[A-Za-z]+', code)
            if prefix:
                prefixes.append(prefix[0])
    # Other factory candidate machines count as planned contenders too; our
    # unchanged historical clone is excluded from this prospective identity scan.
    for path in sorted((repo / 'machine_factory/domains').rglob('*.json')):
        if path.parent.name not in {'machines', 'candidate-machines'} or path.is_relative_to(root):
            continue
        machine = read(path).get('machine')
        if machine:
            stems.append(path.stem)
            names.append(machine['name'])
            windows.extend(interval_objects(machine.get('perceptualMapping', {})))
            code = machine.get('metadata', {}).get('tagging', {}).get('machineCode') or path.stem
            prefix = re.match(r'[A-Za-z]+', code)
            if prefix:
                prefixes.append(prefix[0])
    for rel in ['domains/domain-registry.json', 'domains/region-allocation.json']:
        value = read(repo / rel)
        if 'domains' in value:
            value['domains'].pop(canonical, None)
        windows.extend(interval_objects(value))
    mapping = repo / 'domains/factory-domain-paths.json'
    return dict(existing_stems=stems, existing_names=names, existing_prefixes=prefixes, occupied=windows,
                factory_aliases=read(mapping)['aliases'] if mapping.exists() else {})

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--repo', type=Path)
    parser.add_argument('--write', action='store_true', help='Write the reviewed plan only; never runtime files')
    args = parser.parse_args()
    root = args.root.resolve()
    repo = args.repo.resolve() if args.repo else root.parents[2]
    value = build(root)
    decision = read(root / 'identity-decision.json')
    imports = read(root / 'machine-import-manifest.json')
    errors = validate(value, decision, imports, **current_occupancy(repo, root, decision['canonicalDomain']))
    target = root / 'machine-dispositions.json'
    if args.write and not errors:
        target.write_text(json.dumps(value, indent=2) + '\n')
    elif not target.exists() or read(target) != value:
        errors.append('Disposition plan differs; review before explicit --write')
    print(json.dumps({'result': 'FAIL' if errors else 'PASS', 'verificationType': 'IDENTITY_ALLOCATION_PLAN_ONLY', 'canonicalDomain': decision['canonicalDomain'], 'factoryFolder': decision['factoryFolder'], 'dispositions': len(value['dispositions']), 'adapt': sum(r['disposition'] == 'ADAPT' for r in value['dispositions']), 'replace': sum(r['disposition'] == 'REPLACE' for r in value['dispositions']), 'nativePlan': [value['nativeAllocation']['offset'], value['nativeAllocation']['offset'] + value['nativeAllocation']['length']], 'activeDomainRangeRegistered': False, 'runtimeMachinesAuthored': False, 'errors': errors}, indent=2))
    return bool(errors)

if __name__ == '__main__':
    raise SystemExit(main())
