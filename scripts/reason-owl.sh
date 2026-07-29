#!/bin/bash
# Reasoner-based validation of the OWL semantics layer (roadmap milestone M3).
#
# Merges the core ontology with generated ABoxes and runs ROBOT report +
# reason (ELK by default) to catch inconsistencies that the structural
# contract tests cannot, e.g. an escalation action prescribed by a non-RED
# determination contradicting re:EscalationDetermination.
#
# ROBOT (https://robot.obolibrary.org) is an external toolchain and is not a
# developer-laptop requirement: without it this script prints SKIPPED and
# exits 0. CI containers install ROBOT and set ROBOT_BIN (or put `robot` on
# PATH) to make the gate real; see RealityEngine_CI.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ROBOT="${ROBOT_BIN:-robot}"
DOMAIN="${1:-health-personal}"

if ! command -v "$ROBOT" >/dev/null 2>&1; then
  echo "reason-owl: SKIPPED (ROBOT not installed; set ROBOT_BIN or add 'robot' to PATH)"
  exit 0
fi

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

python3 "$SCRIPT_DIR/generate-owl.py" --domain "$DOMAIN" --write --strict-actions >/dev/null

MERGE_INPUTS=(--input "$REPO_ROOT/semantics/ontology/re-core.ttl")
for abox in "$REPO_ROOT/semantics/abox/$DOMAIN"/*.ttl; do
  MERGE_INPUTS+=(--input "$abox")
done

"$ROBOT" merge "${MERGE_INPUTS[@]}" --output "$WORKDIR/merged.owl"
"$ROBOT" report --input "$WORKDIR/merged.owl" \
  --fail-on ERROR --output "$WORKDIR/report.tsv" || {
    echo "reason-owl: ROBOT report found ERROR-level problems:"
    head -40 "$WORKDIR/report.tsv"
    exit 1
  }
"$ROBOT" reason --reasoner ELK --input "$WORKDIR/merged.owl" \
  --output "$WORKDIR/reasoned.owl"
echo "reason-owl: OK ($DOMAIN merged, reported, and reasoned consistently)"
