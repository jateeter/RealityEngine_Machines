# AI governance regime intake review queue

These findings come from the intake review of the received package (2026-11-20).
Each one stays open until its disposition is recorded here and the affected
step in [PACKAGE_STATUS.md](PACKAGE_STATUS.md) is redone. Findings marked
**owner** need an owner decision; the rest are mechanical.

| Finding | Subject | Blocks | Needs |
|---|---|---|---|
| GOV-R01 | Neither corpus is in the canonical machine form | conversion | mechanical, after R02/R04 |
| GOV-R02 | Machine identity: base templates against corpus ids | conversion | **owner** |
| GOV-R03 | Machine and corpus counts disagree across documents | conversion | mechanical |
| GOV-R04 | The region-allocation patch does not apply | allocation | **owner** (band), then mechanical |
| GOV-R05 | Corpus-315 declares itself `accepted` | admission | mechanical |
| GOV-R06 | Two meanings of "quorum" | specification | **owner** |
| GOV-R07 | Framework alignment has no pinned sources | every alignment claim | **owner** (which editions) |
| GOV-R08 | The authoritative baseline (V0.18) is not in the workspace | every citation | **owner** |
| GOV-R09 | Designed mechanisms are described as if they exist | workplan, specification | **owner** (scope per release) |
| GOV-R10 | Generated-text residue and stale cross-references | documents | mechanical |

## GOV-R01: neither corpus is in the canonical machine form

- `intake/corpus-312.json` holds 312 machines with full automaton specs
  (`automatonSpec`: states, transitions, interval-predicate guards).
- `intake/corpus-315.json` holds those 312 ids plus `M-GOV-HRD-313`–`315`. It
  is in a compact form (`intervalPredicates`, `osreOutputs`) with no states or
  transitions, so for 312 of its machines the behavior exists only in the
  312-machine file.
- Neither file follows `schemas/machine.schema.json`. Neither has CES patterns,
  regions or arbitration in the corpus's terms, and neither is one file per
  machine.

Conversion has to merge the two: the 312 automata, plus the three hardening
machines written out in full from
[HARDENING_TRANSITION_RULES.md](HARDENING_TRANSITION_RULES.md). Then each machine
becomes a canonical file under `machines/domains/ai-governance-regime/`, with a
globally unique filename and one regular expression per CES.

## GOV-R02: machine identity (owner)

- The documents name 17 base governance templates, `M-GOV-01`–`17`. Only 15–17
  have formal rules here; 01–14 appear only as prose in SPECIFICATION.md.
- The corpora instead hold per-target-domain instances: 6 families × 13
  operational domains × 4 = 312, plus 3 global hardening machines.
- The hardening machines are `M-GOV-15`–`17` in the documents and
  `M-GOV-HRD-313`–`315` in the corpus (`baseGovernanceTemplate` links them).

Decide what a canonical machine is: a base template that the clone route
instantiates per target domain at run time (the cloneable-template model,
lass#8), or each of the 315 pre-expanded instances. 262 of the 315 are already
marked cloneable, which points to the template model and far fewer canonical
files.

## GOV-R03: counts disagree

| Source | Machines | Corpus total |
|---|---|---|
| `intake/README.v1.md`, the SoA template, `amendments/region-allocation.md` | 312 (260 + 52) | 1,864 |
| `intake/README.v2.md`, RESOLUTION_WORKPLAN.md, `amendments/region-allocation.patch.json` | 315 (262 + 53) | 1,867 |
| `machines/` today | — | 1,552 across 13 domains |

The documents need to state one count, taken from whatever R02 decides.

## GOV-R04: the region-allocation patch does not apply

All three of its `test` operations, and all four `replace` operations, name
paths that do not exist in `domains/region-allocation.json` or
`domains/domain-manifest.json`: `/corpusFootprint/endCell`,
`/cloneSpace/startCell`, `/summary/totalMachines`, `/summary/totalDomains`, and
`/neuraleseBand/minAllowedStartCell`. The real fields are
`vectorBudget.maxCellExclusive` (16944) and the `engine-clone-space` reserved
band (offset 20480, length 65536).

The admission workflow also regenerates region allocation from the canonical
machines, so it is not hand-patched (docs/DOMAIN_APPROVAL_WORKFLOW.md). The
proposed band `[16960:17087]` sits above the current footprint and below the
clone space, and overlaps no reserved band. Whether governance gets a fixed
band or follows the normal allocation is an owner decision. Cell numbers in
every document follow from it.

## GOV-R05: corpus-315 declares itself `accepted`

`intake/corpus-315.json` has `"status": "accepted"`, and the patch writes
`accepted` into the domain manifest. A new domain enters as experimental and
becomes accepted only through the admission workflow's gates.

## GOV-R06: two meanings of "quorum" (owner)

The documents use quorum for human signers: q-of-n signature bundles with
Byzantine bounds (n ≥ 3f + 1, q ≥ 2f + 1) and signer diversity across org
units. They also cite "3-of-3" engine parity. In this workspace, quorum is the
engine rule of `RealityEngine_CI/docs/QUORUM_CONTRACT.md`: unanimous among C++,
LSP and Scala, no majority, followers never vote. The specification needs
distinct terms for these, for example "approval quorum" against "engine
quorum". It also needs to say that an approval quorum never substitutes for
3-of-3 engine agreement. RESOLUTION_WORKPLAN.md 1.3 proposes changing
QUORUM_CONTRACT.md itself, which is a contract change.

## GOV-R07: framework alignment has no pinned sources (owner)

The domain's purpose is alignment with the frameworks the documents track, but
only ISO/IEC 42001 Annex A has a control-by-control mapping (the SoA
template). IFRS has `source-requirements.json`: every control, with its
obligation, required evidence and source span, against a pinned edition. This
domain needs the same for each framework it claims. The owner decides which
frameworks and editions are in scope for the first version; the rest are
recorded as out of scope, not as aligned.

## GOV-R08: the authoritative baseline is not in the workspace (owner)

Every received document defers to *RealityEngine: Deterministic Pre-Execution
Governance for Agentic AI with Temporally Bounded Incompleteness*, V0.18
(Working Draft, 19 November 2026). Its threat ids (`T1`–`T22`), timing
objectives (`TO-1`–`TO-18`), solutions (`S1`–`S6`) and propositions are used
throughout, but the document is not here. It needs to be pinned (path and
sha256) as a package source, or the citations are unresolvable.

## GOV-R09: designed mechanisms described as if they exist (owner)

The machines' input cells assume sources that do not exist in any repository
today:

- SPIFFE/TPM and in-toto/SLSA attestation;
- offline YubiHSM/TPM root tokens;
- CRL/OCSP quorum-keyring polling;
- AgentDojo red-team gating;
- behavioral canary probes;
- C2PA egress tagging;
- `kperf` latency gates;
- a "neuralese" band at ≥ 86016.

SPECIFICATION.md §1 itself says several are Design. RESOLUTION_WORKPLAN.md
assigns work to CPP, Scala, LSP, CI and localAssetStorageStack. Each item
needs an issue in its repository and an owner decision on the release it
belongs to. Until a source exists, a machine reading its cell can only be
tested against interned test sequences.

## GOV-R10: generated-text residue and stale cross-references

- `intake/ISO42001-SOA-RELEASE-NOTE.md` and `amendments/region-allocation.md`
  begin "Here is your file:".
- `schemas/governance-asset-shapes.md` names
  `AIGovernanceRegime_Asset_Shapes.shacl.ttl`, but the received file was the
  `-v2` edition.
- The SoA template's evidence container is a placeholder
  (`https://pod.enterprise.org/...`).
- The received READMEs give target locations (`docs/architecture/`,
  `audit-binder/iso42001/`, `localAssetStorageStack/schemas/`) that this
  package does not use.
- The documents refer to each other by their received names.

These are fixed when the documents are next revised. The intake copies stay as
received.
