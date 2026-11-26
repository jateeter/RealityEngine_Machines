#!/usr/bin/env python3
"""Validate generic scenario specifications, never simulate hardware or admit a domain."""
import argparse
import json
from pathlib import Path

def validate(data, standard_ids, case_ids):
    errors = []
    def require(ok, message):
        if not ok:
            errors.append(message)
    require(data['status'] == 'SCENARIO_DESIGN_BASELINE_NOT_RUNTIME_ACCEPTANCE', 'Unverified scenario acceptance claim')
    require(data['workstreamId'] == 'EI03', 'Wrong reference-scope workstream')
    require(data.get('assetIntegrationContext',{}).get('standardId')=='OP23' and data['assetIntegrationContext'].get('artifact')=='assets/fsgim-integration-context.json','Missing owner-selected ASHRAE 201 integration context')
    require(data['behavioralCasesRun'] == 0 and not data['simulationModelsImplemented'] and not data['assetTemplatesImplemented'], 'Fabricated runtime/model/template delivery')
    roles = {r['id']: r for r in data['assetRoles']}
    require(len(roles) == len(data['assetRoles']), 'Duplicate functional asset role')
    for role in roles.values():
        require(role['standardClassMappingStatus'] == 'EI04_REQUIRED_NOT_A_NORMATIVE_CLASS_ASSERTION', 'Functional roles must not claim normative class completeness')
        require(role['modelImplementationStatus'] == 'NOT_IMPLEMENTED', 'Fabricated simulator implementation')
        if role['kind'] in ['hardware', 'electrical']:
            require(role['hardwareRepresentation'] == 'SIMULATED_REQUIRED_HARDWARE', 'Physical hardware required by reference scenario')
        else:
            require(role['hardwareRepresentation'] == 'ACTUAL_SOFTWARE_WITH_GENERIC_PEER_DATA', 'Software must execute genuinely')
    authority = {r['id']: r for r in data['authorityRoles']}
    require(len(authority) == len(data['authorityRoles']), 'Duplicate authority role')
    for key in ['ASSURANCE_REVIEWER', 'ADMISSION_RELEASE_OWNER']:
        require(key in authority and authority[key]['identityKind'] == 'AUTHENTIC_REPOSITORY_REVIEW', 'Generic identity cannot approve genuine repository/admission evidence')
    require(authority['MODEL_PLANNER']['identityKind'] == 'ACTUAL_SOFTWARE_ROLE', 'Model authority misclassified')
    require('direct actuator/vector writes' in authority['MODEL_PLANNER']['prohibited'], 'Missing model authority boundary')
    require(all(r['namedPerson'] is None for r in authority.values()), 'Invented named authority assignment')
    scenarios = data['scenarios']
    scenario_ids = {s['id'] for s in scenarios}
    require(len(scenario_ids) == len(scenarios) == 3, 'Expected three distinct generic reference scenarios')
    covered_cases = set()
    covered_modes = set()
    for scenario in scenarios:
        key = scenario['id']
        require(scenario['physicalSiteRequired'] is False, f'Physical site prerequisite: {key}')
        require(scenario['implementationStatus'] == 'SCENARIO_SPECIFICATION_ONLY', f'Unverified executable scenario: {key}')
        require(scenario['engineeringThresholds'] == 'EI06_REVIEWED_REFERENCE_ENVELOPE_REQUIRED', f'Unreviewed engineering envelope: {key}')
        require(scenario['profilePins'] == 'EI05_REQUIRED' and scenario['simulatorCoverage'] == 'EI18_REQUIRED', f'Unverified profiles/simulators: {key}')
        require(set(scenario['assetRoleIds']) <= set(roles), f'Unknown asset role: {key}')
        require(set(scenario['authorityRoleIds']) == set(authority), f'Unknown/missing authority role: {key}')
        require(set(scenario['caseIds']) <= case_ids, f'Unknown acceptance case: {key}')
        covered_cases.update(scenario['caseIds'])
        covered_modes.update(scenario['supportedModes'])
        require({'protection-controller', 'meter', 'clock', 'microgrid-controller'} <= set(scenario['assetRoleIds']), f'Missing protection/observability/control: {key}')
        topology = scenario['electricalConnectivity']
        require(topology['claim'] == 'TOPOLOGY_ONLY_NOT_POWER_FLOW_OR_PHYSICAL_DESIGN', f'Unverified power-system model: {key}')
        endpoints = set(scenario['assetRoleIds']) | set(topology['busIds'])
        require(all(len(edge) == 2 and set(edge) <= endpoints and edge[0] != edge[1] for edge in topology['edges']), f'Unknown/self-loop topology endpoint: {key}')
        for value in scenario['nominalReference'].values():
            require(value['basis'] == 'CHOSEN_GENERIC_REFERENCE_NOT_NORMATIVE_LIMIT' and value['value'] > 0 and bool(value['unit']), f'Generic nominal parameter lacks provenance/unit: {key}')
        if 'BLACK_START' in scenario['supportedModes']:
            require('grid-forming-storage' in scenario['capabilities'], 'Black start lacks grid-forming role')
            require('battery-inverter' in scenario['assetRoleIds'], 'Black start lacks energy-conversion role')
    require(covered_cases == case_ids, 'Reference scenarios do not cover all acceptance cases')
    require({'GRID_CONNECTED', 'PLANNED_ISLAND_TRANSITION', 'UNPLANNED_ISLAND_TRANSITION', 'ISLANDED', 'BLACK_START', 'RESYNCHRONIZING', 'DEGRADED_OBSERVABILITY', 'RECOVERY'} <= covered_modes, 'Operating lifecycle coverage incomplete')
    rows = data['standardsApplicability']
    require(len(rows) == len(standard_ids) and {r['standardId'] for r in rows} == standard_ids, 'Standards applicability coverage incomplete')
    for row in rows:
        require(bool(row['rationale']) and set(row['scenarioIds']) <= scenario_ids, 'Invalid standard/scenario disposition')
        require(row['exactProfileFreezeIssue'] == 'EI05' and row['assetClassEnumerationIssue'] == 'EI04', 'Missing profile/class follow-up ownership')
        require(bool(row['scenarioIds']) or row['scopeDisposition'].startswith('EXCLUDED_'), 'Standard exclusion needs explicit disposition')
    return errors

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    root = parser.parse_args().root.resolve()
    def read(name):
        return json.loads((root / name).read_text())
    data = read('examples/reference-microgrids.json')
    errors = validate(data, {r['id'] for r in read('standards-inventory.json')['standards']}, {r['id'] for r in read('acceptance/cases.json')['cases']})
    print(json.dumps({'result': 'FAIL' if errors else 'PASS', 'verificationType': 'REFERENCE_SCOPE_SPECIFICATION_ONLY', 'scenarios': len(data['scenarios']), 'functionalAssetRoles': len(data['assetRoles']), 'authorityRoles': len(data['authorityRoles']), 'standardsDispositions': len(data['standardsApplicability']), 'behavioralCasesRun': 0, 'errors': errors}, indent=2))
    return bool(errors)

if __name__ == '__main__':
    raise SystemExit(main())
