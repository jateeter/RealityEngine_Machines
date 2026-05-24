#!/bin/bash
# =============================================================================
# validate-corpus.sh — schema-check all machine JSON files before seeding
#
# Checks each file for:
#   1. Valid JSON (parseable by python3)
#   2. Required top-level fields: id, name, ces
#   3. Non-empty id and name strings
#
# Usage:  ./scripts/validate-corpus.sh
# Exit:   0 on success, 1 if any file fails validation.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MACHINES_ROOT="$SCRIPT_DIR/../machines"

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $*"; }
fail() { echo -e "${RED}✗${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC} $*"; }

mapfile -t FILES < <(find "$MACHINES_ROOT" -name "*.json" | sort)

if [ "${#FILES[@]}" -eq 0 ]; then
    warn "No machine JSON files found in $MACHINES_ROOT"
    exit 0
fi

echo "Validating ${#FILES[@]} machine files..."
echo ""

PASS=0
FAIL=0

for file in "${FILES[@]}"; do
    rel="${file#$MACHINES_ROOT/}"
    RESULT=$(python3 - "$file" <<'PYEOF' 2>&1
import json, sys

path = sys.argv[1]
try:
    with open(path) as f:
        m = json.load(f)
except json.JSONDecodeError as e:
    print(f"INVALID_JSON: {e}")
    sys.exit(1)

errors = []
for field in ('id', 'name', 'ces'):
    if field not in m:
        errors.append(f"missing required field '{field}'")
    elif field in ('id', 'name') and not str(m[field]).strip():
        errors.append(f"'{field}' must be a non-empty string")

if errors:
    print("SCHEMA_ERROR: " + "; ".join(errors))
    sys.exit(1)

print(f"OK id={m['id']}")
PYEOF
    || true)

    if echo "$RESULT" | grep -q "^OK"; then
        ok "$rel  ($(echo "$RESULT" | sed 's/^OK //'))"
        PASS=$((PASS+1))
    else
        fail "$rel  — $RESULT"
        FAIL=$((FAIL+1))
    fi
done

echo ""
echo "Result: $PASS valid, $FAIL invalid"
[ "$FAIL" -gt 0 ] && exit 1 || exit 0
