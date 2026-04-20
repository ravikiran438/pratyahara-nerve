# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Tests for the Yathartha extension tools exposed by nerve-mcp.

Covers N-16 (coverage-conditional drift), N-17 (probe battery
maintenance), and N-18 (capability surface integrity) through the JSON
contract exposed to an MCP client.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from nerve.mcp_server.tools import (
    ToolInvocationError,
    handle_validate_capability_surface_integrity,
    handle_validate_coverage_conditional_drift,
    handle_validate_probe_battery_maintenance,
)


def _probe_payload(
    agent_id: str = "agent-1",
    region: str = "arithmetic",
    score: float = 0.90,
    covered: bool = True,
    battery_version: int = 1,
    run_at: datetime | None = None,
) -> dict:
    run_at = run_at or datetime.now(timezone.utc)
    return {
        "id": str(uuid4()),
        "region_id": region,
        "agent_id": agent_id,
        "battery_version": battery_version,
        "run_at": run_at.isoformat(),
        "task_results": [
            {"task_id": "t1", "passed": True, "score": score},
            {"task_id": "t2", "passed": True, "score": score},
        ],
        "aggregate_score": score,
        "covered": covered,
        "confidence": 0.95,
    }


def _surface_payload(
    regions: dict[str, dict],
    policy: str = "defer",
    refresh_cadence_hours: int = 24,
    battery_version: int = 1,
) -> dict:
    return {
        "agent_id": "agent-1",
        "regions": regions,
        "uncovered_policy": policy,
        "refresh_cadence_hours": refresh_cadence_hours,
        "battery_version": battery_version,
        "last_full_refresh_at": datetime.now(timezone.utc).isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────
# N-16: validate_coverage_conditional_drift
# ─────────────────────────────────────────────────────────────────────


def test_coverage_drift_allowed_for_covered_region():
    surface = _surface_payload({"arithmetic": _probe_payload()})
    result = json.loads(
        handle_validate_coverage_conditional_drift(
            {"surface": surface, "task_region": "arithmetic"}
        )
    )
    assert result["ok"] is True
    assert result["allowed_to_flag_drift"] is True
    assert "covered" in result["reason"]


def test_coverage_drift_blocked_for_uncovered_region():
    surface = _surface_payload({"arithmetic": _probe_payload()})
    result = json.loads(
        handle_validate_coverage_conditional_drift(
            {"surface": surface, "task_region": "letter-counting"}
        )
    )
    assert result["ok"] is True
    assert result["allowed_to_flag_drift"] is False
    assert "defer" in result["reason"]


def test_coverage_drift_empty_task_region_raises():
    surface = _surface_payload({"arithmetic": _probe_payload()})
    with pytest.raises(ToolInvocationError, match="non-empty string"):
        handle_validate_coverage_conditional_drift(
            {"surface": surface, "task_region": ""}
        )


# ─────────────────────────────────────────────────────────────────────
# N-17: validate_probe_battery_maintenance
# ─────────────────────────────────────────────────────────────────────


def test_probe_battery_compatible_versions_ok():
    old = _probe_payload(battery_version=1)
    new = _probe_payload(battery_version=1)
    result = json.loads(
        handle_validate_probe_battery_maintenance(
            {"old_result": old, "new_result": new}
        )
    )
    assert result["ok"] is True
    assert result["comparison"] == "compatible"


def test_probe_battery_version_change_rejected():
    old = _probe_payload(battery_version=1)
    new = _probe_payload(battery_version=2)
    result = json.loads(
        handle_validate_probe_battery_maintenance(
            {"old_result": old, "new_result": new}
        )
    )
    assert result["ok"] is False
    assert "N-17" in result["error"]


def test_probe_battery_region_mismatch_rejected():
    old = _probe_payload(region="arithmetic")
    new = _probe_payload(region="scheduling")
    result = json.loads(
        handle_validate_probe_battery_maintenance(
            {"old_result": old, "new_result": new}
        )
    )
    assert result["ok"] is False
    assert "region_id mismatch" in result["error"]


# ─────────────────────────────────────────────────────────────────────
# N-18: validate_capability_surface_integrity
# ─────────────────────────────────────────────────────────────────────


def test_surface_integrity_no_change_ok():
    surface = _surface_payload({"arithmetic": _probe_payload()})
    result = json.loads(
        handle_validate_capability_surface_integrity(
            {"before": surface, "after": surface, "events": []}
        )
    )
    assert result["ok"] is True


def test_surface_integrity_region_entered_without_event_fails():
    before = _surface_payload({"arithmetic": _probe_payload()})
    after = _surface_payload(
        {
            "arithmetic": _probe_payload(),
            "scheduling": _probe_payload(region="scheduling"),
        }
    )
    result = json.loads(
        handle_validate_capability_surface_integrity(
            {"before": before, "after": after, "events": []}
        )
    )
    assert result["ok"] is False
    assert "N-18" in result["error"]


def test_surface_integrity_region_entered_with_event_ok():
    before = _surface_payload({"arithmetic": _probe_payload()})
    after = _surface_payload(
        {
            "arithmetic": _probe_payload(),
            "scheduling": _probe_payload(region="scheduling"),
        }
    )
    events = [
        {
            "id": str(uuid4()),
            "agent_id": "agent-1",
            "region_id": "scheduling",
            "kind": "entered",
            "at": datetime.now(timezone.utc).isoformat(),
        }
    ]
    result = json.loads(
        handle_validate_capability_surface_integrity(
            {"before": before, "after": after, "events": events}
        )
    )
    assert result["ok"] is True


def test_surface_integrity_non_list_events_raises():
    surface = _surface_payload({"arithmetic": _probe_payload()})
    with pytest.raises(ToolInvocationError, match="list of objects"):
        handle_validate_capability_surface_integrity(
            {"before": surface, "after": surface, "events": "not-a-list"}
        )
