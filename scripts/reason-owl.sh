#!/bin/bash
# Reasoner-based validation of the OWL semantics layer (roadmap milestone M3).
#
# Merges the core ontology with generated ABoxes and runs ROBOT report + reason
# to catch inconsistencies the structural contract tests cannot, e.g. an
# escalation action prescribed by a non-RED determination contradicting
# re:EscalationDetermination.
#
# Usage:
#   reason-owl.sh [DOMAIN]                 one domain, ELK + HermiT   (~5-20s)
#   reason-owl.sh --all                    whole corpus, ELK only     (~45s)
#   reason-owl.sh --all --reasoner both    whole corpus, + HermiT     (~18min)
#   reason-owl.sh --all --reasoner hermit  whole corpus, HermiT only
#
# ROBOT (https://robot.obolibrary.org) is an external toolchain and is not a
# developer-laptop requirement: without it this script prints SKIPPED and
# exits 0. CI containers install ROBOT and set ROBOT_BIN (or put `robot` on
# PATH) to make the gate real; see RealityEngine_CI.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ROBOT="${ROBOT_BIN:-robot}"

SCOPE="domain"
DOMAIN="health-personal"
REASONER=""

while [ $# -gt 0 ]; do
  case "$1" in
    --all)          SCOPE="corpus"; shift ;;
    --reasoner)     REASONER="$(printf '%s' "$2" | tr '[:upper:]' '[:lower:]')"; shift 2 ;;
    --reasoner=*)   REASONER="$(printf '%s' "${1#*=}" | tr '[:upper:]' '[:lower:]')"; shift ;;
    -h|--help)      sed -n '6,12p' "$0"; exit 0 ;;
    -*)             echo "reason-owl: unknown option $1" >&2; exit 2 ;;
    *)              DOMAIN="$1"; SCOPE="domain"; shift ;;
  esac
done

# Reasoner defaults differ by scope, and the asymmetry is the point.
#
# Per domain, HermiT costs ~1.5x ELK — a few seconds — so both always run and
# the gate keeps full completeness on every change. Sharding is what makes that
# affordable: twelve domains under both reasoners is ~3 minutes.
#
# Corpus-wide, HermiT is 88x ELK: 1,061s against 12s on the 1,120,783-line
# merged graph. It defaults off there and is scheduled instead (weekly, plus
# on-demand) rather than run per change. What the merged graph tests that the
# shards cannot is cross-domain contradiction — today the machine IRI scheme
# (.../machines/<domain>/<stem>#) makes domains share no individuals, so there
# is nothing for it to find. That is a property of the corpus as it stands now,
# not a permanent one: as cross-domain interaction grows, this run is what will
# notice, so it is scheduled rather than dropped. Raise its frequency when
# cross-domain interaction increases. See RealityEngine_Machines#79.
if [ -z "$REASONER" ]; then
  case "$SCOPE" in
    domain) REASONER="both" ;;
    corpus) REASONER="elk" ;;
  esac
fi
case "$REASONER" in
  elk|hermit|both) ;;
  *) echo "reason-owl: --reasoner must be elk, hermit or both (got '$REASONER')" >&2; exit 2 ;;
esac

if ! command -v "$ROBOT" >/dev/null 2>&1; then
  echo "reason-owl: SKIPPED (ROBOT not installed; set ROBOT_BIN or add 'robot' to PATH)"
  exit 0
fi

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

MERGE_INPUTS=(--input "$REPO_ROOT/semantics/ontology/re-core.ttl")
if [ "$SCOPE" = "corpus" ]; then
  LABEL="corpus (12 domains)"
  # The merged graph is ~96MB in memory and the default JVM heap will not hold
  # it. Only set a default if the caller has not: a runner with less than this
  # available needs to say so rather than be told.
  export ROBOT_JAVA_ARGS="${ROBOT_JAVA_ARGS:--Xmx12g}"
  python3 "$SCRIPT_DIR/generate-owl.py" --all --write --strict-actions >/dev/null
  while IFS= read -r abox; do
    MERGE_INPUTS+=(--input "$abox")
  done < <(find "$REPO_ROOT/semantics/abox" -name '*.ttl' | sort)
else
  LABEL="$DOMAIN"
  if [ ! -d "$REPO_ROOT/semantics/abox/$DOMAIN" ] &&
     [ ! -d "$REPO_ROOT/machines/domains/$DOMAIN" ]; then
    echo "reason-owl: unknown domain '$DOMAIN'" >&2
    exit 2
  fi
  python3 "$SCRIPT_DIR/generate-owl.py" --domain "$DOMAIN" --write --strict-actions >/dev/null
  for abox in "$REPO_ROOT/semantics/abox/$DOMAIN"/*.ttl; do
    MERGE_INPUTS+=(--input "$abox")
  done
fi

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

# ELK is fast and covers EL++ classification. It is NOT sufficient on its own:
# it does not implement functional properties, so it silently passes graphs that
# violate this ontology's own invariants. That is not hypothetical — it is how a
# non-injective trigger-rule IRI survived, asserting GREEN, AMBER and RED on the
# functional re:hasRagStatus. HermiT rejected it; ELK exited 0 (#65).
#
# So HermiT is what makes the audit axioms in re-core.ttl mean anything, and any
# run that omits it is a smoke test rather than a completeness claim.
RAN=()
if [ "$REASONER" = "elk" ] || [ "$REASONER" = "both" ]; then
  "$ROBOT" reason --reasoner ELK --input "$WORKDIR/merged.owl" \
    --output "$WORKDIR/reasoned-elk.owl"
  RAN+=("ELK")
fi
if [ "$REASONER" = "hermit" ] || [ "$REASONER" = "both" ]; then
  "$ROBOT" reason --reasoner HermiT --input "$WORKDIR/merged.owl" \
    --output "$WORKDIR/reasoned-hermit.owl"
  RAN+=("HermiT")
fi

if [ "$REASONER" = "elk" ]; then
  echo "reason-owl: OK ($LABEL merged, reported, and reasoned consistently under ELK)"
  echo "reason-owl: NOTE ELK does not implement functional properties — this is a"
  echo "            well-formedness check, not a completeness claim. HermiT covers"
  echo "            that, scheduled separately (#79)."
else
  echo "reason-owl: OK ($LABEL merged, reported, and reasoned consistently under ${RAN[*]})"
fi
