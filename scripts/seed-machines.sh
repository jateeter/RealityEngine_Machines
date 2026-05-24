#!/bin/bash
# =============================================================================
# seed-machines.sh — POST all machine JSON files to a running RE instance
#
# Usage:
#   ./scripts/seed-machines.sh [RE_URL]
#
# RE_URL defaults to https://localhost:3000.
# Exits 0 if all machines seed successfully; non-zero on any hard failure.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MACHINES_ROOT="$SCRIPT_DIR/../machines"
RE_URL="${1:-https://localhost:3000}"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC} $*"; }
info() { echo -e "  $*"; }

# Collect all machine JSON files
MACHINE_FILES=()
while IFS= read -r _f; do MACHINE_FILES+=("$_f"); done < <(find "$MACHINES_ROOT" -name "*.json" | sort)

if [ "${#MACHINE_FILES[@]}" -eq 0 ]; then
    warn "No machine JSON files found in $MACHINES_ROOT"
    exit 0
fi

echo "Seeding ${#MACHINE_FILES[@]} machines → $RE_URL"
echo ""

SEEDED=0
SKIPPED=0
FAILED=0

for file in "${MACHINE_FILES[@]}"; do
    name=$(basename "$file" .json)

    RESP=$(curl -sk -o /tmp/_seed_resp.json -w "%{http_code}" \
        -X POST "$RE_URL/api/machines" \
        -H "Content-Type: application/json" \
        --data-binary "@$file" \
        --max-time 10 2>/dev/null || echo "000")

    case "$RESP" in
        200|201)
            ok "$name"
            SEEDED=$((SEEDED+1))
            ;;
        409)
            info "$name (already exists — skipped)"
            SKIPPED=$((SKIPPED+1))
            ;;
        *)
            BODY=$(cat /tmp/_seed_resp.json 2>/dev/null | head -c 120 || echo "")
            warn "$name — HTTP $RESP  $BODY"
            FAILED=$((FAILED+1))
            ;;
    esac
done

echo ""
echo "Result: $SEEDED seeded, $SKIPPED skipped, $FAILED failed"

[ "$FAILED" -gt 0 ] && exit 1 || exit 0
