# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""N-3: Asymmetric Trust. decay_rate must exceed reinforcement_rate."""

from __future__ import annotations

from nerve.types.neural_trust_envelope import NeuralTrustEnvelope


class AsymmetricTrustError(ValueError):
    """Raised when decay_rate <= reinforcement_rate."""


def validate_asymmetric_trust(envelope: NeuralTrustEnvelope) -> None:
    """Verify NTE-1 on a constructed envelope.

    The Pydantic model_validator already enforces this at construction,
    but this function lets callers check wire-deserialized envelopes
    that bypassed the model constructor.
    """
    if envelope.decay_rate <= envelope.reinforcement_rate:
        raise AsymmetricTrustError(
            f"N-3 / NTE-1 violated: decay_rate ({envelope.decay_rate}) must "
            f"exceed reinforcement_rate ({envelope.reinforcement_rate})"
        )
