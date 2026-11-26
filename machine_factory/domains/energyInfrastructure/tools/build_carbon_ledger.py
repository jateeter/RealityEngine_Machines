#!/usr/bin/env python3
"""Reproduce synthetic imported-electricity accounting inputs, not real provider factors."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def build(root):
    path='assets/meter-energy-interval.json';raw=(root/path).read_bytes();base=json.loads(raw)
    basis={'gasBasis':'CO2e','gwpBasis':'SYNTHETIC_GWP_BASIS','emissionsScope':'DIRECT','energyBoundary':'IMPORTED_ELECTRICITY_AT_PCC','signalType':'ATTRIBUTIONAL_AVERAGE','reportingBasis':'LOCATION_BASED','geography':'SYNTHETIC_ZONE','factorUnit':'gCO2e/kWh','dataRole':'SYNTHETIC_OBSERVATION'}
    first=copy.deepcopy(base);first['evaluationAt']='2026-01-01T00:30:01.000Z';first['maxAgeMs']=3600000
    second=copy.deepcopy(first);second['start']=copy.deepcopy(first['end']);second['end']['observedAt']='2026-01-01T00:30:00.000Z';second['end']['receivedAt']='2026-01-01T00:30:00.100Z'
    b=bytearray.fromhex(second['end']['blockHex']);b[92:96]=(150000).to_bytes(4,'big');b[76:80]=(17500).to_bytes(4,'big');second['end']['blockHex']=b.hex()
    rows=[]
    for i,(interval,value) in enumerate([(first,'100'),(second,'400')],1):
        rows.append({'id':f'interval.{i}','meterInterval':interval,'factor':{'providerId':'SYNTHETIC_PROVIDER','revision':'fixture-v1','basis':copy.deepcopy(basis),'intervalStart':interval['start']['observedAt'],'intervalEnd':interval['end']['observedAt'],'issuedAt':'2026-01-01T00:30:00.500Z','validUntil':'2026-01-01T01:00:00.000Z','quality':'GOOD','rights':'SYNTHETIC_FIXTURE_ONLY','intensity':value}})
    return {'schemaVersion':'1.0.0','kind':'SYNTHETIC_IMPORT_CARBON_LEDGER','sourceInterval':path,'sourceIntervalSHA256':hashlib.sha256(raw).hexdigest(),'evaluationAt':first['evaluationAt'],'basis':basis,'rows':rows,'accountingUse':'RETROSPECTIVE_ONLY','engineeringReview':'PENDING','controlAction':'DENY','behavioralCasesRun':0}

def check(root):
    try:
        p=root/'assets/import-carbon-ledger.json'
        return [] if p.is_file() and json.loads(p.read_text())==build(root) else ['Synthetic carbon ledger input/source drift']
    except (OSError,ValueError,KeyError,TypeError) as e:return [str(e)]

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--write',action='store_true');args=parser.parse_args()
    if args.write:(ROOT/'assets/import-carbon-ledger.json').write_text(json.dumps(build(ROOT),indent=2)+'\n')
    errors=check(ROOT);print(json.dumps({'result':'FAIL' if errors else 'PASS','syntheticCarbonLedgers':1,'errors':errors}));raise SystemExit(bool(errors))
