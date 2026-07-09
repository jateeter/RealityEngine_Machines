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
python3 "$SCRIPT_DIR/inventory-semantic-buses.py" --check --summary-only
python3 "$SCRIPT_DIR/build-corpus-index.py" --check
python3 "$SCRIPT_DIR/build-region-allocation.py" --check

# JSON-Schema enforcement (machines + registries + trigger files vs schemas/).
# Requires devDependencies (ajv); skip with a clear notice if not installed so
# the Python audit still runs in minimal environments.
if [ -d "$REPO_ROOT/node_modules/ajv" ]; then
  node "$SCRIPT_DIR/validate-schemas.mjs"
else
  echo "validate-schemas: SKIPPED (run 'npm install' to enable ajv JSON-Schema enforcement)"
fi
