#!/usr/bin/env python3
"""Reproduce a draft generic algebraic proposal screen, not operational limits."""
import argparse
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def encode(v):return (json.dumps(v,indent=2)+'\n').encode()
def build(root):
    profile={'schemaVersion':'1.0.0','kind':'DRAFT_GENERIC_STORAGE_SCREEN_PROFILE','revision':'generic.screen.v1','status':'NOT_ENGINEERING_APPROVED','powerUnit':'kW','energyUnit':'kWh','intervalUnit':'h','capacityKWh':'10','reserveKWh':'3','maxChargeKw':'4','maxDischargeKw':'4','maxStepPowerChangeKw':'3','maxImportKw':'6','maxExportKw':'2','minCriticalDemandKw':'2','chargeEfficiency':'0.9','dischargeEfficiency':'0.8','maxIntervalHours':'0.25','maxStateAgeMs':2000,'controlAction':'DENY'}
    path='assets/function-bindings/ref01_connected.json';p=json.loads((root/path).read_text());asset=next(g['primaryViewAssetId'] for g in p['accounting']['resourceGroups'] if g['id']=='STORAGE_AC')
    fixture={'schemaVersion':'1.0.0','kind':'SYNTHETIC_STORAGE_PROPOSAL_SCREEN','referenceScenarioId':'REF01_CONNECTED','sourceProjection':path,'sourceProjectionSHA256':hashlib.sha256((root/path).read_bytes()).hexdigest(),'profilePath':'assets/generic-storage-screen-profile.json','profileSHA256':hashlib.sha256(encode(profile)).hexdigest(),'storageAssetId':asset,'evaluationAt':'2026-01-01T00:30:01.000Z',
    'state':{'observedAt':'2026-01-01T00:30:00.000Z','receivedAt':'2026-01-01T00:30:00.100Z','quality':'GOOD','stateRevision':'fixture.state.1','topologyRevision':'fixture.topology.1','mode':'GRID_CONNECTED','pcc':'CLOSED','gridAvailable':True,'protectiveInterlocks':'HEALTHY','riskDisposition':'CLEAR','storedEnergyKWh':'5','criticalDemandKw':'2','otherDemandKw':'1','pvGenerationKw':'1','previousStorageKw':'0'},
    'proposal':{'id':'synthetic.proposal.1','origin':'MODEL_PLANNER','issuedAt':'2026-01-01T00:30:00.500Z','expiresAt':'2026-01-01T00:30:02.000Z','stateRevision':'fixture.state.1','topologyRevision':'fixture.topology.1','profileSHA256':hashlib.sha256(encode(profile)).hexdigest(),'storageAssetId':asset,'powerUnit':'kW','storagePowerKw':'2','intervalHours':'0.25','criticalServedKw':'2','claimedCarbonReductionPercent':'20','operatingApproval':None},'engineeringReview':'PENDING','controlAction':'DENY','behavioralCasesRun':0}
    return {'generic-storage-screen-profile.json':profile,'storage-proposal-screen.json':fixture}
def check(root):
    try:
        return ['Proposal screen profile/source drift: '+n for n,d in build(root).items() if not (root/'assets'/n).is_file() or json.loads((root/'assets'/n).read_text())!=d]
    except (OSError,ValueError,KeyError,TypeError,StopIteration) as e:return [str(e)]
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--write',action='store_true');args=parser.parse_args()
    if args.write:
        for n,d in build(ROOT).items():(ROOT/'assets'/n).write_bytes(encode(d))
    errors=check(ROOT);print(json.dumps({'result':'FAIL' if errors else 'PASS','syntheticProposalScreens':1,'errors':errors}));raise SystemExit(bool(errors))
