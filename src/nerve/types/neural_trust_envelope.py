# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""NeuralTrustEnvelope: asymmetric trust dynamics (paper Section 3.3).

Invariant NTE-1: decay_rate > reinforcement_rate (trust harder to build).
Invariant NTE-2: trust updates require consensus from all assigned observers.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class NeuralTrustEnvelope(BaseModel):
    """Manages trust dynamics for a single agent with deliberate asymmetry."""

    model_config = ConfigDict(str_strip_whitespace=True)

    envelope_id: str
    agent_id: str
    trust_score: float = Field(default=0.5, ge=0.0, le=1.0)
    trust_history: List[float] = Field(
        default_factory=list,
        description="Sliding window (default 90 days) of trust score values",
    )
    myelination_map: dict = Field(
        default_factory=dict,
        description="channel_id -> myelination_level for this agent's channels",
    )
    pruning_threshold: float = Field(
        default=0.2, ge=0.0, le=1.0,
        description="Trust below this triggers channel severance (AN-1)",
    )
    reinforcement_rate: float = Field(
        default=0.01, gt=0.0,
        description="Trust increase per positive observation",
    )
    decay_rate: float = Field(
        default=0.05, gt=0.0,
        description="Trust decrease per negative observation",
    )
    last_evaluation_at: Optional[str] = Field(default=None)
    evaluating_observers: List[str] = Field(
        default_factory=list,
        description="Observer IDs that contribute to trust evaluation",
    )

    @model_validator(mode="after")
    def _asymmetric_trust(self) -> "NeuralTrustEnvelope":
        """Invariant NTE-1: decay must exceed reinforcement."""
        if self.decay_rate <= self.reinforcement_rate:
            raise ValueError(
                f"NTE-1 violated: decay_rate ({self.decay_rate}) must be "
                f"strictly greater than reinforcement_rate ({self.reinforcement_rate})"
            )
        return self
