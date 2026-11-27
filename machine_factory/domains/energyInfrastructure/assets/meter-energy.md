# Offline meter import/export energy intervals

The [selected meter profile](meter-energy-profile.json), [synthetic interval](meter-energy-interval.json) and [evaluator](../tools/evaluate_meter_interval.mjs) add an interval-energy prerequisite for electricity carbon intensity. They extend EI05 source mapping; they do not complete EI14 accounting or EI18 simulated hardware. ASHRAE Standard 201/FSGIM remains the asset integration context, with the generic projection's selected PCC Meter and existing OPC UA DI type facet. No normative FSGIM energy-property equivalence or actual meter instance is claimed.

## Source mapping and quantity

The already collected Apache-2.0 SunSpec model 203 is pinned at `90b4a331dcca1d6eac69c1bead952fddcc5852e0`. Exact bytes and the retained license are recorded in [the source receipt](source-receipt.json). The profile preserves source definitions and pointers for `TotWhImp`, `TotWhExp` and `TotWh_SF`. Offsets are derived from declared sizes and validated against the profile and source hash before decoding.

| Point | Zero-based register offset from model ID | Encoding | Unit |
| --- | ---: | --- | --- |
| TotWhImp | 46 | acc32, two big-endian registers | Wh |
| TotWhExp | 38 | acc32, two big-endian registers | Wh |
| TotWh_SF | 54 | signed sunssf | decimal scale |

The complete model block has 107 registers including ID/L. Header ID 203, declared data length 105 and exact byte count are mandatory. This is a decoded model block, not a Modbus PDU, ADU, discovery map or authenticated peer response. Other registers are zero-filled fixture placeholders and are not interpreted or qualified.

Official [SunSpec Device Information Model Specification 1.4, §§6.4.2 and 6.4.8](https://sunspec.org/wp-content/uploads/2009/03/SunSpec-Device-Information-Model-Specificiation-V1-4.pdf) supplies representation guidance: acc32 is an unsigned 32-bit quantity with zero representing not accumulated, while sunssf uses signed decimal scaling with an unimplemented sentinel. The selected profile excludes zero counters and `0x8000` scale factors, accepts scale exponents -10 through +10, and treats `0xffffffff` as a valid acc32 value. The PDF was consulted as public guidance, not collected/indexed or asserted fully reviewed.

## Interval eligibility and exact differences

Each endpoint declares a scoped synthetic meter identity, counter epoch, observation/receipt times, source quality and model block. Both endpoints must refer to the same identity and epoch and the selected facility PCC Meter in the source-bound generic or REF01 connected projection. Identity/epoch changes require a new interval. Times must be valid UTC whole-second or millisecond values; observation precedes receipt, receipt precedes evaluation, and end observation follows start observation. Receipt order and a declared generic maximum interval are enforced. Freshness applies to the interval end; the start may legitimately precede the freshness horizon. These policy values and aligned-clock assumptions require engineering review before any operational use.

Only GOOD endpoints with accumulated counters, unchanged valid scale, a fresh end and nondecreasing import/export counters are eligible. A decrease is explicitly ambiguous between reset and rollover: the evaluator does not guess a wrap or invent recovered energy. BAD/UNKNOWN, unaccumulated counters, missing scale, scale changes and stale endpoints produce null quantities with reasons. A valid unchanged **nonzero** cumulative counter produces a zero delta; that differs from an unaccumulated zero counter.

For eligible data, each counter difference is converted independently to exact decimal Wh and kWh using integer arithmetic. Imports and exports are never netted, credited against emissions or added to resource conversion-chain views. The fixture gives 1.25 kWh imported and 0.25 kWh exported over 15 minutes. These are synthetic mathematical results, not measured grid flows or energy balance. No emissions factor is supplied: carbon intensity stays null with `NOT_COMPUTED_NO_EMISSIONS_FACTOR`, even when interval energy is zero.

## Reproduction and acceptance limits

```bash
python3 tools/build_meter_intervals.py --write
python3 tools/build_meter_intervals.py
node tools/evaluate_meter_interval.mjs assets/meter-energy-interval.json
node --test tools/test_meter_intervals.mjs
```

PASS from the command means the interval input satisfies the offline contract; inspect `eligible` and `reasons` before using any quantity. Structural/source/time/identity errors throw before success. Tests include independent high/low word vectors, valid all-ones counters, exact scale edges, zero delta, sentinel exclusion, apparent wraps/resets, epoch/source changes, stale data, malformed blocks and false execution claims. Package checks reproduce both profile and fixture.

Endpoint identities, epochs, GOOD status and timestamps are synthetic declarations, not native acquisition evidence. Device coherence, counter continuity, orientation, calibration/uncertainty, status/time mappings, secure peer interoperability, independent review and complete simulated meter behavior remain pending. No network/runtime link is created; control remains DENY, engineering review PENDING and all 43 behavioral cases NOT_RUN. Required hardware remains simulated and generic/template assets remain permitted in every case. Corpus admission is NOT_PERFORMED.

The [storage component version 0.2.0](storage-component.md#cumulative-energy-readback-version-020) now generates selected cumulative meter points and source-bound REF01 interval inputs. This is partial offline behavior; the original generic interval fixture remains unchanged. Only the two explicit projection paths are allowed, with their source hashes and selected PCC Meter validated.
