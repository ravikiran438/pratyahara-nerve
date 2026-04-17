# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""MicroglialObserver: lightweight surveillance agent (paper Section 3.1).

Invariant MO-1: Every AgentNeuron assigned to >= 2 observers.
Invariant MO-2: Observer MUST NOT modify the AgentNeuron it monitors.
Invariant MO-3: Observer infrastructure independent of monitored agents.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ActivationState(str, Enum):
    SURVEILLING = "surveilling"
    ACTIVATED = "activated"
    CASCADING = "cascading"


class DetectionThresholds(BaseModel):
    """Configurable thresholds for anomaly detection.

    All defaults are reference values from the companion implementation,
    not proven optimal. Deployments SHOULD calibrate against their own
    agent populations and threat models.
    """

    model_config = ConfigDict(frozen=True)

    activation_deviation: float = Field(
        default=2.0, gt=0.0,
        description="Standard deviations from baseline before flagging",
    )
    fingerprint_drift: float = Field(
        default=0.15, gt=0.0, le=1.0,
        description="Cosine distance threshold for behavioral drift",
    )
    message_rate_anomaly: float = Field(
        default=3.0, gt=0.0,
        description="Ratio vs baseline before flagging message rate",
    )
    latency_anomaly: float = Field(
        default=2.5, gt=0.0,
        description="Ratio vs baseline before flagging latency",
    )
    trust_decay_rate: float = Field(
        default=0.1, gt=0.0, le=1.0,
        description="Max trust drop per observation cycle",
    )
    collusion_correlation: float = Field(
        default=0.7, gt=0.0, le=1.0,
        description="Cross-agent correlation threshold for collusion detection",
    )


class MicroglialObserver(BaseModel):
    """A lightweight agent that monitors a set of AgentNeurons for drift.

    Observers are read-only (MO-2) and must run on independent
    infrastructure (MO-3).
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    observer_id: str
    assigned_agents: List[str] = Field(
        ..., min_length=1,
        description="AgentNeuron IDs this observer monitors",
    )
    observation_schedule: Dict[str, int] = Field(
        default_factory=lambda: {"active": 60, "idle": 300},
        description="Scan interval in seconds by agent activity state",
    )
    detection_thresholds: DetectionThresholds = Field(
        default_factory=DetectionThresholds,
    )
    activation_state: ActivationState = Field(default=ActivationState.SURVEILLING)
    alert_history: List[dict] = Field(
        default_factory=list,
        description="Append-only log of detections and resolutions",
    )
    coverage_overlap: Optional[List[str]] = Field(
        default=None,
        description="Peer observer IDs sharing coverage for cascade coordination",
    )
