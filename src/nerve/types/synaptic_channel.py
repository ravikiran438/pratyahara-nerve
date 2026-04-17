# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""SynapticChannel: communication link with selective permeability (paper Section 3.2).

Also carries GlymphaticPolicy (Section 4.3) and inhibitory-gating
fields (Section 4.4).
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ChannelType(str, Enum):
    A2A_TASK = "a2a_task"
    MCP_TOOL = "mcp_tool"
    A2A_STREAMING = "a2a_streaming"
    INTERNAL = "internal"


class ChannelState(str, Enum):
    ACTIVE = "active"
    ATTENUATED = "attenuated"
    SEVERED = "severed"
    QUARANTINED = "quarantined"


class PermeabilityPolicy(BaseModel):
    """Receptor-level gating for what context crosses the channel boundary."""

    model_config = ConfigDict(frozen=True)

    allowed_context_types: List[str] = Field(default_factory=list)
    prohibited_context_types: List[str] = Field(default_factory=list)
    max_context_size_bytes: int = Field(default=4096, gt=0)
    memory_access_scope: str = Field(
        default="session",
        description="none | session | persistent",
    )
    dynamic_restriction: bool = Field(
        default=True,
        description="If true, tightens when network homeostasis_state is stressed or critical",
    )


class GlymphaticPolicy(BaseModel):
    """Context hygiene policy enforcing active clearance of stale context (paper Section 4.3).

    Invariant GL-1: Context older than max_context_age_seconds purged before next send.
    Invariant GL-2: Provenance deeper than max_provenance_depth summarized.
    Invariant GL-3: context_compression_required=true means raw concatenation prohibited.
    Invariant GL-4: context-to-payload ratio exceeding excitotoxicity_threshold triggers alert.
    """

    model_config = ConfigDict(frozen=True)

    max_context_age_seconds: int = Field(default=3600, gt=0)
    max_provenance_depth: int = Field(default=3, gt=0)
    context_compression_required: bool = Field(default=True)
    max_accumulated_tokens: int = Field(default=50000, gt=0)
    clearance_schedule: str = Field(default="per_task")
    excitotoxicity_threshold: float = Field(
        default=5.0, gt=0.0,
        description="Max context-to-payload ratio before observer alert",
    )


class SynapticChannel(BaseModel):
    """A communication link between two agents or between an agent and a tool server.

    Invariant SC-1: state=severed transmits zero messages.
    Invariant SC-2: myelination_level cannot increase during quarantined state.
    Invariant SC-3: Myelination follows Hebbian dynamics.
    Invariant SC-4: confidence below quality_threshold blocks propagation.
    Invariant SC-5: Rejected sender enters refractory cooldown.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    channel_id: str
    source_agent_id: str
    target_agent_id: str
    channel_type: ChannelType
    myelination_level: float = Field(default=0.3, ge=0.0, le=1.0)
    message_rate_baseline: float = Field(default=0.0, ge=0.0)
    current_message_rate: float = Field(default=0.0, ge=0.0)
    last_message_hash: Optional[str] = Field(default=None)
    state: ChannelState = Field(default=ChannelState.ACTIVE)
    permeability_policy: PermeabilityPolicy = Field(
        default_factory=PermeabilityPolicy,
    )
    glymphatic_policy: Optional[GlymphaticPolicy] = Field(default=None)

    # Inhibitory gating fields (Section 4.4)
    quality_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0,
        description="Minimum output confidence for propagation",
    )
    refractory_ms: int = Field(
        default=2000, ge=0,
        description="Cooldown after rejection before sender can retransmit",
    )
    cascade_depth: int = Field(
        default=0, ge=0,
        description=(
            "Incremented each time a message crosses an agent boundary. "
            "The paper describes this as a message-level property; in the "
            "v0.1 reference implementation it is tracked per-channel as a "
            "simplification. A production implementation would propagate "
            "this counter on the message itself."
        ),
    )
