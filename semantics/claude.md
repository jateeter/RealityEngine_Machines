# RealityEngine_Machines Semantics Guidance

This directory holds the OWL semantic representation of machine behavior used
by verification and auditing in the RE and PE components. See
`docs/SEMANTIC_OWL_ROADMAP.md` for the rollout plan.

- `ontology/re-core.ttl`: core TBox — classes, properties, canonical action
  individuals (`re:actionCode`), RAG statuses, autonomy modes, the agent
  vocabulary, and audit axioms. This file is the single source of truth for the
  action vocabulary; add new action codes here (with the correct consequence
  class: Logging / Notification / Escalation) before generating ABoxes that use
  them.
- Agent vocabulary (`0.2.0`): `re:Agent`, `re:AgentFamily`, `re:AgentBinding`,
  `re:AutonomyMode`, `re:SemanticAxis`, `re:CompletionMapping`,
  `re:ResponseMapping`. It models both axes the corpus binds agents on — the
  per-machine assessment written into the machine's own input region, and the
  role-level completion written into the reserved band. `re:autonomyMode` values
  must stay in step with the enum in `schemas/agent-binding.schema.json`.
  `re:axisName` is functional on purpose: one region position carries one
  meaning, so two sources naming it differently is an inconsistency rather than
  a variant spelling. `generate-owl.py` does not emit these individuals yet;
  the vocabulary is declared ahead of the generator.
- `abox/<domain>/<MachineFile>.ttl`: generated per-machine ABox files.
  **Never edit by hand** — regenerate with
  `python3 scripts/generate-owl.py --machine <json> --write`. Machine JSON
  stays the source of truth for behavior; drift is caught by
  `generate-owl.py --check` and `tests/contracts/owl_semantics_test.py`.
- Generated output must stay byte-deterministic; treat any nondeterminism in
  `scripts/generate-owl.py` as a bug.
- IRIs follow `https://realityengine.example.org/machines/<domain>/<stem>#`;
  file renames therefore change semantic identity and must be treated as
  contract changes.

## Which corpus routine validation reasons over

**The full corpus is not loaded by routine validation.** The regression lanes
boot a minimal provable corpus, and full-corpus checks run manually or on a
cycle. The reasoner follows the same split:

| scope | command | cost | when |
|---|---|--:|---|
| minimal provable corpus | `npm run owl:reason:corpus` | ~5s | every PR |
| arbiter fixtures | `npm run owl:reason:arbiter` | ~4s | with the arbiter gate |
| one domain | `npm run owl:reason` | ~5-20s | while working in it |
| every domain | `npm run owl:reason:domains` | ~3min | cyclic |
| corpus-wide merge | `npm run owl:reason:all:complete` | ~18min | weekly |

This matters more as the corpus grows. Domains, machines and CES all expand at
MVP, and a gate whose cost scales with the corpus is a gate that eventually gets
switched off — which is worse than a smaller gate that keeps running. The
minimal corpus is chosen to be *provable*, not merely small: it carries the
machine classes, the bus and the fixtures the contracts are stated against.

## The ROBOT report profile, and its two deliberate INFOs

`robot-report-profile.txt` lists all 32 rules ROBOT ships rather than expressing
a delta, so a rule cannot be disabled by omission (#46). Two of them report
against this ontology permanently, and that is a decision rather than a backlog:

- **`missing_definition` (120)** looks for a definition annotation property
  (`IAO:0000115` by convention). This ontology documents with `rdfs:comment`
  instead, and every class carries one — asserted by
  `owl_semantics_test.test_every_class_is_documented`. Properties are described
  by label, domain and range; requiring prose for each would add ~104
  restatements of the obvious.
- **`missing_superclass` (16)** wants every class under an upper ontology (BFO
  or similar). These 16 are the vocabulary's root concepts — `re:Machine`,
  `re:Determination`, `re:Action` and so on. Introducing a vacuous `re:Entity`
  to satisfy a linter would add a layer carrying no information.

Both are OBO Foundry publishing conventions, and this is not a published OBO
ontology. `ERROR` and `WARN` are both zero and should stay that way; a new
violation at either level is a real defect.

The escalation invariant — an emergency-path action may only be prescribed by a
`RED` determination — is the reason `reason-owl.sh` runs HermiT and not ELK
alone. ELK does not implement the constructs it relies on and passes a corpus
that violates it. Verified: asserting `re:UrgentIntervention` on a `GREEN`
determination makes HermiT reject the graph and ELK exit 0.

## MUST: every use of the word "registry" carries a qualifier

**The word "registry" MUST NEVER appear unqualified. Every single use of the
word takes a qualifier naming which registry is meant.**

This is a hard requirement, not a style preference. It applies to every
occurrence in every context, with no exceptions: prose, end-of-task summaries,
commit messages, PR bodies, issue titles and bodies, code comments, docstrings,
variable and function names, log lines, and documentation.

Wrong, in every case — these are all violations:

- "the registry"
- "a versioned registry"
- "the registry file" / "update the registry" / "registry-backed"
- "check the registry first"
- "registry drift"

Right — a qualifier every time:

- "the **instance** registry"
- "a versioned **cesgen** registry"
- "the **arbitration** registry"
- "**machine** registry drift"

If you type the word "registry" and the word immediately before it is not a
qualifier, stop and add one. Re-read every summary and every message for the
bare word before sending it — that is where this rule is actually broken, because
the surrounding context makes the referent feel obvious in the moment. That
feeling is exactly the assumption the rule exists to block.

Qualifiers currently in use. **This list is open, not exhaustive** — a registry
added later gets a qualifier too; nothing is ever promoted to being "the
registry" by virtue of being the one under discussion:

- **instance** registry — `/tmp/re-registry/re-registry.json`, served at
  `:5999/re-registry.json`. Running RE/PE instances with `re_url`/`pe_url`/ports,
  plus `services` and `allocation`. What `RE_REGISTRY_URL` points at.
- **machine** registry — the machines a runtime holds in memory, reported by
  `GET /api/machines`. Distinct from `GET /api/machines/json/list`, the on-disk
  corpus catalog.
- **cesgen** registry — `RealityEngine_Machines/domains/ces-contract-registry.json`.
  Which CES output-stream contract shards exist, what corpus each was recorded
  against, whether each is current.
- **arbitration** registry — `machines/domains/arbitration-registry.json`.
- **domain** registry — `machines/domains/domain-registry.json`.
- **semantic-bus** registry — `machines/domains/semantic-bus-registry.json`.
- **tag** registry — `RealityEngine_CI/docs/TAG_REGISTRY.md`.

## MUST: never commit to main — branch, PR, verify, merge, clean up

**No change reaches `main` in any repo except through a branch and a pull
request.** Not documentation, not a one-line fix, not a "trivial" follow-up, and
not a hotfix for a gate that is currently red. There is no size or urgency
threshold below which this stops applying.

The full workflow, every time:

1. **Branch from `origin/main`** — `git fetch origin main && git checkout -B <branch> origin/main`.
   Branch from the remote, not from whatever the local `main` happens to be:
   a stale local ref is how a change gets built on a tree that no longer exists.
2. **Commit** with a message that says what changed and *why*, including the
   evidence that motivated it.
3. **Push** and **open a PR**.
4. **Verify** — see "MUST: verify a merge beyond the hosted checks". State in the
   PR which gates ran, what they returned, and what could not be exercised.
5. **Merge** — squash, and delete the remote branch.
6. **Clean up** — delete the local branch, `git worktree prune`, and remove any
   run directories the work created.

Two things about cleanup that are easy to get wrong:

- **Squash-merged branches are not ancestors of `main`.** `git merge-base
  --is-ancestor` and "empty diff against origin/main" both report *nothing to
  delete*, and a branch that is merely behind `main` shows a diff full of
  reversions. Ask the forge which PRs merged — `gh pr list --state merged
  --json headRefName` — and delete those heads.
- **Never delete a branch with an open PR.** Check state before pruning.

Why this is absolute: a direct commit to `main` has no diff anyone reviewed, no
place to record the verification, and nothing to revert cleanly if it is wrong.
It also breaks the only reliable cleanup signal — a merged PR — so the branch
inventory stops meaning anything.
