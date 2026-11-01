"""Synthetic small inventories exercise exact, hash-bound count transitions."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('corpus_transition', ROOT / 'scripts/corpus_contract.py')
c = importlib.util.module_from_spec(spec); spec.loader.exec_module(c)


class CorpusTransitions(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup); self.repo = Path(tmp.name)
        (self.repo / 'domains').mkdir()
        self.machine('base', 'Base')
        self.manifest({'base': 1, 'candidate': 0})
        members = c.inventory(self.repo)
        self.base = dict(schemaVersion='1.0.0', kind='PUBLISHED_BASELINE', contractRef='corpus-exit-v2.0', measuredCommit='synthetic-unit-fixture', members=members, counts=c.counts(members))
        self.fixture_counts = patch.object(c, 'BASE_COUNTS', self.base['counts']); self.fixture_counts.start(); self.addCleanup(self.fixture_counts.stop)
        c.write_transition(self.repo, self.base, None)

    def machine(self, domain, name, suffix=''):
        p = self.repo / 'machines/domains' / domain / (name + '.json'); p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({'machine': {'name': name, 'description': suffix, 'metadata': {}}})); return p

    def manifest(self, domains):
        (self.repo / 'domains/domain-manifest.json').write_text(json.dumps({'domains': {k: {'currentMachineCount': v, 'status': 'experimental'} for k, v in domains.items()}}))

    def addition(self):
        self.machine('candidate', 'Added'); self.manifest({'base': 1, 'candidate': 1})
        result, before = c.prepare(self.repo, 'candidate', '1.0.0', 'TEST_ONLY'); c.write_transition(self.repo, result, before); return result

    def test_exact_addition_passes(self):
        result = self.addition(); self.assertEqual(result['countDelta'], dict(machines=1, domains=1, agents=1, agentBindings=0, projections=0)); self.assertEqual(c.validate(self.repo), result)

    def test_unchanged_repeat_is_idempotent(self):
        result = self.addition(); self.assertEqual(c.prepare(self.repo, 'candidate', '1.0.0', 'TEST_ONLY'), (result, None))

    def test_unexplained_peer_change_rejected(self):
        self.machine('base', 'Base', 'unauthorized change')
        with self.assertRaisesRegex(ValueError, 'outside candidate'): c.prepare(self.repo, 'candidate', '1.0.0', 'TEST_ONLY')

    def test_extra_machine_after_preparation_rejected(self):
        self.addition(); self.machine('candidate', 'Unreviewed')
        with self.assertRaisesRegex(ValueError, 'reviewed transition'): c.validate(self.repo)

    def test_same_count_content_change_rejected(self):
        self.addition(); self.machine('candidate', 'Added', 'changed')
        with self.assertRaisesRegex(ValueError, 'reviewed transition'): c.validate(self.repo)

    def test_removal_is_explicit_negative_delta(self):
        self.addition(); (self.repo / 'machines/domains/candidate/Added.json').unlink(); self.manifest({'base': 1, 'candidate': 0})
        result, before = c.prepare(self.repo, 'candidate', '2.0.0', 'TEST_ONLY'); c.write_transition(self.repo, result, before)
        self.assertEqual(result['countDelta']['machines'], -1); self.assertEqual(c.validate(self.repo), result)

    def test_declared_count_tamper_rejected(self):
        result = self.addition(); result['counts']['machines'] += 1; c.write_transition(self.repo, result, None)
        with self.assertRaisesRegex(ValueError, 'counts'): c.validate(self.repo)

    def test_history_tamper_rejected(self):
        result = self.addition(); p = self.repo / 'domains/corpus-contracts' / (result['predecessorSHA256'] + '.json'); p.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'hash changed'): c.validate(self.repo)

    def test_false_approval_rejected(self):
        result = self.addition(); result['productionApproval'] = True; c.write_transition(self.repo, result, None)
        with self.assertRaisesRegex(ValueError, 'cannot grant approval'): c.validate(self.repo)

    def test_wrong_manifest_count_rejected(self):
        self.addition(); self.manifest({'base': 1, 'candidate': 2})
        with self.assertRaisesRegex(ValueError, 'manifest count'): c.validate(self.repo)


if __name__ == '__main__': unittest.main()
