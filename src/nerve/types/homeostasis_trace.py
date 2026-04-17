# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""HomeostasisTrace: network-level health monitoring (paper Section 3.4).

Invariant HT-1: Computed by a dedicated, non-participating agent.
Invariant HT-2: critical state triggers maximum permeability restriction.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class HomeostasisState(str, Enum):
    STABLE = "stable"
    STRESSED = "stressed"
    CRITICAL = "critical"
    RECOVERY = "recovery"


class HomeostasisTrace(BaseModel):
    """Network-wide health signal, the astrocyte analog.

    Detects systemic attacks (supply chain compromise, shared-dependency
    poisoning) invisible to per-agent observers.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    network_id: str
    computed_at: str = Field(..., description="ISO 8601 timestamp")
    window_days: int = Field(default=7, gt=0)
    network_entropy: float = Field(
        ..., ge=0.0,
        description=(
            "Shannon entropy of trust score distribution. "
            "Healthy: moderate. Very low: manipulation. Very high: evaluation failure."
        ),
    )
    pruning_rate_7d: float = Field(
        default=0.0, ge=0.0,
        description="Rate of channel pruning events in last 7 days; rising = sustained attack",
    )
    activation_distribution: List[float] = Field(
        default_factory=list,
        description="Distribution of current_activation values across all agents",
    )
    myelination_distribution: List[float] = Field(
        default_factory=list,
        description="Distribution of myelination_level values across all channels",
    )
    observer_consensus_rate: float = Field(
        default=1.0, ge=0.0, le=1.0,
        description="Fraction of trust evaluations where all observers agree; low = compromise",
    )
    anomaly_density: float = Field(
        default=0.0, ge=0.0,
        description="Fraction of agents currently flagged by observers",
    )
    cascade_events_30d: int = Field(
        default=0, ge=0,
        description="Count of cascade (MO activation_state=cascading) events in 30 days",
    )
    homeostasis_state: HomeostasisState = Field(default=HomeostasisState.STABLE)
