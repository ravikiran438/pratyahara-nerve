# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""NeuralPostureRef: the NERVE service descriptor on an A2A AgentCard.

This is the typed payload of the entry whose ``uri`` equals
``NERVE_EXTENSION_URI`` inside ``AgentCard.capabilities.extensions[]``.
Modeled after ACAP's ``UsagePolicyRef``: a small, declarative reference
that tells callers what trust posture the agent presents — neuron type,
current behavioral fingerprint, observer cohort, and homeostasis state.

Per A2A's extension model, this block is the *only* place NERVE-specific
fields appear on the AgentCard; per-message NERVE telemetry travels via
A2A ``message.metadata`` under the same URI key (see ``NerveEnvelope``).
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from nerve.types.agent_neuron import NeuronType
from nerve.types.fingerprint import is_well_formed_fingerprint


NERVE_EXTENSION_URI = "https://github.com/ravikiran438/pratyahara-nerve/v1"


class NeuralPostureRef(BaseModel):
    """NERVE-specific fields contributed to an A2A AgentCard.

    Validators detect NERVE support by the presence of an entry in
    ``capabilities.extensions[]`` whose ``uri`` equals
    ``NERVE_EXTENSION_URI``. The body of that entry SHOULD deserialize
    to this model.
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    version: str = Field(
        ..., description="NERVE protocol semver this agent implements."
    )

    neuron_type: NeuronType = Field(
        ...,
        description=(
            "The role this agent plays in the network: SENSORY accepts "
            "external inputs; PROCESSING transforms; MOTOR drives external "
            "side-effects; INTERNEURON routes between others."
        ),
    )

    behavioral_fingerprint: str = Field(
        ...,
        description=(
            "Current ``sha256:<hex>`` fingerprint of this agent's output "
            "distribution embedding, computed per nerve.types.fingerprint. "
            "Validators check format only; semantic verification requires "
            "the embedding which lives with the observer."
        ),
    )

    trust_score: float = Field(
        ..., ge=0.0, le=1.0,
        description="Last observer-consensus trust value in [0, 1].",
    )

    observer_ids: List[str] = Field(
        ..., min_length=2,
        description=(
            "Identifiers of the MicroglialObservers monitoring this agent. "
            "Per N-1 each agent MUST be observed by at least 2 observers."
        ),
    )

    myelination_levels: dict[str, float] = Field(
        default_factory=dict,
        description=(
            "Per-channel myelination map (channel_id -> level in [0, 1]). "
            "Empty when the agent has no established channels yet."
        ),
    )

    last_evaluated_at: Optional[str] = Field(
        default=None,
        description="ISO 8601 UTC of the most recent trust evaluation.",
    )

    homeostasis_state: str = Field(
        default="STABLE",
        description=(
            "The network homeostasis_state observed at last evaluation. "
            "One of STABLE | STRESSED | CRITICAL | RECOVERY (see "
            "HomeostasisState)."
        ),
    )

    @field_validator("behavioral_fingerprint")
    @classmethod
    def _validate_fingerprint_format(cls, value: str) -> str:
        """Reject malformed fingerprint strings at field-validation time.

        Earlier drafts performed this check inside ``__init__`` after
        ``super().__init__`` returned, which worked but bypassed
        pydantic's standard error reporting and was confusing for
        anyone adding validators in the future. v0.2 moves the check
        into a proper ``@field_validator`` so the failure surfaces in
        pydantic's ``ValidationError`` like every other field.
        """
        if not is_well_formed_fingerprint(value):
            raise ValueError(
                f"behavioral_fingerprint {value!r} is not a well-formed "
                "sha256:<64-hex> value"
            )
        return value


class NerveEnvelope(BaseModel):
    """Per-message NERVE telemetry attached via A2A ``message.metadata``.

    Lives at ``message.metadata[NERVE_EXTENSION_URI]`` (or under the key
    ``"nerve.envelope"`` for transports that disallow URI keys). Lets
    receivers reason about the sender's trust posture without a side
    channel to the observer.

    This schema is the formalization of the paper's ``task.nerve_envelope``;
    it does NOT live inside A2A's core message — only in the metadata
    bag, per A2A's extension contract.
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    sender_trust_score: float = Field(..., ge=0.0, le=1.0)
    sender_confidence: float = Field(
        ..., ge=0.0, le=1.0,
        description=(
            "Sender's self-reported confidence in this output. Compared "
            "against SynapticChannel.quality_threshold for SC-4 gating."
        ),
    )
    channel_myelination: float = Field(..., ge=0.0, le=1.0)
    channel_state: str = Field(
        ...,
        description="active | attenuated | severed | quarantined",
    )
    homeostasis_state: str = Field(
        ...,
        description="STABLE | STRESSED | CRITICAL | RECOVERY",
    )
    cascade_depth: int = Field(..., ge=0)
    permeability_clearance: List[str] = Field(
        ...,
        description=(
            "ClearanceLevel values asserted by the sender for this message. "
            "Receivers reject if any value is not in their channel's "
            "PermeabilityPolicy.allowed_context_types or appears in "
            "prohibited_context_types."
        ),
    )
