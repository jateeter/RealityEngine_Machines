#!/bin/bash
# =============================================================================
# seed-machines.sh — POST all machine JSON files to RE and register
#                    TestSourceConfig entries in the PE.
#
# Usage:
#   ./scripts/seed-machines.sh [--re-only] [RE_URL] [PE_URL]
#
# RE_URL defaults to https://localhost:3000.
# PE_URL defaults to https://localhost:3004.
#
# Flags:
#   --re-only   Skip Phase 2 (PE TestSourceConfig binding).  Use when PE
#               sources will be materialised separately via the PE's own
#               POST /api/sources/bootstrap-from-machines endpoint.
#
# For each machine file:
#   1. POST machine definition (CES) to RE /api/machines
#   2. (unless --re-only) POST a TestSourceConfig to PE /api/sources
#      binding the machine's inputSequences to its perceptualMapping.input
#      region.  active=false so sources sit idle until explicitly started.
#
# Exits 0 if all machines seed successfully; non-zero on any hard failure.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MACHINES_ROOT="$SCRIPT_DIR/../machines"

RE_URL="https://localhost:3000"
PE_URL="https://localhost:3004"
RE_ONLY=false

_pos=0
for _arg in "$@"; do
  case "$_arg" in
    --re-only) RE_ONLY=true ;;
    --*) echo "Unknown flag: $_arg" >&2; exit 1 ;;
    *)
      _pos=$((_pos+1))
      case "$_pos" in
        1) RE_URL="$_arg" ;;
        2) PE_URL="$_arg" ;;
      esac
      ;;
  esac
done

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC} $*"; }
info() { echo -e "  $*"; }

# ── Audit log setup ────────────────────────────────────────────────────────────
SEED_LOG="${SEED_LOG:-$HOME/.realityengine/seed-audit.log}"
mkdir -p "$(dirname "$SEED_LOG")" 2>/dev/null || true
_SEED_TS=$(date -u +%FT%TZ 2>/dev/null || date +%FT%TZ)
_audit() { printf '%s\t%s\n' "$_SEED_TS" "$*" >> "$SEED_LOG" 2>/dev/null || true; }
_audit "RUN\tre=$RE_URL\tpe=$PE_URL"

# Collect all machine JSON files
MACHINE_FILES=()
while IFS= read -r _f; do MACHINE_FILES+=("$_f"); done < <(find "$MACHINES_ROOT" -name "*.json" | sort)

if [ "${#MACHINE_FILES[@]}" -eq 0 ]; then
    warn "No machine JSON files found in $MACHINES_ROOT"
    exit 0
fi

echo "Seeding ${#MACHINE_FILES[@]} machines → RE: $RE_URL  PE: $PE_URL"
echo ""

# ── Pre-flight 1: JSON schema validation ────────────────────────────────────
SCHEMA_ERRORS=0
for file in "${MACHINE_FILES[@]}"; do
    filename=$(basename "$file" .json)
    ERRS=$(python3 - "$file" <<'PYEOF' 2>/dev/null
import json, sys
path = sys.argv[1]
errs = []
try:
    with open(path) as f:
        data = json.load(f)
except Exception as e:
    print(f"JSON parse error: {e}")
    sys.exit(0)

if not isinstance(data.get('version'), str):
    errs.append("missing/invalid 'version'")
m = data.get('machine')
if not isinstance(m, dict):
    errs.append("missing 'machine' object")
    print('\n'.join(errs))
    sys.exit(0)
if not m.get('name'):
    errs.append("missing machine.name")
if 'description' not in m:
    errs.append("missing machine.description")
rule = m.get('arbiterRule', '')
if rule.upper() not in ('PASSTHROUGH', 'AND', 'OR'):
    errs.append(f"invalid machine.arbiterRule '{rule}' (must be PASSTHROUGH, AND, or OR)")
if not isinstance(m.get('sequences'), list):
    errs.append("machine.sequences must be an array")
print('\n'.join(errs))
PYEOF
)
    if [ -n "$ERRS" ]; then
        warn "$filename — schema errors:"
        while IFS= read -r line; do warn "  $line"; done <<< "$ERRS"
        SCHEMA_ERRORS=$((SCHEMA_ERRORS+1))
    fi
done
if [ "$SCHEMA_ERRORS" -gt 0 ]; then
    echo ""
    warn "Schema validation failed for $SCHEMA_ERRORS machine(s). Fix errors before seeding."
    exit 1
fi
ok "Schema validation passed (${#MACHINE_FILES[@]} files)"

# ── Pre-flight 2: perceptual interconnect validation ────────────────────────
INTERCONNECT_ISSUES=$(python3 - "${MACHINE_FILES[@]}" <<'PYEOF' 2>/dev/null
import json, sys
files = sys.argv[1:]
name_to_pm = {}
for path in files:
    with open(path) as f:
        data = json.load(f)
    m = data.get('machine', {})
    name_to_pm[m.get('name', '')] = m.get('perceptualMapping', {})

for path in files:
    with open(path) as f:
        data = json.load(f)
    m = data.get('machine', {})
    name   = m.get('name', '')
    up_out = m.get('perceptualMapping', {}).get('output')
    if not up_out:
        continue
    for ds_name in m.get('metadata', {}).get('downstreamMachines', []):
        ds_pm = name_to_pm.get(ds_name)
        if ds_pm is None:
            print(f"{name}: downstream '{ds_name}' not found in corpus")
            continue
        ds_in = ds_pm.get('input')
        if ds_in is None:
            print(f"{name} → {ds_name}: downstream has no perceptualMapping.input")
            continue
        if up_out.get('offset') != ds_in.get('offset') or up_out.get('length') != ds_in.get('length'):
            print(f"{name} output {up_out} ≠ {ds_name} input {ds_in}")
PYEOF
)
if [ -n "$INTERCONNECT_ISSUES" ]; then
    warn "Interconnect region mismatches:"
    while IFS= read -r line; do warn "  $line"; done <<< "$INTERCONNECT_ISSUES"
    echo ""
else
    ok "Interconnect validation passed"
fi
echo ""

# Fetch existing PE test source names once for idempotency checks (skipped in --re-only mode)
PE_TEST_NAMES=""
if [ "$RE_ONLY" = false ]; then
PE_TEST_NAMES=$(curl -sk "$PE_URL/api/sources" --max-time 5 2>/dev/null \
    | python3 -c "
import json, sys
try:
    sources = json.load(sys.stdin).get('sources', [])
    names = [s['name'] for s in sources if s.get('type') == 'test']
    print('\n'.join(names))
except Exception:
    pass
" 2>/dev/null || true)
fi

RE_SEEDED=0
RE_SKIPPED=0
RE_FAILED=0
PE_BOUND=0
PE_SKIPPED=0
PE_FAILED=0

for file in "${MACHINE_FILES[@]}"; do
    filename=$(basename "$file" .json)

    # ── Phase 1: seed machine to RE ─────────────────────────────────────────
    RESP=$(curl -sk -o /tmp/_seed_resp.json -w "%{http_code}" \
        -X POST "$RE_URL/api/machines" \
        -H "Content-Type: application/json" \
        --data-binary "@$file" \
        --max-time 10 2>/dev/null || echo "000")

    MACHINE_ID=""
    case "$RESP" in
        200|201)
            MACHINE_ID=$(python3 -c "
import json, sys
try:
    print(json.load(open('/tmp/_seed_resp.json')).get('id',''))
except Exception:
    print('')
" 2>/dev/null || true)
            RE_SEEDED=$((RE_SEEDED+1))
            _audit "SEEDED\t$filename\t$MACHINE_ID"
            ;;
        409)
            # Already in RE — still need to check PE binding
            MACHINE_ID=$(python3 -c "
import json, sys
try:
    print(json.load(open('/tmp/_seed_resp.json')).get('id',''))
except Exception:
    print('')
" 2>/dev/null || true)
            RE_SKIPPED=$((RE_SKIPPED+1))
            _audit "SKIPPED\t$filename\t$MACHINE_ID"
            ;;
        *)
            BODY=$(cat /tmp/_seed_resp.json 2>/dev/null | head -c 120 || echo "")
            warn "$filename — RE HTTP $RESP  $BODY"
            RE_FAILED=$((RE_FAILED+1))
            _audit "FAILED\t$filename\tre_http=$RESP"
            continue
            ;;
    esac

    # ── Phase 2: register TestSourceConfig in PE ────────────────────────────
    # Skipped when --re-only is set; use pe-source-bootstrap.sh instead.
    [ "$RE_ONLY" = true ] && continue

    PE_BODY=$(python3 - "$file" "$MACHINE_ID" <<'PYEOF' 2>/dev/null
import json, sys

path       = sys.argv[1]
machine_id = sys.argv[2]

with open(path) as f:
    data = json.load(f)

machine = data['machine']
name    = machine['name']
pm      = machine.get('perceptualMapping', {}).get('input', {})
offset  = pm.get('offset')
length  = pm.get('length')

if offset is None or length is None:
    sys.exit(2)   # real schema problem — report as failure

inputs = []
for seq in machine.get('inputSequences', []):
    for vec in seq.get('vectors', []):
        inputs.append([float(v) for v in vec])

if not inputs:
    sys.exit(1)   # no test sequences (topology/aggregator) — skip silently

body = {
    "type":         "test",
    "name":         name,
    "region":       {"offset": offset, "length": length},
    "active":       False,
    "machineId":    machine_id,
    "machineName":  name,
    "sequenceName": "all",
    "inputs":       inputs,
    "loop":         True,
}
print(json.dumps(body))
PYEOF
)
    _pe_gen_exit=$?

    if [ "$_pe_gen_exit" -eq 1 ]; then
        PE_SKIPPED=$((PE_SKIPPED+1))
        [ "$RESP" = "409" ] && info "$filename (RE: exists, PE: no test sequences)" \
                             || info "$filename (PE: no test sequences — skipped)"
        continue
    fi

    if [ -z "$PE_BODY" ] || [ "$_pe_gen_exit" -gt 1 ]; then
        warn "$filename — PE body generation failed (missing perceptualMapping)"
        PE_FAILED=$((PE_FAILED+1))
        continue
    fi

    MACHINE_NAME=$(echo "$PE_BODY" | python3 -c "import json,sys; print(json.load(sys.stdin)['name'])" 2>/dev/null || echo "$filename")

    # Skip if a test source with this name already exists in PE
    if echo "$PE_TEST_NAMES" | grep -qxF "$MACHINE_NAME" 2>/dev/null; then
        PE_SKIPPED=$((PE_SKIPPED+1))
        [ "$RESP" = "409" ] && info "$filename (RE: exists, PE: exists)" || ok "$filename  →  PE: exists"
        continue
    fi

    PE_RESP=$(echo "$PE_BODY" | curl -sk -o /tmp/_pe_seed_resp.json -w "%{http_code}" \
        -X POST "$PE_URL/api/sources" \
        -H "Content-Type: application/json" \
        --data-binary @- \
        --max-time 10 2>/dev/null || echo "000")

    case "$PE_RESP" in
        200|201)
            PE_BOUND=$((PE_BOUND+1))
            if [ "$RESP" = "409" ]; then
                info "$filename (RE: exists, PE: bound)"
            else
                ok "$filename"
            fi
            ;;
        *)
            PE_BODY_ERR=$(cat /tmp/_pe_seed_resp.json 2>/dev/null | head -c 120 || echo "")
            warn "$filename — PE HTTP $PE_RESP  $PE_BODY_ERR"
            PE_FAILED=$((PE_FAILED+1))
            ;;
    esac
done

echo ""
echo "RE  — seeded: $RE_SEEDED  skipped: $RE_SKIPPED  failed: $RE_FAILED"
if [ "$RE_ONLY" = false ]; then
  echo "PE  — bound:  $PE_BOUND   skipped: $PE_SKIPPED  failed: $PE_FAILED"
else
  echo "PE  — skipped (--re-only; use pe-source-bootstrap.sh for PE source binding)"
fi

_audit "SUMMARY\tre_seeded=$RE_SEEDED\tre_skipped=$RE_SKIPPED\tre_failed=$RE_FAILED\tpe_bound=$PE_BOUND\tpe_skipped=$PE_SKIPPED\tpe_failed=$PE_FAILED"
echo "  Audit log: $SEED_LOG"

[ "$RE_FAILED" -gt 0 ] || [ "$PE_FAILED" -gt 0 ] && exit 1 || exit 0
