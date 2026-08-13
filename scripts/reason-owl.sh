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
# Report against this project's profile rather than ROBOT's default. The default
# encodes OBO Foundry publishing conventions — it raises 3,418 ERRORs on the
# generated ABoxes, 3,417 of them missing_label — and fails before `reason` ever
# runs, so the check with real value never executed. See semantics/robot-report-profile.txt
# and RealityEngine_Machines#46.
"$ROBOT" report --input "$WORKDIR/merged.owl" \
  --profile "$REPO_ROOT/semantics/robot-report-profile.txt" \
  --fail-on ERROR --output "$WORKDIR/report.tsv" || {
    echo "reason-owl: ROBOT report found ERROR-level problems:"
    head -40 "$WORKDIR/report.tsv"
    exit 1
  }
# Two reasoners, deliberately.
#
# ELK is fast and covers EL++ classification. It is NOT sufficient on its own
# here: it does not support functional properties, so it silently passes a
# corpus that violates this ontology's own headline invariant — an escalation
# action prescribed by a non-RED determination. Verified: ELK exits 0 on that
# case, HermiT exits 1.
#
# HermiT is the one that makes the audit axioms in re-core.ttl mean anything.
# On the health-personal corpus it costs ~3s against ELK's ~2s, so completeness
# is effectively free at this scale. If it ever becomes the bottleneck, keep
# HermiT and shard the ABoxes rather than dropping back to ELK alone.
"$ROBOT" reason --reasoner ELK --input "$WORKDIR/merged.owl" \
  --output "$WORKDIR/reasoned-elk.owl"
"$ROBOT" reason --reasoner HermiT --input "$WORKDIR/merged.owl" \
  --output "$WORKDIR/reasoned-hermit.owl"
echo "reason-owl: OK ($DOMAIN merged, reported, and reasoned consistently under ELK and HermiT)"
