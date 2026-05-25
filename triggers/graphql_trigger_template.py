"""
Machine → local-AI upstream trigger template.

This is the reference implementation for the "trigger sequence" carried in a
machine's `triggerConfig` metadata block.  When a machine asserts an output
whose `triggerOn` condition is satisfied, the dispatcher running on the
visualizer/perception side invokes this handler with an event shaped like:

    {
        "processState": {
            "id":     "RS-FLIPFLOP-TRIGGER",
            "name":   "RS Flipflop Trigger",
            "status": "warning" | "error" | "ok",
            ...
        },
        "context": {
            "sourceMachine":  "RSFlipFlopTrigger",
            "sourceSequence": "rs-set-sequence",
            "outputVector":   [1, 0],
            ...
        }
    }

and this module POSTs a GraphQL `updateProcessState` mutation to the local AI
endpoint (localAIStack `/graphql`).  The shape of the mutation matches the
strawberry schema in
`localAIStack/services/api/routers/graphql_endpoint.py`.

This file is intentionally a runnable *template*: it can be imported by an
in-process dispatcher or copied into a serverless handler.  The only external
dependency at runtime is `httpx`, which is already in the RE tooling.
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx


# ── Status code mapping ───────────────────────────────────────────────────────
# The RAG taxonomy (Red/Amber/Green) is the canonical vocabulary the receiver
# knows how to interpret.  Machines can override the mapping in their
# triggerConfig, but the defaults below cover the common cases.
GREEN = "GREEN"
AMBER = "AMBER"
RED = "RED"


DEFAULT_ENDPOINT = os.environ.get(
    "LOCAL_AI_GRAPHQL_URL", "http://localhost:4000/graphql",
)

MUTATION = """
mutation UpdateProcessState($input: UpdateProcessStateInput!) {
  updateProcessState(input: $input) {
    processState {
      id
      name
      status
      ragStatus {
        code
        description
      }
    }
  }
}
""".strip()


class TriggerError(RuntimeError):
    """Raised when the upstream GraphQL call fails or returns errors."""


def _status_to_rag_code(process_status: str | None) -> str:
    status = (process_status or "").lower()
    if status in {"error", "critical", "red"}:
        return RED
    if status in {"warning", "warn", "degraded", "amber"}:
        return AMBER
    return GREEN


def dispatch(event: dict[str, Any], *, endpoint: str | None = None,
             timeout_s: float = 5.0) -> dict[str, Any]:
    """
    Fire the upstream GraphQL mutation for the given machine-output event.

    Raises TriggerError on HTTP failure or GraphQL error; returns the
    `updateProcessState.processState` payload on success.
    """
    process_state = event.get("processState") or {}
    context = event.get("context") or {}

    rag_status_code = (
        event.get("ragStatusCode")
        or _status_to_rag_code(process_state.get("status"))
    )

    variables = {
        "input": {
            "id":             process_state.get("id") or "UNKNOWN",
            "name":           process_state.get("name"),
            "status":         process_state.get("status"),
            "ragStatusCode":  rag_status_code,
            "sourceMachine":  context.get("sourceMachine"),
            "sourceSequence": context.get("sourceSequence"),
            "context":        json.dumps(context) if context else None,
        }
    }

    url = endpoint or DEFAULT_ENDPOINT
    resp = httpx.post(
        url,
        json={"query": MUTATION, "variables": variables},
        timeout=timeout_s,
    )
    if resp.status_code >= 400:
        raise TriggerError(f"{resp.status_code} from {url}: {resp.text[:200]}")

    body = resp.json()
    if body.get("errors"):
        raise TriggerError(f"GraphQL errors: {body['errors']}")

    return body["data"]["updateProcessState"]["processState"]


# ── AWS-Lambda-compatible entrypoint ─────────────────────────────────────────
# Mirrors the Lambda handler signature from the spec so this file can be
# dropped into a Lambda/Fargate deployment without edits.  `context` is unused.
def lambda_handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    try:
        result = dispatch(event)
    except TriggerError as e:
        return {"statusCode": 502, "statusMessage": f"TRIGGER_FAILED: {e}"}
    return {
        "statusCode": 200,
        "statusMessage": "OK",
        "processState": result,
    }


if __name__ == "__main__":
    # Manual smoke test:
    #   python graphql_trigger_template.py
    # Expects localAIStack API running at $LOCAL_AI_GRAPHQL_URL.
    demo = {
        "processState": {
            "id": "RS-FLIPFLOP-TRIGGER",
            "name": "RS Flipflop Trigger (demo)",
            "status": "warning",
        },
        "context": {
            "sourceMachine": "RSFlipFlopTrigger",
            "sourceSequence": "rs-set-sequence",
            "outputVector": [1, 0],
        },
    }
    print(json.dumps(lambda_handler(demo), indent=2))
