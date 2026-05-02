# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Behavioral fingerprint canonicalization and computation.

The NERVE preprint declares ``AgentNeuron.behavioral_fingerprint`` as
"a SHA-256 integrity tag over the canonical serialization of the agent's
output-distribution embedding vector." Until this module existed, the
canonical form was unspecified, so two compliant implementations could
produce different hashes for the same embedding and a third-party
validator had no way to verify a claimed fingerprint.

This module pins the canonical form so any party holding the embedding
can recompute the same hex digest.

## Wire format

```
behavioral_fingerprint := "sha256:" <64-hex>
```

## Canonicalization (FINGERPRINT_VERSION = "v1")

Input is a real-valued embedding vector ``e = [e_0, e_1, ..., e_{n-1}]``
of length ``n >= 1``.

1. Round each ``e_i`` to ``FINGERPRINT_PRECISION`` (= 6) decimal places using
   banker's rounding (Python's default ``round``).
2. Format each rounded value as a fixed-precision string with exactly
   ``FINGERPRINT_PRECISION`` digits after the decimal point. Negative zero
   is normalized to positive zero. The locale is C; the decimal separator
   is ``"."``. No exponent notation. Examples: ``0.123456``, ``-0.000123``,
   ``42.000000``.
3. Wrap the strings in a JSON array using ``json.dumps`` with
   ``separators=(",", ":")`` to produce a single-line, whitespace-free
   serialization. The array preserves the original index order; do NOT
   sort.
4. UTF-8 encode the JSON.
5. Compute SHA-256 of the encoded bytes; take the lowercase hex digest.
6. Prefix with ``"sha256:"`` to match the format used by ACAP
   ``policy_hash`` and Phala ``context_hash``.

The version tag ``FINGERPRINT_VERSION`` is embedded in the hash domain by
prepending ``"nerve-fp/v1\\n"`` to the canonical bytes before hashing, so
future versions can rotate without colliding with v1 hashes.
"""

from __future__ import annotations

import hashlib
import json
from typing import Sequence


FINGERPRINT_VERSION = "v1"
FINGERPRINT_PRECISION = 6
FINGERPRINT_DOMAIN_TAG = b"nerve-fp/v1\n"


def _canonical_components(embedding: Sequence[float]) -> list[str]:
    if len(embedding) == 0:
        raise ValueError("behavioral fingerprint embedding must be non-empty")
    out: list[str] = []
    for x in embedding:
        rounded = round(float(x), FINGERPRINT_PRECISION)
        # Normalize negative zero to positive zero. Without this, the
        # ``%.6f`` formatter emits ``-0.000000`` for ``-0.0`` while
        # producing ``0.000000`` for ``0.0`` — breaking the documented
        # invariant that ``[0.0]`` and ``[-0.0]`` hash to the same value.
        # ``+ 0.0`` collapses negative zero to positive zero per IEEE 754.
        if rounded == 0.0:
            rounded = rounded + 0.0  # forces +0.0
        out.append(f"{rounded:.{FINGERPRINT_PRECISION}f}")
    return out


def canonical_fingerprint_bytes(embedding: Sequence[float]) -> bytes:
    """Return the exact bytes that get hashed.

    Exposed primarily so tests can assert the canonical form matches the
    documented contract.
    """
    components = _canonical_components(embedding)
    payload = json.dumps(components, separators=(",", ":")).encode("utf-8")
    return FINGERPRINT_DOMAIN_TAG + payload


def compute_behavioral_fingerprint(embedding: Sequence[float]) -> str:
    """Compute the canonical ``sha256:<hex>`` fingerprint for an embedding.

    Stable across implementations: any party with the same embedding
    vector produces the same string.
    """
    digest = hashlib.sha256(canonical_fingerprint_bytes(embedding)).hexdigest()
    return f"sha256:{digest}"


def verify_behavioral_fingerprint(
    claimed: str, embedding: Sequence[float]
) -> bool:
    """True iff ``claimed`` matches the canonical fingerprint for ``embedding``.

    Constant-time comparison to avoid leaking via response-time signals
    on collision attempts.
    """
    expected = compute_behavioral_fingerprint(embedding)
    if len(expected) != len(claimed):
        return False
    diff = 0
    for a, b in zip(expected.encode("utf-8"), claimed.encode("utf-8")):
        diff |= a ^ b
    return diff == 0


def is_well_formed_fingerprint(value: str) -> bool:
    """Cheap structural check: does this string look like a NERVE fingerprint?

    Used by validators that lack the embedding (so cannot recompute) but
    can still reject obviously malformed values.
    """
    if not isinstance(value, str):
        return False
    if not value.startswith("sha256:"):
        return False
    hex_part = value[len("sha256:") :]
    if len(hex_part) != 64:
        return False
    try:
        int(hex_part, 16)
    except ValueError:
        return False
    return True
