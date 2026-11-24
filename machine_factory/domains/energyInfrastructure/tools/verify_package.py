#!/usr/bin/env python3
"""Offline package integrity only; never admission, runtime or field assurance."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

EXCLUDED = {'asset-manifest.json', 'verification-summary.json'}
EXPECTED_COUNTS = {'standards': 46, 'implementations': 29, 'sources': 18,
                   'carbonProviders': 7, 'risks': 20, 'cases': 43, 'phases': 10}
PDF_HASH = 'c1e6193af8f94b3f4fc48725a2e3c6eea497d9999cb968ecec2cb6be5d429c86'

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def excluded(path: Path, root: Path) -> bool:
    return path.relative_to(root).as_posix() in EXCLUDED or path.name == '.DS_Store' or '__pycache__' in path.parts or path.suffix == '.pyc'

def check(root: Path) -> dict:
    root = root.resolve()
    errors: list[str] = []
    checks = 0
    def require(ok: bool, message: str) -> None:
        nonlocal checks
        checks += 1
        if not ok:
            errors.append(message)
    def read(rel: str):
        return json.loads((root / rel).read_text())
    def safe(rel: str) -> Path:
        p = root / rel
        if Path(rel).is_absolute() or not p.resolve().is_relative_to(root):
            raise ValueError(f'Path escapes package: {rel}')
        return p
    required = ['README.md','PACKAGE_STATUS.md','WORKPLAN.md','reports/Secure microgrid interoperability.md',
                'documents/workflow/architecture.md','documents/workflow/security-and-dynamic-risk.md',
                'documents/workflow/agent-model-integration.md','documents/workflow/rag-collection-and-governance.md',
                'documents/workflow/electricity-carbon-intensity.md','standards-inventory.json',
                'implementation-inventory.json','rag-source-manifest.json','risk-register.json',
                'acceptance/cases.json','acceptance/workplan.json','machine-import-manifest.json',
                'acceptance/issues.json','acceptance/scope.json','acceptance/coverage-requirements.json',
                'intake/NIST.SP.1108r4_1.pdf','templates/interoperability-profile.json',
                'templates/command-proposal.json','templates/rag-source-record.json',
                'examples/der-supervisory-profile.json','asset-manifest.json']
    for rel in required:
        require(safe(rel).is_file(), f'Missing required file: {rel}')
    if errors:
        return {'result':'FAIL','checks':checks,'errors':errors}
    files = [p for p in root.rglob('*') if p.is_file() and not excluded(p, root)]
    for p in files:
        require(not p.is_symlink(),f'Symlink not allowed: {p.relative_to(root)}')
        if p.suffix == '.json':
            try: json.loads(p.read_text())
            except (ValueError,UnicodeError) as e: require(False,f'Invalid JSON {p.relative_to(root)}: {e}')
    asset = read('asset-manifest.json')
    require(asset.get('excludedOutputs') == sorted(EXCLUDED), 'Asset exclusion contract changed')
    recorded = {e['path']: e for e in asset['files']}
    require(len(recorded)==len(asset['files']), 'Duplicate asset paths')
    actual = {p.relative_to(root).as_posix() for p in files}
    require(actual == set(recorded), f'Asset file-set mismatch: missing={sorted(set(recorded)-actual)} extra={sorted(actual-set(recorded))}')
    for rel,e in recorded.items():
        p=safe(rel)
        require(p.is_file(),f'Missing hashed asset: {rel}')
        if p.is_file():
            require(digest(p)==e['sha256'],f'Asset digest mismatch: {rel}')
            require(p.stat().st_size==e['bytes'],f'Asset size mismatch: {rel}')
    imports=read('machine-import-manifest.json')
    require(imports['domain']=='energyInfrastructure','Clone domain changed')
    require(imports['status']=='CLONED_NOT_ADMITTED','Clone status changed')
    require(imports['machineCount']==187 and imports['copiedFileCount']==188,'Clone counts changed')
    original_names=set()
    for e in imports['files']:
        p=safe(e['path']);original_names.add(e['path'])
        require(p.is_file() and digest(p)==e['sha256'],f'Historical clone mismatch: {e["path"]}')
    clone_files={p.relative_to(root).as_posix() for p in (root/'machines').rglob('*') if p.is_file() and p.name!='.DS_Store'}
    require(clone_files==original_names,'Historical clone file set changed')
    datasets={
        'standards':read('standards-inventory.json')['standards'],
        'implementations':read('implementation-inventory.json')['implementations'],
        'sources':read('rag-source-manifest.json')['sources'],
        'carbonProviders':read('rag-source-manifest.json')['carbonProviders'],
        'risks':read('risk-register.json')['risks'],
        'cases':read('acceptance/cases.json')['cases'],
        'phases':read('acceptance/workplan.json')['phases']}
    ids={}
    for name,entries in datasets.items():
        values=[e['id'] for e in entries];ids[name]=set(values)
        require(len(entries)==EXPECTED_COUNTS[name],f'{name} count changed; review expectation intentionally')
        require(len(values)==len(set(values)),f'Duplicate {name} identifiers')
    for rel in ['standards-inventory.json','implementation-inventory.json','rag-source-manifest.json','risk-register.json','acceptance/cases.json','acceptance/workplan.json']:
        d=read(rel)
        require(d['domain']=='energyInfrastructure' and d['status']=='DESIGN_PACKAGE_NOT_ADMITTED',f'Unreviewed domain/status: {rel}')
        require(d['canonicalDomainProposal']=='energy-infrastructure',f'Canonical proposal changed: {rel}')
    for e in datasets['standards']:
        require(bool(e['primarySources']) and e['conformanceStatus']=='NOT_ASSESSED',f'Standard lacks source or claims assessment: {e["id"]}')
    for e in datasets['implementations']:
        require(e['immutableVersion']=='REQUIRED_BEFORE_USE' and e['integrationEvidence'] is None,f'Implementation evidence/pin claim changed: {e["id"]}')
    rag=read('rag-source-manifest.json')
    require(rag['ingestionPerformed'] is False,'Unexpected ingestion claim')
    for e in datasets['sources']:
        require(not e['extracted'] and not e['indexed'] and not e['retrievalValidated'],f'Unverified RAG state: {e["id"]}')
        if e['id']=='R01':
            require(e['collectionStatus']=='RECEIVED' and e['physicalPages']==239,'NIST receipt state/count changed')
            p=safe(e['localArtifact'])
            require(e['sourceSHA256']==PDF_HASH and digest(p)==PDF_HASH,'NIST original hash mismatch')
            require(p.stat().st_size==e['bytes'],'NIST byte count mismatch')
        else:
            require(e['collectionStatus']=='TO_COLLECT' and e['sourceSHA256'] is None and e['localArtifact'] is None,f'Unverified collection claim: {e["id"]}')
    require(any(x['status']=='DO_NOT_INGEST' and x['project']=='Step Function DNP3' for x in rag['excludedMaterials']),'Restricted DNP exclusion missing')
    for c in datasets['cases']:
        require(c['status']=='NOT_RUN' and c['resultReceipt'] is None,f'Unverified behavioral PASS: {c["id"]}')
        require(set(c['standardIds'])<=ids['standards'],f'Unknown standard in {c["id"]}')
        require(set(c['riskIds'])<=ids['risks'],f'Unknown risk in {c["id"]}')
    for r in datasets['risks']:
        require(r['initialRisk']=='UNASSESSED_REFERENCE_SCENARIO_REQUIRED' and r['residualRisk']=='NOT_ACCEPTED',f'Unreviewed risk acceptance: {r["id"]}')
        require(bool(r['acceptanceCaseIds']) and set(r['acceptanceCaseIds'])<=ids['cases'],f'Unknown/missing risk case: {r["id"]}')
        for c in datasets['cases']:
            require((r['id'] in c['riskIds'])==(c['id'] in r['acceptanceCaseIds']),f'Asymmetric risk/case traceability: {r["id"]}/{c["id"]}')
    seen=set()
    for phase in datasets['phases']:
        require(set(phase['dependsOn'])<=seen,f'Phase order/cycle error: {phase["id"]}')
        require(phase['status']=='NOT_STARTED' and phase['evidenceReceipt'] is None,f'Unverified workplan execution: {phase["id"]}')
        seen.add(phase['id'])
    require(set(read('acceptance/workplan.json')['requiredCaseIds'])==ids['cases'],'Workplan case coverage mismatch')
    backlog=read('acceptance/issues.json')
    scope=read('acceptance/scope.json')
    expected_policy={
        'hardwareMode':'SIMULATED_REQUIRED_HARDWARE',
        'genericAssetsAllowedForAllCases':True,
        'assetClassesDefinedByAssociatedStandards':True,
        'physicalHardwareRequired':False,
        'physicalCommissioningRequiredForAdmission':False,
        'softwareExecutionMustBeGenuine':True,
        'authenticAdmissionEvidenceRequired':True,
        'assetTemplateDeliveryIssue':'EI04',
        'simulatedHardwareCoverageIssue':'EI18',
        'templateCoverageStatus':'PLANNED_NOT_IMPLEMENTED',
        'simulatorCoverageStatus':'PLANNED_NOT_IMPLEMENTED'}
    for rel in ['acceptance/scope.json','acceptance/issues.json','acceptance/cases.json',
                'acceptance/workplan.json','risk-register.json','standards-inventory.json',
                'implementation-inventory.json','rag-source-manifest.json',
                'templates/interoperability-profile.json','templates/command-proposal.json',
                'examples/der-supervisory-profile.json']:
        require(read(rel).get('acceptancePolicy')==expected_policy,f'Acceptance scope mismatch: {rel}')
    require(scope['status']=='APPROVED_PLANNING_SCOPE_NOT_EXECUTION','Scope is not an execution receipt')
    issue_entries=backlog['issues']
    issue_ids={f'EI{n:02}' for n in range(1,25)}
    require(len(issue_entries)==24 and {e['id'] for e in issue_entries}==issue_ids,'Expected24 distinct workstreams')
    require(backlog['epic']['id']=='EI00' and backlog['repository']=='jateeter/RealityEngine_Machines','Wrong umbrella/repository')
    require(backlog['status']=='ISSUES_PUBLISHED','Issue publication not completed')
    all_issues=[backlog['epic'],*issue_entries]
    require(len({e['issueNumber'] for e in all_issues})==25,'Duplicate issue numbers')
    for e in all_issues:
        require(isinstance(e['issueNumber'],int) and e['issueURL']==f"https://github.com/jateeter/RealityEngine_Machines/issues/{e['issueNumber']}",f'Invalid published URL: {e["id"]}')
        require(e['trackingId']=='energyInfrastructure/'+e['id'],f'Wrong tracking ID: {e["id"]}')
    published=backlog['publicationVerification']
    require(published['status']=='PASS' and published['issuesReadBack']==25 and published['behavioralCasesRun']==0,'Unverified issue publication')
    require(set(published['verifiedIssueNumbers'])=={e['issueNumber'] for e in all_issues},'Published readback set mismatch')
    seen_issues=set()
    covered_phases=set()
    by_issue={e['id']:e for e in issue_entries}
    for e in issue_entries:
        require(set(e['dependsOn'])<=seen_issues,f'Issue dependency cycle/order/unknown: {e["id"]}')
        require(e['deliveryStatus']=='PLANNED',f'Unverified implementation completion: {e["id"]}')
        require(bool(e['phaseIds']) and set(e['phaseIds'])<=ids['phases'],f'Unknown phase: {e["id"]}')
        covered_phases.update(e['phaseIds'])
        require(set(e['caseIds'])<=ids['cases'] and set(e['primaryCaseIds'])<=set(e['caseIds']),f'Unknown/unsupported case: {e["id"]}')
        require(set(e['standardIds'])<=ids['standards'] and set(e['riskIds'])<=ids['risks'],f'Issue references unknown standard/risk: {e["id"]}')
        require(set(e['implementationIds'])<=ids['implementations'],f'Issue references unknown implementation: {e["id"]}')
        require(all(e.get(k) for k in ['implementationChecklist','requiredArtifacts','acceptanceCriteria','responsibleRepositories','accountableRoles']),f'Incomplete issue specification: {e["id"]}')
        require('link resolved after publication' not in e['body'],f'Unresolved issue link: {e["id"]}')
        require(backlog['epic']['issueURL'] in e['body'],f'Missing parent backlink: {e["id"]}')
        for dep in e['dependsOn']:
            require(by_issue[dep]['issueURL'] in e['body'],f'Missing dependency link: {e["id"]}/{dep}')
        seen_issues.add(e['id'])
    require(covered_phases==ids['phases'],'Issue phase coverage incomplete')
    primary=backlog['primaryCaseOwnership']
    require(set(primary)==ids['cases'],'Primary case ownership incomplete')
    for c in datasets['cases']:
        owners=[e['id'] for e in issue_entries if c['id'] in e['primaryCaseIds']]
        require(owners==[primary[c['id']]] and c['primaryIssueId']==primary[c['id']],f'Case needs one consistent primary owner: {c["id"]}')
        require(c['hardwareMode']=='SIMULATED_REQUIRED_HARDWARE' and c['genericAssetsAllowed'] is True,f'Physical/site prerequisite: {c["id"]}')
        require(not any(x in c['level'] for x in ['CHIL','PHIL','SUPERVISED_COMMISSIONING']),f'Physical test level: {c["id"]}')
    coverage=read('acceptance/coverage-requirements.json')
    require(coverage['status']=='REQUIREMENTS_ONLY_NOT_FULFILLED','Fabricated template/simulator coverage')
    class_rows=coverage['standardClassCoverage']
    require(len(class_rows)==46 and {r['standardId'] for r in class_rows}==ids['standards'],'Missing standard asset-class coverage obligation')
    for row in class_rows:
        require(row['ownerIssueId']=='EI04' and row['taxonomyDisposition']=='NOT_REVIEWED' and row['fulfillmentReceipt'] is None,'Fabricated/misowned template coverage')
        require(row['rule']=='EVERY_DEFINED_CLASS_OF_ASSOCIATED_APPLICABLE_STANDARD_REQUIRES_TEMPLATE','Weakened asset-class template coverage')
    hardware_rows=coverage['hardwareCoverage']
    require(len(hardware_rows)==43 and {r['caseId'] for r in hardware_rows}==ids['cases'],'Missing simulated-hardware coverage obligation')
    for row in hardware_rows:
        require(row['ownerIssueId']=='EI18' and row['assetMode']=='GENERIC_OR_TEMPLATE_ALLOWED' and row['assetClassSource']=='ASSOCIATED_STANDARDS' and row['fulfillmentReceipt'] is None,'Fabricated/misowned hardware coverage')
        require(row['rule']=='EVERY_REQUIRED_HARDWARE_DEPENDENCY_REQUIRES_VERSIONED_SIMULATED_COUNTERPART','Weakened simulated-hardware coverage')
    for rel in ['templates/interoperability-profile.json','examples/der-supervisory-profile.json']:
        d=read(rel)
        require(set(d['standardIds'])<=ids['standards'] and set(d['caseIds'])<=ids['cases'],f'Profile reference mismatch: {rel}')
        require(d['measuredIntegrationReceipt'] is None and d['deadlinesRampsFreshnessAndLimits']=='GENERIC_REFERENCE_PROFILE_REQUIRED',f'Unreviewed profile settings/evidence: {rel}')
    for p in files:
        if p.suffix!='.md': continue
        for raw in re.findall(r'\]\(([^\n]+?)\)',p.read_text()):
            target=raw.strip().strip('<>')
            if urlsplit(target).scheme or target.startswith('#'):continue
            path=unquote(target.split('#',1)[0])
            if not path:continue
            require(not Path(path).is_absolute(),f'Nonportable absolute Markdown link: {p.relative_to(root)} -> {target}')
            dest=Path(path) if path.startswith('/') else p.parent/path
            require(dest.exists(),f'Broken local link: {p.relative_to(root)} -> {target}')
    return {'schemaVersion':'1.0.0','domain':'energyInfrastructure','verificationType':'OFFLINE_PACKAGE_INTEGRITY_ONLY',
            'result':'FAIL' if errors else 'PASS','checks':checks,'assetFiles':len(recorded),
            'inventoryCounts':{k:len(v) for k,v in datasets.items()},'cloneMachinesVerified':187,
            'collectedSources':1,'behavioralCasesRun':0,'runtimeTestsRun':0,'domainAdmission':'NOT_PERFORMED',
            'publishedIssuesVerified':25,'templateAndSimulatorCoverage':'REQUIREMENTS_ONLY_NOT_FULFILLED',
            'assetManifestSHA256':digest(root/'asset-manifest.json'),'errors':errors,
            'limitations':['No runtime/model/adapter or RAG execution','No simulated-hardware behavior/protocol or physical conformance evidence','No standards compliance or security assurance claim','No domain admission/deployment; source package not committed or published','Issue body readback is recorded publication evidence, not an ongoing live GitHub check','Asset-class templates and simulator catalog remain EI04/EI18 deliverables']}

def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--write-summary',action='store_true',help='Write explicitly excluded verification-summary.json')
    args=parser.parse_args()
    root=args.root.resolve()
    try:
        result=check(root)
    except (OSError,ValueError,KeyError,TypeError) as error:
        result={'result':'FAIL','verificationType':'OFFLINE_PACKAGE_INTEGRITY_ONLY','errors':[str(error)]}
    if args.write_summary:
        (root/'verification-summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    return 0 if result['result']=='PASS' else 1

if __name__=='__main__':
    sys.exit(main())
