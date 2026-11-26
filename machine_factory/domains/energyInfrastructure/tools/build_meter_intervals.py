#!/usr/bin/env python3
"""Reproduce the selected SunSpec meter counter profile and synthetic interval."""
import argparse
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def build(root):
    path='intake/public-models/sunspec/model_203.json';raw=(root/path).read_bytes();source=json.loads(raw);points={};offset=0
    for i,p in enumerate(source['group']['points']):
        points[p['name']]={'offset':offset,'pointer':f'/group/points/{i}','definition':p};offset+=p['size']
    names=['TotWhImp','TotWhExp','TotWh_SF']
    profile={'schemaVersion':'1.0.0','kind':'OFFLINE_METER_ENERGY_SUBSET','modelId':203,'sourcePath':path,'sourceSHA256':hashlib.sha256(raw).hexdigest(),'modelCommit':'90b4a331dcca1d6eac69c1bead952fddcc5852e0','registerCount':offset,'points':{n:points[n] for n in names},'byteOrder':'BIG_ENDIAN','notAccumulated':0,'missingScaleFactor':32768,'scaleRange':[-10,10],'normativeFsgimPropertyEquivalence':False,'peerVerified':False,'controlAction':'DENY'}
    def reading(imp,exp,time):
        b=bytearray(offset*2);b[:2]=(203).to_bytes(2,'big');b[2:4]=(offset-2).to_bytes(2,'big')
        for n,v,size in [('TotWhImp',imp,4),('TotWhExp',exp,4),('TotWh_SF',65535,2)]:
            pos=points[n]['offset']*2;b[pos:pos+size]=v.to_bytes(size,'big')
        return {'observedAt':time+'.000Z','receivedAt':time+'.100Z','counterEpochId':'synthetic.epoch.1','sourceIdentity':{'sourceSystemId':'synthetic.meter-source','namespaceUri':'urn:energy:synthetic:sunspec','identifier':'meter.203'},'quality':'GOOD','blockHex':b.hex()}
    path='assets/function-bindings/generic.json';projection=json.loads((root/path).read_text())
    fixture={'schemaVersion':'1.0.0','kind':'SYNTHETIC_METER_ENERGY_INTERVAL','sourceProjection':path,'sourceProjectionSHA256':hashlib.sha256((root/path).read_bytes()).hexdigest(),'meterAssetId':projection['accounting']['facilityNetMeterAssetId'],'boundaryId':'FACILITY_PCC','modelId':203,'start':reading(100000,10000,'2026-01-01T00:00:00'),'end':reading(112500,12500,'2026-01-01T00:15:00'),'evaluationAt':'2026-01-01T00:15:01.000Z','maxAgeMs':2000,'maxIntervalMs':900000,'synthetic':True,'engineeringReview':'PENDING','controlAction':'DENY','behavioralCasesRun':0}
    return {'meter-energy-profile.json':profile,'meter-energy-interval.json':fixture}

def check(root):
    try:
        return ['Meter energy profile/interval drift: '+n for n,d in build(root).items() if not (root/'assets'/n).is_file() or json.loads((root/'assets'/n).read_text())!=d]
    except (OSError,ValueError,KeyError,TypeError) as e:return [str(e)]

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--write',action='store_true');args=parser.parse_args()
    if args.write:
        for n,d in build(ROOT).items():(ROOT/'assets'/n).write_text(json.dumps(d,indent=2)+'\n')
    errors=check(ROOT);print(json.dumps({'result':'FAIL' if errors else 'PASS','selectedMeterEnergyModels':1,'errors':errors}));raise SystemExit(bool(errors))
