import json
from pathlib import Path
import unittest
from verify_reference_scope import validate

ROOT = Path(__file__).resolve().parents[1]

class ReferenceScopeTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'examples/reference-microgrids.json').read_text())
        self.standards = {r['id'] for r in json.loads((ROOT / 'standards-inventory.json').read_text())['standards']}
        self.cases = {r['id'] for r in json.loads((ROOT / 'acceptance/cases.json').read_text())['cases']}

    def check_error(self, expected):
        self.assertTrue(any(expected in e for e in validate(self.data, self.standards, self.cases)))

    def test_baseline(self):
        self.assertEqual(validate(self.data, self.standards, self.cases), [])

    def test_missing_case(self):
        for s in self.data['scenarios']:
            s['caseIds'] = [c for c in s['caseIds'] if c != 'AC43']
        self.check_error('cover all acceptance cases')

    def test_unknown_role(self):
        self.data['scenarios'][0]['assetRoleIds'].append('unreviewed-device')
        self.check_error('Unknown asset role')

    def test_missing_standard(self):
        self.data['standardsApplicability'].pop()
        self.check_error('Standards applicability coverage')

    def test_fake_admission_authority(self):
        next(r for r in self.data['authorityRoles'] if r['id'] == 'ADMISSION_RELEASE_OWNER')['identityKind'] = 'GENERIC_OPERATING_ROLE'
        self.check_error('Generic identity cannot approve')

    def test_physical_dependency(self):
        self.data['assetRoles'][1]['hardwareRepresentation'] = 'REAL_DEVICE_REQUIRED'
        self.check_error('Physical hardware required')

    def test_normative_taxonomy_overclaim(self):
        self.data['assetRoles'][0]['standardClassMappingStatus'] = 'ALL_STANDARD_CLASSES_IMPLEMENTED'
        self.check_error('must not claim normative class completeness')

    def test_invalid_topology(self):
        self.data['scenarios'][0]['electricalConnectivity']['edges'].append(['local-ac-bus', 'nonexistent-terminal'])
        self.check_error('Unknown/self-loop topology')

    def test_nominal_value_masquerades_as_standard_limit(self):
        self.data['scenarios'][0]['nominalReference']['frequency']['basis'] = 'STANDARD_MANDATED'
        self.check_error('lacks provenance/unit')

    def test_fabricated_execution(self):
        self.data['behavioralCasesRun'] = 43
        self.check_error('Fabricated runtime/model/template')

if __name__ == '__main__':
    unittest.main()
