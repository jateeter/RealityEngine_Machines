#!/usr/bin/env python3
"""A determination that escalates must state its RAG status explicitly.

## Why this exists

`re:EscalationDetermination` forbids dispatching an escalating action from a
determination whose RAG status contradicts it. The axiom is open-world on
purpose: an *unstated* status is not a contradiction, because a reasoner infers
the RED the axiom requires. Only an explicit non-RED value is a violation.

That is correct for OWL and it is also how the guardrail came to protect almost
nothing. Measured on the full corpus before this gate existed: **78 of the 80
escalating output events carried no `ragStatusCode` on the determination at
all.** Only `FallDetection`'s two `emergency-dispatch` events did. The audit
invariant was running, passing, and evaluating two cases out of eighty — and
from outside, "unstated" and "correctly RED" look identical.

The information was not missing. All 78 had a `ragStatusCode` on the machine's
`metadata.triggerConfig.rules[]` entry for that sequence, and propagating it
revealed 28 determinations whose rule said GREEN or AMBER while prescribing an
escalating action — the exact contradiction the guardrail forbids, invisible for
as long as the status stayed on the rule.

So the OWL axiom stays open-world, and the corpus side is closed here instead:
a determination that escalates must say what it is. "Nobody said" stops being
indistinguishable from RED at the point where a human authors it.

## What it enforces

1. An escalating determination carries an explicit `ragStatusCode`.
2. That status is RED. A non-RED escalation is the contradiction itself, and it
   is caught here rather than only at reasoning time.
3. Where the sequence also has a trigger rule, the rule agrees with the
   determination. The determination is authoritative (issue #145); the rule
   mirrors it. Two places holding the same fact is how they came to disagree.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MACHINES = REPO / "machines"

ESCALATING_ACTIONS = {"urgent-intervention", "emergency-dispatch"}


def _iter_escalating_determinations():
    """(relFile, machineName, sequenceId, determination metadata, trigger rule)."""
    for path in sorted(MACHINES.rglob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001  — schema validity is another gate's job
            continue
        machine = doc.get("machine")
        if not isinstance(machine, dict):
            continue
        rules = {
            r.get("sequenceId"): r
            for r in ((machine.get("metadata") or {}).get("triggerConfig") or {}).get("rules", [])
            or []
        }
        for seq in machine.get("sequences") or []:
            rule = rules.get(seq.get("id")) or {}
            for event in seq.get("events") or []:
                for out in event.get("outputEvents") or []:
                    meta = out.get("metadata") or {}
                    if meta.get("action") in ESCALATING_ACTIONS:
                        yield (
                            str(path.relative_to(MACHINES)),
                            machine.get("name"),
                            seq.get("id"),
                            meta,
                            rule,
                        )


class EscalationRagStatus(unittest.TestCase):
    def test_escalating_determination_states_a_rag_status(self) -> None:
        """Unstated is not permitted where a human authored the escalation.

        The reasoner may infer RED from silence; an author may not rely on that.
        """
        missing = [
            f"{rel} :: {seq} ({meta.get('action')})"
            for rel, _name, seq, meta, _rule in _iter_escalating_determinations()
            if not meta.get("ragStatusCode")
        ]
        self.assertEqual(
            [], missing,
            f"{len(missing)} escalating determination(s) state no ragStatusCode. "
            f"The OWL axiom would infer RED and pass, which is why this must be "
            f"caught here instead:\n  " + "\n  ".join(missing[:20]))

    def test_escalating_determination_is_red(self) -> None:
        """A non-RED escalation is the contradiction the guardrail forbids."""
        wrong = [
            f"{rel} :: {seq} ({meta.get('action')} from {meta.get('ragStatusCode')})"
            for rel, _name, seq, meta, _rule in _iter_escalating_determinations()
            if meta.get("ragStatusCode") and meta.get("ragStatusCode") != "RED"
        ]
        self.assertEqual(
            [], wrong,
            f"{len(wrong)} escalating determination(s) assert a non-RED status:\n  "
            + "\n  ".join(wrong[:20]))

    def test_trigger_rule_mirrors_the_determination(self) -> None:
        """The determination is authoritative; the rule must not disagree.

        Both carried the status independently, and that is how 28 of them came
        to contradict each other without anything noticing.
        """
        disagree = [
            f"{rel} :: {seq} (determination {meta.get('ragStatusCode')} "
            f"!= rule {rule.get('ragStatusCode')})"
            for rel, _name, seq, meta, rule in _iter_escalating_determinations()
            if rule.get("ragStatusCode")
            and meta.get("ragStatusCode")
            and rule["ragStatusCode"] != meta["ragStatusCode"]
        ]
        self.assertEqual(
            [], disagree,
            f"{len(disagree)} trigger rule(s) disagree with their determination:\n  "
            + "\n  ".join(disagree[:20]))

    def test_the_gate_is_actually_reaching_the_corpus(self) -> None:
        """A gate that inspects nothing passes for the same reason a clean one does.

        This is the failure the guardrail itself had: running, passing, and
        evaluating two cases out of eighty. Assert the walk finds escalations at
        all, so a future refactor that breaks the traversal fails loudly rather
        than reporting health.
        """
        found = list(_iter_escalating_determinations())
        self.assertGreater(
            len(found), 50,
            f"only {len(found)} escalating determination(s) found in the corpus; "
            f"the traversal is probably broken rather than the corpus empty")


if __name__ == "__main__":
    unittest.main()
