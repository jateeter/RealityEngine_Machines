# Synthetic active-power snapshot contract

The [four synthetic snapshots](power-snapshots/) exercise project measurement semantics against the [draft FSGIM function bindings](function-bindings.md). They are a partial EI05 prerequisite for native profile integration. ASHRAE Standard 201 remains the energy-asset integration context; the property `project:activePower` is a project extension, not a claimed normative FSGIM property. The official UML collection and complete property/multiplicity review remain pending. OPC UA DI identity facets remain source type metadata, not actual equipment instances or measurement variables.

## Quantity, boundaries and signs

Each snapshot contains exactly one instantaneous active-power sample for the draft facility PCC net-meter view and every resource group's selected primary view. Conversion-chain secondary assets cannot substitute for their primary. Sample identities, boundary identities and scoped synthetic point identities must be unique. Source-projection paths are allowlisted and their exact bytes are SHA-256 bound; source function and topology validation runs first.

All boundaries use **net import/consumption positive**, export/generation negative. Integer source register values, a decimal scale exponent from -6 through 6, and W or kW units produce exact decimal watt strings using integer arithmetic. Decimal strings preserve precision beyond JavaScript's safe numeric range after scaling; raw registers must remain safe integers. A Load sample cannot normalize negative and a Generator sample cannot normalize positive. Meter readings permit either direction. Storage samples select one inactive Load or Generator function; there is only one snapshot per boundary, so concurrent charge/discharge contributions cannot be added. These are project profile conventions, not FSGIM wire enumerations.

The four examples use independent arbitrary sample magnitudes and do **not** assert a balanced microgrid. Facility net and resource views are separate observations, never an additive total. There is no interval energy integration, DC/AC loss calculation, emissions inference, tariff, state estimation, dispatch or hardware simulation.

## Time and quality

UTC timestamps have whole-second or millisecond precision. Source observation time must be no later than receipt, and receipt no later than the explicit evaluation time. Unparseable times and unsupported leap seconds fail the batch. This profile assumes aligned clocks; source clock uncertainty, clock synchronization and native status mappings require separate review before real adapter use. Freshness is inclusive at `maxAgeMs` and is evaluated from observation time, so a recent receipt cannot make an old reading fresh. The TTL is a generic fixture assumption, not an engineering-approved safety threshold.

GOOD requires a value. BAD, UNKNOWN, missing and stale values produce an ineligible observation with null normalized watts and explicit reasons. Unknown never becomes zero. A structurally valid snapshot can contain ineligible observations: PASS means the contract is valid, not that every measurement is usable. Structural, source, identity, sign or timestamp errors invalidate every observation in the batch. Eligibility means only that a **synthetic** sample satisfies this offline profile; it never authorizes control. Every snapshot fixes control to DENY, engineering review to PENDING and behavioral cases run to zero.

## Source and acceptance limits

Synthetic source tuples are test point identifiers, not verified peer aliases, OPC UA NodeIds, certificates or equipment identity proofs. Native property IDs, protocol quality bits, endian/encoding/scale mappings, units and time provenance must be frozen alongside real peer versions and actual simulated device endpoints in EI05/EI18. Real source data cannot be promoted through this synthetic-only fixture schema. Calibration, uncertainty, capability/mode evidence and independent engineering review remain absent. Carbon intensity still needs reviewed energy intervals, emissions boundaries, provider method and missing-data policy; instantaneous watts do not establish electricity carbon intensity.

## Reproduction

```bash
python3 tools/build_power_snapshots.py --write
python3 tools/build_power_snapshots.py
node tools/validate_power_snapshot.mjs assets/power-snapshots/generic.json
node --test tools/test_power_snapshots.mjs
```

[The generator](../tools/build_power_snapshots.py) reproduces the four fixtures. [The schema](active-power-snapshot.schema.json) and [evaluator](../tools/validate_power_snapshot.mjs) validate input structure and source-linked semantics. Tests cover exact conversions, import/export signs, freshness edges, quality exclusion, unsafe numbers, missing/duplicate boundaries, alias reuse, timestamp errors, source drift and false execution claims. All 43 acceptance cases remain NOT_RUN; domain admission remains NOT_PERFORMED.
