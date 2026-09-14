#!/bin/bash
# Interpreter hook for extract-qudt-subset.py.
#
# rdflib is an external toolchain and is not a developer-laptop requirement:
# without it this prints SKIPPED and exits 0, mirroring reason-owl.sh and
# validate-guardrails.sh. CI containers install rdflib, or set QUDT_PYTHON to an
# interpreter that has it, to make the gate real.
#
# This wrapper exists because the gate was unreachable in a way installing the
# package did not fix. `validate-corpus.sh` invoked the script with a bare
# `python3`, so on a host whose system interpreter is PEP 668
# externally-managed — Homebrew's python@3.14 here — rdflib cannot be installed
# into it and the gate skipped forever. validate-guardrails.sh already solved
# this with PYSHACL_PYTHON; this is the same solution for the same problem,
# rather than a second mechanism.
#
# See docs/SEMANTIC_OWL_ROADMAP.md.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${QUDT_PYTHON:-${PYSHACL_PYTHON:-python3}}"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "extract-qudt-subset: SKIPPED (no python3; set QUDT_PYTHON)"
  exit 0
fi

if ! "$PYTHON" -c "import rdflib" >/dev/null 2>&1; then
  echo "extract-qudt-subset: SKIPPED (rdflib not installed; pip install rdflib, or set QUDT_PYTHON)"
  exit 0
fi

exec "$PYTHON" "$SCRIPT_DIR/extract-qudt-subset.py" "$@"
