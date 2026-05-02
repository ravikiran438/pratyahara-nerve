# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Tests for the canonical behavioral fingerprint algorithm."""

from __future__ import annotations

import hashlib

import pytest

from nerve.types import (
    FINGERPRINT_PRECISION,
    FINGERPRINT_VERSION,
    canonical_fingerprint_bytes,
    compute_behavioral_fingerprint,
    is_well_formed_fingerprint,
    verify_behavioral_fingerprint,
)


def test_fingerprint_format_is_sha256_prefixed_64_hex():
    fp = compute_behavioral_fingerprint([0.1, 0.2, 0.3])
    assert fp.startswith("sha256:")
    assert len(fp) == len("sha256:") + 64
    int(fp[len("sha256:") :], 16)  # raises if non-hex


def test_fingerprint_is_deterministic():
    a = compute_behavioral_fingerprint([0.1, 0.2, 0.3])
    b = compute_behavioral_fingerprint([0.1, 0.2, 0.3])
    assert a == b


def test_fingerprint_changes_with_perturbed_value_above_precision():
    a = compute_behavioral_fingerprint([0.1, 0.2, 0.3])
    b = compute_behavioral_fingerprint([0.1, 0.2, 0.300001])
    assert a != b


def test_fingerprint_stable_within_precision():
    """Sub-precision noise is rounded away."""
    a = compute_behavioral_fingerprint([0.1, 0.2, 0.3])
    b = compute_behavioral_fingerprint([0.1, 0.2, 0.3 + 1e-9])
    assert a == b


def test_fingerprint_canonical_form_includes_domain_tag():
    raw = canonical_fingerprint_bytes([0.0])
    assert raw.startswith(f"nerve-fp/{FINGERPRINT_VERSION}\n".encode("utf-8"))


def test_fingerprint_canonical_form_uses_fixed_precision():
    raw = canonical_fingerprint_bytes([0.0, 1.5])
    payload = raw.split(b"\n", 1)[1]
    assert payload == b'["0.000000","1.500000"]'
    assert FINGERPRINT_PRECISION == 6


def test_fingerprint_negative_zero_normalizes_to_positive_zero():
    a = compute_behavioral_fingerprint([0.0, 1.0])
    b = compute_behavioral_fingerprint([-0.0, 1.0])
    assert a == b


def test_fingerprint_negative_zero_normalization_regression():
    """Regression: an earlier draft's normalization was a no-op
    (``rounded = 0.0`` after ``rounded == 0.0`` is just ``rounded`` again).
    Without ``+ 0.0`` to force +0.0, ``f'{-0.0:.6f}'`` emits ``-0.000000``
    and breaks the equality. Pin both single-element and mixed cases."""
    assert (
        compute_behavioral_fingerprint([-0.0])
        == compute_behavioral_fingerprint([0.0])
    )
    assert (
        compute_behavioral_fingerprint([0.0, -0.0])
        == compute_behavioral_fingerprint([0.0, 0.0])
    )
    assert (
        compute_behavioral_fingerprint([1.0, -0.0, 2.0])
        == compute_behavioral_fingerprint([1.0, 0.0, 2.0])
    )


def test_fingerprint_order_matters():
    """Index order is preserved; do NOT sort."""
    a = compute_behavioral_fingerprint([0.1, 0.2])
    b = compute_behavioral_fingerprint([0.2, 0.1])
    assert a != b


def test_empty_embedding_rejected():
    with pytest.raises(ValueError, match="non-empty"):
        compute_behavioral_fingerprint([])


def test_verify_round_trip():
    embedding = [0.42, -0.17, 0.99]
    fp = compute_behavioral_fingerprint(embedding)
    assert verify_behavioral_fingerprint(fp, embedding) is True


def test_verify_rejects_tampered_fingerprint():
    fp = compute_behavioral_fingerprint([0.1, 0.2, 0.3])
    tampered = "sha256:" + "0" * 64
    assert verify_behavioral_fingerprint(tampered, [0.1, 0.2, 0.3]) is False


def test_well_formed_check():
    assert is_well_formed_fingerprint("sha256:" + "a" * 64)
    assert not is_well_formed_fingerprint("sha256:" + "a" * 63)
    assert not is_well_formed_fingerprint("md5:" + "a" * 64)
    assert not is_well_formed_fingerprint("sha256:" + "g" * 64)
    assert not is_well_formed_fingerprint("")


def test_fingerprint_matches_manual_sha256():
    """Spot-check that we are in fact SHA-256 over the documented bytes."""
    embedding = [1.0, 2.0]
    raw = canonical_fingerprint_bytes(embedding)
    expected_hex = hashlib.sha256(raw).hexdigest()
    assert compute_behavioral_fingerprint(embedding) == f"sha256:{expected_hex}"
