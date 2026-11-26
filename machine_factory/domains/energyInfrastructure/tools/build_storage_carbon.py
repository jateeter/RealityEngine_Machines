#!/usr/bin/env python3
"""Reproduce synthetic storage allocation inputs, not device or standards evidence."""
import argparse
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def build(root):
    path='assets/import-carbon-ledger.json';raw=(root/path).read_bytes();source=json.loads(raw)
    projection=json.loads((root/source['rows'][0]['meterInterval']['sourceProjection']).read_text())
    asset=next(g['primaryViewAssetId'] for g in projection['accounting']['resourceGroups'] if g['id']=='STORAGE_AC')
    return {'schemaVersion':'1.0.0','kind':'SYNTHETIC_STORAGE_CARBON_ALLOCATION','sourceLedger':path,'sourceLedgerSHA256':hashlib.sha256(raw).hexdigest(),'storageAssetId':asset,'evaluationAt':'2026-01-01T01:00:01.000Z','accountingUse':'RETROSPECTIVE_ONLY','initialInventory':{'status':'KNOWN_EMPTY_SYNTHETIC','storedKWh':'0','carriedGCO2e':'0'},'accountingPolicy':'DRAFT_WELL_MIXED_POOL_ALL_CONVERSION_LOSS_EMISSIONS_TO_DELIVERY','events':[
        {'id':'charge.1','type':'CHARGE_ALLOCATION','at':source['rows'][0]['factor']['intervalEnd'],'sourceRowId':'interval.1','inputAcKWh':'1','storedKWh':'0.9'},
        {'id':'charge.2','type':'CHARGE_ALLOCATION','at':source['rows'][1]['factor']['intervalEnd'],'sourceRowId':'interval.2','inputAcKWh':'1','storedKWh':'0.8'},
        {'id':'discharge.1','type':'DISCHARGE_ALLOCATION','at':'2026-01-01T00:45:00.000Z','removedStoredKWh':'0.85','deliveredAcKWh':'0.68'}
    ],'engineeringReview':'PENDING','controlAction':'DENY','behavioralCasesRun':0}

def check(root):
    try:
        p=root/'assets/storage-carbon-allocation.json'
        return [] if p.is_file() and json.loads(p.read_text())==build(root) else ['Storage carbon source/input drift']
    except (OSError,ValueError,KeyError,TypeError,StopIteration) as e:return [str(e)]

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--write',action='store_true');args=parser.parse_args()
    if args.write:(ROOT/'assets/storage-carbon-allocation.json').write_text(json.dumps(build(ROOT),indent=2)+'\n')
    errors=check(ROOT);print(json.dumps({'result':'FAIL' if errors else 'PASS','syntheticStorageAllocations':1,'errors':errors}));raise SystemExit(bool(errors))
