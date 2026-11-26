# Offline SunSpec active-power subset

EI05 now has a reproducible [selected-point profile](sunspec-power-profile.json), [synthetic register replay](sunspec-power-replay.json) and [decoder](../tools/decode_sunspec_power.mjs). These connect selected SunSpec source definitions to the existing [FSGIM accounting snapshot](power-snapshots.md). ASHRAE 201 remains the energy-asset integration context, including the existing OPC UA DI type facets. This change does not establish normative FSGIM property equivalence or instantiate DI equipment nodes.

## Pinned source and selected mapping

The already collected Apache-2.0 SunSpec models are pinned at `90b4a331dcca1d6eac69c1bead952fddcc5852e0`, with retained license and exact file hashes in [the source receipt](source-receipt.json). Model 103 is the selected three-phase inverter source and model 203 the selected wye three-phase meter source. Only root `W` (int16, W) and its same-group `W_SF` (sunssf) are decoded. Offsets and full block lengths are derived from all preceding declared point sizes, including ID/L. There are no guessed absolute addresses or 40001-style address conversions.

| Selected model | Total registers including ID/L | W offset | W_SF offset | Generic boundary |
| --- | ---: | ---: | ---: | --- |
| 103 | 52 | 14 | 15 | PV_AC |
| 203 | 107 | 18 | 22 | FACILITY_PCC |

Offsets are zero-based from the model ID register. A complete model block is supplied as hexadecimal big-endian register bytes. The ID and L fields must match the selected model and its fixed size. These are decoded model blocks, **not** Modbus PDUs, TCP ADUs, discovery maps or complete SunSpec devices. Unselected points in the replay are zero-filled placeholders and are not validated or interpreted as valid device measurements.

Representation guidance was checked against official [SunSpec Device Information Model Specification 1.2, §§6.4.1 and 6.4.8](https://sunspec.org/wp-content/uploads/2025/01/SunSpec-Device-Information-Model-Specificiation-V1-2-1.pdf) and [Specification 1.4, §6.4.8](https://sunspec.org/wp-content/uploads/2009/03/SunSpec-Device-Information-Model-Specificiation-V1-4.pdf). The selected decoder uses big-endian signed two's-complement int16, excludes the `0x8000` unimplemented sentinel for either W or W_SF, and accepts scale factors -10 through +10. The existing project snapshot range is expanded to those limits, with exact decimal normalization tests. This bounded implementation is not a complete review of either specification; the PDFs were not collected or indexed by this increment.

## Missing data, signs and time

An unimplemented W or scale factor produces UNKNOWN quality, null raw value and null decoded scale, with explicit reasons. The replay uses a zero placeholder exponent only after null/UNKNOWN is established, so the snapshot excludes the sample and never produces a zero reading. An implemented zero remains a valid zero. Out-of-range scale factors, malformed/truncated/extra bytes, unsupported models and mismatched headers are errors.

The generic inverter sample assumes source export-positive and the generic meter assumes import-positive. These are explicit existing project assumptions requiring peer/orientation and engineering verification, not sign semantics inferred from a model label. Native model values supply no observation timestamps or trustworthy GOOD status in this subset. The replay retains the fixture's synthetic times and assigns GOOD only to implemented numeric values within this offline test. Native status/event mapping, atomic acquisition, sample coherence, clock uncertainty, receipt-time capture and freshness evidence remain unimplemented.

Decoded samples replace only the two named boundaries in the immutable generic snapshot; other boundary samples remain synthetic placeholders from that fixture. Snapshot hash, source-model hash/receipt, selected point definitions, offsets and profile flags are verified before use. The downstream snapshot evaluator checks function direction, selected accounting primaries, time/quality and exact watts. Invalid replay input throws before a success result is produced. These observations cannot authorize control; control remains DENY and peerVerified remains false.

## Reproduction and evidence limits

```bash
python3 tools/build_sunspec_power.py --write
python3 tools/build_sunspec_power.py
node tools/decode_sunspec_power.mjs assets/sunspec-power-replay.json
node --test tools/test_sunspec_power.mjs
```

Tests use independently specified model offsets and known signed-register vectors. They cover sentinel handling, valid zero, signed limits, scale edges, malformed framing, provenance/profile drift and the downstream accounting result. This is offline byte-level software evidence, not pairwise interoperability, native transport security, a complete simulated hardware counterpart or any AC01–AC43 behavioral acceptance run. No network listener, Modbus client, device, certificate or runtime registration is created. Actual secure peer pairs, complete protocol profiles, simulator behavior, energy/carbon balance, engineering approval and corpus admission remain pending. All required hardware remains simulated required hardware; generic/template assets remain permitted for every case.
