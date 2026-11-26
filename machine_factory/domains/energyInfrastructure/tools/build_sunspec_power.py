#!/usr/bin/env python3
"""Reproduce the offline SunSpec selected-point profile and synthetic register replay."""
import argparse
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def build(root):
    models=[];blocks=[]
    for n,boundary,raw,sf in [(103,'PV_AC',25000,-1),(203,'FACILITY_PCC',12500,-1)]:
        path=f'intake/public-models/sunspec/model_{n}.json';data=(root/path).read_bytes();d=json.loads(data);points={};offset=0
        for i,p in enumerate(d['group']['points']):
            points[p['name']]={'offset':offset,'pointer':f'/group/points/{i}','definition':p};offset+=p['size']
        models.append({'modelId':n,'sourcePath':path,'sourceSHA256':hashlib.sha256(data).hexdigest(),'registerCount':offset,'powerOffset':points['W']['offset'],'scaleOffset':points['W_SF']['offset'],'powerPointer':points['W']['pointer'],'scalePointer':points['W_SF']['pointer']})
        words=[0]*offset;words[0]=n;words[1]=offset-2;words[points['W']['offset']]=raw&0xffff;words[points['W_SF']['offset']]=sf&0xffff
        blocks.append({'boundaryId':boundary,'modelId':n,'blockHex':b''.join(w.to_bytes(2,'big') for w in words).hex()})
    profile={'schemaVersion':'1.0.0','kind':'OFFLINE_SUNSPEC_POWER_SUBSET','modelCommit':'90b4a331dcca1d6eac69c1bead952fddcc5852e0','byteOrder':'BIG_ENDIAN','missingInt16':32768,'missingScaleFactor':32768,'scaleRange':[-10,10],'models':models,'normativeFsgimPropertyEquivalence':False,'peerVerified':False,'controlAction':'DENY'}
    path='assets/power-snapshots/generic.json'
    replay={'schemaVersion':'1.0.0','kind':'SYNTHETIC_REGISTER_BLOCK_REPLAY','sourceSnapshot':path,'sourceSnapshotSHA256':hashlib.sha256((root/path).read_bytes()).hexdigest(),'blocks':blocks,'networkExecution':False,'behavioralCasesRun':0,'controlAction':'DENY'}
    return {'sunspec-power-profile.json':profile,'sunspec-power-replay.json':replay}

def check(root):
    try:
        return ['SunSpec power profile/replay drift: '+name for name,data in build(root).items() if not (root/'assets'/name).is_file() or json.loads((root/'assets'/name).read_text())!=data]
    except (OSError,ValueError,KeyError,TypeError) as e:return [str(e)]

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--write',action='store_true');args=parser.parse_args()
    if args.write:
        for name,data in build(ROOT).items():(ROOT/'assets'/name).write_text(json.dumps(data,indent=2)+'\n')
    errors=check(ROOT);print(json.dumps({'result':'FAIL' if errors else 'PASS','selectedPowerModels':2,'errors':errors}));raise SystemExit(bool(errors))
