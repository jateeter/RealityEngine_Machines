# OPC UA Device Integration types in the FSGIM context

[The device class catalog](device-class-catalog.json) provides all 58 declared type templates from OPC Foundation's DI NodeSet: 42 ObjectTypes, two VariableTypes, nine DataTypes and five ReferenceTypes. These are distinct source-defined kinds; data and reference types are not presented as physical equipment classes. The source model is DI 1.05.0, published 2025-11-15, pinned to official repository commit `ed0b821f6a6f1f0c440c442ed95a9146ae8b7f8d`.

The DI declaration requires core 1.05.04 published 2025-01-08. The [source receipt](opcua-source-receipt.json) retains that exact core release from commit `dee199135d85a5cb0dc5db25e27228b1f9d7ea0d`, tag `UA-1.05.04-2025-01-08`, rather than substituting the newer core model. The [DI source](../intake/opcua-di/Opc.Ua.Di.NodeSet2.xml) and [required core source](../intake/opcua-di/Opc.Ua.NodeSet2.xml) remain unchanged with their file-embedded OPC Foundation MIT License 1.00 notices. Binary Git attributes preserve source bytes.

The [generator](../tools/build_device_templates.py) resolves namespace-qualified NodeIds, aliases, references, data types, parent links and Definition field types for all 447 DI declarations. It distinguishes equal numeric identifiers in different namespaces. It retains 1,539 references, full source attributes, XML value definitions, documentation links and source-node locators. All 58 templates preserve abstract flags, base/ancestor links, direct members, direct mandatory members, mandatory placeholders and implemented interface links. Supporting core definitions are dependency context, not complete core template coverage.

[ASHRAE 201 FSGIM](fsgim-integration.md) is the owner-selected integration context, identified by OP23. DI supplies equipment identity, nameplate/capability and topology facets; an asset instance's actual load, generator, meter or energy-manager behavior determines its FSGIM composition. A DeviceType is not automatically a Load, Meter or Generator. The source DeviceType is abstract and needs a concrete derived type before runtime instantiation. Identifiers remain scoped aliases; matching strings alone do not prove physical identity.

Source access/executable flags and software update/locking methods grant no project authority. Every template remains unbound, uses simulated required hardware for hardware roles, denies control actions and has no simulator version or execution receipt. Source values and enums are not project operating limits.

```bash
python3 tools/build_device_templates.py --write
python3 tools/build_device_templates.py
python3 -m unittest discover -s tools -p 'test_device_templates.py'
```

This delivery does not instantiate a UA server, register types, execute methods, verify endpoints/TLS, validate complete inherited runtime instances, approve safety/fault/uncertainty parameters or demonstrate stack conformance. DI formal type coverage is complete for this pinned file; OP17 remains partial for the complete selected OPC UA/core/companion and MQTT scope. EI04, EI05, EI06 and EI18 retain their remaining obligations.
