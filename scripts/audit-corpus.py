#!/usr/bin/env python3
"""Architecture-level corpus audit for RealityEngine machines.

The old validator only checked parseability, name, and non-empty sequences.
This audit keeps those hard gates, then adds compatibility warnings for the
new domain and agent contracts so the existing corpus can continue to load
while new domains get a stronger review path.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ALLOWED_BITS = {1, 2, 4, 8}
AUTONOMY_MODES = {"observe", "advise", "supervised-act", "automated-act"}
AUTONOMY_ORDER = {"observe": 0, "advise": 1, "supervised-act": 2, "automated-act": 3}
AUTONOMY_POLICY = {
    "observe": {
        "stage": 0,
        "writeBackType": "none",
        "canWriteBack": False,
        "canStageActions": False,
        "canExecuteActions": False,
        "requiresHumanApproval": False,
        "requiresRunbook": False,
        "blockedWhenRag": [],
    },
    "advise": {
        "stage": 1,
        "writeBackType": "pe-sensor",
        "canWriteBack": True,
        "canStageActions": False,
        "canExecuteActions": False,
        "requiresHumanApproval": False,
        "requiresRunbook": False,
        "blockedWhenRag": [],
    },
    "supervised-act": {
        "stage": 2,
        "writeBackType": "pe-sensor",
        "canWriteBack": True,
        "canStageActions": True,
        "canExecuteActions": False,
        "requiresHumanApproval": True,
        "requiresRunbook": True,
        "blockedWhenRag": ["RED"],
    },
    "automated-act": {
        "stage": 3,
        "writeBackType": "pe-sensor",
        "canWriteBack": True,
        "canStageActions": True,
        "canExecuteActions": True,
        "requiresHumanApproval": False,
        "requiresRunbook": True,
        "blockedWhenRag": ["AMBER", "RED"],
        "rollbackRequired": True,
    },
}
MACHINE_CLASSES = {
    "signal-monitor",
    "risk-forecaster",
    "agent-dispatcher",
    "outcome-stabilizer",
    "governance-escalator",
    "bridge",
    "sensor-preaggregator",
    "safety-compliance-checker",
    "evidence-archive",
    "optimizer",
}
LOCALAI_ENDPOINT = "http://localhost:4000/graphql"
LOCALAI_TEMPLATE = "triggers/graphql_trigger_template.py"
LOCALAI_DISPATCH_CONTRACT = {
    "target": "localAIStack",
    "transport": "graphql",
    "mutation": "updateProcessState",
    "envelopeSchema": "schemas/ai-trigger-envelope.schema.json",
    "schemaRef": "localAIStack/services/api/routers/graphql_endpoint.py",
}
LOCALAI_WRITEBACK_INGEST = {
    "endpoint": "/api/integrations/completions",
    "method": "POST",
    "triggerPush": False,
    "compactPush": True,
}


def as_object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def primary_domain(metadata: dict[str, Any]) -> str:
    tagging = as_object(metadata.get("tagging"))
    return str(
        tagging.get("primaryDomain")
        or metadata.get("category")
        or metadata.get("domain")
        or "missing"
    )


def load_domain_registry(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "domains" / "domain-registry.json"
    if not path.exists():
        return {}
    with path.open() as handle:
        data = json.load(handle)
    return as_object(data.get("domains"))


def load_registry_root(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "domains" / "domain-registry.json"
    if not path.exists():
        return {}
    with path.open() as handle:
        return as_object(json.load(handle))


def load_domain_manifest(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "domains" / "domain-manifest.json"
    if not path.exists():
        return {}
    with path.open() as handle:
        data = json.load(handle)
    return as_object(data.get("domains"))


def validate_domain_contracts(
    registry: dict[str, Any],
    manifest: dict[str, Any],
    domain_counts: Counter[str],
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not manifest:
        warnings.append("domains/domain-manifest.json is missing or has no domains")
        return errors, warnings

    if registry:
        registry_domains = set(registry)
        manifest_domains = set(manifest)
        for domain in sorted(registry_domains - manifest_domains):
            errors.append(f"domain {domain!r} is in domain-registry.json but missing from domain-manifest.json")
        for domain in sorted(manifest_domains - registry_domains):
            errors.append(f"domain {domain!r} is in domain-manifest.json but missing from domain-registry.json")

    for domain, entry in sorted(manifest.items()):
        if not isinstance(entry, dict):
            errors.append(f"domain manifest entry {domain!r} must be an object")
            continue
        for field in (
            "displayName",
            "status",
            "description",
            "sourceDataDefault",
            "peIngestPattern",
            "agentWorkflow",
        ):
            if not nonempty_string(entry.get(field)):
                errors.append(f"domain manifest {domain!r}.{field} must be a non-empty string")
        if entry.get("status") not in {"accepted", "experimental", "deprecated"}:
            errors.append(f"domain manifest {domain!r}.status must be accepted, experimental, or deprecated")
        if entry.get("defaultAutonomy") not in AUTONOMY_MODES:
            errors.append(f"domain manifest {domain!r}.defaultAutonomy must be one of {sorted(AUTONOMY_MODES)}")
        for field in ("codePrefixes", "requiredMachineClasses", "defaultAgentFamilies"):
            values = entry.get(field)
            if not isinstance(values, list) or not values or not all(nonempty_string(x) for x in values):
                errors.append(f"domain manifest {domain!r}.{field} must be a non-empty string array")
        for machine_class in as_list(entry.get("requiredMachineClasses")):
            if machine_class not in MACHINE_CLASSES:
                errors.append(f"domain manifest {domain!r}.requiredMachineClasses includes unknown class {machine_class!r}")
        expected_count = entry.get("currentMachineCount")
        if not isinstance(expected_count, int) or expected_count < 0:
            errors.append(f"domain manifest {domain!r}.currentMachineCount must be a non-negative integer")
        elif domain_counts.get(domain, 0) != expected_count:
            warnings.append(
                f"domain manifest {domain!r}.currentMachineCount={expected_count} "
                f"but corpus has {domain_counts.get(domain, 0)}"
            )

    for domain in sorted(set(domain_counts) - set(manifest)):
        if domain != "missing":
            warnings.append(f"corpus domain {domain!r} is not listed in domain-manifest.json")

    return errors, warnings


def validate_agent_ready_classes(registry_root: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    class_descriptions = as_object(registry_root.get("machineClasses"))
    class_contracts = as_object(registry_root.get("agentReadyMachineClasses"))
    if not class_contracts:
        return ["domains/domain-registry.json.agentReadyMachineClasses is required"]

    described_classes = set(class_descriptions)
    contract_classes = set(class_contracts)
    if described_classes != MACHINE_CLASSES:
        errors.append("domains/domain-registry.json.machineClasses must match the standard class catalog")
    for machine_class in sorted(MACHINE_CLASSES - contract_classes):
        errors.append(f"agent-ready contract missing for machine class {machine_class!r}")
    for machine_class in sorted(contract_classes - MACHINE_CLASSES):
        errors.append(f"agent-ready contract includes unknown machine class {machine_class!r}")

    stages: Counter[int] = Counter()
    for machine_class, contract in sorted(class_contracts.items()):
        if machine_class not in MACHINE_CLASSES:
            continue
        if not isinstance(contract, dict):
            errors.append(f"agent-ready contract {machine_class!r} must be an object")
            continue
        stage = contract.get("workflowStage")
        if not isinstance(stage, int) or stage <= 0:
            errors.append(f"agent-ready contract {machine_class!r}.workflowStage must be a positive integer")
        else:
            stages[stage] += 1
        for field in ("stageName", "role", "inputContract", "outputContract"):
            if not nonempty_string(contract.get(field)):
                errors.append(f"agent-ready contract {machine_class!r}.{field} must be a non-empty string")
        for field in (
            "requiresGovernance",
            "requiresTriggerConfig",
            "requiresInputSemantics",
            "requiresSensorNormalization",
            "requiresAgentBinding",
        ):
            if not isinstance(contract.get(field), bool):
                errors.append(f"agent-ready contract {machine_class!r}.{field} must be boolean")
        modes = contract.get("allowedAutonomyModes")
        if not isinstance(modes, list) or not modes or not all(mode in AUTONOMY_MODES for mode in modes):
            errors.append(f"agent-ready contract {machine_class!r}.allowedAutonomyModes must be a non-empty autonomy mode array")
        writebacks = contract.get("allowedWriteBackTypes")
        if (
            not isinstance(writebacks, list)
            or not writebacks
            or not all(item in {"none", "pe-sensor", "pe-domain-vector"} for item in writebacks)
        ):
            errors.append(f"agent-ready contract {machine_class!r}.allowedWriteBackTypes must be a non-empty write-back type array")
        emits_to = contract.get("emitsTo")
        if not isinstance(emits_to, list) or not all(item in MACHINE_CLASSES for item in emits_to):
            errors.append(f"agent-ready contract {machine_class!r}.emitsTo must be a machine-class array")
        if machine_class == "agent-dispatcher" and contract.get("requiresAgentBinding") is not True:
            errors.append("agent-dispatcher must require metadata.agentBinding")
        if machine_class != "agent-dispatcher" and contract.get("requiresAgentBinding") is True:
            errors.append(f"{machine_class!r} must not require metadata.agentBinding")

    for stage, count in stages.items():
        if count > 1:
            errors.append(f"agent-ready workflowStage {stage} is assigned to more than one class")
    return errors


def validate_region(region: Any, label: str, errors: list[str]) -> tuple[int, int] | None:
    if not isinstance(region, dict):
        errors.append(f"perceptualMapping.{label} must be an object")
        return None
    offset = region.get("offset")
    length = region.get("length")
    if not isinstance(offset, int) or offset < 0:
        errors.append(f"perceptualMapping.{label}.offset must be a non-negative integer")
    if not isinstance(length, int) or length <= 0:
        errors.append(f"perceptualMapping.{label}.length must be a positive integer")
    if isinstance(offset, int) and isinstance(length, int) and offset >= 0 and length > 0:
        return offset, length
    return None


def validate_agent_binding(binding: Any, errors: list[str], warnings: list[str]) -> None:
    if not isinstance(binding, dict):
        errors.append("metadata.agentBinding must be an object when present")
        return
    if not nonempty_string(binding.get("agent")):
        errors.append("metadata.agentBinding.agent must be a non-empty string")
    mode = binding.get("mode")
    if mode not in AUTONOMY_MODES:
        errors.append(f"metadata.agentBinding.mode must be one of {sorted(AUTONOMY_MODES)}")
    policy = as_object(binding.get("autonomyPolicy"))
    expected_policy = AUTONOMY_POLICY.get(mode)
    if not policy:
        errors.append("metadata.agentBinding.autonomyPolicy must be an object")
    elif expected_policy:
        for key, expected in expected_policy.items():
            if policy.get(key) != expected:
                errors.append(f"metadata.agentBinding.autonomyPolicy.{key} must be {expected!r} for mode {mode!r}")
        if policy.get("mode") != mode:
            errors.append("metadata.agentBinding.autonomyPolicy.mode must match metadata.agentBinding.mode")
    allowed_actions = binding.get("allowedActions")
    if not isinstance(allowed_actions, list) or not all(nonempty_string(x) for x in allowed_actions):
        errors.append("metadata.agentBinding.allowedActions must be a non-empty string array")
    write_back = binding.get("writeBack")
    if not isinstance(write_back, dict):
        errors.append("metadata.agentBinding.writeBack must be an object")
    else:
        wb = as_object(write_back)
        wb_type = wb.get("type")
        if wb_type not in {"pe-sensor", "pe-domain-vector", "none"}:
            errors.append("metadata.agentBinding.writeBack.type must be pe-sensor, pe-domain-vector, or none")
        if mode == "observe" and wb_type != "none":
            errors.append("observe metadata.agentBinding.writeBack must be type=none")
        if mode != "observe" and wb_type == "none":
            errors.append("non-observe metadata.agentBinding.writeBack must return through PE, not type=none")
        if expected_policy and wb_type != expected_policy["writeBackType"]:
            errors.append(
                f"metadata.agentBinding.writeBack.type must be {expected_policy['writeBackType']!r} "
                f"for mode {mode!r}"
            )
        if wb_type == "pe-sensor":
            if wb.get("provider") != "localai":
                errors.append("metadata.agentBinding.writeBack.provider must be 'localai'")
            if not nonempty_string(wb.get("sensorId")):
                errors.append("metadata.agentBinding.writeBack.sensorId is required for pe-sensor write-back")
            if not nonempty_string(wb.get("name")):
                errors.append("metadata.agentBinding.writeBack.name is required for pe-sensor write-back")
            if wb.get("normalization") not in {"already-normalized-0-1", "one-hot", "binary", "scalar-risk"}:
                errors.append("metadata.agentBinding.writeBack.normalization is invalid")
            if not isinstance(wb.get("ttlMs"), int) or wb.get("ttlMs") <= 0:
                errors.append("metadata.agentBinding.writeBack.ttlMs must be a positive integer")
            ingest = as_object(wb.get("ingest"))
            for key, expected in LOCALAI_WRITEBACK_INGEST.items():
                if ingest.get(key) != expected:
                    errors.append(f"metadata.agentBinding.writeBack.ingest.{key} must be {expected!r}")
            source_mapping = as_object(wb.get("sourceMapping"))
            if not nonempty_string(source_mapping.get("id")):
                errors.append("metadata.agentBinding.writeBack.sourceMapping.id is required")
            if source_mapping.get("sensorId") != wb.get("sensorId"):
                errors.append("metadata.agentBinding.writeBack.sourceMapping.sensorId must match writeBack.sensorId")
            if source_mapping.get("ttlMs") != wb.get("ttlMs"):
                errors.append("metadata.agentBinding.writeBack.sourceMapping.ttlMs must match writeBack.ttlMs")
            validate_region(source_mapping.get("region"), "agentBinding.writeBack.sourceMapping.region", errors)
        if wb_type in {"pe-sensor", "pe-domain-vector"}:
            validate_region(wb.get("region"), "agentBinding.writeBack.region", errors)
            semantics = wb.get("semantics")
            if semantics is not None and (
                not isinstance(semantics, list)
                or not all(nonempty_string(item) for item in semantics)
                or (isinstance(wb.get("region"), dict) and len(semantics) != wb["region"].get("length"))
            ):
                errors.append("metadata.agentBinding.writeBack.semantics must match writeBack.region.length when present")
    risk_controls = binding.get("riskControls")
    if not isinstance(risk_controls, dict):
        errors.append("metadata.agentBinding.riskControls must be an object")
    else:
        if not isinstance(risk_controls.get("requiresHumanApproval"), bool):
            errors.append("metadata.agentBinding.riskControls.requiresHumanApproval must be boolean")
        if not isinstance(risk_controls.get("requiresRunbook"), bool):
            errors.append("metadata.agentBinding.riskControls.requiresRunbook must be boolean")
        if risk_controls.get("maxAutonomy") not in AUTONOMY_MODES:
            errors.append("metadata.agentBinding.riskControls.maxAutonomy must be a valid autonomy mode")
        elif mode in AUTONOMY_ORDER and AUTONOMY_ORDER[risk_controls.get("maxAutonomy")] < AUTONOMY_ORDER[mode]:
            errors.append("metadata.agentBinding.riskControls.maxAutonomy cannot be less permissive than mode")
        blocked = risk_controls.get("blockedWhenRag")
        if not isinstance(blocked, list) or not all(x in {"GREEN", "AMBER", "RED"} for x in blocked):
            errors.append("metadata.agentBinding.riskControls.blockedWhenRag must be a RAG code array")
        if expected_policy:
            if risk_controls.get("requiresHumanApproval") != expected_policy["requiresHumanApproval"]:
                errors.append("metadata.agentBinding.riskControls.requiresHumanApproval does not match autonomy policy")
            if risk_controls.get("requiresRunbook") != expected_policy["requiresRunbook"]:
                errors.append("metadata.agentBinding.riskControls.requiresRunbook does not match autonomy policy")
            if risk_controls.get("maxAutonomy") != mode:
                errors.append("metadata.agentBinding.riskControls.maxAutonomy must match metadata.agentBinding.mode")
            if blocked != expected_policy["blockedWhenRag"]:
                errors.append("metadata.agentBinding.riskControls.blockedWhenRag does not match autonomy policy")


def validate_dispatch_contract(metadata: dict[str, Any], errors: list[str]) -> None:
    if not metadata.get("agentBinding"):
        return
    trigger_config = as_object(metadata.get("triggerConfig"))
    if not nonempty_string(trigger_config.get("processId")):
        errors.append("metadata.triggerConfig.processId is required for localAIStack dispatch")
    if not nonempty_string(trigger_config.get("processName")):
        errors.append("metadata.triggerConfig.processName is required for localAIStack dispatch")
    if trigger_config.get("endpoint") != LOCALAI_ENDPOINT:
        errors.append(f"metadata.triggerConfig.endpoint must be {LOCALAI_ENDPOINT!r} for localAIStack dispatch")
    if trigger_config.get("template") != LOCALAI_TEMPLATE:
        errors.append(f"metadata.triggerConfig.template must be {LOCALAI_TEMPLATE!r} for localAIStack dispatch")
    dispatch = as_object(trigger_config.get("dispatch"))
    for key, expected in LOCALAI_DISPATCH_CONTRACT.items():
        if dispatch.get(key) != expected:
            errors.append(f"metadata.triggerConfig.dispatch.{key} must be {expected!r}")


def validate_machine_class(
    metadata: dict[str, Any],
    agent_ready_classes: dict[str, Any],
    errors: list[str],
    warnings: list[str],
) -> None:
    value = metadata.get("machineClass")
    if value is None:
        warnings.append("metadata.machineClass missing; classify as signal-monitor/risk-forecaster/agent-dispatcher/etc.")
        return
    if value not in MACHINE_CLASSES:
        warnings.append(f"metadata.machineClass={value!r} is not in the standard class catalog")
        return
    contract = as_object(agent_ready_classes.get(value))
    if not contract:
        errors.append(f"metadata.machineClass={value!r} has no agent-ready class contract")
        return
    if contract.get("requiresAgentBinding") and not isinstance(metadata.get("agentBinding"), dict):
        errors.append(f"metadata.machineClass={value!r} requires metadata.agentBinding")
    binding = as_object(metadata.get("agentBinding"))
    if binding:
        mode = binding.get("mode")
        write_back = as_object(binding.get("writeBack"))
        if mode not in as_list(contract.get("allowedAutonomyModes")):
            errors.append(f"metadata.agentBinding.mode={mode!r} is not allowed for machineClass {value!r}")
        if write_back.get("type") not in as_list(contract.get("allowedWriteBackTypes")):
            errors.append(
                f"metadata.agentBinding.writeBack.type={write_back.get('type')!r} "
                f"is not allowed for machineClass {value!r}"
            )
        if value != "agent-dispatcher":
            warnings.append("metadata.agentBinding present on a non-dispatcher machineClass")
    if contract.get("requiresSensorNormalization") and "sensorNormalization" not in metadata:
        warnings.append(f"metadata.machineClass={value!r} expects metadata.sensorNormalization")


def audit_machine(
    path: Path,
    registry: dict[str, Any],
    agent_ready_classes: dict[str, Any],
) -> tuple[list[str], list[str], dict[str, Any]]:
    errors: list[str] = []
    warnings: list[str] = []
    facts: dict[str, Any] = {}
    try:
        with path.open() as handle:
            root = json.load(handle)
    except json.JSONDecodeError as exc:
        return [f"INVALID_JSON: {exc}"], warnings, facts

    machine = as_object(root.get("machine"))
    if not machine:
        errors.append("top-level machine object missing or not an object")
        return errors, warnings, facts

    name = machine.get("name")
    if not nonempty_string(name):
        errors.append("machine.name must be a non-empty string")
    if not nonempty_string(machine.get("description")):
        errors.append("machine.description must be a non-empty string")

    metadata = as_object(machine.get("metadata"))
    if not metadata:
        errors.append("machine.metadata must be an object")

    sequences = as_list(machine.get("sequences"))
    if not sequences:
        errors.append("machine.sequences must be a non-empty array")
    sequence_ids = {seq.get("id") for seq in sequences if isinstance(seq, dict)}

    mapping = as_object(machine.get("perceptualMapping"))
    if not mapping:
        errors.append("machine.perceptualMapping must be an object")
    input_region = validate_region(mapping.get("input"), "input", errors)
    output_region = validate_region(mapping.get("output"), "output", errors)
    bits = mapping.get("bitsPerElement")
    if bits not in ALLOWED_BITS:
        errors.append("perceptualMapping.bitsPerElement must be one of 1, 2, 4, 8")

    domain = primary_domain(metadata)
    facts["domain"] = domain
    facts["bits"] = bits
    facts["agent"] = metadata.get("dispatchableAgent")
    facts["hasAgentBinding"] = isinstance(metadata.get("agentBinding"), dict)

    if domain == "missing":
        errors.append("metadata.tagging.primaryDomain, metadata.category, or metadata.domain is required")
    elif registry and domain not in registry:
        warnings.append(f"domain {domain!r} is not registered in domains/domain-registry.json")

    if "governance" not in metadata:
        errors.append("metadata.governance is required")
    if "triggerConfig" not in metadata:
        errors.append("metadata.triggerConfig is required")

    trigger_config = as_object(metadata.get("triggerConfig"))
    rules = as_list(trigger_config.get("rules"))
    if trigger_config and not rules:
        errors.append("metadata.triggerConfig.rules must be a non-empty array")
    for idx, rule in enumerate(rules):
        if not isinstance(rule, dict):
            errors.append(f"triggerConfig.rules[{idx}] must be an object")
            continue
        sid = rule.get("sequenceId")
        if sid not in sequence_ids:
            errors.append(f"triggerConfig.rules[{idx}].sequenceId does not match a machine sequence")
        if not isinstance(rule.get("outputMatches"), list):
            errors.append(f"triggerConfig.rules[{idx}].outputMatches must be an array")
        if rule.get("ragStatusCode") not in {"GREEN", "AMBER", "RED"}:
            errors.append(f"triggerConfig.rules[{idx}].ragStatusCode must be GREEN, AMBER, or RED")

    input_semantics = metadata.get("inputSemantics")
    if input_semantics is not None:
        if not isinstance(input_semantics, list) or not all(nonempty_string(x) for x in input_semantics):
            errors.append("metadata.inputSemantics must be a string array when present")
        elif input_region and len(input_semantics) != input_region[1]:
            warnings.append("metadata.inputSemantics length does not match perceptualMapping.input.length")
    else:
        warnings.append("metadata.inputSemantics missing")

    if "sensorNormalization" in metadata and not isinstance(metadata.get("sensorNormalization"), dict):
        errors.append("metadata.sensorNormalization must be an object when present")

    if metadata.get("dispatchableAgent") and not metadata.get("agentBinding"):
        errors.append("legacy dispatchableAgent requires first-class metadata.agentBinding")
    if metadata.get("agentBinding"):
        validate_agent_binding(metadata.get("agentBinding"), errors, warnings)
        validate_dispatch_contract(metadata, errors)

    validate_machine_class(metadata, agent_ready_classes, errors, warnings)

    if output_region and bits == 1:
        # Binary output machines are expected to be one-hot/multi-hot CES emitters.
        # The exact vector semantics live in outputVectors, so this remains a warning.
        if output_region[1] > 16:
            warnings.append("1-bit output region is unusually wide; verify output semantics are explicit")

    return errors, warnings, facts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--machines-root", default="machines")
    parser.add_argument("--strict", action="store_true", help="treat compatibility warnings as failures")
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    machines_root = Path(args.machines_root)
    if not machines_root.is_absolute():
        machines_root = repo_root / machines_root
    registry_root = load_registry_root(repo_root)
    registry = as_object(registry_root.get("domains"))
    agent_ready_classes = as_object(registry_root.get("agentReadyMachineClasses"))
    manifest = load_domain_manifest(repo_root)
    files = sorted(machines_root.rglob("*.json"))

    errors_by_file: dict[str, list[str]] = {}
    warnings_by_file: dict[str, list[str]] = {}
    domains: Counter[str] = Counter()
    bits: Counter[str] = Counter()
    agents: Counter[str] = Counter()
    agent_binding_count = 0

    for path in files:
        errors, warnings, facts = audit_machine(path, registry, agent_ready_classes)
        rel = str(path.relative_to(machines_root))
        if errors:
            errors_by_file[rel] = errors
        if warnings:
            warnings_by_file[rel] = warnings
        if facts.get("domain"):
            domains[str(facts["domain"])] += 1
        if facts.get("bits") is not None:
            bits[str(facts["bits"])] += 1
        if facts.get("agent"):
            agents[str(facts["agent"])] += 1
        if facts.get("hasAgentBinding"):
            agent_binding_count += 1

    contract_errors, contract_warnings = validate_domain_contracts(registry, manifest, domains)
    contract_errors.extend(validate_agent_ready_classes(registry_root))
    if contract_errors:
        errors_by_file["domains/domain-manifest.json"] = contract_errors
    if contract_warnings:
        warnings_by_file["domains/domain-manifest.json"] = contract_warnings

    if not args.summary_only:
        for rel in sorted(errors_by_file):
            print(f"ERROR {rel}")
            for item in errors_by_file[rel]:
                print(f"  - {item}")
        for rel in sorted(warnings_by_file)[:50]:
            print(f"WARN  {rel}")
            for item in warnings_by_file[rel][:5]:
                print(f"  - {item}")
        if len(warnings_by_file) > 50:
            print(f"WARN  ... {len(warnings_by_file) - 50} more files with compatibility warnings")

    print("Corpus audit summary")
    print(f"  machineFiles: {len(files)}")
    print(f"  errors:       {sum(len(v) for v in errors_by_file.values())} across {len(errors_by_file)} files")
    print(f"  warnings:     {sum(len(v) for v in warnings_by_file.values())} across {len(warnings_by_file)} files")
    print(f"  bits:         {dict(sorted(bits.items()))}")
    print(f"  domains:      {dict(domains.most_common())}")
    print(f"  agents:       {sum(agents.values())} bindings across {len(agents)} legacy dispatchableAgent ids")
    print(f"  agentBinding: {agent_binding_count} first-class bindings")

    if errors_by_file:
        return 1
    if args.strict and warnings_by_file:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
