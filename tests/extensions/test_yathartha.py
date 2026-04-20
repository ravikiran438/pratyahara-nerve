"""Tests for the Yathartha capability-surface extension (N-16 through N-18)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from nerve.extensions.yathartha import (
    CapabilitySurface,
    ProbeBatteryResult,
    SurfaceChangeEvent,
    TaskResult,
    UncoveredPolicy,
    YatharthaInvariantError,
    check_capability_surface_integrity,
    check_coverage_conditional_drift,
    check_probe_battery_maintenance,
)


def _probe(
    agent_id: str = "agent-1",
    region: str = "arithmetic",
    score: float = 0.90,
    covered: bool = True,
    battery_version: int = 1,
    run_at: datetime | None = None,
) -> ProbeBatteryResult:
    run_at = run_at or datetime.now(timezone.utc)
    return ProbeBatteryResult(
        id=uuid4(),
        region_id=region,
        agent_id=agent_id,
        battery_version=battery_version,
        run_at=run_at,
        task_results=[
            TaskResult(task_id="t1", passed=True, score=score),
            TaskResult(task_id="t2", passed=True, score=score),
        ],
        aggregate_score=score,
        covered=covered,
        confidence=0.95,
    )


def _surface(
    regions: dict[str, ProbeBatteryResult],
    policy: UncoveredPolicy = UncoveredPolicy.DEFER,
) -> CapabilitySurface:
    return CapabilitySurface(
        agent_id="agent-1",
        regions=regions,
        uncovered_policy=policy,
        refresh_cadence_hours=24,
        battery_version=1,
        last_full_refresh_at=datetime.now(timezone.utc),
    )


# ─────────────────────────────────────────────────────────────────────
# N-16: Coverage-Conditional Drift
# ─────────────────────────────────────────────────────────────────────


class TestCoverageConditionalDrift:
    def test_drift_allowed_for_covered_fresh_region(self):
        surface = _surface({"arithmetic": _probe()})
        allowed, reason = check_coverage_conditional_drift(surface, "arithmetic")
        assert allowed is True
        assert "covered" in reason

    def test_drift_blocked_for_uncovered_region(self):
        surface = _surface({"arithmetic": _probe()})
        allowed, reason = check_coverage_conditional_drift(surface, "letter-counting")
        assert allowed is False
        assert "defer" in reason

    def test_drift_blocked_for_stale_region(self):
        stale_probe = _probe(
            run_at=datetime.now(timezone.utc) - timedelta(hours=48),
        )
        surface = _surface({"arithmetic": stale_probe})
        allowed, reason = check_coverage_conditional_drift(surface, "arithmetic")
        assert allowed is False
        assert "stale" in reason

    def test_drift_blocked_when_probe_failed_coverage(self):
        failed_probe = _probe(score=0.10, covered=False)
        surface = _surface({"arithmetic": failed_probe})
        allowed, reason = check_coverage_conditional_drift(surface, "arithmetic")
        assert allowed is False

    def test_uncovered_policy_surfaced_in_reason(self):
        surface = _surface({"arithmetic": _probe()}, policy=UncoveredPolicy.REJECT)
        allowed, reason = check_coverage_conditional_drift(surface, "unknown")
        assert allowed is False
        assert "reject" in reason


# ─────────────────────────────────────────────────────────────────────
# N-17: Probe Battery Maintenance
# ─────────────────────────────────────────────────────────────────────


class TestProbeBatteryMaintenance:
    def test_same_battery_version_compares_ok(self):
        old = _probe(battery_version=1)
        new = _probe(battery_version=1)
        check_probe_battery_maintenance(old, new)  # does not raise

    def test_battery_version_change_rejected(self):
        old = _probe(battery_version=1)
        new = _probe(battery_version=2)
        with pytest.raises(YatharthaInvariantError, match="battery version changed"):
            check_probe_battery_maintenance(old, new)

    def test_region_mismatch_rejected(self):
        old = _probe(region="arithmetic")
        new = _probe(region="scheduling")
        with pytest.raises(YatharthaInvariantError, match="region_id mismatch"):
            check_probe_battery_maintenance(old, new)

    def test_agent_mismatch_rejected(self):
        old = _probe(agent_id="agent-1")
        new = _probe(agent_id="agent-2")
        with pytest.raises(YatharthaInvariantError, match="agent_id mismatch"):
            check_probe_battery_maintenance(old, new)


# ─────────────────────────────────────────────────────────────────────
# N-18: Capability Surface Integrity
# ─────────────────────────────────────────────────────────────────────


def _event(region: str | None, kind: str) -> SurfaceChangeEvent:
    return SurfaceChangeEvent(
        id=uuid4(),
        agent_id="agent-1",
        region_id=region,
        kind=kind,  # type: ignore[arg-type]
        at=datetime.now(timezone.utc),
    )


class TestCapabilitySurfaceIntegrity:
    def test_no_change_no_events_ok(self):
        before = _surface({"arithmetic": _probe()})
        after = _surface({"arithmetic": _probe()})
        check_capability_surface_integrity(before, after, [])

    def test_region_entered_without_event_rejected(self):
        before = _surface({"arithmetic": _probe(covered=False, score=0.1)})
        after = _surface({"arithmetic": _probe()})
        with pytest.raises(YatharthaInvariantError, match="entered coverage"):
            check_capability_surface_integrity(before, after, [])

    def test_region_entered_with_event_ok(self):
        before = _surface({"arithmetic": _probe(covered=False, score=0.1)})
        after = _surface({"arithmetic": _probe()})
        check_capability_surface_integrity(
            before, after, [_event("arithmetic", "entered")]
        )

    def test_region_left_without_event_rejected(self):
        before = _surface({"arithmetic": _probe()})
        after = _surface({"arithmetic": _probe(covered=False, score=0.1)})
        with pytest.raises(YatharthaInvariantError, match="left coverage"):
            check_capability_surface_integrity(before, after, [])

    def test_region_left_with_event_ok(self):
        before = _surface({"arithmetic": _probe()})
        after = _surface({"arithmetic": _probe(covered=False, score=0.1)})
        check_capability_surface_integrity(
            before, after, [_event("arithmetic", "left")]
        )

    def test_policy_change_without_event_rejected(self):
        before = _surface({"arithmetic": _probe()}, policy=UncoveredPolicy.DEFER)
        after = _surface({"arithmetic": _probe()}, policy=UncoveredPolicy.REJECT)
        with pytest.raises(YatharthaInvariantError, match="uncovered_policy"):
            check_capability_surface_integrity(before, after, [])

    def test_policy_change_with_event_ok(self):
        before = _surface({"arithmetic": _probe()}, policy=UncoveredPolicy.DEFER)
        after = _surface({"arithmetic": _probe()}, policy=UncoveredPolicy.REJECT)
        check_capability_surface_integrity(
            before, after, [_event(None, "policy")]
        )

    def test_different_agent_rejected(self):
        before = _surface({"arithmetic": _probe()})
        after = CapabilitySurface(
            agent_id="other-agent",
            regions={"arithmetic": _probe(agent_id="other-agent")},
            uncovered_policy=UncoveredPolicy.DEFER,
            refresh_cadence_hours=24,
            battery_version=1,
            last_full_refresh_at=datetime.now(timezone.utc),
        )
        with pytest.raises(YatharthaInvariantError, match="different agents"):
            check_capability_surface_integrity(before, after, [])


# ─────────────────────────────────────────────────────────────────────
# Type-level sanity
# ─────────────────────────────────────────────────────────────────────


class TestTypes:
    def test_probe_aggregate_must_match_task_results(self):
        with pytest.raises(ValueError, match="aggregate_score"):
            ProbeBatteryResult(
                id=uuid4(),
                region_id="r",
                agent_id="a",
                battery_version=1,
                run_at=datetime.now(timezone.utc),
                task_results=[TaskResult(task_id="t1", passed=True, score=0.9)],
                aggregate_score=0.5,  # wrong
                covered=True,
                confidence=0.9,
            )

    def test_probe_result_is_immutable(self):
        p = _probe()
        with pytest.raises(ValueError):
            p.aggregate_score = 0.1  # type: ignore[misc]

    def test_covered_regions_excludes_stale(self):
        stale = _probe(run_at=datetime.now(timezone.utc) - timedelta(hours=48))
        surface = _surface({"arithmetic": stale})
        assert "arithmetic" not in surface.covered_regions

    def test_covered_regions_includes_fresh_passing(self):
        surface = _surface({"arithmetic": _probe()})
        assert "arithmetic" in surface.covered_regions
