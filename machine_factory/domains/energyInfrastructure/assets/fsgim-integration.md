# ASHRAE 201 as the energy-asset integration context

The owner selected ANSI/ASHRAE/NEMA Standard 201-2016 (RA2026), Facility Smart Grid Information Model (FSGIM), as the integration context for all appropriate energy-related assets, including the OPC Foundation Device Integration NodeSet. It is recorded as OP23 in the [standards inventory](../standards-inventory.json), bringing the current inventory to 47 entries. ASHRAE's [2026 publication notice](https://www.ashrae.org/file%20library/technical%20resources/standards%20and%20guidelines/standards%20actions/sa-feb_6_2026.pdf) confirms the reaffirmation. The original 46-entry issue/research snapshots remain historical publication evidence.

## Integration contract

[The machine-readable context](fsgim-integration-context.json) supplies explicit dispositions for all 19 reference asset roles, all 112 SunSpec model templates and all 58 DI type templates. New roles or class/resource catalogs must receive an integration-context disposition; unknown catalogs fail the context coverage check. This enforces a common context without collapsing source-specific models or claiming class equivalence.

FSGIM expresses energy behavior through device/component composition. Project projections use Device, Load, Generator, Meter and the energy-manager EM concept. Electrical consumers such as HVAC, lighting, industrial and ICT equipment can use load patterns; electrical sources use generator patterns; managers coordinate functions and meter boundaries. Passive distribution/protection assets retain device/topology context. Fuel, thermal, weather, market, carbon and threat semantics require explicit support models or extensions where appropriate; they are not silently invented FSGIM classes.

Storage exposes charge Load and discharge Generator roles on the same equipment identity. EV/EVSE generation is conditional on actual bidirectional capability and a reviewed profile. PV, storage and EV conversion-chain views share accounting groups, with explicit electrical boundaries and aggregation rules required to prevent double counting. Unmeasured supporting-device losses or consumption are not assumed to be zero.

The OPC UA DI bridge supplies identity, nameplate, capability and topology facets within this context. Native namespace URIs, NodeIds, units, data types, inheritance, modelling rules and source semantics remain intact. A generic DI DeviceType does not itself determine a FSGIM function, and its abstract definition cannot be instantiated directly. FSGIM, DI and project asset identifiers remain distinct, linked by reviewed instance bindings and identity evidence. Candidate member names such as Manufacturer, Model and SerialNumber are not asserted as verified FSGIM property equivalences.

## Sources and authority

[The source receipt](fsgim-source-receipt.json) distinguishes three authorities:

- The selected reaffirmed standard and its official normative UML/model archive. ASHRAE's [public model listing](https://data.ashrae.org/standard201/) publishes an Apache-2.0 license. The archive download returned HTTP 403 with a browser challenge; no archive hash or collection is claimed. The published [2018 errata](https://www.ashrae.org/file%20library/technical%20resources/standards%20and%20guidelines/standards%20errata/standards/201-2016errata-1-17-2018-.pdf) states that the model artifacts were updated. Exact reaffirmation/errata equivalence remains unverified.
- A [supplementary SHACL implementation](https://github.com/steveraysteveray/fsgim-shacl/tree/1759521d70e8535fdd261f2f6e53cb97079db1af), pinned to commit `1759521d70e8535fdd261f2f6e53cb97079db1af` with its BSD-3-Clause license and original README. It reports translation differences from UML. The retained explicit-node variant supplies five source class IRI anchors; those IRIs are implementation identifiers, not normative standard identifiers. No complete RDF/SHACL validation or equivalence proof is claimed.
- A restricted historical review draft was identified locally. It was not copied into this public package, indexed or used for normative mapping assertions.

The [generator](../tools/build_fsgim_context.py) verifies source hashes and the selected class declarations. It performs a deliberately narrow, source-pinned declaration lookup, not general Turtle parsing or SHACL reasoning. External ontology imports are not loaded. Source text remains data and cannot grant tool, control or admission authority.

## Carbon and safety

Electricity carbon intensity remains an explicit project extension, `urn:realityengine:energyInfrastructure:carbon-context:1`, connected to metered energy and energy-manager decisions. It is not asserted as a native FSGIM class/property. Required bindings include quantity/gas basis, electrical/geographic boundary, interval/timezone, location-based/market-based/marginal method, source version/rights, quality, freshness and uncertainty. Missing data means unknown, not zero. Carbon objectives cannot override protection, operating constraints or authentic approvals.

Generic fixture format 1.1.0 now requires an OP23 integration-context link. All three reference topology fixtures inherit it. The fixture validator rejects context-free 1.0.0 data and substituted context identifiers. Draft fixture validation is still not normative conformance or simulation execution.

```bash
python3 tools/build_fsgim_context.py --write
python3 tools/build_fsgim_context.py
node --test tools/test_asset_instances.mjs
```

## Remaining work and acceptance

R19 in the [RAG source inventory](../rag-source-manifest.json) tracks the normative Standard 201 model/text/errata collection and mapping review; there are now 19 source families. Supplementary source receipts do not fulfill that family or authorize indexing. Acquire and verify the official UML archive, preserve source rights, review exact class/property/multiplicity/unit and conformance-block mappings, then author typed asset/function instances and protocol adapters. Actual software, crypto, solver and admission evidence remain genuine, while all required hardware remains simulated and generic assets remain permitted in every case.

The current context is an owner-selected architecture with provisional project crosswalks. Normative equivalence remains false, control actions remain denied and all 43 behavioral acceptance cases remain NOT_RUN. EI04 stays open; EI05 must carry this context into profile/peer selections and EI18 into simulated asset bindings.
