"""Reading corpus machine structure while the schema keys are mid-rename.

RealityEngine_CI#220 layer 1 renames the three keys that describe a machine's
event structure:

    vectors        -> events
    outputVectors  -> outputEvents
    nextVectorIds  -> nextEventIds

The corpus in this repository carries the canonical spelling as of layer 1b.
Other corpora do not yet — `localAIStack/data/machines` is loaded by the same
tooling, machines arrive from generators and fixtures, and the four runtimes
accept both spellings for the duration of layer 1. So the readers here accept
both too, and layer 1c deletes this module when the tolerance retires.

## Why a module rather than `seq.get("events") or seq.get("vectors")`

Because the failure is silent. Every one of these reads is a `.get()` with a
default, so a reader looking for the wrong spelling does not raise — it gets an
empty list and carries on. That is not hypothetical: the first attempt at the
layer 1b corpus rewrite left `inventory-semantic-buses.py` reading
`outputVectors`, and it regenerated `semantic-bus-registry.json` **1276 lines
shorter**, reporting success. The registry would have been silently emptied of
every output semantic in the corpus.

Routing the reads through named functions makes them greppable, gives the
tolerance one place to live, and makes the eventual deletion a single change.
"""
from __future__ import annotations

from typing import Any


def _as_list(value: Any) -> list:
    """A list, or empty — never None, and never a non-iterable."""
    return value if isinstance(value, list) else []


def sequence_events(sequence: Any) -> list:
    """The events of a sequence (`events`, or the pre-#220 `vectors`)."""
    if not isinstance(sequence, dict):
        return []
    events = sequence.get("events")
    return _as_list(events if events is not None else sequence.get("vectors"))


def output_events(event: Any) -> list:
    """The outputs an event fires (`outputEvents`, or pre-#220 `outputVectors`)."""
    if not isinstance(event, dict):
        return []
    outputs = event.get("outputEvents")
    return _as_list(outputs if outputs is not None else event.get("outputVectors"))


def next_event_ids(event: Any) -> list:
    """The ids an event arms (`nextEventIds`, or pre-#220 `nextVectorIds`)."""
    if not isinstance(event, dict):
        return []
    nxt = event.get("nextEventIds")
    return _as_list(nxt if nxt is not None else event.get("nextVectorIds"))
