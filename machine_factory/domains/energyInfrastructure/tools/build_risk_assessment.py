#!/usr/bin/env python3
"""Reproduce conservative synthetic risk inputs; never operational risk acceptance."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def encode(v):return (json.dumps(v,indent=2)+'\n').encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def build(root):
    policy={'schemaVersion':'1.0.0','kind':'DRAFT_GENERIC_RISK_POLICY','revision':'generic.risk.v1','status':'NOT_SECURITY_APPROVED','maxFeedAgeMs':2000,'maxFindingAgeMs':2000,'clearanceSupported':False,'treatment':'HOLD_DISCRETIONARY_PROPOSALS_ONLY','controlAction':'DENY'}
    projection='assets/function-bindings/ref01_connected.json';threat='assets/synthetic-threat-fixture.json';objects=json.loads((root/threat).read_text())['bundle']['objects'];bytype={o['type']:o for o in objects}
    context={'topologyRevision':'fixture.topology.1','credentialRevision':'fixture.credential.1','firmwareRevision':'fixture.firmware.1','policyRevision':policy['revision'],'modelRevision':'fixture.model.1','ragRevision':'fixture.rag.1','electricalMode':'GRID_CONNECTED'}
    assessment={'schemaVersion':'1.0.0','kind':'SYNTHETIC_OT_RISK_ASSESSMENT','sourceProjection':projection,'sourceProjectionSHA256':sha((root/projection).read_bytes()),'sourceThreatFixture':threat,'sourceThreatFixtureSHA256':sha((root/threat).read_bytes()),'policyPath':'assets/generic-risk-policy.json','policySHA256':sha(encode(policy)),'evaluationAt':'2026-11-25T00:00:01.000Z','context':context,'previousContext':copy.deepcopy(context),'priorRiskDisposition':'UNKNOWN','feed':{'sourceId':'SYNTHETIC_FEED','receivedAt':'2026-11-25T00:00:00.200Z','quality':'GOOD','complete':False},'assetBindings':[{'infrastructureRef':bytype['infrastructure']['id'],'assetId':'fixture.microgrid-controller'}],'findings':[{'id':'synthetic.finding.1','infrastructureRef':bytype['infrastructure']['id'],'vulnerabilityRef':bytype['vulnerability']['id'],'relationshipRef':bytype['relationship']['id'],'assetId':'fixture.microgrid-controller','observedAt':'2026-11-25T00:00:00.000Z','receivedAt':'2026-11-25T00:00:00.200Z','quality':'GOOD','applicability':'UNKNOWN','evidenceClass':'SYNTHETIC_ASSERTION_ONLY'}],'engineeringReview':'PENDING','controlAction':'DENY','behavioralCasesRun':0}
    path='assets/storage-proposal-screen.json';screen=json.loads((root/path).read_text());screen['evaluationAt']=assessment['evaluationAt']
    screen['state']['observedAt']='2026-11-25T00:00:00.000Z';screen['state']['receivedAt']='2026-11-25T00:00:00.100Z';screen['proposal']['issuedAt']='2026-11-25T00:00:00.500Z';screen['proposal']['expiresAt']='2026-11-25T00:00:02.000Z'
    bridge={'schemaVersion':'1.0.0','kind':'SYNTHETIC_RISK_PROPOSAL_BRIDGE','sourceAssessment':'assets/risk-assessment-fixture.json','sourceAssessmentSHA256':sha(encode(assessment)),'sourceProposalTemplate':path,'sourceProposalTemplateSHA256':sha((root/path).read_bytes()),'proposalFrame':screen,'controlAction':'DENY','behavioralCasesRun':0}
    return {'generic-risk-policy.json':policy,'risk-assessment-fixture.json':assessment,'risk-proposal-bridge.json':bridge}
def check(root):
    try:return ['Risk policy/assessment/bridge source drift: '+n for n,d in build(root).items() if not (root/'assets'/n).is_file() or json.loads((root/'assets'/n).read_text())!=d]
    except (OSError,ValueError,KeyError,TypeError) as e:return [str(e)]
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');args=p.parse_args()
    if args.write:
        for n,d in build(ROOT).items():(ROOT/'assets'/n).write_bytes(encode(d))
    errors=check(ROOT);print(json.dumps({'result':'FAIL' if errors else 'PASS','syntheticRiskAssessments':1,'errors':errors}));raise SystemExit(bool(errors))
