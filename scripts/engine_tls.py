"""engine_tls — one TLS trust decision for scripts that reach a live engine.

The universe serves its RE/PE surfaces over TLS with certificates from the dev
CA in RealityEngine_CI/certs/ca.crt. urllib trusts only the system store, which
does not include that CA, so every https call from export-runtime-trace.py and
validate-runtime-trace.py failed with

    urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] unable to get local issuer certificate

and the four live trace tests in tests/contracts reported it as a contract
failure (RealityEngine_Machines#126). That is a harness problem, not a finding.

Policy — the same as RealityEngine_CI/scripts/lib/re_tls.py, so the two repos
cannot disagree about what "reached the engine" means:

  * trust the dev CA when it can be found and verified against — that is real
    verification, not verification switched off;
  * fall back to an unverified context only when the CA is absent, or present
    but unusable (no keyUsage extension: OpenSSL 3 refuses to verify against it;
    certs/generate-dev-certs.sh has emitted keyUsage since 2026-09-12, so an
    older CA should be regenerated). The fallback announces itself on stderr.

Where the CA is looked for: RE_CA_CERT, then CI_DIR/certs/ca.crt, then the
sibling RealityEngine_CI checkout next to this repo.
"""
from __future__ import annotations

import os
import ssl
import subprocess
import sys
from pathlib import Path

_WARNED = False
_CTX: ssl.SSLContext | None = None


def ca_path() -> str | None:
    candidates = [os.environ.get("RE_CA_CERT")]
    if os.environ.get("CI_DIR"):
        candidates.append(os.path.join(os.environ["CI_DIR"], "certs", "ca.crt"))
    candidates.append(str(Path(__file__).resolve().parents[2] / "RealityEngine_CI" / "certs" / "ca.crt"))
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None


def _ca_is_usable(ca: str) -> bool:
    try:
        out = subprocess.run(["openssl", "x509", "-in", ca, "-noout", "-ext", "keyUsage"],
                             capture_output=True, text=True, timeout=10)
        return "Key Usage" in (out.stdout or "")
    except Exception:  # noqa: BLE001 — no openssl, or an unreadable file
        return False


def _warn(msg: str) -> None:
    global _WARNED
    if not _WARNED:
        print(f"engine_tls: {msg}", file=sys.stderr)
        _WARNED = True


def tls_context() -> ssl.SSLContext:
    """The context every https call to an engine should use."""
    global _CTX
    if _CTX is not None:
        return _CTX
    ctx = ssl.create_default_context()
    ca = ca_path()
    if ca and _ca_is_usable(ca):
        ctx.load_verify_locations(ca)
    else:
        if ca:
            _warn(f"{ca} has no keyUsage extension, so OpenSSL cannot verify against it — "
                  "proceeding unverified. Regenerate with RealityEngine_CI/certs/generate-dev-certs.sh.")
        else:
            _warn("dev CA not found (set RE_CA_CERT or CI_DIR) — proceeding without certificate verification")
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    _CTX = ctx
    return ctx


def urlopen(req, timeout: float):
    """urllib.request.urlopen with the engine trust decision applied to https."""
    import urllib.request
    url = req.full_url if hasattr(req, "full_url") else str(req)
    if url.startswith("https://"):
        return urllib.request.urlopen(req, timeout=timeout, context=tls_context())
    return urllib.request.urlopen(req, timeout=timeout)
