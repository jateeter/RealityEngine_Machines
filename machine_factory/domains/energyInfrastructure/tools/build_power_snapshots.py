#!/usr/bin/env python3
"""Generate synthetic instantaneous point samples, never device or energy-balance evidence."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
NAMES=['generic.json','ref01_connected.json','ref02_island_restore.json','ref03_flex_ev.json']

def build(root):
    result={}
    for name in NAMES:
        path='assets/function-bindings/'+name
        p=json.loads((root/path).read_text());bindings={b['assetId']:b for b in p['bindings']}
        selections=[('FACILITY_PCC',p['accounting']['facilityNetMeterAssetId'])]
        selections += [(g['id'],g['primaryViewAssetId']) for g in p['accounting']['resourceGroups']]
        samples=[]
        for boundary,asset in selections:
            binding=bindings[asset]
            f=next(f for f in binding['functions'] if f['concept'] in ['Meter','Load','Generator'])
            # Deliberately independent sample magnitudes: no power-balance assertion.
            generator=f['concept']=='Generator'
            samples.append({'id':'sample.'+boundary,'boundaryId':boundary,'assetId':asset,
                'functionProjectionId':f['projectionId'],'propertyId':'project:activePower',
                'sourceIdentity':{'sourceSystemId':'synthetic.point-source','namespaceUri':'urn:energy:synthetic:points','identifier':boundary+'.activePower'},
                'rawValue':2500 if generator else 1250,'scaleExponent':-3,'unit':'kW',
                'positiveDirection':'EXPORT' if generator else 'IMPORT','quality':'GOOD',
                'observedAt':'2026-01-01T00:00:00.000Z','receivedAt':'2026-01-01T00:00:00.100Z','synthetic':True})
        result[name]={'schemaVersion':'1.0.0','kind':'SYNTHETIC_ACTIVE_POWER_SNAPSHOT',
            'sourceProjection':path,'sourceProjectionSHA256':hashlib.sha256((root/path).read_bytes()).hexdigest(),
            'evaluationAt':'2026-01-01T00:00:01.000Z','maxAgeMs':2000,'engineeringReview':'PENDING',
            'normativePropertyEquivalence':False,'controlAction':'DENY','behavioralCasesRun':0,'samples':samples}
    return result

def check(root):
    try:
        expected=build(root);folder=root/'assets/power-snapshots';errors=[]
        if {p.name for p in folder.glob('*.json')}!=set(expected):errors.append('Power snapshot inventory mismatch')
        for name,data in expected.items():
            p=folder/name
            if not p.is_file() or json.loads(p.read_text())!=data:errors.append('Power snapshot source/output drift: '+name)
        return errors
    except (OSError,ValueError,KeyError,TypeError,StopIteration) as e:return [str(e)]

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--write',action='store_true');args=parser.parse_args()
    if args.write:
        (ROOT/'assets/power-snapshots').mkdir(exist_ok=True)
        for name,data in build(ROOT).items():(ROOT/'assets/power-snapshots'/name).write_text(json.dumps(data,indent=2)+'\n')
    errors=check(ROOT);print(json.dumps({'result':'FAIL' if errors else 'PASS','syntheticSnapshotSets':4,'errors':errors}));raise SystemExit(bool(errors))
