"""Where is the instance registry? The same order as RealityEngine_CI's
scripts/lib/registry-url.sh:

  1. RE_REGISTRY_URL, when set.
  2. RealityEngine_CI/.universe-registry-url — startUniverse.sh writes the
     address the running universe serves there; stopUniverse.sh removes it.
     The CI checkout is REALITY_ENGINE_CI_DIR, else the sibling directory.
  3. http://127.0.0.1:${RE_REGISTRY_PORT:-5999}/re-registry.json.

5999 is the shim's port only with fixed ports; under --free-ports it is
OS-assigned, and a literal :5999 fallback looked where nothing listened.
"""
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def registry_url() -> str:
    env = os.environ.get("RE_REGISTRY_URL", "").strip()
    if env:
        return env
    ci_dir = Path(os.environ.get("REALITY_ENGINE_CI_DIR") or REPO_ROOT.parent / "RealityEngine_CI")
    try:
        first = (ci_dir / ".universe-registry-url").read_text().splitlines()[0].strip()
    except (OSError, IndexError):
        first = ""
    if first:
        return first
    return f"http://127.0.0.1:{os.environ.get('RE_REGISTRY_PORT', '5999')}/re-registry.json"
