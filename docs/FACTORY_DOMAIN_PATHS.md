# Canonical domains and factory directories

Runtime and admission identities remain lowercase kebab-case. An owner-selected factory directory may have a different single-component name. [domains/factory-domain-paths.json](../domains/factory-domain-paths.json) records explicit exceptions; [scripts/factory_paths.py](../scripts/factory_paths.py) is the shared resolver. This is a directory lookup, not a runtime/domain alias or acceptance permission.

`energy-infrastructure` resolves to `machine_factory/domains/energyInfrastructure`. All unmapped domains retain `machine_factory/domains/<canonical-slug>`. Canonical machine files still belong under `machines/domains/<canonical-slug>` and must use that category and their own globally unique stems/IDs. The historical energy clone is not a valid new-domain deployment payload.

## Admission and deployment

`approve-domain.sh plan` reports `factoryDirectory`; `prepare` calls the same planner and binds the tracked mapping file in its input snapshot. Both still require a staged nonaccepted canonical candidate, manifest/domain-registry entries and all existing admission prerequisites. A factory alias cannot make an unstaged or unverified domain admissible.

`package-deployment` and payload validation use the resolver for `deployments/<version>` under the chosen factory folder. Immutable manifests retain their canonical `domain`, and `payloadRoot` records the actual factory location. `deploy`, `check-deployment`, and `publish-deployment` validate those manifests through the same path. Changing a mapping cannot reinterpret an old payload as belonging to a new location; validation rejects it. Mapping changes after payload publication require explicit migration design, never edits to frozen manifests. Existing default-folder deployment history cannot be redirected by adding an alias.

The test-only rehearsal uses the resolver for source assets. Its existing IFRS-specific document checks remain IFRS-specific; this does not implement a generic Energy rehearsal or waive production evidence.

## Validation and boundaries

The schema gate checks [factory-domain-paths.schema.json](../schemas/factory-domain-paths.schema.json). The resolver additionally rejects duplicate case-folded target folders, another canonical domain's folder, path traversal/absolute components, symlink paths, and redirection of existing default deployment history. Tests exercise actual plan generation, protected-input fingerprints, immutable packaging and payload validation in isolated synthetic repositories.

The canonical slug `energy-infrastructure` is selected by the Energy identity decision; the exact requested factory name `energyInfrastructure` is preserved. This change does not add the new domain to the active manifest, move vector lanes, author candidate runtime machines, bootstrap Sources or execute admission/field actions.
