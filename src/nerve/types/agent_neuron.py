# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""AgentNeuron: behavioral baseline and trust state per agent (paper Section 3.1)."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class NeuronType(str, Enum):
    SENSORY = "sensory"
    PROCESSING = "processing"
    MOTOR = "motor"
    INTERNEURON = "interneuron"


class AgentNeuron(BaseModel):
    """Represents an agent's behavioral state within a NERVE-monitored network.

    Invariant AN-1: trust_score below pruning_threshold triggers severance
    of all connected_channels within one observation cycle.

    Invariant AN-2: behavioral_fingerprint is computed from output
    distributions only, never from raw prompt content or principal data.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    agent_id: str = Field(..., description="A2A agent identifier or MCP server identifier")
    neuron_type: NeuronType
    activation_baseline: float = Field(
        ..., ge=0.0,
        description="Rolling mean of message rate, latency, output entropy (resting potential)",
    )
    current_activation: float = Field(
        ..., ge=0.0,
        description="Real-time activation over sliding window (default 1 hour)",
    )
    trust_score: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Observer-computed trust in [0.0, 1.0], initialized at 0.5",
    )
    connected_channels: List[str] = Field(
        default_factory=list,
        description="Channel IDs this agent participates in",
    )
    myelination_level: float = Field(
        default=0.3, ge=0.0, le=1.0,
        description="Aggregate myelination across channels; starts at 0.3 for new agents",
    )
    last_observed_at: Optional[str] = Field(
        default=None, description="ISO 8601 timestamp of last observer scan",
    )
    behavioral_fingerprint: str = Field(
        ...,
        description=(
            "SHA-256 integrity tag over the canonical serialization of the "
            "agent's output-distribution embedding vector. The embedding "
            "lives with the observer; this hash lets parties verify they "
            "compare the same vector."
        ),
    )
