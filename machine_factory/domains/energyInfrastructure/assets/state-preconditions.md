# Snapshot preconditions for simulated storage steps

Storage component 0.5.0 adds an optional `expectedStateSHA256` to the existing
`{id, storagePowerKw}` request. `stateToken()` returns a read-only snapshot
digest, synthetic run label, state revision and sealed package manifest hash.
The digest binds the complete observation (energy, meter counters, simulated
clock, risk, fault/protection labels, source/profile provenance and run label)
plus the manifest bytes. Observations now expose their synthetic run label.

For a new state-bound request, the component compares the supplied digest to
the current snapshot before advancing its held interval. A mismatch returns
`EXPECTED_STATE_CHANGED`, null calculations and no energy interval. Energy,
counters, clock and state revision do not advance. A matching snapshot still
passes the normal draft feasibility, risk and protection checks; it grants no
operating authority. Receipts expose the expected/evaluated digest and match
result in `stateBinding`. The older two-field fixture request remains supported
and has `stateBinding: null`; it is an unbound component-test path.

The [journal](../tools/storage_execution_journal.mjs) exposes the same inspection
method. Journal inspection and state-bound submissions reverify package bytes
against its pinned source inventory. A changed manifest or unsealed source-byte
drift cannot be refreshed into the old journal epoch. The standalone component
snapshot comparison binds manifest bytes; it is not a substitute for the
journal's full source verification. No continuous filesystem monitor or
cross-process file lock is installed.

## Replay and reconstruction

The expected digest is part of request intent. Reusing an ID with a different
digest, or switching that ID between bound and unbound mode, is rejected.
A valid stale request is retained as a denied receipt. Retrying it returns that
denial; a refreshed intent requires a new ID. Replaying an earlier accepted
request returns its original historical receipt, marked `replayed: true`,
without executing again or weakening the current state. Historical
`applied: true` is not fresh authorization.

The journal records the request through the existing STEP event and reconstructs
the same comparison at the same state. Existing carbon/storage/revision tools
can consume these journals without treating stale denials or historical replays
as additional energy. The versioned catalog pins implementation bytes; old
source-bound journals are not silently migrated.

From the repository root:

```bash
node machine_factory/domains/energyInfrastructure/tools/run_state_precondition_scenario.mjs
node --test machine_factory/domains/energyInfrastructure/tools/test_state_preconditions.mjs
```

The scenario captures a snapshot, applies a discharge, rejects a second request
using the old snapshot, applies a fresh request with a new ID and reconstructs
the journal. Its 22 tests cover one-instance interleaving, replay/conflicting
intent, different run labels, malformed digests, faults, assessed risk changes,
source drift, reconstruction and existing carbon/storage integration.

## Scope and acceptance limits

This is a public consistency precondition, not a secret capability, signature,
operator approval or model/tool credential. Run labels are caller-selected and
not globally unique; independent instances using the same label/state can have
the same snapshot. The check reserves nothing across instances or processes.
The synchronous single-instance comparison is not a distributed lock, durable
reservation, authenticated command gateway or proof of physical completion.

The held-interval simulated clock does not expire snapshots with wall time.
Topology is the existing fixed REF01 topology; no dynamic topology-change model
is added. Future operational integration must require its own fresh-state,
identity, authorization, protection and durable execution contracts. This
offline fixture API is not exposed as a production tool, and its legacy unbound
path must not be mistaken for a qualified gateway.

The initial CLEAR bootstrap remains an unreviewed synthetic assumption. No real
engine, peer, device, provider, gateway, Large Model or RAG service is exercised.
FSGIM/OPC DI context stays provisional; carbon qualification stays unresolved.
Control remains DENY and all 43 integrated acceptance cases remain NOT_RUN,
including AC14's complete approval-to-execution contract. Required hardware
remains simulated; generic/template assets remain allowed in every case.
