# RealityEngine_Machines

A collection of machines that represent the skills known to the RealityEngine.

## Architecture Contracts

This repository also owns the machine-domain constraints used to admit new
domains and agent-capable machines:

- [Architecture audit and agent workflow roadmap](docs/ARCHITECTURE_AUDIT.md)
- [Domain manifest](domains/domain-manifest.json)
- [Domain registry](domains/domain-registry.json)
- [Domain manifest schema](schemas/domain-manifest.schema.json)
- [Agent binding schema](schemas/agent-binding.schema.json)
- [Agent autonomy policy schema](schemas/autonomy-policy.schema.json)
- [Agent-ready machine class schema](schemas/agent-ready-machine-class.schema.json)
- [localAIStack write-back schema](schemas/localai-writeback.schema.json)
- [localAIStack completion write-back schema](schemas/localai-completion-writeback.schema.json)
- [RE to localAIStack dispatch envelope schema](schemas/ai-trigger-envelope.schema.json)
- [Machine class catalog](schemas/machine-class.schema.json)

Run the compatibility validator:

```bash
npm run validate
```

Run the local architecture contract tests:

```bash
npm run test:contracts
```

Run the stricter new-domain gate:

```bash
STRICT_DOMAIN_CONTRACT=1 npm run validate
```
