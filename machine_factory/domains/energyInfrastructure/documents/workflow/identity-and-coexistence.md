# Canonical identity, coexistence and machine dispositions

EI02: [issue #266](https://github.com/jateeter/RealityEngine_Machines/issues/266). Authored decision: [identity-decision.json](../../identity-decision.json). Reproducible dispositions: [machine-dispositions.json](../../machine-dispositions.json).

## Preserve the original and create an independent domain

The canonical runtime/admission identity is **energy-infrastructure**, code prefix **ENI**. The owner-requested factory directory remains **energyInfrastructure**. The existing accepted `energy` domain, ENX names, native lanes, Sources, buses and agents remain unchanged. There is no retirement and no runtime alias from energy to the new domain.

This is a coexistence decision made under the owner's authorization to implement the new-domain workplan through reviewed branches/PRs/merges. The real source/merge record binds the decision; no owner signature or independent domain-admission approval is fabricated. Signed source provenance, where provided by the forge, is distinct from the later independent admission approval.

The explicit [factory mapping](../../../../../domains/factory-domain-paths.json) and its [contract](../../../../../docs/FACTORY_DOMAIN_PATHS.md) support planning/preparation and packaging under the preserved folder. The canonical CLI argument is `--domain energy-infrastructure`, never `--domain energyInfrastructure`. Candidate files must later be staged under `machines/domains/energy-infrastructure`; the mapping alone does not admit or stage anything.

## One disposition per historical definition

All 187 source definitions retain their original bytes and import hashes. The inventory assigns exactly one prospective disposition to each:

- **170 ADAPT:** scoped operational capabilities get ENI identities and new Source/agent/governance/quality contracts. Historical generic CESs are design references, not acceptance or an executable new capability.
- **17 REPLACE:** family interconnects and the command-center bus require explicit new-domain truth tables, semantic transfers, arbitration and consumers. Their legacy one-hot patterns and lane addresses are not copied mechanically.

Each row includes source/hash/name, rationale, target ID/stem/file/code/name, a unique block and input/output/routing windows, source dimensions, and rewiring obligations. `machine.id` must equal the future filename stem. Human names are scoped with `Energy Infrastructure /`; no original file, trigger, agent or callback is renamed or silently rebound. Target names and codes are checked case-insensitively against one another and prospective external collisions.

EI08 still must implement reviewed behavior, remove placeholder governance, replace semantic identities, and create a separate JSON-only `candidate-machines/` payload. Original documentation stays with the clone. Admission count is not fixed to 187: later additions/splits/exclusions need explicit reviewed changes and coverage.

## Planned native allocation

The nonactive factory plan is **[86016, 102400)**: 256 static blocks of 64 cells. The 187 seed rows occupy distinct blocks; 69 blocks remain for new capabilities. Every block reserves 32 input, 16 output and 16 routing cells. These are regular static candidate windows, not the engine's runtime clone nest or a claim that clones have a 32-cell input quarter.

The base 86016 follows the current reserved engine clone band [20480, 86016). The checker compares the whole proposed band against current canonical machine windows, reserved/provider/service ranges, and other factory candidate machine windows. Identity/prefix checks cover the manifest and other candidate machines. Adjacent half-open ranges do not overlap.

No active domain range is registered here. EI08/EI19 must register reviewed candidate windows and refresh derived domain/arbitration/semantic-bus/cesgen views using their producers. Recheck occupancy immediately before use; new unrelated allocations can invalidate this plan. A capability exceeding its declared window or requiring more capacity needs a reviewed plan change, not an unchecked overflow.

There is no implicit shared native bus with the old energy domain. Any future cross-domain bridge requires explicit semantics and arbitration. Existing shared ACP completion Sources keep their service-owned meaning and per-dispatch scope; these are not reassigned to ENI.

## Verify

From the factory directory:

```bash
python3 tools/build_identity_plan.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tools -p 'test_identity_plan.py'
```

`--write` explicitly regenerates only the disposition plan after a reviewed decision/source change; it never writes runtime machines or registers ranges. The package verifier checks reproducibility and internal consistency offline; the command above additionally scans current repository occupancy. These checks do not execute AC41, run engines or confer domain acceptance.
