#!/bin/bash
# Architecture-aware corpus validation before seeding or accepting new domains.
#
# Default mode is compatibility-safe: hard schema errors fail the build, while
# migration gaps such as legacy dispatchableAgent without agentBinding are
# reported as warnings.  Set STRICT_DOMAIN_CONTRACT=1 to make warnings fail.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

ARGS=("--machines-root" "$REPO_ROOT/machines")
if [ "${STRICT_DOMAIN_CONTRACT:-0}" != "0" ]; then
  ARGS+=("--strict")
fi

python3 "$SCRIPT_DIR/audit-corpus.py" "${ARGS[@]}" "$@"
