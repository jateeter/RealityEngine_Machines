# Draft FSGIM asset/function bindings

The [generic projection](function-bindings/generic.json) and [three reference projections](function-bindings/) turn the owner-selected [ASHRAE 201 context](fsgim-integration.md) into typed, source-linked draft bindings. Each source asset receives one binding with its project identity, scoped source aliases, role disposition, inactive function projections, source DI type facet where appropriate, and accounting-group membership.

The official UML archive still returned HTTP 403 on the current recheck. These records use the existing provisional project crosswalk and supplementary class IRIs; they do not instantiate normative FSGIM Devices or satisfy all class/property/multiplicity requirements. They are not SHACL conformance results.

## Identity and type boundaries

Source aliases are exact `(sourceSystemId, namespaceUri, identifier)` tuples. Duplicate tuples across or within asset bindings fail validation, while distinct source systems/namespaces may reuse identifier strings. This is literal scoped uniqueness, not physical identity proof or complete OPC UA wire-identifier normalization. Type NodeIds are not equipment instance identifiers.

Physical supporting/device roles receive the abstract DI DeviceType as an identity facet. Its namespace-qualified class key and abstract flag must match the pinned catalog. Direct node instantiation, a registered concrete derived type and peer receipts remain explicitly absent. Software and external-service roles do not silently acquire physical DI facets; the external utility boundary remains a service/boundary role.

## Functions, modes and accounting

Storage has separate Load and Generator projections with CHARGING and DISCHARGING gates. Gate names are project profile values, not asserted FSGIM wire enumerations. Every function is inactive. EV/EVSE generation may be declared only with a generic bidirectional capability and remains an inactive draft awaiting reviewed operating/profile bindings. A capability declaration is not an operating approval.

PV, storage and EV conversion-chain members retain separate equipment identities but share accounting groups. Each group selects exactly one primary view; the validator rejects missing/duplicate groups, orphan or incomplete membership and a primary outside its group. Resource groups remain separate from the draft facility net-meter view, so they cannot be configured for addition to that net meter total. No power, energy, emissions or balance is calculated. Measurement bindings remain null.

The single meter role is provisionally selected as a PCC net meter under an explicit generic assumption requiring engineering review. This does not prove its topology, direction/sign, calibration, interval, quantity or physical boundary. The generator stops if a source fixture has multiple meter roles rather than guessing which one is the facility meter. Actual source readings, units/sign conversions, time windows and energy-balance oracles remain downstream work.

## Validation and reproduction

[The schema](fsgim-function-binding.schema.json) limits source links to the four published fixture paths. [The validator](../tools/validate_function_bindings.mjs) checks the exact source fixture hash and existing fixture validation before checking binding/role/function coverage, supplementary IRIs, mode gates, optional capability conditions, identities, type facets and accounting selections. All execution flags deny control and prohibit fabricated simulator/integration receipts.

```bash
python3 tools/build_function_bindings.py --write
python3 tools/build_function_bindings.py
node tools/validate_function_bindings.mjs assets/function-bindings/generic.json
node --test tools/test_function_bindings.mjs
```

[The generator](../tools/build_function_bindings.py) reproduces the four canonical project fixtures. Semantically valid alternative draft parameters still require deliberate source/policy changes and regenerated fixtures before publication. Successful validation means draft structure and project profile checks passed; no network, runtime node, solver, control, normative conformance or behavioral acceptance case executed. EI04, EI05, EI06 and EI18 retain the remaining obligations.
