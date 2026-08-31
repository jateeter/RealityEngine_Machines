# Shadow Machines — declared footprint, late binding

**Status:** design note. Nothing here is implemented yet.
**Last reviewed:** 2026-08-17

A shadow machine is a corpus entry that declares a machine's *footprint and
contract* without carrying its implementation. The implementation is bound later
— at runtime, by whoever owns it — and the binding is checked against the
declaration rather than trusted.

This note is expected to grow. It starts with the case that forced it, states
what already exists, and records the decisions that are still open, so that
later sections can be added without re-deriving the argument.

---

## 1. The problem it solves

The corpus is the authority for five things: region allocation, the arbitration
registry, schema conformance, OWL semantics, and byte-parity across runtimes.
All five derive from `machines/**.json`. A machine that is not in the corpus is
invisible to all of them.

That invisibility is not hypothetical. `scripts/build-arbitration-registry.py`
documents it about itself:

> Other integration surfaces (mcp, mqtt, healthkit, localai, sensor) register
> their write-back regions **outside the corpus, so they cannot be derived
> here**.

localAIStack made the consequence concrete (jateeter/localAIStack#38, #46): ten
`localai/*` machines register into the RE at runtime and write real positions in
the universal vector. A 14-machine boot corpus was observed loading as 24. Until
recently no schema had ever validated them, their regions were declared nowhere,
and because only one engine received them, the cross-runtime parity gate was
comparing engines that held different machine sets.

Two of those ten have no file at all — they are synthesized at runtime from live
LangGraph graphs. They cannot become corpus files without ceasing to be what
they are. That is the case the pattern has to handle, not the easy one.

## 2. The shape

```
corpus                          runtime
------                          -------
shadow machine        boot      loaded as machine-<stem>
  regions              -->      footprint reserved, gates satisfied
  contract
  provider                      ...
                       bind
                        -->     real implementation replaces it,
                                checked against the declaration
```

The corpus owns **what the footprint is**. The provider owns **what fills it**.
The bind step is where those two are reconciled, and it fails loudly when they
disagree.

## 3. What already exists

Most of the mechanism is built. This pattern is more assembly than invention.

**Replacement by canonical id** — `RealityEngine_CPP/src/reality_engine_server.cpp`:

```cpp
// Same id canonicalization as startup loading so re-loading a corpus
// file replaces the startup machine instead of duplicating it.
std::string stem = path.stem().string();
... Machine m = load_machine_from_json_string(raw, "machine-" + stem);
add_machine(m);
```

A machine's identity is derived from its file stem, and `add_machine` replaces
by id. A shadow loaded at boot is therefore *already* replaceable by a later
definition of the same name. This is relied upon today for corpus reloads.

**Declared footprints with external writers** — `serviceLanes` in
`domains/region-allocation.json` is this pattern in degenerate form: a declared
offset and length, a named provider, and `corpusReaders`/`corpusWriters`
computed against the corpus. It works; it is simply limited to a bare 4-cell
lane rather than a machine-shaped contract.

**An unused slot** — `reservedBands` has been `[]` since it was introduced.

**A pure counterfactual primitive** — `POST /api/machines/:id/whatif` and
`whatif-universal` exist in C++ and Scala, and are non-mutating by construction:

```cpp
Machine copy = it->second;   // value copy
lock.unlock();
auto result = copy.process_input(...);
```

The machine is copied, stepped in isolation, and discarded. Nothing observable
changes. Section 6 builds on this.

## 4. The one change required

The binding path must be *replace-with-check*, not *import-if-absent*.

`localAIStack`'s bridge currently uses `import_machine_if_missing`, which skips
when a machine of that name is present. With a shadow in the corpus that is
always true, so the shadow would permanently block its own replacement. This is
observable today: restarting the bridge after editing its machine definitions
left the old `arbiterRule` in place, because the import skipped.

Bind must therefore:

1. locate the shadow by canonical id,
2. verify the incoming implementation against the shadow's declaration,
3. replace on success, **fail loudly on mismatch** — never silently overwrite.

Step 2 is the whole value of the pattern. A bind that accepts anything is just a
slower import.

## 5. Open decisions

These are unresolved. Nothing should be built until 5.1 and 5.2 are settled;
they determine whether the pattern helps or makes the corpus confidently wrong.

### 5.1 The inertness window

Between boot and bind, a shadow is a loaded machine. If it carries `isInitial`
sequences it can fire and contribute to cells its real implementation will also
write — double-writing into a contended cell that the arbitration registry
believes has one writer.

Options:

- **Inert shadows** — no initial vectors, no outputs. Safe, but the shadow then
  cannot assert the full contract it exists to assert, and schema conformance
  becomes a weaker claim than it looks.
- **Deferred activation** — engines do not activate a machine marked
  runtime-bound until it is bound. Stronger, and needs runtime support in all
  three engines.

Recommendation: deferred activation. Inert shadows trade away the guarantee that
motivates the pattern. But this is a real cost in three runtimes and should be
decided deliberately.

### 5.2 Drift between shadow and implementation

Two hand-maintained descriptions of one machine is exactly the drift the pattern
claims to prevent, relocated one level up.

**Constraint: the shadow must be generated by the same generator that produces
the real machine**, and committed to the corpus as a build artifact with a
drift check — the same posture as `profiles/regression.txt` in
localOpenClawStack, which is generated from a CI corpus manifest and gated by
`--check`.

A hand-authored shadow is out of scope on purpose.

### 5.3 Binding must fan out

If one engine binds and another does not, the engines hold different machine
sets, byte-parity is meaningless, and the parity gate reports a baseline
mismatch that has nothing to do with the runtimes. This is precisely the failure
observed on 2026-08-17, where one engine held 17 machines and the others 7.

This pattern therefore **depends on** jateeter/localAIStack#46 (all running
RE/PE engines receive the integrations) rather than being independent of it.

### 5.4 Unbound shadows must be detectable

A shadow nobody replaced means the corpus declares a footprint no machine fills
— reserved cells with no writer, and arbitration entries for a contributor that
is not there. The corpus would be claiming a capability the system does not
have.

The regression lane already enumerates loaded machines per engine, so the check
is cheap: every shadow must be bound on every engine, or the stage fails.

## 6. Why this matters beyond provisioning

The pattern separates a machine's **contract** from its **implementation**. Once
that separation exists, the same mechanism serves more than late arrival:

| use | what varies | what is fixed |
| --- | --- | --- |
| provisioning | the implementation arrives late | footprint, contract |
| counterfactual | an *alternative* implementation is bound | footprint, contract |
| search / learning | many alternatives are bound and scored | footprint, contract |

The third row is the interesting one. Today the counterfactual primitive exists
only at **machine** scope — `whatif` copies one machine and steps it in
isolation. There is no engine-scope equivalent: no way to ask what the whole
reality would have done under a different set of machines, deterministically and
without disturbing the live one.

A declared footprint is what makes engine-scope what-if tractable. Because the
corpus fixes the regions, the arbitration rules, and the contract at each cell,
two bindings of the same shadow are directly comparable: they write the same
cells under the same resolution rules, so the difference in outcome is
attributable to the binding rather than to a changed topology. Determinism comes
from the same place it comes from today — the arbiter's rules are commutative
monoids (`ARBITER_CONTRACT.md` 4.1), and a deterministic contribution is
derivable from the corpus and IS(k) alone (4.3a).

This is the intended substrate for the *omega sprite* work: agents that occupy a
declared footprint, can be swapped, compared and scored against a fixed
contract, and whose effect on the Reality Event is reproducible because the
footprint and the resolution rules were declared before the agent existed.

Nothing in section 6 is designed yet. It is recorded here because it is the
reason to get sections 4 and 5 right rather than expedient: a binding mechanism
that cannot be trusted to be conformant cannot support comparison, and a
comparison that is not deterministic cannot support learning.

## 7. Where else the pattern applies

- the 1,320 generated OpenClaw agents
- the mcp / mqtt / healthkit / carekit / sensor write-backs the arbitration
  registry generator cannot currently derive
- the two runtime-synthesized topology machines, which have no static form
- machines added by the corpus expansion expected at MVP

## 8. Naming

"Shadow", "virtual" and "placeholder" have all been used informally. This note
uses **shadow machine** for the corpus entry and **bind** for the act of
replacing it with an implementation. A machine marked for this treatment is
**runtime-bound**.

## 9. Related

- `docs/ARBITER_CONTRACT.md` — 3.1 registry admission, 4.1 commutative rules,
  4.3a precedence
- `docs/CORPUS_EXIT_CRITERIA.md` — §5 records the localAI machines as outside
  corpus validation at `corpus-exit-v1.0`
- jateeter/localAIStack#38 — schema conformance of the localAI definitions
- jateeter/localAIStack#46 — single-target bridge; 5.3 depends on it
