#!/usr/bin/env python3
"""Local contract tests for agent-ready RealityEngine machine definitions."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
MACHINES_ROOT = REPO_ROOT / "machines"
SAMPLE_AGENT_MACHINE = MACHINES_ROOT / "AGX001_aquaculture-water-quality-stability.json"
SAMPLE_OBSERVE_MACHINE = MACHINES_ROOT / "AGX016_aquaculture-energy-backup-readiness.json"


def load_json(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        return json.load(handle)


def machine_files() -> list[Path]:
    return sorted(MACHINES_ROOT.rglob("*.json"))


def metadata(path: Path) -> dict[str, Any]:
    return load_json(path).get("machine", {}).get("metadata", {})


class AgentContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = load_json(REPO_ROOT / "domains" / "domain-registry.json")
        cls.machine_class_schema = load_json(REPO_ROOT / "schemas" / "machine-class.schema.json")
        cls.agent_ready_schema = load_json(REPO_ROOT / "schemas" / "agent-ready-machine-class.schema.json")
        cls.autonomy_schema = load_json(REPO_ROOT / "schemas" / "autonomy-policy.schema.json")
        cls.files = machine_files()
        cls.machines = [(path, load_json(path).get("machine", {})) for path in cls.files]

    def test_agent_ready_class_catalog_is_complete_and_ordered(self) -> None:
        schema_classes = set(self.machine_class_schema["enum"])
        described_classes = set(self.registry["machineClasses"])
        contract_classes = set(self.registry["agentReadyMachineClasses"])

        self.assertEqual(schema_classes, described_classes)
        self.assertEqual(schema_classes, contract_classes)

        stages = [
            contract["workflowStage"]
            for contract in self.registry["agentReadyMachineClasses"].values()
        ]
        self.assertEqual(len(stages), len(set(stages)), "workflow stages must be unique")
        self.assertEqual(min(stages), 1)

        for machine_class, contract in self.registry["agentReadyMachineClasses"].items():
            with self.subTest(machineClass=machine_class):
                self.assertIn(contract["stageName"], {
                    "ingest-normalize",
                    "detect-state",
                    "predict-risk",
                    "dispatch-agent",
                    "watch-recovery",
                    "route-governance",
                    "project-range",
                    "apply-safety-gate",
                    "capture-evidence",
                    "optimize-action",
                })
                self.assertTrue(contract["allowedAutonomyModes"])
                self.assertTrue(contract["allowedWriteBackTypes"])
                self.assertLessEqual(set(contract["emitsTo"]), schema_classes)

    def test_agent_dispatcher_class_is_exactly_agent_bound_corpus(self) -> None:
        class_counts: Counter[str] = Counter()
        agent_bound_counts: Counter[str] = Counter()
        exceptions: list[str] = []

        for path, machine in self.machines:
            md = machine.get("metadata", {})
            machine_class = md.get("machineClass")
            class_counts[machine_class] += 1
            if isinstance(md.get("agentBinding"), dict):
                agent_bound_counts[machine_class] += 1
                if machine_class != "agent-dispatcher":
                    exceptions.append(str(path.relative_to(REPO_ROOT)))
            if machine_class == "agent-dispatcher" and not isinstance(md.get("agentBinding"), dict):
                exceptions.append(str(path.relative_to(REPO_ROOT)))

        self.assertFalse(exceptions, "\n".join(exceptions))
        self.assertEqual(class_counts["agent-dispatcher"], agent_bound_counts["agent-dispatcher"])
        self.assertEqual(agent_bound_counts["agent-dispatcher"], 1055)

    def test_agent_binding_autonomy_policy_matches_registry(self) -> None:
        registry_policy = self.registry["autonomyPolicy"]
        checked = 0

        for path, machine in self.machines:
            binding = machine.get("metadata", {}).get("agentBinding")
            if not isinstance(binding, dict):
                continue
            checked += 1
            mode = binding.get("mode")
            expected_policy = {"mode": mode, **registry_policy[mode]}
            risk_controls = binding.get("riskControls", {})

            with self.subTest(machine=str(path.relative_to(REPO_ROOT)), mode=mode):
                self.assertEqual(binding.get("autonomyPolicy"), expected_policy)
                self.assertEqual(binding.get("writeBack", {}).get("type"), expected_policy["writeBackType"])
                self.assertEqual(risk_controls.get("requiresHumanApproval"), expected_policy["requiresHumanApproval"])
                self.assertEqual(risk_controls.get("requiresRunbook"), expected_policy["requiresRunbook"])
                self.assertEqual(risk_controls.get("maxAutonomy"), mode)
                self.assertEqual(risk_controls.get("blockedWhenRag"), expected_policy["blockedWhenRag"])

        self.assertEqual(checked, 1055)

    def test_non_observe_writeback_is_pe_sensor_and_observe_has_none(self) -> None:
        observe_count = 0
        pe_sensor_count = 0

        for path, machine in self.machines:
            binding = machine.get("metadata", {}).get("agentBinding")
            if not isinstance(binding, dict):
                continue
            mode = binding["mode"]
            write_back = binding["writeBack"]

            with self.subTest(machine=str(path.relative_to(REPO_ROOT)), mode=mode):
                if mode == "observe":
                    observe_count += 1
                    self.assertEqual(write_back, {"type": "none"})
                    continue

                pe_sensor_count += 1
                self.assertEqual(write_back["type"], "pe-sensor")
                self.assertEqual(write_back["provider"], "localai")
                self.assertEqual(write_back["ingest"]["endpoint"], "/api/integrations/completions")
                self.assertFalse(write_back["ingest"]["triggerPush"])
                self.assertTrue(write_back["ingest"]["compactPush"])
                self.assertEqual(write_back["sourceMapping"]["sensorId"], write_back["sensorId"])
                self.assertEqual(write_back["sourceMapping"]["ttlMs"], write_back["ttlMs"])
                self.assertEqual(write_back["sourceMapping"]["region"], write_back["region"])
                self.assertEqual(len(write_back["semantics"]), write_back["region"]["length"])

        self.assertGreater(observe_count, 0)
        self.assertGreater(pe_sensor_count, 0)

    def test_dispatch_envelope_builder_preserves_agent_contract(self) -> None:
        result = subprocess.run(
            ["python3", "scripts/build-dispatch-envelope.py", str(SAMPLE_AGENT_MACHINE)],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        envelope = json.loads(result.stdout)
        sample_md = metadata(SAMPLE_AGENT_MACHINE)
        binding = sample_md["agentBinding"]

        self.assertEqual(envelope["schemaVersion"], "1.0.0")
        self.assertEqual(envelope["envelopeType"], "ces.terminal.event")
        self.assertEqual(envelope["dispatch"]["agent"], binding["agent"])
        self.assertEqual(envelope["dispatch"]["autonomyMode"], binding["mode"])
        self.assertEqual(envelope["dispatch"]["writeBack"], binding["writeBack"])
        self.assertEqual(envelope["dispatch"]["endpoint"]["kind"], "graphql")
        self.assertEqual(envelope["dispatch"]["endpoint"]["mutation"], "updateProcessState")
        self.assertEqual(envelope["governance"]["ownerTeam"], sample_md["governance"]["ownerTeam"])

    def test_writeback_payload_builder_preserves_pe_sensor_contract(self) -> None:
        result = subprocess.run(
            ["python3", "scripts/build-writeback-completion.py", str(SAMPLE_AGENT_MACHINE)],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
        payload = json.loads(result.stdout)
        write_back = metadata(SAMPLE_AGENT_MACHINE)["agentBinding"]["writeBack"]

        self.assertEqual(payload["provider"], "localai")
        self.assertEqual(payload["sensorId"], write_back["sensorId"])
        self.assertEqual(payload["sourceMapping"], write_back["sourceMapping"])
        self.assertEqual(payload["ttlMs"], write_back["ttlMs"])
        self.assertEqual(payload["region"], write_back["region"])
        self.assertEqual(len(payload["values"]), write_back["region"]["length"])
        self.assertFalse(payload["triggerPush"])
        self.assertTrue(payload["compactPush"])

    def test_observe_machine_rejects_writeback_payload_generation(self) -> None:
        result = subprocess.run(
            ["python3", "scripts/build-writeback-completion.py", str(SAMPLE_OBSERVE_MACHINE)],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("agentBinding.writeBack.type is not pe-sensor", result.stderr)

    def test_audit_rejects_agent_dispatcher_without_agent_binding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            target = tmp_root / SAMPLE_AGENT_MACHINE.name
            shutil.copyfile(SAMPLE_AGENT_MACHINE, target)
            data = load_json(target)
            del data["machine"]["metadata"]["agentBinding"]
            target.write_text(json.dumps(data, indent=2) + "\n")

            result = subprocess.run(
                ["python3", "scripts/audit-corpus.py", "--machines-root", str(tmp_root)],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("legacy dispatchableAgent requires first-class metadata.agentBinding", result.stdout)
        self.assertIn("metadata.machineClass='agent-dispatcher' requires metadata.agentBinding", result.stdout)

    def test_audit_rejects_autonomy_policy_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            target = tmp_root / SAMPLE_AGENT_MACHINE.name
            shutil.copyfile(SAMPLE_AGENT_MACHINE, target)
            data = load_json(target)
            data["machine"]["metadata"]["agentBinding"]["autonomyPolicy"]["canExecuteActions"] = True
            target.write_text(json.dumps(data, indent=2) + "\n")

            result = subprocess.run(
                ["python3", "scripts/audit-corpus.py", "--machines-root", str(tmp_root)],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("metadata.agentBinding.autonomyPolicy.canExecuteActions", result.stdout)


if __name__ == "__main__":
    unittest.main()
