#!/usr/bin/env python3
"""Build and verify synthetic document examples and scoped development dispositions.

No named sample staff sign-off, independent approval, native acceptance or mutation
of historical runtime stores. `--check` detects artifact or input drift.
"""
import argparse, hashlib, importlib.util, json, subprocess, sys, tempfile
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[1]
REPO = ASSETS.parents[2]
SAMPLES = ASSETS / 'acceptance/synthetic/review-samples'
EVIDENCE = REPO / 'docs/admission/ifrs-accounting/1.4.0/completion-batch'
PACKAGES = ['accounting-package.json','foundation-cases.json','policy-cases.json','lease-compliance-cases.json','source-disclosure-cases.json','reporting-cases.json','remaining-cases.json']
GENERATED = ['DOCUMENT_INDEX.md','documents','manifest.json','document-review.json','case-annex.json','contribution-dispositions.json','finding-dispositions.json','requirement-dispositions.json','README.md']

def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(x): return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def digest(x): return hashlib.sha256(canonical(x).encode()).hexdigest()
def write(p,x): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def reviewed_findings(attestation):
    # GitHub checks out a shallow merge commit. Exact reviewed bytes are verified
    # from unchanged current files or retained snapshots, not unavailable history.
    verified={}
    for rel,expected in attestation['reviewedFileSHA256'].items():
        current=REPO/rel if rel.startswith('machines/') else ASSETS/rel
        snapshot=SAMPLES/'reviewed-baseline'/rel
        source=current if current.is_file() and sha(current)==expected else snapshot
        assert source.is_file() and sha(source)==expected, 'Attested source baseline differs: '+rel
        verified[rel]=source
    return read(verified['accounting-findings.json'])['findings']

def build(out):
    catalog=read(ASSETS/'document-asset-catalog.json')['assetTypes'];byid={a['assetTypeId']:a for a in catalog}
    authored=read(SAMPLES/'sample-document-content.json')['documents'];assert set(authored)==set(byid)
    attestation=read(SAMPLES/'operator-review-attestation.json');findings=reviewed_findings(attestation)
    lifecycle=module('ifrs_sample_lifecycle',ASSETS/'tools/document_workflow.py');controls=module('ifrs_sample_controls',ASSETS/'tools/accounting_controls.py')
    cases=[case for name in PACKAGES for case in read(ASSETS/'acceptance/synthetic'/name)['cases']];assert len(cases)==320 and len({c['caseId'] for c in cases})==320
    mappings={c['control']:c['targetAssetTypeId'] for c in read(ASSETS/'remaining-control-map.json')['controls']}
    mappings.update({'trial-balance':'FINANCIAL-POSITION','source-reference-screen':'SEMANTIC-INTEGRITY-LOG','section-1-eligibility':'ELIGIBILITY-MEMO','version-3-period-applicability':'EDITION-TRANSITION-PACK','section-2-recognition-screen':'JUDGMENT-REGISTER','section-2-substance-screen':'JUDGMENT-REGISTER','section-1-fiduciary-screen':'ELIGIBILITY-MEMO','section-2-undue-cost-screen':'COST-EFFORT-MEMO','section-12-bid-ask-screen':'VALUATION-PACK','section-18-useful-life-screen':'INTANGIBLE-SCHEDULE','section-19-goodwill-life-screen':'GOODWILL-SCHEDULE','section-28-actuarial-policy-screen':'BENEFITS-SCHEDULE','section-20-classification-screen':'LEASE-REGISTER','section-20-finance-initial-measurement':'LEASE-SCHEDULE','section-3-compliance-evidence-screen':'COMPLIANCE-REVIEW','section-8-policy-materiality-screen':'POLICY-REGISTER','section-8-supplemental-capital-screen':'NOTES-PACK','section-29-pillar-two-screen':'TAX-SCHEDULE','section-15-commitments-screen':'JOINT-ARRANGEMENT-MEMO','section-23-allocation-basis-screen':'REVENUE-SCHEDULE','section-6-dividend-note':'DIVIDEND-REGISTER','section-7-financing-reconciliation':'FINANCING-RECONCILIATION','section-7-supplier-finance-note':'SUPPLIER-FINANCE-NOTE','section-8-note-structure-screen':'NOTES-PACK','section-23-contract-cost':'CONTRACT-REGISTER'})
    previous={r['result']['caseId']:r['result'] for r in read(EVIDENCE/'synthetic-accounting-cases.json')}
    annex=[]
    for c in cases:
        assert c['control'] in mappings,c['control']
        if c['control']=='section-3-compliance-evidence-screen':
            result=previous[c['caseId']]['determination'];method='RETAINED_CANONICAL_LIVE_BLOCKING_PROOF_NOT_CALLER_FLAGS'
        else:result=controls.determine(c['control'],c['facts']);method='DETERMINISTIC_REPLAY_AGAINST_EXPLICIT_EXPECTATION'
        for k,v in c['expected'].items():assert result[k]==v,(c['caseId'],k,result.get(k),v)
        annex.append(dict(caseId=c['caseId'],entityId=c['entityId'],period=c.get('period',c['facts'].get('periodStart','2027')[:4]),control=c['control'],targetAssetTypeId=mappings[c['control']],facts=c['facts'],expected=c['expected'],observed=result,check='PASS',method=method,scenarioRule='Independent case variant; never aggregate conflicting facts or alternative policies into core statements',sourceReceiptReference='../../../../../docs/admission/ifrs-accounting/1.4.0/completion-batch/synthetic-accounting-cases.json#'+c['caseId']))
    write(out/'case-annex.json',annex)
    requirements=read(ASSETS/'source-requirements.json')['controls']
    dispositions=[dict(controlId=r['id'],status='PENDING_INDEPENDENT_APPLICABILITY_AND_ACCOUNTING_REVIEW',documentTypes=[a['assetTypeId'] for a in catalog if r['id'] in a['controlIds']],basis='Concrete sample fields and case annexes do not prove every obligation satisfied; no blanket not-applicable or compliance claim') for r in requirements]
    assert len(dispositions)==595 and all(r['documentTypes'] for r in dispositions)
    write(out/'requirement-dispositions.json',dispositions)
    package=read(ASSETS/'acceptance/synthetic/accounting-package.json');tb=package['trialBalance'];debits=sum(Decimal(x['amount']) for x in tb if x['side']=='debit');credits=sum(Decimal(x['amount']) for x in tb if x['side']=='credit');assert debits==credits==Decimal('100000.00')
    context=dict(entityId='SYNTHETIC-ASTER-SERVICES',period='2027',evidenceClass='synthetic',factsFingerprint=digest({'trialBalance':tb,'examples':authored,'annex':annex}),sourceFingerprint=digest(read(EVIDENCE/'all-section-source-bindings.json')),policyFingerprint=digest(read(ASSETS/'semantic-amendments.json')),indexSnapshot=read(EVIDENCE/'all-section-source-bindings.json')[0].get('indexSnapshot','HISTORICAL_RUN_026_BINDINGS'),unresolvedRequirements=['Independent review and native acceptance remain pending'])
    previous_contributions=read(EVIDENCE/'remaining-control-contributions.json')
    rows=[];docs={};pending=set(byid)
    with tempfile.TemporaryDirectory() as temp:
        store=lifecycle.Store(temp,{'assetTypes':catalog})
        while pending:
            ready=sorted(a for a in pending if set(byid[a]['dependencies'])<=set(docs));assert ready,'Dependency cycle'
            for aid in ready:
                a=byid[aid];content=dict(authored[aid]);assert set(a['requiredFields'])<=set(content)
                if aid=='SOURCE-REGISTER':
                    content['sourceFiles']=['source-reference-map.json','source-requirements.json','completion-batch/all-section-source-bindings.json']
                    content['sourceHashes']={n:sha(ASSETS/n) for n in ['source-reference-map.json','source-requirements.json']}
                linked=[x['caseId'] for x in annex if x['targetAssetTypeId']==aid]
                content.update(contributionRefs=[c['contributionId'] for c in previous_contributions if c['assetTypeId']==aid],sampleScope='Core statements follow the original four-row trial balance. Topic-specific amounts and case variants are isolated annexes, not additional core transactions.',scenarioCaseRefs=linked,sampleEvidenceClass='synthetic',independentReviewStatus='PENDING_REAL_REVIEWER',sampleHRSignoff=False)
                refs=['synthetic:sample-workpaper']+[r['recordId'] for r in package['supportingRecords'] if r['entityId']==context['entityId'] and r['period']==context['period']]
                head=store.draft(context,aid,content,refs,0)
                record=store.revision(context,aid,head['revision'])
                assert record['contentHash']==lifecycle.hashed({k:record[k] for k in ['assetTypeId','entityId','period','evidenceClass','content','evidenceRefs','upstreamRefs','inputFingerprint']})
                path=out/'documents'/aid/'v1.json';write(path,record);docs[aid]=record
                review=dict(assetTypeId=aid,revision=1,contentHash=record['contentHash'],artifactSHA256=sha(path),reviewer='Codex automated technical inspection; not independent accounting sign-off',checks=dict(contentHash='PASS',requiredFieldPresence='PASS',scopeEvidence='PASS_SYNTHETIC_ONLY',upstreamRevisionBinding='PASS_DRAFT_REFERENCES',independentAccountingApproval='PENDING',currentRAGFreshness='NOT_REVALIDATED_HISTORICAL_BINDINGS_ONLY'),accountingReview='LIMITED_TECHNICAL_CHECKS_ONLY',status='REVIEWED_TECHNICALLY_DRAFT_NOT_APPROVED',issues=['Exact-revision independent accounting review required','Upstream examples are drafts; approval is not inferred'])
                if aid in {'HEDGE-PACK','TAX-SCHEDULE','EXTRACTIVE-MEMO','LEASE-SCHEDULE','FIRST-ADOPTION-PACK','EDITION-TRANSITION-PACK','RELATED-PARTY-NOTE','FAIR-VALUE-NOTE'}:review['issues'].append('Explicit incomplete specialist/population analysis in sample; do not treat as completed accounting acceptance')
                rows.append(review);pending.remove(aid)
    checks={'trialBalance':str(debits)+' = '+str(credits),'financialPosition':'98200.00 assets = 0.00 liabilities + 98200.00 equity','profitToEquity':'100000.00 capital - 1800.00 loss = 98200.00 equity','cashFlow':'0.00 opening + 100000.00 financing - 7800.00 operating = 92200.00 closing','coreScenarioExclusion':'Topic annex amounts excluded from core totals','caseExpectations':len(annex)}
    fpos=docs['FINANCIAL-POSITION']['content'];assert Decimal(fpos['assets']['total']['amount'])==Decimal(fpos['liabilities']['total']['amount'])+Decimal(fpos['equity']['total']['amount'])
    assert sum(Decimal(x) for x in ['0.00','100000.00','-7800.00'])==Decimal(docs['CASH-FLOW-STATEMENT']['content']['cashReconciliation']['closing']['amount'])
    lease=docs['LEASE-SCHEDULE']['content']['interestSchedule'];last=Decimal('9000.00')
    for line in lease:
        assert Decimal(line['opening'])==last
        assert Decimal(line['interest'])==(last*Decimal('0.05')).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)
        assert Decimal(line['closing'])==last+Decimal(line['interest'])-Decimal(line['payment'])
        last=Decimal(line['closing'])
    assert last==0
    checks['leaseSchedule']='Five annual 5% rows reconcile to zero; ROUND_HALF_UP cents and explicit final rounding payment'
    write(out/'document-review.json',dict(reviewScope='Technical exact-revision/hash/field/evidence/reconciliation checks performed on all 68 examples; no independent accounting approval',documents=rows,coreReconciliations=checks,approvedDocuments=0,independentReviewerIdentity=None))
    previous_contributions=read(EVIDENCE/'remaining-control-contributions.json');states={r['contributionId']:r for r in read(SAMPLES/'canonical-contribution-state-snapshot.json')['contributions']};bycase={r['caseId']:r for r in annex};contributions=[]
    for c in previous_contributions:
        cid=c['contributionId'];case=bycase[c['content']['caseId']];aid=c['assetTypeId'];assert aid==case['targetAssetTypeId'];r=docs[aid];assert cid in r['content']['contributionRefs']
        contributions.append(dict(contributionId=cid,caseId=case['caseId'],assetTypeId=aid,sourceMachine=c['sourceMachine'],targetMachine=c['targetMachine'],entityId=c['entityId'],period=c['period'],developmentDisposition='CLOSED_SYNTHETIC_CASE_REPLAY_AND_DOCUMENT_ANNEX',dispositionReason='Expected unresolved/rejection preserved as a guard case; no financial recognition' if case['observed']['status']=='UNRESOLVED' else 'Conditional advisory result incorporated in the matching isolated document case annex; not a posted/approved transaction',observedCaseStatus=case['observed']['status'],caseReplay='PASS',documentRef=dict(path='documents/'+aid+'/v1.json',revision=1,contentHash=r['contentHash']),caseAnnexSHA256=sha(out/'case-annex.json'),historicalCanonicalStatus=states[cid]['status'],canonicalSatisfaction='NOT_ASSERTED_EXACT_APPROVED_ARTIFACT_REQUIRED',independentReview='PENDING_ISSUE_231',followupIssue=attestation['followupIssue']))
    assert len(contributions)==147 and len({c['contributionId'] for c in contributions})==147
    write(out/'contribution-dispositions.json',dict(scope='Development case inbox only; historical runtime store remains unchanged. All cases dispositioned, none falsely marked SATISFIED.',closedDevelopmentCases=147,canonicalStatusCounts=dict(Counter(r['historicalCanonicalStatus'] for r in contributions)),canonicalSatisfactionCount=0,rows=contributions))
    coverage=read(ASSETS/'finding-coverage.json');finding_rows=[]
    for f in findings:
        row=next(r for r in coverage['rows'] if r['findingId']==f['id']);linked=[bycase[x['caseId']] for x in row['syntheticCases']];assert linked
        targets=sorted({x['targetAssetTypeId'] for x in linked});finding_rows.append(dict(findingId=f['id'],context={k:v for k,v in f.items() if k not in ['status','closure','developmentResolution']},controls=row['controls'],caseIds=[x['caseId'] for x in linked],documentRefs=[dict(assetTypeId=a,path='documents/'+a+'/v1.json',revision=1,contentHash=docs[a]['contentHash']) for a in targets],developmentStatus='CLOSED_SYNTHETIC_IMPLEMENTATION_SCOPE',sourceInterpretationReview=dict(type=attestation['recordType'],recordId=attestation['recordId'],fileSHA256=sha(SAMPLES/'operator-review-attestation.json')),independentReview='PENDING_ISSUE_231',admissionClosure=False,nativeAcceptance='DEFERRED_BY_OPERATOR',followupIssue=attestation['followupIssue']))
    assert len(finding_rows)==53
    write(out/'finding-dispositions.json',dict(scope='Development implementation closure only. Original admission status and independent-review criteria remain intact.',closedDevelopmentFindings=53,closedAdmissionFindings=0,rows=finding_rows))
    index=['# Sample accounting document index','','All documents are revision 1 drafts. Full content hashes are in the manifest and technical review. Topic scenarios are not additions to the core financial statements.','','| Document | Content hash | Cases | Contributions |','|---|---|---:|---:|']
    for aid,r in sorted(docs.items()):index.append('| ['+aid+'](documents/'+aid+'/v1.json) | '+r['contentHash']+' | '+str(len(r['content']['scenarioCaseRefs']))+' | '+str(len(r['content']['contributionRefs']))+' |')
    (out/'DOCUMENT_INDEX.md').write_text('\n'.join(index)+'\n')
    hr=read(SAMPLES/'hr-reviewers.json');staff={r['staffId']:r for r in hr['staff']}
    def reviewer(aid):
        section=byid[aid]['sectionId']
        if section in {'11','12','07'}:return 'SAMPLE-HR-002'
        if section in {'09','14','15','16','17','18','19','20','27'}:return 'SAMPLE-HR-003'
        if section in {'26','28','29'}:return 'SAMPLE-HR-004'
        return 'SAMPLE-HR-001'
    assignments=[dict(assetTypeId=a['assetTypeId'],accountableOwnerRole=a['ownerName'],requiredReviewerRole=a['reviewerName'],proposedSampleReviewerId=reviewer(a['assetTypeId']),proposedSampleReviewerName=staff[reviewer(a['assetTypeId'])]['name'],actualAppointment=False,independenceAndQualifications='REQUIRES_REAL_PERSON_VERIFICATION') for a in catalog]
    write(out/'reviewer-assignments.json',dict(synthetic=True,scope='Illustrative proposed staffing only; canonical reviewer principals and permissions unchanged',documents=assignments))
    (out/'CORE_FINANCIAL_EXAMPLE.md').write_text('''# Fictional Aster Services — core 2027 example

Synthetic, limited workpapers; not approved financial statements. All figures USD. The separate topic scenarios are excluded.

| Financial position at 31 December 2027 | USD |
|---|---:|
| Cash | 92,200.00 |
| Contract fulfilment resources | 6,000.00 |
| Total assets | 98,200.00 |
| Liabilities | 0.00 |
| Owner capital | 100,000.00 |
| Accumulated loss | (1,800.00) |
| Total equity | 98,200.00 |

| Performance for 2027 | USD |
|---|---:|
| Revenue | 0.00 |
| Obtaining commission expense | (1,800.00) |
| Tax charge under stipulated fictional tax assumptions | 0.00 |
| Loss and total comprehensive loss | (1,800.00) |

Equity: zero opening + 100,000.00 capital - 1,800.00 loss = 98,200.00 closing.

Cash: zero opening + 100,000.00 owner financing - 1,800.00 commission - 6,000.00 fulfilment-resource payment = 92,200.00 closing. Contract-resource payments are treated as operating in this sample.

The 2026 comparative is stipulated dormant with zero balances/activity. Resources relate to supported future services, not recognised 2027 revenue. The core has no borrowings, dividends or OCI. Fictional jurisdiction-X assumptions give a tax loss of 1,800.00; potential loss DTA 360.00 is unrecognised because probable future taxable profits are not supported. These are invented fixture facts, not actual tax law.

See exact JSON revisions for financial position, performance, equity, cash flows, notes and tax. Independent accounting review, full applicability assessment and authorisation remain pending.
''')
    files=sorted(x for x in out.rglob('*') if x.is_file() and x.name!='manifest.json');inputs=[SAMPLES/'sample-document-content.json',SAMPLES/'hr-reviewers.json',SAMPLES/'operator-review-attestation.json',SAMPLES/'canonical-contribution-state-snapshot.json',ASSETS/'document-asset-catalog.json',ASSETS/'semantic-amendments.json',ASSETS/'tools/accounting_controls.py',ASSETS/'tools/remaining_controls.py',ASSETS/'tools/reporting_controls.py',Path(__file__)]+[ASSETS/'acceptance/synthetic'/n for n in PACKAGES]
    write(out/'manifest.json',dict(schemaVersion='1.0.0',evidenceClass='synthetic',entityId=context['entityId'],period='2027',policy='DRAFT_EXAMPLES_AND_TECHNICAL_REVIEW_ONLY_NO_SYNTHETIC_PERSON_APPROVAL',documents=68,developmentContributionsDispositioned=147,developmentFindingsClosed=53,admissionFindingsClosed=0,sourceInputs={str(p.relative_to(REPO)):sha(p) for p in inputs},artifacts={str(p.relative_to(out)):sha(p) for p in files},context=context))
    text=['# IFRS sample accounting documents and review dispositions','','This packet contains all 68 catalogued document examples, the sample HR roster, the operator source-review attestation, technical exact-revision/hash checks, 147 case dispositions and 53 scoped development closures. All entity records and staff profiles are fictional.','','The original limited core financial statements reconcile; topic cases are isolated scenarios and must not be consolidated into core figures. Some specialist workpapers explicitly identify missing analysis. Samples establish document shape and reproducible technical checks, not complete accounting acceptance.','','- `manifest.json`: artifact and input hashes.','- `documents/<ASSET>/v1.json`: exact reference-lifecycle revision and content hash.','- `document-review.json`: all 68 technical reviews and outstanding substantive limitations.','- `case-annex.json`: all 320 expected-outcome checks; negative/unresolved cases remain guards.','- `contribution-dispositions.json`: all 147 development cases handled; historical runtime states unchanged (143 OPEN, 4 SUPERSEDED), zero canonical satisfaction claims.','- `finding-dispositions.json`: all 53 development contexts and scoped closures; zero admission closures.','- `requirement-dispositions.json`: all 595 controls still need independent applicability/accounting assessment.','- `HR_REVIEWERS.md` / `hr-reviewers.json`: proposed fictional staffing examples only.','- `operator-review-attestation.json`: records the operator statement against the earlier Git revision and file hashes.','','Independent follow-up: https://github.com/jateeter/RealityEngine_Machines/issues/231. Original finding closure gates are preserved. Native acceptance and final approval are deferred as requested.','','Run `python3 machine_factory/domains/ifrs-accounting/tools/build_review_samples.py --check` to detect altered artifacts or input drift.']
    (out/'README.md').write_text('\n'.join(text)+'\n')

def verify_packet(packet):
    manifest=read(packet/'manifest.json')
    for rel,expected in manifest['artifacts'].items():
        path=(packet/rel).resolve()
        assert path.is_relative_to(packet.resolve()) and path.is_file(), 'Missing/out-of-packet artifact '+rel
        assert sha(path)==expected, 'Artifact hash mismatch '+rel
    docs={}
    for path in (packet/'documents').glob('*/v1.json'):
        record=read(path)
        fields=['assetTypeId','entityId','period','evidenceClass','content','evidenceRefs','upstreamRefs','inputFingerprint']
        assert digest({k:record[k] for k in fields})==record['contentHash'], 'Canonical content hash mismatch '+record['assetTypeId']
        assert record['revision']==1 and record['evidenceClass']=='synthetic'
        assert record['content']['independentReviewStatus']=='PENDING_REAL_REVIEWER' and record['content']['sampleHRSignoff'] is False
        docs[record['assetTypeId']]=record
    assert len(docs)==68
    for doc in docs.values():
        for ref in doc['upstreamRefs']:
            target=docs[ref['assetTypeId']]
            assert ref['revision']==target['revision'] and ref['contentHash']==target['contentHash'], 'Upstream revision/hash mismatch'
            assert ref['status']=='DRAFT'
    for row in read(packet/'contribution-dispositions.json')['rows']:
        doc=docs[row['assetTypeId']];ref=row['documentRef']
        assert ref['revision']==doc['revision'] and ref['contentHash']==doc['contentHash'], 'Contribution exact-revision mismatch'
        assert row['contributionId'] in doc['content']['contributionRefs']
        assert row['canonicalSatisfaction']=='NOT_ASSERTED_EXACT_APPROVED_ARTIFACT_REQUIRED'
    assert read(packet/'finding-dispositions.json')['closedAdmissionFindings']==0
    assert read(packet/'document-review.json')['approvedDocuments']==0

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    with tempfile.TemporaryDirectory() as t:
        generated=Path(t);build(generated);verify_packet(generated)
        changed=[]
        expected={str(p.relative_to(generated)):p for p in generated.rglob('*') if p.is_file()}
        for rel,p in expected.items():
            target=SAMPLES/rel
            if not target.exists() or p.read_bytes()!=target.read_bytes():changed.append(rel)
        extra=[str(p.relative_to(SAMPLES)) for p in (SAMPLES/'documents').rglob('*') if p.is_file() and str(p.relative_to(SAMPLES)) not in expected] if (SAMPLES/'documents').exists() else []
        if args.check:
            if changed or extra:raise ValueError('Sample evidence drift: '+', '.join(changed+extra))
        else:
            import shutil
            for rel,p in expected.items():(SAMPLES/rel).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,SAMPLES/rel)
            for rel in extra:(SAMPLES/rel).unlink()
        print('PASS: 68 exact-revision samples, 320 case checks, 147 development dispositions, 53 scoped development closures; zero independent/admission approvals')
if __name__=='__main__':
    try:main()
    except (AssertionError,ValueError,KeyError) as exc:raise SystemExit('FAIL: '+str(exc))
