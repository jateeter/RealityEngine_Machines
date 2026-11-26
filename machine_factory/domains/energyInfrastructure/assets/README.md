# EI04 public-model template delivery

This is a partial, reproducible asset-template library. It contains all 112 JSON models in the [SunSpec models snapshot](https://github.com/sunspec/models/tree/90b4a331dcca1d6eac69c1bead952fddcc5852e0), retained under [Apache-2.0](../intake/public-models/sunspec/LICENSE). Original JSON and its schema remain unmodified. The [source receipt](source-receipt.json) records hashes and the exact commit; the [catalog](asset-class-catalog.json) contains generated templates and dispositions for all 46 standards/framework entries.

A SunSpec information model can describe a function, measurement group or vendor extension. It is not necessarily a physical asset class. OP08 public snapshot coverage is complete; normative SunSpec, IEEE and IEC class coverage is not established. Upstream IEEE point annotations are preserved as related references, never promoted to normative equivalence or compliance.

Each template preserves the full group hierarchy, repeating-group metadata, every point definition, units, scale-factor references, enumerations, access and mandatory flags. JSON pointers locate individual points. A commit identifies the model edition; model file and pointer identify its source clause. These are public-model locators, not invented IEEE/IEC clause numbers.

Instantiation fields require explicit topology, authority, safety limits, uncertainty/fault models, simulator version and case bindings. Nulls and empty bindings are unresolved requirements, not operational defaults. RW flags grant no control authority. Commands need deterministic authorization, safety checks, approvals and readback. The library executes no controls, simulation, model inference or retrieval.

All required hardware remains simulated required hardware, and generic assets are permitted in every acceptance case. This delivery does not provide an executable simulator or genuine acceptance receipts. All 43 cases remain NOT_RUN. The existing planning status fields describe complete normative template delivery, which remains pending; this supplemental library records partial delivery separately.

Reproduce and check offline from this domain folder:

```bash
python3 tools/build_asset_templates.py --write
python3 tools/build_asset_templates.py
python3 -m unittest discover -s tools -p 'test_*.py'
python3 tools/seal_assets.py --write
python3 tools/verify_package.py --write-summary
```

EI04 remains open. For each associated applicable standard, freeze a lawful edition/profile, enumerate every class with actual clause references (or justify that it defines no taxonomy), create class-specific templates and reconcile cross-standard mappings. Review source rights separately from implementation licenses. The 46 coverage rows specify this remaining work. IEEE/IEC normative texts are still uncollected in the RAG source inventory. This snapshot is collected implementation material only; no RAG extraction, indexing or retrieval approval is asserted.

The catalog also provides 19 unbound generic role templates and seven generic document templates for topology, utility profiles, equipment capabilities, calibration, hazard analysis, operating procedures and evidence records. Every document permits all 43 cases; none contains a fabricated approval or execution result. Role-to-normative-class bindings, populated reviewed fixtures and actual simulated-hardware linkage remain pending. No real customer records or physical commissioning are prerequisites for corpus admission. Authentic software execution and admission approvals remain required.

## Generic instance validation

[The JSON Schema](asset-instance.schema.json) defines a synthetic fixture bundle; [the sample bundle](generic-instance-fixture.json) instantiates all 19 generic roles and seven document templates. All 43 cases are permitted, but none is executed. Unresolved document field values remain explicitly null with generic-assumption provenance. The topology is an isolated list of fixture assets with no electrical connectivity asserted. No populated safety envelope is supplied.

The [instance validator](../tools/validate_asset_instances.mjs) uses the repository's existing Ajv dependency. It checks schema shape, unique identities, required generic template coverage when requested, role/template consistency, topology and document asset references, authority-role references and case scope. Document field names must exactly match their template. Synthetic evidence cannot contain execution digests, observed readbacks, results or authentic review receipts. All command decisions remain DENY and simulator versions remain null.

Optional SunSpec point bindings identify an exact model template and source JSON pointer. The validator checks source units (`1` when absent), raw-register encoding, safe JSON integer ranges, float32 range, string byte capacity, listed enum values, constants and same-group scale-factor bindings. This is a selected point-binding check, not validation of a whole SunSpec device/model instance: mandatory-point completeness, repeating-group cardinality, wire addresses/encoders, sentinel interpretation and engineering-unit conversion remain pending. EUI/IP address types and 64-bit integers beyond JavaScript's safe integer range are explicitly rejected pending encoder support. No wire conformance or operating-limit claim follows from a valid fixture.

```bash
node tools/validate_asset_instances.mjs assets/generic-instance-fixture.json
node --test tools/test_asset_instances.mjs
```

Hosted corpus checks run the instance contract tests. Neither a schema-valid draft nor a successful validation result can authorize operations, populate simulation receipts or satisfy behavioral admission cases. Normative class coverage, complete reviewed operational-instance validation, protocol conformance and simulator linkage remain open in EI04 and downstream workstreams.

## Reference topology instances

[REF01 connected](reference-instances/ref01_connected.json), [REF02 island/restoration](reference-instances/ref02_island_restore.json) and [REF03 flexibility/EV](reference-instances/ref03_flex_ev.json) now instantiate the electrical connectivity already declared in the reference microgrid scope. Each includes exactly its scenario's role set and case scope, one local AC bus, and nine, nine or eleven undirected connections respectively. Selected point examples remain raw synthetic fixture values, not simulated device observations.

The instance validator requires exactly one topology document per reference scenario, complete asset/bus node coverage and exact expected connections. It rejects duplicate/reversed edges, self-edges, orphan endpoints, missing nodes, role/case drift and changed voltage assumptions. The 480 V line-to-line RMS base remains a chosen generic reference, not a normative limit. Grounding and normative class mappings remain unresolved/null. No impedance, phase detail, power-flow feasibility, protection coordination, operating approval or energized state is inferred from an edge.

```bash
python3 tools/build_reference_instances.py --write
python3 tools/build_reference_instances.py
node tools/validate_asset_instances.mjs assets/reference-instances/ref01_connected.json
node --test tools/test_asset_instances.mjs
```

The generator uses only the current checked-in scenario scope and generic fixture; package verification checks exact reproduction. Behavioral cases remain NOT_RUN. EI04, EI05 profile selection, EI06 safety envelopes and EI18 simulator linkage remain open as applicable.

## Threat information class templates

[SC16 threat information classes](threat-classes.md) add a pinned, licensed OASIS schema snapshot, 57 templates, 43 top-level object/container clause mappings and an offline synthetic bundle validator. STIX schemas are explicitly non-normative; TAXII and full normative coverage remain pending. No operational threat feed or control action executes.

## TAXII resource class templates

[SC16 TAXII resources](taxii-resources.md) now include the official unchanged standard HTML and rights/source receipt, nine resource templates, two supporting record templates, project schemas and a complete synthetic resource fixture set. This advances resource-table coverage; full protocol/prose review, peer integration and normative completion remain pending.


## Primary energy-asset integration context

[ASHRAE 201 FSGIM](fsgim-integration.md) is now the owner-selected context for appropriate energy assets. [OPC UA DI](device-types.md) adds 58 formal type templates and 447 source declarations, using the exact required core model. Context crosswalks preserve native semantics and cover all 19 roles and 170 SunSpec/DI type/model templates. The source and normative-equivalence gaps remain explicit.

## Draft asset/function bindings

[Typed FSGIM projections](function-bindings.md) now bind every asset in the generic and three reference fixtures to its draft role/function, scoped identity, optional DI type facet and accounting selection. Validation rejects incomplete/contradictory bindings and false execution claims. These remain inactive project projections, with normative, engineering and runtime verification pending.


## EI05 synthetic measurement semantics

[Four source-bound active-power snapshots](power-snapshots.md) now exercise exact decimal W/kW normalization, net-import-positive signs, selected FSGIM accounting boundaries, timestamp ordering, observation-time freshness and null-preserving quality exclusion. This is offline project-contract validation only. Native property/peer mappings, engineering review, energy/carbon balance, simulated required hardware behavior and corpus admission remain pending; all 43 behavioral cases remain NOT_RUN.


## EI05 offline SunSpec active-power subset

[The selected model 103/203 decoder and register replay](sunspec-power.md) now connect pinned W/W_SF definitions to draft FSGIM accounting views, preserving signed values, missing-value sentinels and exact decimal scale conversion. This is offline byte-level software evidence only. Secure peer pairs, native status/time mappings, full simulated device behavior, engineering review and admission remain pending; all 43 behavioral cases remain NOT_RUN.


## EI05 offline meter energy intervals

[Selected SunSpec import/export counters and exact interval differences](meter-energy.md) now provide separate synthetic Wh/kWh quantities linked to the draft facility PCC Meter. Missing data, resets/rollovers, scale changes and stale endpoints never become zero-energy assertions. This is an offline accounting prerequisite; no carbon factor, native peer, complete device simulation or admission is verified. All 43 behavioral cases remain NOT_RUN.
