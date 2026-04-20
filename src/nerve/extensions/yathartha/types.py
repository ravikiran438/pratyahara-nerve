"""Pydantic types for the Yathartha capability-surface extension.

Reference: Yathartha: A Protocol-Layer Treatment of Jagged Intelligence in
Autonomous Agent Networks (Kadaboina, 2026).
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class UncoveredPolicy(str, Enum):
    """What an observer does when a task falls outside covered regions."""

    OBSERVE = "observe"
    DEFER = "defer"
    REJECT = "reject"


class TaskResult(BaseModel):
    """A single probe task outcome within a ProbeBatteryResult."""

    task_id: str
    passed: bool
    score: float = Field(ge=0.0, le=1.0)

    model_config = ConfigDict(extra="forbid")


class CapabilityRegion(BaseModel):
    """A named region of the task space in which the agent claims competence."""

    region_id: str
    description: str
    probe_task_ids: list[str] = Field(min_length=1)
    acceptance_threshold: float = Field(ge=0.0, le=1.0, default=0.85)

    model_config = ConfigDict(extra="forbid")


class ProbeBatteryResult(BaseModel):
    """Outcome of running a region's probe battery at a specific time.

    Immutable and append-only. A re-run produces a new ProbeBatteryResult
    with a new id and run_at timestamp.
    """

    id: UUID
    region_id: str
    agent_id: str
    battery_version: int = Field(ge=1)
    run_at: datetime
    task_results: list[TaskResult] = Field(min_length=1)
    aggregate_score: float = Field(ge=0.0, le=1.0)
    covered: bool
    confidence: float = Field(ge=0.0, le=1.0)

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def _check_aggregate(self) -> "ProbeBatteryResult":
        if not self.task_results:
            return self
        computed = sum(t.score for t in self.task_results) / len(self.task_results)
        if abs(computed - self.aggregate_score) > 1e-6:
            raise ValueError(
                f"aggregate_score {self.aggregate_score} does not match mean "
                f"of task_results {computed}"
            )
        return self


class SurfaceChangeEvent(BaseModel):
    """Distinct event type recording coverage transitions (N-18)."""

    id: UUID
    agent_id: str
    region_id: str | None
    kind: Literal["entered", "left", "battery", "policy"]
    at: datetime
    previous_battery_version: int | None = None
    new_battery_version: int | None = None
    previous_policy: UncoveredPolicy | None = None
    new_policy: UncoveredPolicy | None = None

    model_config = ConfigDict(extra="forbid", frozen=True)


class CapabilitySurface(BaseModel):
    """An agent's published capability map."""

    agent_id: str
    regions: dict[str, ProbeBatteryResult]
    uncovered_policy: UncoveredPolicy = UncoveredPolicy.DEFER
    refresh_cadence_hours: int = Field(ge=1)
    battery_version: int = Field(ge=1)
    last_full_refresh_at: datetime

    model_config = ConfigDict(extra="forbid")

    @property
    def covered_regions(self) -> set[str]:
        """Regions whose latest probe result is both covered and fresh."""
        now = datetime.now(timezone.utc)
        fresh: set[str] = set()
        for region_id, result in self.regions.items():
            if not result.covered:
                continue
            age_hours = (now - result.run_at).total_seconds() / 3600.0
            if age_hours <= self.refresh_cadence_hours:
                fresh.add(region_id)
        return fresh

    def is_covered(self, region_id: str) -> bool:
        return region_id in self.covered_regions

    def is_stale(self, region_id: str) -> bool:
        """True if the region was covered but is past its freshness window."""
        result = self.regions.get(region_id)
        if result is None or not result.covered:
            return False
        age_hours = (
            datetime.now(timezone.utc) - result.run_at
        ).total_seconds() / 3600.0
        return age_hours > self.refresh_cadence_hours
