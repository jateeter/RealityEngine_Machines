#!/usr/bin/env python3
"""Reproduce the versioned partial storage simulated-hardware catalog."""
import argparse
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def build(root):
    paths=['tools/simulate_storage_component.mjs','assets/storage-proposal-screen.json','assets/generic-storage-screen-profile.json','assets/function-bindings/ref01_connected.json','assets/sunspec-power-profile.json','assets/meter-energy-profile.json','tools/evaluate_meter_interval.mjs','tools/storage_execution_journal.mjs','tools/assess_risk.mjs','assets/risk-assessment-fixture.json']
    return {'storage-component-catalog.json':{
        'schemaVersion':'1.0.0','kind':'PARTIAL_SIMULATED_REQUIRED_HARDWARE_COMPONENT',
        'version':'energy-storage-component/0.6.0','status':'COMPONENT_ONLY_NOT_DOMAIN_ACCEPTANCE',
        'ownerIssueId':'EI18','referenceScenarioId':'REF01_CONNECTED',
        'assetMode':'GENERIC_OR_TEMPLATE_ALLOWED','storageAssetId':'fixture.battery-inverter',
        'integrationContext':'OP23_FSGIM_WITH_OP17_DI_FACET_PROVISIONAL_NOT_NORMATIVE_EQUIVALENCE',
        'partialCounterparts':['BATTERY_ENERGY_STATE','FIXED_EFFICIENCY_CONVERSION','SELECTED_PCC_POWER_AND_ENERGY_READBACK'],
        'initialObservedAt':'2026-11-25T00:00:00.000Z','initialStoredEnergyKWh':'5','initialImportedCounterRaw':1000000,'initialExportedCounterRaw':100000,'energyScaleExponent':-2,'intervalSeconds':900,'powerResolutionW':10,'evaluationClockMode':'EXPLICIT_FORWARD_ONLY_NO_PLANT_EVOLUTION','maxAdditionalEvaluationOffsetMs':3600000,
        'chargeEfficiency':'0.9','dischargeEfficiency':'0.8','riskBootstrap':'UNREVIEWED_SYNTHETIC_CLEAR_ASSUMPTION',
        'sources':[{'path':p,'sha256':hashlib.sha256((root/p).read_bytes()).hexdigest()} for p in paths],
        'simulationOnly':True,'realDeviceAccessEnabled':False,'networkExecution':False,
        'controlAction':'DENY','carriedCarbonGCO2e':None,'behavioralCasesRun':0,
        'coverageFulfillmentReceipt':None,'engineeringReview':'PENDING',
        'limitations':['No wire peer, full hardware coverage or physical solver',
                       'Plant clock advances only on accepted held intervals; evaluation-only advances add no plant dynamics',
                       'Source-bound offline journal reconstruction available; no authenticated durable or distributed execution guarantee',
                       'No authenticated risk clearance, engineering approval or native admission']}}
def check(root):
    try:return ['Storage component catalog drift: '+n for n,d in build(root).items() if not (root/'assets'/n).is_file() or json.loads((root/'assets'/n).read_text())!=d]
    except (OSError,ValueError,KeyError,TypeError) as e:return [str(e)]
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');args=p.parse_args()
    if args.write:
        for n,d in build(ROOT).items():(ROOT/'assets'/n).write_text(json.dumps(d,indent=2)+'\n')
    errors=check(ROOT);print(json.dumps({'result':'FAIL' if errors else 'PASS','errors':errors}));raise SystemExit(bool(errors))
