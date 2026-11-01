"""Synthetic deployment copies exercise version, evidence and rollback guards."""
import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('domain_deployment', ROOT / 'scripts/domain-approval/deployment.py')
d = importlib.util.module_from_spec(spec); spec.loader.exec_module(d)
spec = importlib.util.spec_from_file_location('deployment_approval', ROOT / 'scripts/domain-approval/approval.py')
a = importlib.util.module_from_spec(spec); spec.loader.exec_module(a)


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup); self.repo = Path(temporary.name)
        self.target = self.repo / 'machines/domains/unit'; self.target.mkdir(parents=True)
        self.runtime = self.target / 'One.json'
        self.runtime.write_text(json.dumps({'version': '1.0.0', 'machine': {'id': 'One', 'name': 'One', 'metadata': {'category': 'unit'}, 'sequences': [{'id': 's1'}], 'perceptualMapping': {'output': {'offset': 0, 'length': 1}}}}))
        (self.repo / 'domains').mkdir()
        self.manifest = self.repo / 'domains/domain-manifest.json'
        self.manifest.write_text(json.dumps({'domains': {'unit': {'status': 'experimental'}}}))
        self.residual = self.repo / 'machine_factory/domains/unit/tools/active.txt'; self.residual.parent.mkdir(parents=True); self.residual.write_text('retained for future extensions')
        self.payload, self.package = d.package(self.repo, 'unit', '1.0.0-test.1', 'TEST_ONLY', self.target, True)
        contract = {'members': {'domains/unit/One.json': {'sha256': d.filehash(self.runtime)}}}
        (self.repo / 'domains/corpus-contract.json').write_text(json.dumps(contract))
        self.evidence = self.repo / 'evidence.json'
        self.evidence.write_text(json.dumps({'approvalContext': 'TEST_ONLY', 'productionApproval': False, 'countReconciliation': {'transitionSHA256': d.objecthash(contract)}, 'native': {'quorum': '3-of-3', 'machinesPerRuntime': 1}, 'managerLoad': {'result': 'PASS_MANAGER_LOAD_API'}}))
        self.waiver = self.repo / 'waiver.json'
        self.waiver.write_text(json.dumps({'domain': 'unit', 'approvalContext': 'TEST_ONLY', 'productionApproval': False, 'independentSignoff': 'WAIVED_BY_OPERATOR_FOR_WORKFLOW_TEST'}))
        # Global corpus-history validation has its own real contract tests;
        # this fixture is explicitly a one-machine synthetic unit repository.
        self.counter = patch.object(d, 'check_counts'); self.check_counts = self.counter.start(); self.addCleanup(self.counter.stop)

    def deploy(self, write=True):
        return d.deploy(self.repo, self.payload, self.evidence, self.waiver, write)

    def test_copy_and_factory_retention(self):
        original = self.runtime.read_bytes(); self.runtime.unlink(); self.target.rmdir()
        record = self.deploy()
        self.assertEqual(self.runtime.read_bytes(), original)
        self.assertEqual(self.residual.read_text(), 'retained for future extensions')
        self.assertEqual(record['factoryLifecycle'], 'ACTIVE_FOR_FUTURE_EXTENSIONS')
        self.assertFalse(record['productionApproval'])

    def test_dry_run_has_no_deployment_side_effect(self):
        record = self.deploy(False)
        self.assertEqual(record['state'], 'DEPLOYMENT_DRY_RUN')
        self.assertFalse((self.repo / 'domains/deployments').exists())

    def test_idempotent_deployment_preserves_receipt(self):
        record = self.deploy(); self.assertEqual(self.deploy(), record)

    def test_package_repeated_is_immutable(self):
        self.assertEqual(d.package(self.repo, 'unit', '1.0.0-test.1', 'TEST_ONLY', self.target, True)[1], self.package)
        self.runtime.write_text(self.runtime.read_text() + '\n')
        with self.assertRaisesRegex(ValueError, 'another payload'): d.package(self.repo, 'unit', '1.0.0-test.1', 'TEST_ONLY', self.target, True)

    def test_changed_factory_payload_rejected(self):
        source = self.repo / self.package['payloadRoot'] / 'One.json'; source.write_text(source.read_text() + '\n')
        with self.assertRaisesRegex(ValueError, 'hash changed'): self.deploy()

    def test_missing_testing_waiver_rejected(self):
        with self.assertRaisesRegex(ValueError, 'waiver'): d.deploy(self.repo, self.payload, self.evidence, write=True)

    def test_unknown_target_file_is_not_deleted(self):
        extra = self.target / 'Extra.json'; obj = d.read(self.runtime); obj['machine']['id'] = 'Extra'; extra.write_text(json.dumps(obj))
        with self.assertRaisesRegex(ValueError, 'Unapproved target'): self.deploy()
        self.assertTrue(extra.exists())

    def test_failed_post_copy_gate_rolls_back(self):
        before = self.runtime.read_bytes(); self.check_counts.side_effect = ValueError('synthetic gate failure')
        with self.assertRaisesRegex(ValueError, 'gate failure'): self.deploy()
        self.assertEqual(self.runtime.read_bytes(), before)
        self.assertFalse((self.repo / 'domains/deployments/unit/current.json').exists())

    def test_pointer_hash_tamper_rejected(self):
        self.deploy(); pointer = self.repo / 'domains/deployments/unit/current.json'; obj = d.read(pointer); obj['receiptSHA256'] = '0' * 64; pointer.write_text(json.dumps(obj))
        with self.assertRaisesRegex(ValueError, 'integrity'): self.deploy()

    def test_rehashed_false_production_claim_rejected(self):
        self.deploy(); folder = self.repo / 'domains/deployments/unit'
        receipt_path = folder / '1.0.0-test.1.json'; record = d.read(receipt_path); record['productionApproval'] = True; receipt_path.write_text(json.dumps(record))
        pointer_path = folder / 'current.json'; pointer = d.read(pointer_path); pointer['receiptSHA256'] = d.filehash(receipt_path); pointer['productionApproval'] = True; pointer_path.write_text(json.dumps(pointer))
        with self.assertRaisesRegex(ValueError, 'verified payload'): d.check_deployment(self.repo, 'unit', '1.0.0-test.1')

    def test_symlink_payload_rejected(self):
        source = self.repo / self.package['payloadRoot'] / 'One.json'; source.unlink(); source.symlink_to(self.runtime)
        with self.assertRaisesRegex(ValueError, 'only runtime'): self.deploy()

    def test_test_deployment_cannot_replace_accepted_domain(self):
        self.manifest.write_text(json.dumps({'domains': {'unit': {'status': 'accepted'}}}))
        with self.assertRaisesRegex(ValueError, 'cannot replace'): self.deploy()

    def test_test_payload_requires_test_version(self):
        with self.assertRaisesRegex(ValueError, 'prerelease'): d.package(self.repo, 'unit', '1.0.0', 'TEST_ONLY', self.target)

    def test_invalid_prerelease_version_rejected(self):
        for value in ['1.0.0-test..1', '1.0.0-test.01', '../1.0.0']:
            with self.subTest(version=value), self.assertRaises(ValueError): d.package(self.repo, 'unit', value, 'TEST_ONLY', self.target)

    def test_other_transition_evidence_rejected(self):
        evidence = d.read(self.evidence); evidence['countReconciliation']['transitionSHA256'] = 'wrong'; self.evidence.write_text(json.dumps(evidence))
        with self.assertRaisesRegex(ValueError, 'another corpus transition'): self.deploy()

    def test_production_cannot_use_test_receipt(self):
        path, _ = d.package(self.repo, 'unit', '1.0.0', 'PRODUCTION', self.target, True)
        self.manifest.write_text(json.dumps({'domains': {'unit': {'status': 'accepted'}}}))
        with self.assertRaisesRegex(ValueError, 'finalized domain approval'): d.deploy(self.repo, path, self.evidence, write=True)

    def git_approval_fixture(self):
        self.manifest.write_text(json.dumps({'domains': {'unit': {'status': 'accepted'}}}))
        def git(*args): return subprocess.check_output(['git', *args], cwd=self.repo, text=True).strip()
        git('init', '-q'); git('config', 'user.name', 'Synthetic deployment fixture'); git('config', 'user.email', 'fixture@example.invalid')
        git('add', '.'); git('commit', '-qm', 'synthetic approved revision')
        commit = git('rev-parse', 'HEAD')
        receipt = dict(domain='unit', version='1.0.0', mergeCommit=commit, tag='domain/unit/v1.0.0', machinesPR={'url': 'https://forge.invalid/pull/1', 'headRefOid': commit}, candidateMachines={'domains/unit/One.json': d.filehash(self.runtime)})
        original = a.cmd
        def command(argv, cwd=a.MACHINES):
            if argv[:2] == ['git', 'ls-remote']: return commit + '\trefs/tags/domain/unit/v1.0.0^{}'
            if argv[:2] == ['git', 'fetch']: return ''
            return original(argv, cwd)
        return receipt, command

    def test_production_inventory_is_checked_against_real_git_bytes(self):
        receipt, command = self.git_approval_fixture()
        with patch.object(a, 'merged_pr', return_value={'mergeCommit': {'oid': receipt['mergeCommit']}}), patch.object(a, 'cmd', side_effect=command):
            a.verify_deployment_approval(self.repo, receipt)
            receipt['candidateMachines']['domains/unit/One.json'] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'approved Git revision'): a.verify_deployment_approval(self.repo, receipt)

    def test_production_partial_inventory_is_rejected(self):
        receipt, command = self.git_approval_fixture(); receipt['candidateMachines'] = {}
        with patch.object(a, 'merged_pr', return_value={'mergeCommit': {'oid': receipt['mergeCommit']}}), patch.object(a, 'cmd', side_effect=command):
            with self.assertRaisesRegex(ValueError, 'omits or adds'): a.verify_deployment_approval(self.repo, receipt)


if __name__ == '__main__': unittest.main()
