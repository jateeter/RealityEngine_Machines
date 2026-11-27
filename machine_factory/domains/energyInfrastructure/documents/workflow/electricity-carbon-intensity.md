# Electricity carbon intensity measurement and trajectories

## Current acceptance scope

The [owner-approved acceptance scope](../../acceptance/scope.json) governs this active document: **all required hardware is simulated**, and **template/generic assets may be used in every case**. EI04 must provide templates for each asset class defined by the associated applicable standards, with edition/clause traceability; EI18 must verify a simulated counterpart for every hardware dependency. Generic reference parameters replace site-specific prerequisites for corpus admission. Actual software execution and genuine admission/reviewer evidence remain mandatory. Physical equipment certification and field commissioning are separate future activities. Historical research notes retain their original research context and do not override this decision.

**PROPOSED_ACCOUNTING_CONTRACT** · No site ledger, provider connection or owner-approved target trajectory exists yet. The cloned machines contain operational readiness/dispatch states, not measured carbon performance.

## Keep distinct questions in distinct series

An inventory intensity describes allocated emissions per generated, imported, consumed or delivered kWh over a declared boundary. A marginal signal estimates the emissions consequence of an incremental action under a stated counterfactual. Contractual Scope 2 reporting follows its adopted method and quality criteria. These signals answer different questions and must not be spliced or substituted. ElectricityMaps describes consumption-based attributional flow tracing and direct/lifecycle options; WattTime distinguishes marginal operational use from average inventory signals and imposes purpose-specific rights. [ElectricityMaps methodology](https://www.electricitymaps.com/data/methodology), [WattTime terms](https://watttime.org/noncommercial-agreement/), [GHG Protocol Scope 2](https://ghgprotocol.org/scope-2-guidance).

For each value record mass numerator and gas basis (CO2/CO2e and GWP vintage), direct/lifecycle scope, energy denominator, generated/imported/consumed/delivered boundary, location/market basis, average/marginal type, geography/grid zone/site, time interval/timezone, source/method/vintage, observation/estimate/forecast/target, completeness, uncertainty and freshness horizon. Require explicit reviewed conversions rather than joining incompatible series.

For aligned interval energies E_i and compatible intensities I_i, compute allocated emissions M = sum(E_i × I_i), and energy-weighted intensity I = M / sum(E_i). Convert units explicitly; never arithmetic-average unequal-energy intervals. With zero delivered energy, intensity is undefined with a reason, not zero. Report total emissions, energy and critical-service delivery alongside intensity; a lower intensity can coexist with higher absolute emissions.

## Account for storage, generation and export without false credit

Maintain storage energy and associated charging-emissions inventories with SOC/time/source lineage. Allocate charged energy × compatible interval intensity and losses/auxiliaries under the reviewed accounting boundary; allocate carried carbon to discharged energy. Do not label battery discharge intrinsically zero carbon. Do not count charge and discharge twice in the same final-consumption total or omit fossil backup. Keep direct backup combustion, selected PV/storage lifecycle factors and owned/purchased/supply-chain reporting boundaries explicit.

Maintain exports and estimated avoided emissions in separate ledgers unless an approved method expressly allocates them. Do not deduct an export twice or claim measured global reduction from a local low-intensity schedule. An avoided-emissions estimate needs counterfactual, method, forecast vintage and uncertainty. Market instruments do not change physical flow-traced intensity. Bind every dispatch to the factors available at decision time; revised provider data creates an auditable reporting revision rather than rewriting the original receipt.

## Select provider and target trajectories deliberately

EIA/Grid Monitor and EPA eGRID are US operating/annual reference options; ENTSO-E supplies European generation/load/flow data from which a declared method can derive intensity. ElectricityMaps offers consumption-based average signals; WattTime offers authorized marginal signals; geography/coverage/purpose and license must match the task. Ember annual/monthly and IEA outlook/scenario series supply global context. Annual global factors must not masquerade as hourly local observations. [EIA](https://www.eia.gov/opendata/), [eGRID](https://www.epa.gov/egrid), [ENTSO-E](https://www.entsoe.eu/data/transparency-platform/), [Ember](https://ember-energy.org/data/electricity-data-explorer/), [IEA](https://www.iea.org/reports/electricity-2026).

Keep observed, forecast and approved target paths separate, with baseline year, scope, time horizon, uncertainty and target owner. Stratify connected/islanded/emergency operation. No numeric target is invented here. Optimizing carbon is subordinate to protection, reserve, thermal, feeder, ramp and critical-service constraints. Unknown/stale/unlicensed carbon inputs hold the dependent discretionary carbon objective while deterministic safe operation continues.

Cases AC26–AC35 in [the case inventory](../../acceptance/cases.json) cover weighting, absolute totals, incompatible bases, imports, storage, export, freshness, rights, unsafe proposals and revisions. Their results are NOT_RUN; metering/provider tolerances require approved source uncertainty and calibration evidence.


## Implemented interval-energy prerequisite

[The offline meter interval contract](../../assets/meter-energy.md) now decodes selected pinned SunSpec model 203 import/export accumulators and derives separate exact synthetic Wh/kWh differences. Its quality/continuity/time checks exclude unusable intervals rather than filling missing values with zero. No compatible emissions factor, storage ledger, actual provider or carbon-intensity calculation is implemented by this step; AC26–AC35 remain NOT_RUN.


## Implemented synthetic import ledger

[The exact retrospective import ledger](../../assets/import-carbon-ledger.md) now exercises energy-weighted emissions/intensity, zero-denominator handling and strict compatibility/time/continuity checks using synthetic factors. It keeps exports separate without credits. This bounded arithmetic does not establish real provider rights/methods, uncertainty, storage allocation, trajectories, operational safety or AC26–AC35 acceptance; all remain pending.


## Implemented draft storage allocation

[The synthetic storage carbon pool](../../assets/storage-carbon.md) now carries source-row charging emissions through declared conversion losses and proportional discharge allocation. It prevents treating discharge as intrinsically zero-carbon or adding carried emissions to the upstream import inventory again. This draft policy does not establish physical SOC/flows, idle-loss treatment, durable revisions, uncertainty, safety or AC26–AC35 acceptance.


## Implemented synthetic revision/series integrity

[The bounded trajectory archive](../../assets/carbon-trajectories.md) now preserves a synthetic original and factor-corrected report, keeps historical references on their declared available snapshot, and separates observations from forecasts and unadopted target examples. Hashes are internal consistency checks, not durable or authenticated dispatch evidence. Actual trajectories, approved targets, uncertainty, historic qualification and operational acceptance remain pending.


## Implemented draft proposal-screen prerequisite

[The synthetic REF01 algebraic screen](../../assets/proposal-screen.md) rejects selected reserve, critical-service and active-power-envelope violations regardless of a claimed carbon benefit. It neither qualifies the carbon objective nor authorizes operation. Full deterministic safety feasibility, actual control-gateway enforcement and AC34 acceptance remain pending.
