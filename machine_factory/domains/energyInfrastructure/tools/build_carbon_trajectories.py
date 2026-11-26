#!/usr/bin/env python3
"""Reproduce a synthetic revision archive and separate forecast/target examples."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def build(root):
    path='assets/import-carbon-ledger.json';raw=(root/path).read_bytes();base=json.loads(raw);corrected=copy.deepcopy(base)
    corrected['evaluationAt']='2026-01-01T00:40:01.000Z'
    for row in corrected['rows']:row['meterInterval']['evaluationAt']=corrected['evaluationAt']
    corrected['rows'][0]['factor'].update(revision='fixture-v2',intensity='200',issuedAt='2026-01-01T00:40:00.000Z')
    first=digest(base);second=digest(corrected)
    forecast_basis=copy.deepcopy(base['basis']);forecast_basis['dataRole']='SYNTHETIC_FORECAST'
    target_basis=copy.deepcopy(base['basis']);target_basis['dataRole']='SYNTHETIC_TARGET'
    return {'schemaVersion':'1.0.0','kind':'SYNTHETIC_CARBON_TRAJECTORY_ARCHIVE','sourceLedger':path,'sourceLedgerSHA256':hashlib.sha256(raw).hexdigest(),'evaluationAt':'2026-01-01T00:45:01.000Z','observedRevisions':[
        {'id':'report.v1','parentSnapshotDigest':None,'snapshotDigest':first,'ledger':base},
        {'id':'report.v2','parentSnapshotDigest':first,'snapshotDigest':second,'ledger':corrected}
    ],'forecasts':[{'id':'forecast.example.1','sourceType':'SYNTHETIC_FORECAST','basis':forecast_basis,'issuedAt':'2026-01-01T00:20:00.000Z','intervalStart':'2026-01-01T00:30:00.000Z','intervalEnd':'2026-01-01T00:45:00.000Z','quality':'GOOD','intensity':'310'}],
    'draftTargets':[{'id':'target.example.1','sourceType':'SYNTHETIC_TARGET_EXAMPLE','basis':target_basis,'baselineSnapshotDigest':first,'issuedAt':'2026-01-01T00:30:01.000Z','intervalStart':'2026-01-02T00:00:00.000Z','intervalEnd':'2026-01-03T00:00:00.000Z','intensity':'300','status':'DRAFT_EXAMPLE_NOT_ADOPTED','owner':None,'approvalReceipt':None}],
    'decisionReferences':[{'id':'reference.example.1','at':'2026-01-01T00:31:00.000Z','observedSnapshotDigest':first,'actionExecuted':False,'controlAction':'DENY'}],
    'engineeringReview':'PENDING','controlAction':'DENY','behavioralCasesRun':0}

def check(root):
    try:
        p=root/'assets/carbon-trajectories.json'
        return [] if p.is_file() and json.loads(p.read_text())==build(root) else ['Carbon trajectory archive source/input drift']
    except (OSError,ValueError,KeyError,TypeError) as e:return [str(e)]

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--write',action='store_true');args=parser.parse_args()
    if args.write:(ROOT/'assets/carbon-trajectories.json').write_text(json.dumps(build(ROOT),indent=2)+'\n')
    errors=check(ROOT);print(json.dumps({'result':'FAIL' if errors else 'PASS','syntheticTrajectoryArchives':1,'errors':errors}));raise SystemExit(bool(errors))
