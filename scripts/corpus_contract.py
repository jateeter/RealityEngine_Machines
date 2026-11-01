#!/usr/bin/env python3
"""Versioned corpus-count transitions. Counts describe inventory, not admission."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

EXCLUDED = {'ArbitrationProviderPeer', 'ArbitrationProviderTarget', 'ArbitrationReader', 'ArbitrationWriterA', 'ArbitrationWriterB'}
BASE_COUNTS = dict(machines=1327, domains=12, agents=1322, agentBindings=1058, projections=1184)


def require(ok, message):
    if not ok: raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def sha(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def entry(data):
    machine = json.loads(data)['machine']; metadata = machine.get('metadata', {})
    return dict(sha256=hashlib.sha256(data).hexdigest(), name=machine['name'],
                agentExpected=re.sub('[^a-z0-9]', '', machine['name'].lower()) not in {re.sub('[^a-z0-9]', '', n.lower()) for n in EXCLUDED},
                agentBinding=bool(metadata.get('agentBinding')), projection=bool(metadata.get('openClawProjection')))


def inventory(repo):
    return {p.relative_to(repo / 'machines').as_posix(): entry(p.read_bytes())
            for p in sorted((repo / 'machines/domains').glob('*/*.json'))}


def counts(members):
    return dict(machines=len(members), domains=len({p.split('/')[1] for p in members}),
                agents=sum(m['agentExpected'] for m in members.values()),
                agentBindings=sum(m['agentBinding'] for m in members.values()),
                projections=sum(m['projection'] for m in members.values()))


def changes(before, after):
    return {p: {'before': before.get(p), 'after': after.get(p)}
            for p in sorted(set(before) | set(after)) if before.get(p) != after.get(p)}


def baseline(repo, ref):
    commit = subprocess.check_output(['git', 'rev-parse', '--verify', ref + '^{commit}'], cwd=repo, text=True).strip()
    paths = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', commit, 'machines/domains'], cwd=repo, text=True).splitlines()
    members = {p.removeprefix('machines/'): entry(subprocess.check_output(['git', 'show', commit + ':' + p], cwd=repo))
               for p in paths if p.endswith('.json') and len(Path(p).parts) == 4}
    require(counts(members) == BASE_COUNTS, 'Bootstrap baseline does not match published corpus-exit-v2.0 counts')
    return dict(schemaVersion='1.0.0', kind='PUBLISHED_BASELINE', contractRef='corpus-exit-v2.0',
                measuredCommit=commit, members=members, counts=counts(members))


def prepare(repo, domain, version, context, baseline_ref=None):
    require(re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', domain), 'Invalid domain')
    require(re.fullmatch(r'\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?', version), 'Invalid version')
    require(context in {'TEST_ONLY', 'PRODUCTION_CANDIDATE'}, 'Explicit approval context required')
    current = repo / 'domains/corpus-contract.json'
    predecessor = json.loads(current.read_text()) if current.exists() else baseline(repo, baseline_ref or 'corpus-exit-v2.0')
    if current.exists():
        validate_history(repo, predecessor)
    members = inventory(repo)
    # An unchanged repeat is deterministic; changing only context creates a new
    # reviewed transition rather than relabeling an old testing receipt.
    if predecessor.get('domain') == domain and predecessor.get('domainVersion') == version and predecessor.get('approvalContext') == context and predecessor['members'] == members:
        validate(repo)
        return predecessor, None
    delta = changes(predecessor['members'], members)
    require(all(p.startswith('domains/' + domain + '/') for p in delta), 'Undeclared changes outside candidate domain')
    manifest = json.loads((repo / 'domains/domain-manifest.json').read_text())['domains']
    require(domain in manifest, 'Candidate domain must be declared')
    require(manifest[domain]['currentMachineCount'] == sum(p.startswith('domains/' + domain + '/') for p in members), 'Manifest candidate count differs')
    before, after = predecessor['counts'], counts(members)
    result = dict(schemaVersion='1.0.0', kind='DOMAIN_TRANSITION', domain=domain, domainVersion=version,
                  approvalContext=context, productionApproval=False, status='PREPARED_INVENTORY_NOT_DOMAIN_APPROVAL',
                  predecessorSHA256=sha(predecessor), predecessorCounts=before, changes=delta,
                  countDelta={key: after[key] - before[key] for key in after}, members=members, counts=after)
    return result, predecessor


def write_transition(repo, contract, predecessor):
    if predecessor is not None:
        folder = repo / 'domains/corpus-contracts'; folder.mkdir(exist_ok=True)
        target = folder / (sha(predecessor) + '.json')
        if target.exists(): require(json.loads(target.read_text()) == predecessor, 'Immutable predecessor changed')
        else: target.write_text(json.dumps(predecessor, indent=2, sort_keys=True) + '\n')
    (repo / 'domains/corpus-contract.json').write_text(json.dumps(contract, indent=2, sort_keys=True) + '\n')


def validate_history(repo, contract, seen=None):
    seen = set() if seen is None else seen
    fingerprint = sha(contract); require(fingerprint not in seen, 'Corpus contract history cycle'); seen.add(fingerprint)
    require(contract['counts'] == counts(contract['members']), 'Contract counts do not describe its members')
    if contract['kind'] == 'PUBLISHED_BASELINE':
        require(contract['contractRef'] == 'corpus-exit-v2.0' and contract['counts'] == BASE_COUNTS, 'Invalid published baseline')
        return
    require(contract['kind'] == 'DOMAIN_TRANSITION' and contract['productionApproval'] is False, 'Inventory transition cannot grant approval')
    require(contract['approvalContext'] in {'TEST_ONLY', 'PRODUCTION_CANDIDATE'}, 'Invalid approval context')
    digest = contract['predecessorSHA256']; require(re.fullmatch('[0-9a-f]{64}', digest), 'Invalid predecessor digest')
    previous = json.loads((repo / 'domains/corpus-contracts' / (digest + '.json')).read_text())
    require(sha(previous) == digest, 'Predecessor content hash changed')
    validate_history(repo, previous, seen)
    require(contract['predecessorCounts'] == previous['counts'], 'Predecessor counts changed')
    delta = changes(previous['members'], contract['members'])
    require(delta == contract['changes'], 'Declared candidate changes differ from inventory')
    require(all(p.startswith('domains/' + contract['domain'] + '/') for p in delta), 'Undeclared peer-domain change')
    require(contract['countDelta'] == {k: contract['counts'][k] - previous['counts'][k] for k in contract['counts']}, 'Count delta changed')


def validate(repo):
    contract = json.loads((repo / 'domains/corpus-contract.json').read_text())
    validate_history(repo, contract)
    require(contract['members'] == inventory(repo), 'Current corpus differs from reviewed transition inventory')
    manifest = json.loads((repo / 'domains/domain-manifest.json').read_text())['domains']
    for domain in {p.split('/')[1] for p in contract['members']}:
        require(domain in manifest, 'Unregistered domain in corpus transition')
        require(manifest[domain]['currentMachineCount'] == sum(p.startswith('domains/' + domain + '/') for p in contract['members']), 'Domain manifest count differs: ' + domain)
    return contract


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('prepare'); p.add_argument('--domain', required=True); p.add_argument('--version', required=True)
    p.add_argument('--approval-context', required=True, choices=['TEST_ONLY', 'PRODUCTION_CANDIDATE'])
    p.add_argument('--baseline-ref'); p.add_argument('--write', action='store_true')
    sub.add_parser('check')
    args = parser.parse_args(); repo = args.repo.resolve()
    if args.action == 'prepare':
        result, previous = prepare(repo, args.domain, args.version, args.approval_context, args.baseline_ref)
        if args.write: write_transition(repo, result, previous); validate(repo)
    else: result = validate(repo)
    print(json.dumps({k: result[k] for k in ['kind', 'counts'] + (['approvalContext', 'countDelta'] if result['kind'] == 'DOMAIN_TRANSITION' else [])}, indent=2))


if __name__ == '__main__': main()
