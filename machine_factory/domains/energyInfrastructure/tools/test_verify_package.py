"""Resealed negative fixtures prove semantic checks beyond checksum comparison."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from seal_assets import inventory
from verify_package import check

ROOT = Path(__file__).resolve().parents[1]

class AcceptancePlanVerificationTests(unittest.TestCase):
    def fixture(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        dest = Path(temp.name) / 'package'
        shutil.copytree(ROOT, dest, ignore=shutil.ignore_patterns('__pycache__', '.DS_Store', '*.pyc'))
        return dest

    def mutate(self, root, rel, change):
        path = root / rel
        value = json.loads(path.read_text())
        change(value)
        path.write_text(json.dumps(value, indent=2) + '\n')
        (root / 'asset-manifest.json').write_text(json.dumps(inventory(root), indent=2) + '\n')

    def rejected(self, root, expected):
        result = check(root)
        self.assertEqual(result['result'], 'FAIL')
        self.assertTrue(any(expected in error for error in result['errors']), result['errors'])
        self.assertFalse(any('digest mismatch' in error for error in result['errors']))

    def test_baseline(self):
        self.assertEqual(check(ROOT)['result'], 'PASS')

    def test_dependency_cycle(self):
        root = self.fixture()
        self.mutate(root, 'acceptance/issues.json', lambda d: d['issues'][0]['dependsOn'].append('EI24'))
        self.rejected(root, 'dependency cycle')

    def test_absolute_workspace_link(self):
        root = self.fixture()
        with (root / 'README.md').open('a') as stream:
            stream.write('\n[Host-only reference](/tmp/host-only.md)\n')
        (root / 'asset-manifest.json').write_text(json.dumps(inventory(root), indent=2) + '\n')
        self.rejected(root, 'Nonportable absolute Markdown link')

    def test_physical_hardware_prerequisite(self):
        root = self.fixture()
        self.mutate(root, 'acceptance/cases.json', lambda d: d['cases'][0].update(hardwareMode='PHYSICAL_REQUIRED'))
        self.rejected(root, 'Physical/site prerequisite')

    def test_generic_assets_denied(self):
        root = self.fixture()
        self.mutate(root, 'acceptance/cases.json', lambda d: d['cases'][1].update(genericAssetsAllowed=False))
        self.rejected(root, 'Physical/site prerequisite')

    def test_standard_class_coverage_missing(self):
        root = self.fixture()
        self.mutate(root, 'acceptance/coverage-requirements.json', lambda d: d['standardClassCoverage'].pop())
        self.rejected(root, 'Missing standard asset-class')

    def test_simulated_hardware_coverage_missing(self):
        root = self.fixture()
        self.mutate(root, 'acceptance/coverage-requirements.json', lambda d: d['hardwareCoverage'].pop())
        self.rejected(root, 'Missing simulated-hardware')

    def test_fabricated_coverage_receipt(self):
        root = self.fixture()
        self.mutate(root, 'acceptance/coverage-requirements.json', lambda d: d['hardwareCoverage'][0].update(fulfillmentReceipt='invented'))
        self.rejected(root, 'Fabricated/misowned hardware')

    def test_fabricated_behavioral_success(self):
        root = self.fixture()
        self.mutate(root, 'acceptance/cases.json', lambda d: d['cases'][0].update(status='PASS'))
        self.rejected(root, 'Unverified behavioral PASS')

    def test_duplicate_primary_owner(self):
        root = self.fixture()
        self.mutate(root, 'acceptance/issues.json', lambda d: d['issues'][16]['primaryCaseIds'].append('AC01'))
        self.rejected(root, 'one consistent primary owner')

if __name__ == '__main__':
    unittest.main()
