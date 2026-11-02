"""Final runtime copy with immutable deployment versions; factory assets stay active."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import uuid


def require(ok, message):
    if not ok: raise ValueError(message)


def read(path): return json.loads(Path(path).read_text())
def filehash(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def objecthash(value): return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def identity(domain, version, context):
    require(re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', domain), 'Invalid domain')
    require(re.fullmatch(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[A-Za-z0-9.-]+)?', version), 'Invalid deployment version')
    if '-' in version:
        require(all(p and not (p.isdigit() and len(p)>1 and p.startswith('0')) for p in version.split('-',1)[1].split('.')), 'Invalid deployment prerelease version')
    require(context in {'TEST_ONLY', 'PRODUCTION'}, 'Explicit deployment context required')
    if context == 'TEST_ONLY': require('-' in version, 'Test deployment needs a prerelease version')


def inside(repo, path):
    require(path.resolve().is_relative_to(repo.resolve()), 'Path escapes repository')
    require(not path.is_symlink(), 'Symlink deployment paths are forbidden')
    for parent in path.parents:
        if parent == repo: break
        require(not parent.is_symlink(), 'Symlink deployment ancestor is forbidden')


def machine_files(directory, domain):
    require(directory.is_dir() and not directory.is_symlink(), 'Runtime machine source directory required')
    result = {}
    for p in sorted(directory.iterdir()):
        require(p.is_file() and not p.is_symlink() and p.suffix == '.json', 'Payload directory must contain only runtime machine JSON files')
        data = read(p); m = data.get('machine', {})
        require(m.get('id') == p.stem and m.get('name') and m.get('metadata', {}).get('category') == domain,
                'Invalid runtime machine identity/domain: ' + p.name)
        require(m.get('sequences') and m.get('perceptualMapping'), 'Not a runtime machine: ' + p.name)
        result[p.name] = filehash(p)
    require(result, 'Empty runtime payload')
    return result


def atomic_write(path, data, exclusive=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name('.' + path.name + '.' + uuid.uuid4().hex)
    try:
        temporary.write_bytes(data)
        if exclusive: os.link(temporary, path)
        else: os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def json_bytes(value): return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def package(repo, domain, version, context, source, write=False):
    identity(domain, version, context); inside(repo, source)
    members = machine_files(source, domain)
    folder = repo / 'machine_factory/domains' / domain / 'deployments' / version
    inside(repo, folder)
    manifest_path = folder / 'payload-manifest.json'
    if manifest_path.exists():
        existing = validate_payload(repo, manifest_path)
        require(existing['files'] == members and existing['approvalContext'] == context, 'Deployment version already contains another payload')
        return manifest_path, existing
    domain_versions = {read(source / name).get('version') for name in members}
    require(len(domain_versions) == 1 and None not in domain_versions, 'Runtime document versions must agree')
    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=repo, capture_output=True, text=True)
    manifest = dict(schemaVersion='1.0.0', domain=domain, deploymentVersion=version,
                    domainVersion=next(iter(domain_versions)), approvalContext=context,
                    payloadRoot=str((folder / 'machines').relative_to(repo)), files=members,
                    sourceCommit=commit.stdout.strip() if commit.returncode == 0 else 'SYNTHETIC_UNIT_REPOSITORY',
                    factoryLifecycle='ACTIVE_FOR_FUTURE_EXTENSIONS')
    if write:
        require(not folder.exists(), 'Unfinished payload directory exists; inspect it before reusing this version')
        for name in members: atomic_write(folder / 'machines' / name, (source / name).read_bytes(), exclusive=True)
        atomic_write(manifest_path, json_bytes(manifest), exclusive=True)
        validate_payload(repo, manifest_path)
    return manifest_path, manifest


def validate_payload(repo, path):
    inside(repo, path); manifest = read(path)
    domain, version, context = (manifest[k] for k in ['domain', 'deploymentVersion', 'approvalContext'])
    identity(domain, version, context)
    folder = repo / 'machine_factory/domains' / domain / 'deployments' / version
    require(path.resolve() == (folder / 'payload-manifest.json').resolve(), 'Unexpected factory payload location')
    require(manifest['payloadRoot'] == str((folder / 'machines').relative_to(repo)), 'Payload root changed')
    inside(repo, folder / 'machines')
    require(machine_files(folder / 'machines', domain) == manifest['files'], 'Factory payload content/hash changed')
    return manifest


def check_counts(repo):
    spec = importlib.util.spec_from_file_location('deployment_corpus_contract', Path(__file__).resolve().parents[1] / 'corpus_contract.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    module.validate(repo)


def verify_evidence(repo, manifest, evidence, waiver, production_verifier):
    domain = manifest['domain']
    status = read(repo / 'domains/domain-manifest.json')['domains'][domain]['status']
    expected = {'domains/' + domain + '/' + name: sha for name, sha in manifest['files'].items()}
    if manifest['approvalContext'] == 'PRODUCTION':
        require(waiver is None, 'Testing waivers cannot authorize production deployment')
        require(status == 'accepted', 'Production domain must already be admitted')
        require(evidence.get('state') == 'APPROVED_MERGED' and evidence.get('domain') == domain,
                'Production deployment requires finalized domain approval')
        require(evidence.get('version') == manifest['domainVersion'], 'Approval belongs to another domain version')
        require(evidence.get('candidateMachines') == expected, 'Approved machine inventory differs from payload')
        require(evidence.get('approvalContext') != 'TEST_ONLY' and evidence.get('productionApproval') is not False,
                'Test evidence cannot authorize production deployment')
        require(production_verifier is not None, 'Live Git approval verification required')
        production_verifier(evidence)
    else:
        require(status != 'accepted', 'Test deployment cannot replace an admitted production domain')
        require(evidence.get('approvalContext') == 'TEST_ONLY' and evidence.get('productionApproval') is False,
                'Test deployment requires explicit test-only evidence')
        require(waiver and waiver.get('domain') == domain and waiver.get('approvalContext') == 'TEST_ONLY'
                and waiver.get('productionApproval') is False
                and waiver.get('independentSignoff') == 'WAIVED_BY_OPERATOR_FOR_WORKFLOW_TEST', 'Testing waiver required')
        contract = read(repo / 'domains/corpus-contract.json')
        require(evidence.get('countReconciliation', {}).get('transitionSHA256') == objecthash(contract), 'Evidence names another corpus transition')
        scoped = {p: m['sha256'] for p, m in contract['members'].items() if p.startswith('domains/' + domain + '/')}
        require(scoped == expected, 'Tested runtime inventory differs from deployment payload')
        require(evidence.get('native', {}).get('quorum') == '3-of-3'
                and evidence['native'].get('machinesPerRuntime') == len(expected), 'Actual native test inventory required')
        require(evidence.get('managerLoad', {}).get('result') == 'PASS_MANAGER_LOAD_API', 'Manager load evidence required')


def check_deployment(repo, domain, version):
    path = repo / 'domains/deployments' / domain / (version + '.json'); inside(repo, path)
    record = read(path); identity(domain, version, record['approvalContext'])
    require(record['domain'] == domain and record['deploymentVersion'] == version
            and record['state'] == 'DEPLOYED_RUNTIME_COPY_VERIFIED', 'Deployment record identity/state differs')
    payload = repo / record['payloadManifest']; manifest = validate_payload(repo, payload)
    require(record['payloadManifestSHA256'] == filehash(payload) and record['files'] == manifest['files']
            and record['approvalContext'] == manifest['approvalContext']
            and record['productionApproval'] == (manifest['approvalContext'] == 'PRODUCTION')
            and record['machineCount'] == len(manifest['files'])
            and record['domainVersion'] == manifest['domainVersion'], 'Deployment record differs from verified payload')
    require(record['target'] == 'machines/domains/' + domain, 'Unexpected deployment target')
    evidence = repo / record['approvalEvidence']; inside(repo, evidence)
    require(filehash(evidence) == record['approvalEvidenceSHA256'], 'Deployment approval evidence changed')
    if record.get('operatorWaiver'):
        waiver = repo / record['operatorWaiver']; inside(repo, waiver)
        require(filehash(waiver) == record['operatorWaiverSHA256'], 'Deployment waiver changed')
    pointer = read(path.parent / 'current.json')
    require(pointer['domain'] == domain and pointer['deploymentVersion'] == version
            and pointer['approvalContext'] == record['approvalContext'] and pointer['productionApproval'] == record['productionApproval']
            and pointer['receipt'] == str(path.relative_to(repo)) and pointer['receiptSHA256'] == filehash(path), 'Current deployment pointer/receipt integrity mismatch')
    require(machine_files(repo / record['target'], domain) == record['files'], 'Deployed runtime has drifted')
    check_counts(repo)
    return record


def deploy(repo, payload, evidence_path, waiver_path=None, write=False, production_verifier=None):
    inside(repo, evidence_path)
    if waiver_path: inside(repo, waiver_path)
    manifest = validate_payload(repo, payload)
    evidence = read(evidence_path); waiver = read(waiver_path) if waiver_path else None
    verify_evidence(repo, manifest, evidence, waiver, production_verifier)
    domain, version = manifest['domain'], manifest['deploymentVersion']
    target = repo / 'machines/domains' / domain; inside(repo, target)
    receipts = repo / 'domains/deployments' / domain; inside(repo, receipts)
    record_path, current_path = receipts / (version + '.json'), receipts / 'current.json'
    require(not current_path.is_symlink() and not record_path.is_symlink(), 'Deployment receipt symlink forbidden')
    expected = manifest['files']; before = machine_files(target, domain) if target.exists() else {}
    require(set(before) <= set(expected), 'Unapproved target files would survive deployment; reconcile removals first')
    previous = read(current_path) if current_path.exists() else None
    if previous:
        identity(domain, previous['deploymentVersion'], previous['approvalContext'])
        previous_receipt = receipts / (previous['deploymentVersion'] + '.json')
        require(previous.get('domain') == domain and previous.get('receipt') == str(previous_receipt.relative_to(repo))
                and not previous_receipt.is_symlink() and filehash(previous_receipt) == previous.get('receiptSHA256'),
                'Current deployment pointer/receipt integrity mismatch')
    if record_path.exists():
        record = read(record_path)
        require(record['payloadManifestSHA256'] == filehash(payload), 'Immutable deployment version already used')
        require(previous and previous['deploymentVersion'] == version, 'Use a new version for rollback; do not move the current pointer backwards')
        require(before == expected, 'Deployed runtime has drifted')
        return check_deployment(repo, domain, version)
    if previous:
        last = read(receipts / (previous['deploymentVersion'] + '.json'))
        require(before == last['files'] or before == expected, 'Current runtime differs from both prior and approved inventories')
    record = dict(schemaVersion='1.0.0', domain=domain, deploymentVersion=version, domainVersion=manifest['domainVersion'],
                  approvalContext=manifest['approvalContext'], productionApproval=manifest['approvalContext'] == 'PRODUCTION',
                  state='DEPLOYED_RUNTIME_COPY_VERIFIED' if write else 'DEPLOYMENT_DRY_RUN',
                  target=str(target.relative_to(repo)), files=expected, machineCount=len(expected),
                  payloadManifest=str(payload.relative_to(repo)), payloadManifestSHA256=filehash(payload),
                  approvalEvidence=str(evidence_path.relative_to(repo)), operatorWaiver=str(waiver_path.relative_to(repo)) if waiver_path else None,
                  approvalEvidenceSHA256=filehash(evidence_path), operatorWaiverSHA256=filehash(waiver_path) if waiver_path else None,
                  factoryLifecycle='ACTIVE_FOR_FUTURE_EXTENSIONS', previousDeployment=previous)
    if not write: return record
    originals = {name: (target / name).read_bytes() if (target / name).exists() else None for name in expected}
    old_pointer = current_path.read_bytes() if current_path.exists() else None
    created_receipt = False
    try:
        for name in expected: atomic_write(target / name, (repo / manifest['payloadRoot'] / name).read_bytes())
        require(machine_files(target, domain) == expected, 'Runtime copy verification failed')
        check_counts(repo)
        atomic_write(record_path, json_bytes(record), exclusive=True)
        created_receipt = True
        atomic_write(current_path, json_bytes(dict(schemaVersion='1.0.0', domain=domain, deploymentVersion=version,
                     approvalContext=record['approvalContext'], productionApproval=record['productionApproval'],
                     receipt=str(record_path.relative_to(repo)), receiptSHA256=filehash(record_path))))
    except BaseException:
        for name, data in originals.items():
            if data is None: (target / name).unlink(missing_ok=True)
            else: atomic_write(target / name, data)
        if created_receipt: record_path.unlink(missing_ok=True)
        if old_pointer is None: current_path.unlink(missing_ok=True)
        else: atomic_write(current_path, old_pointer)
        raise
    return record
