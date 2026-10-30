"""Reference IFRS assertion boundary; PE integration must call this explicitly.

Values are categorical assertion tokens, not confidence or accounting measures.
A ValueError means no contribution and a failed-transformation analysis record
at the PE integration boundary, never substitution of zero.
"""
import math

def _number(value, top):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('Expected a finite number')
    if not math.isfinite(value) or not 0 <= value <= top:
        raise ValueError('Value outside declared range')
    return float(value)

def bound_native(value):
    return _number(value, 2) / 2

def canonicalize_bounded(value):
    value = _number(value, 1)
    if value < 0.25:
        return 0.0
    if value < 0.75:
        return 0.5
    return 1.0

def encode_native_lane(values):
    if len(values) != 8:
        raise ValueError('Expected eight input cells')
    return [canonicalize_bounded(bound_native(x)) for x in values]

def decode_assertion_lane(values):
    if len(values) != 4:
        raise ValueError('Expected four output cells')
    return [int(2 * canonicalize_bounded(x)) for x in values]

def precedence_max(contributions):
    """Reference fold over (determinism_rank, bounded_value), not a runtime API.

    Identity (0,0) represents no contributor; production observability must
    retain every tied and suppressed contribution's identity separately.
    """
    result = (0, 0.0)
    for rank, value in contributions:
        if isinstance(rank, bool) or rank not in (1, 2, 3):
            raise ValueError('Expected generated=1, measured=2 or deterministic=3')
        result = max(result, (rank, _number(value, 1)))
    return result
