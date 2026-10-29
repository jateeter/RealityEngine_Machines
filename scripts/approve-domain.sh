#!/opt/homebrew/bin/bash
# Versioned domain admission: read-only planning, gated preparation, PR publication,
# and a post-merge approval receipt. The Python helper preserves structured data.
set -euo pipefail
if (( BASH_VERSINFO[0] < 5 )); then
  echo 'Use /opt/homebrew/bin/bash (Bash 5 or newer).' >&2
  exit 2
fi
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/domain-approval/approval.py" "$@"
