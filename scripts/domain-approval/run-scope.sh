#!/opt/homebrew/bin/bash
# Concrete CI scope driver. Called by approve-domain.sh with request and output.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/scope.py" "$@"
