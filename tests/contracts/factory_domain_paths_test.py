"""Factory aliases preserve canonical admission and immutable payload boundaries."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from factory_paths import factory_directory, aliases

def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts/domain-approval' / filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value

deployment = load('factory_deployment', 'deployment.py')
approval = load('factory_approval', 'approval.py')

class FactoryDomainPathsTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name)
        (self.repo / 'domains').mkdir()
        self.config = self.repo / 'domains/factory-domain-paths.json'

    def mapping(self, value=None):
        self.config.write_text(json.dumps({'schemaVersion': '1.0.0', 'purpose': 'Synthetic unit mapping', 'aliases': value if value is not None else {'energy-infrastructure': 'energyInfrastructure'}}))

    def candidate(self):
        source = self.repo / 'machines/domains/energy-infrastructure'
        source.mkdir(parents=True)
        (source / 'ENI001.json').write_text(json.dumps({'version': '0.1.0', 'machine': {'id': 'ENI001', 'name': 'Synthetic candidate', 'metadata': {'category': 'energy-infrastructure'}, 'sequences': [{'id': 'one'}], 'perceptualMapping': {'input': {'offset': 86016, 'length': 1}, 'output': {'offset': 86017, 'length': 1}}}}))
        return source

    def test_no_mapping_preserves_default(self):
        self.assertEqual(factory_directory(self.repo, 'unit'), self.repo / 'machine_factory/domains/unit')

    def test_repository_configuration(self):
        self.assertEqual(aliases(ROOT)['energy-infrastructure'], 'energyInfrastructure')
        self.assertEqual(factory_directory(ROOT, 'energy-infrastructure'), ROOT / 'machine_factory/domains/energyInfrastructure')

    def test_owner_selected_folder(self):
        self.mapping()
        self.assertEqual(factory_directory(self.repo, 'energy-infrastructure'), self.repo / 'machine_factory/domains/energyInfrastructure')
        self.assertEqual(factory_directory(self.repo, 'ifrs-accounting'), self.repo / 'machine_factory/domains/ifrs-accounting')

    def test_factory_name_is_not_a_canonical_slug(self):
        self.mapping()
        with self.assertRaisesRegex(ValueError, 'canonical.*slug'):
            factory_directory(self.repo, 'energyInfrastructure')
        with self.assertRaisesRegex(ValueError, 'domain slug'):
            approval.slug('energyInfrastructure')
        with self.assertRaisesRegex(ValueError, 'Invalid domain'):
            deployment.identity('energyInfrastructure', '1.0.0', 'PRODUCTION')

    def test_traversal_and_absolute_components_rejected(self):
        for target in ['../escape', '/tmp/escape', 'one/two', r'one\two', '.', '..', '', 'safe\n', 'x'*129]:
            with self.subTest(target=target), self.assertRaises(ValueError):
                self.mapping({'unit': target})
                factory_directory(self.repo, 'unit')

    def test_invalid_canonical_key_rejected(self):
        for key in ['../escape', 'MixedCase', 'a/b', '']:
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.mapping({key: 'safe'})
                aliases(self.repo)

    def test_duplicate_casefolded_aliases_rejected(self):
        self.mapping({'one': 'ChosenFolder', 'two': 'chosenfolder'})
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            aliases(self.repo)

    def test_alias_cannot_shadow_manifest_domain(self):
        self.mapping({'unit': 'energy'})
        (self.repo / 'domains/domain-manifest.json').write_text(json.dumps({'domains': {'energy': {}}}))
        with self.assertRaisesRegex(ValueError, 'shadows'):
            aliases(self.repo)

    def test_alias_cannot_shadow_other_factory_domain(self):
        self.mapping({'unit': 'other'})
        (self.repo / 'machine_factory/domains/other').mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, 'shadows'):
            aliases(self.repo)

    def test_existing_default_payload_history_cannot_move(self):
        self.mapping({'unit': 'unitFactory'})
        (self.repo / 'machine_factory/domains/unit/deployments/1.0.0').mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, 'history cannot be redirected'):
            factory_directory(self.repo, 'unit')

    def test_symlink_target_rejected(self):
        self.mapping()
        factory = self.repo / 'machine_factory/domains'
        factory.mkdir(parents=True)
        real = self.repo / 'real'
        real.mkdir()
        (factory / 'energyInfrastructure').symlink_to(real, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            factory_directory(self.repo, 'energy-infrastructure')

    def test_symlink_config_rejected(self):
        self.mapping()
        real = self.repo / 'mapping.json'
        self.config.rename(real)
        self.config.symlink_to(real)
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            aliases(self.repo)

    def test_unknown_config_fields_rejected(self):
        self.mapping()
        value = json.loads(self.config.read_text())
        value['runtimeAlias'] = True
        self.config.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, 'configuration'):
            aliases(self.repo)

    def test_package_and_validation_use_mapped_folder(self):
        self.mapping()
        source = self.candidate()
        path, manifest = deployment.package(self.repo, 'energy-infrastructure', '0.1.0-test.1', 'TEST_ONLY', source, True)
        self.assertEqual(path, self.repo / 'machine_factory/domains/energyInfrastructure/deployments/0.1.0-test.1/payload-manifest.json')
        self.assertEqual(manifest['domain'], 'energy-infrastructure')
        self.assertTrue(manifest['payloadRoot'].startswith('machine_factory/domains/energyInfrastructure/'))
        self.assertEqual(deployment.validate_payload(self.repo, path), manifest)
        self.assertFalse((self.repo / 'machine_factory/domains/energy-infrastructure').exists())

    def test_mapping_change_does_not_reinterpret_old_payload(self):
        self.mapping()
        path, _ = deployment.package(self.repo, 'energy-infrastructure', '0.1.0-test.1', 'TEST_ONLY', self.candidate(), True)
        self.mapping({'energy-infrastructure': 'otherFactory'})
        with self.assertRaisesRegex(ValueError, 'Unexpected factory payload location'):
            deployment.validate_payload(self.repo, path)

    def test_legacy_category_cannot_enter_new_payload(self):
        self.mapping()
        source = self.candidate()
        file = source / 'ENI001.json'
        value = json.loads(file.read_text())
        value['machine']['metadata']['category'] = 'energy'
        file.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, 'identity/domain'):
            deployment.package(self.repo, 'energy-infrastructure', '0.1.0-test.1', 'TEST_ONLY', source)

    def test_plan_resolves_factory_and_binds_mapping_input(self):
        self.mapping()
        self.candidate()
        (self.repo / 'domains/domain-manifest.json').write_text(json.dumps({'domains': {'energy-infrastructure': {'status': 'experimental'}}}))
        (self.repo / 'domains/domain-registry.json').write_text(json.dumps({'domains': {'energy-infrastructure': {}}}))
        (self.repo / 'domains/ces-contract-registry.json').write_text(json.dumps({'scopes': {}}))
        ci = self.repo / 'ci'
        (ci / 'config').mkdir(parents=True)
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        subprocess.run(['git', 'add', 'domains/factory-domain-paths.json'], cwd=self.repo, check=True)
        # plan only needs a candidate commit ID, not an admission or forge.
        from unittest.mock import patch
        with patch.object(approval, 'git', return_value='0'*40):
            result = approval.plan(self.repo, ci, 'energy-infrastructure', '0.1.0')
        self.assertEqual(result['state'], 'PLAN_ONLY_NOT_APPROVED')
        self.assertEqual(result['factoryDirectory'], 'machine_factory/domains/energyInfrastructure')
        self.assertIn('domains/factory-domain-paths.json', result['authoredInputs'])
        before = approval.input_snapshot(self.repo)
        self.mapping({'energy-infrastructure': 'changedFactory'})
        self.assertNotEqual(before, approval.input_snapshot(self.repo))

if __name__ == '__main__':
    unittest.main()
