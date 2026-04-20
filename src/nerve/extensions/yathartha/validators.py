"""Runtime validators for the Yathartha invariants (N-16 through N-18)."""

from __future__ import annotations

from datetime import timedelta

from .types import (
    CapabilitySurface,
    ProbeBatteryResult,
    SurfaceChangeEvent,
    UncoveredPolicy,
)


class YatharthaInvariantError(ValueError):
    """Raised when a Yathartha safety invariant is violated."""


def check_coverage_conditional_drift(
    surface: CapabilitySurface,
    task_region: str,
) -> tuple[bool, str]:
    """N-16. Return (allowed_to_flag_drift, reason).

    A MicroglialObserver may raise a drift flag for a task only if the
    task's classified region is in the covered set AND not stale.
    Otherwise the task is jaggedness (unknown competence) and must be
    handled by the agent's uncovered_policy.
    """
    if surface.is_stale(task_region):
        return (
            False,
            f"region '{task_region}' is stale; re-probe before flagging drift",
        )
    if not surface.is_covered(task_region):
        return (
            False,
            f"region '{task_region}' not in covered set; "
            f"apply uncovered_policy={surface.uncovered_policy.value}",
        )
    return True, "covered and fresh"


def check_probe_battery_maintenance(
    old_result: ProbeBatteryResult,
    new_result: ProbeBatteryResult,
) -> None:
    """N-17. Comparing two ProbeBatteryResult across battery versions MUST
    NOT be permitted. If the battery_version differs, a full re-baseline
    is required; the two results measure different things.
    """
    if old_result.battery_version != new_result.battery_version:
        raise YatharthaInvariantError(
            f"battery version changed from {old_result.battery_version} to "
            f"{new_result.battery_version}; full re-baseline required "
            f"(N-17)"
        )
    if old_result.region_id != new_result.region_id:
        raise YatharthaInvariantError(
            f"region_id mismatch: {old_result.region_id} vs {new_result.region_id}"
        )
    if old_result.agent_id != new_result.agent_id:
        raise YatharthaInvariantError(
            f"agent_id mismatch: {old_result.agent_id} vs {new_result.agent_id}"
        )


def check_capability_surface_integrity(
    before: CapabilitySurface,
    after: CapabilitySurface,
    events: list[SurfaceChangeEvent],
) -> None:
    """N-18. Every change in the covered_regions set between two snapshots
    MUST be accompanied by a SurfaceChangeEvent of kind 'entered', 'left',
    'battery', or 'policy' with matching agent_id and region_id.
    """
    if before.agent_id != after.agent_id:
        raise YatharthaInvariantError("cannot compare surfaces from different agents")

    before_cov = before.covered_regions
    after_cov = after.covered_regions
    entered = after_cov - before_cov
    left = before_cov - after_cov

    by_region: dict[str, list[SurfaceChangeEvent]] = {}
    for e in events:
        if e.agent_id != after.agent_id:
            continue
        if e.region_id is not None:
            by_region.setdefault(e.region_id, []).append(e)

    for region in entered:
        matches = [e for e in by_region.get(region, []) if e.kind in {"entered", "battery"}]
        if not matches:
            raise YatharthaInvariantError(
                f"region '{region}' entered coverage without a matching "
                f"SurfaceChangeEvent (N-18)"
            )

    for region in left:
        matches = [e for e in by_region.get(region, []) if e.kind in {"left", "battery", "policy"}]
        if not matches:
            raise YatharthaInvariantError(
                f"region '{region}' left coverage without a matching "
                f"SurfaceChangeEvent (N-18)"
            )

    if before.battery_version != after.battery_version:
        battery_events = [e for e in events if e.kind == "battery"]
        if not battery_events:
            raise YatharthaInvariantError(
                f"battery_version changed from {before.battery_version} to "
                f"{after.battery_version} without a 'battery' "
                f"SurfaceChangeEvent (N-18)"
            )

    if before.uncovered_policy != after.uncovered_policy:
        policy_events = [e for e in events if e.kind == "policy"]
        if not policy_events:
            raise YatharthaInvariantError(
                f"uncovered_policy changed from {before.uncovered_policy.value} "
                f"to {after.uncovered_policy.value} without a 'policy' "
                f"SurfaceChangeEvent (N-18)"
            )
