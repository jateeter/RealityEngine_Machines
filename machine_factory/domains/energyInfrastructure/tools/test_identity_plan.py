import json
from pathlib import Path
import tempfile
import unittest
from build_identity_plan import build, current_occupancy, validate

ROOT = Path(__file__).resolve().parents[1]

class IdentityPlanTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads((ROOT / 'machine-dispositions.json').read_text())
        self.decision = json.loads((ROOT / 'identity-decision.json').read_text())
        self.imports = json.loads((ROOT / 'machine-import-manifest.json').read_text())

    def check_error(self, text, **kwargs):
        errors = validate(self.plan, self.decision, self.imports, **kwargs)
        self.assertTrue(any(text in e for e in errors), errors)

    def test_reproducible_and_collision_free_current_corpus(self):
        self.assertEqual(build(ROOT), self.plan)
        self.assertEqual(validate(self.plan, self.decision, self.imports, **current_occupancy(ROOT.parents[2], ROOT, self.decision['canonicalDomain'])), [])

    def test_all187_have_one_disposition(self):
        self.plan['dispositions'].pop()
        self.check_error('disposition coverage')

    def test_duplicate_target(self):
        self.plan['dispositions'][1]['targetId'] = self.plan['dispositions'][0]['targetId']
        self.check_error('Duplicate target identity')

    def test_other_domain_prefix(self):
        self.check_error('Code prefix collision', existing_prefixes=['ENI'])

    def test_other_machine_stem(self):
        self.check_error('Existing machine identity collision', existing_stems=[self.plan['dispositions'][0]['targetStem']])

    def test_other_machine_name(self):
        self.check_error('Existing machine identity collision', existing_names=[self.plan['dispositions'][0]['targetName']])

    def test_reserved_or_service_overlap(self):
        start = self.plan['nativeAllocation']['offset']
        self.check_error('Native allocation collision', occupied=[(start - 16, 32)])

    def test_adjacent_clone_band_is_not_overlap(self):
        self.assertEqual(validate(self.plan, self.decision, self.imports, occupied=[(20480, 65536)]), [])

    def test_window_overlap(self):
        row = self.plan['dispositions'][0]
        row['candidateWindows']['output']['offset'] = row['candidateWindows']['input']['offset']
        self.check_error('Intra-block overlap')

    def test_out_of_band_block(self):
        self.plan['dispositions'][-1]['block']['offset'] = 102400
        self.check_error('out-of-band')

    def test_source_provenance(self):
        self.plan['dispositions'][0]['sourceSHA256'] = '0'*64
        self.check_error('Source provenance mismatch')

    def test_false_admission(self):
        self.decision['candidateMachinesAuthored'] = True
        self.check_error('False identity/admission')

    def test_legacy_code_not_reused(self):
        self.plan['dispositions'][0]['targetCode'] = 'ENX001'
        self.check_error('ID/stem/prefix mismatch')

    def test_factory_mapping_drift(self):
        self.check_error('mapping/identity decision mismatch', factory_aliases={'energy-infrastructure': 'wrongFolder'})

    def factory_fixture(self, code, offset):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        repo = Path(temp.name)
        (repo / 'domains').mkdir()
        for name, value in [('domain-manifest', {'domains': {}}), ('domain-registry', {}), ('region-allocation', {})]:
            (repo / 'domains' / (name + '.json')).write_text(json.dumps(value))
        file = repo / 'machine_factory/domains/other/machines' / (code + '999.json')
        file.parent.mkdir(parents=True)
        file.write_text(json.dumps({'machine': {'name': 'Other prototype', 'metadata': {'tagging': {'machineCode': code + '999'}}, 'perceptualMapping': {'input': {'offset': offset, 'length': 4}}}}))
        return repo

    def test_other_factory_prefix_scanned(self):
        repo = self.factory_fixture('ENI', 120000)
        self.check_error('Code prefix collision', **current_occupancy(repo, ROOT, 'energy-infrastructure'))

    def test_other_factory_window_scanned(self):
        repo = self.factory_fixture('OTHER', 86016)
        self.check_error('Native allocation collision', **current_occupancy(repo, ROOT, 'energy-infrastructure'))

    def test_nested_factory_payload_scanned(self):
        repo = self.factory_fixture('OTHER', 86016)
        source = repo / 'machine_factory/domains/other/machines/OTHER999.json'
        target = repo / 'machine_factory/domains/other/deployments/v1/machines/OTHER999.json'
        target.parent.mkdir(parents=True)
        source.rename(target)
        self.check_error('Native allocation collision', **current_occupancy(repo, ROOT, 'energy-infrastructure'))

if __name__ == '__main__':
    unittest.main()
