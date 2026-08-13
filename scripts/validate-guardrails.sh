#!/bin/bash
# Conformance gate for the ingress/egress semantic guardrails.
#
# Validates semantics/shapes/fixtures/cases.trig against
# semantics/shapes/re-guardrails.shacl.ttl and checks every accept/reject
# decision against semantics/shapes/fixtures/cases.json.
#
# pyshacl is an external toolchain and is not a developer-laptop requirement:
# without it this script prints SKIPPED and exits 0, mirroring reason-owl.sh.
# CI containers install pyshacl (or set PYSHACL_PYTHON to an interpreter that
# has it) to make the gate real.
#
# See docs/SEMANTIC_GUARDRAIL_CONTRACT.md.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYSHACL_PYTHON:-python3}"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "validate-guardrails: SKIPPED (no python3; set PYSHACL_PYTHON)"
  exit 0
fi

if ! "$PYTHON" -c "import pyshacl" >/dev/null 2>&1; then
  echo "validate-guardrails: SKIPPED (pyshacl not installed; pip install pyshacl, or set PYSHACL_PYTHON)"
  exit 0
fi

exec "$PYTHON" "$SCRIPT_DIR/validate_guardrails.py" "$@"
