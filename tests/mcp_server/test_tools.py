# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Tests for the NERVE MCP server tool handlers.

Covers each of the seven named invariants through the JSON contract
exposed to an MCP client. The stdio transport is covered separately in
test_server_stdio.py.
"""

from __future__ import annotations

import json

import pytest

from nerve.mcp_server.tools import (
    HANDLERS,
    TOOL_SCHEMAS,
    ToolInvocationError,
    handle_validate_asymmetric_trust,
    handle_validate_critical_restriction,
    handle_validate_dual_coverage,
    handle_validate_inhibitory_gating,
    handle_validate_quarantine_freeze,
    handle_validate_refractory,
    handle_validate_severance_finality,
    list_tool_names,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


def _channel(
    channel_id: str = "c1",
    state: str = "active",
    myelination_level: float = 0.5,
    quality_threshold: float = 0.7,
) -> dict:
    return {
        "channel_id": channel_id,
        "source_agent_id": "a1",
        "target_agent_id": "a2",
        "channel_type": "a2a_task",
        "state": state,
        "myelination_level": myelination_level,
        "quality_threshold": quality_threshold,
    }


def _trace(state: str = "stable") -> dict:
    return {
        "network_id": "net1",
        "computed_at": "2026-04-17T10:00:00Z",
        "network_entropy": 2.0,
        "homeostasis_state": state,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────────────────────────────────────


def test_schemas_and_handlers_consistent():
    assert set(TOOL_SCHEMAS.keys()) == set(HANDLERS.keys())
    assert set(list_tool_names()) == set(HANDLERS.keys())


def test_all_schemas_have_shape():
    for name, schema in TOOL_SCHEMAS.items():
        assert "description" in schema, f"{name} missing description"
        assert "inputSchema" in schema, f"{name} missing inputSchema"
        assert schema["inputSchema"]["type"] == "object"


# ─────────────────────────────────────────────────────────────────────────────
# N-1 dual coverage
# ─────────────────────────────────────────────────────────────────────────────


def test_dual_coverage_valid():
    result = json.loads(
        handle_validate_dual_coverage(
            {"agent_to_observers": {"a1": ["o1", "o2"], "a2": ["o2", "o3"]}}
        )
    )
    assert result["ok"] is True
    assert result["agents_checked"] == 2


def test_dual_coverage_single_observer_fails():
    result = json.loads(
        handle_validate_dual_coverage(
            {"agent_to_observers": {"a1": ["o1"]}}
        )
    )
    assert result["ok"] is False
    assert "N-1" in result["error"]


def test_dual_coverage_non_object_input_raises():
    with pytest.raises(ToolInvocationError, match="expected object"):
        handle_validate_dual_coverage({"agent_to_observers": "not-a-dict"})


def test_dual_coverage_non_list_observer_value_raises():
    with pytest.raises(ToolInvocationError, match="list of strings"):
        handle_validate_dual_coverage(
            {"agent_to_observers": {"a1": "not-a-list"}}
        )


# ─────────────────────────────────────────────────────────────────────────────
# Asymmetric trust
# ─────────────────────────────────────────────────────────────────────────────


def test_asymmetric_trust_valid():
    envelope = {
        "envelope_id": "nte1",
        "agent_id": "a1",
        "decay_rate": 0.05,
        "reinforcement_rate": 0.01,
    }
    result = json.loads(
        handle_validate_asymmetric_trust({"envelope": envelope})
    )
    assert result["ok"] is True


def test_asymmetric_trust_rejects_equal_rates():
    envelope = {
        "envelope_id": "nte-bad",
        "agent_id": "a1",
        "decay_rate": 0.03,
        "reinforcement_rate": 0.03,
    }
    with pytest.raises(ToolInvocationError, match="invalid envelope"):
        handle_validate_asymmetric_trust({"envelope": envelope})


# ─────────────────────────────────────────────────────────────────────────────
# Severance finality
# ─────────────────────────────────────────────────────────────────────────────


def test_severance_finality_severed_no_message_ok():
    result = json.loads(
        handle_validate_severance_finality(
            {"channel": _channel(state="severed"), "message_delivered": False}
        )
    )
    assert result["ok"] is True


def test_severance_finality_severed_with_message_fails():
    result = json.loads(
        handle_validate_severance_finality(
            {"channel": _channel(state="severed"), "message_delivered": True}
        )
    )
    assert result["ok"] is False
    assert "N-4" in result["error"]


def test_severance_finality_non_bool_delivered_raises():
    with pytest.raises(ToolInvocationError, match="must be a boolean"):
        handle_validate_severance_finality(
            {"channel": _channel(), "message_delivered": "maybe"}
        )


# ─────────────────────────────────────────────────────────────────────────────
# Quarantine freeze
# ─────────────────────────────────────────────────────────────────────────────


def test_quarantine_freeze_stable_ok():
    result = json.loads(
        handle_validate_quarantine_freeze(
            {
                "channel": _channel(
                    state="quarantined", myelination_level=0.5
                ),
                "previous_myelination": 0.5,
            }
        )
    )
    assert result["ok"] is True


def test_quarantine_freeze_increased_fails():
    result = json.loads(
        handle_validate_quarantine_freeze(
            {
                "channel": _channel(
                    state="quarantined", myelination_level=0.7
                ),
                "previous_myelination": 0.5,
            }
        )
    )
    assert result["ok"] is False
    assert "N-5" in result["error"]


def test_quarantine_freeze_non_number_previous_raises():
    with pytest.raises(ToolInvocationError, match="must be a number"):
        handle_validate_quarantine_freeze(
            {"channel": _channel(), "previous_myelination": "high"}
        )


# ─────────────────────────────────────────────────────────────────────────────
# Inhibitory gating
# ─────────────────────────────────────────────────────────────────────────────


def test_inhibitory_gating_high_confidence_ok():
    result = json.loads(
        handle_validate_inhibitory_gating(
            {
                "channel": _channel(quality_threshold=0.7),
                "sender_confidence": 0.85,
            }
        )
    )
    assert result["ok"] is True


def test_inhibitory_gating_low_confidence_blocked():
    result = json.loads(
        handle_validate_inhibitory_gating(
            {
                "channel": _channel(quality_threshold=0.7),
                "sender_confidence": 0.3,
            }
        )
    )
    assert result["ok"] is False


# ─────────────────────────────────────────────────────────────────────────────
# Refractory
# ─────────────────────────────────────────────────────────────────────────────


def test_refractory_not_in_period_ok():
    result = json.loads(
        handle_validate_refractory(
            {
                "channel": _channel(),
                "is_in_refractory": False,
                "message_attempted": True,
            }
        )
    )
    assert result["ok"] is True


def test_refractory_message_during_period_fails():
    result = json.loads(
        handle_validate_refractory(
            {
                "channel": _channel(),
                "is_in_refractory": True,
                "message_attempted": True,
            }
        )
    )
    assert result["ok"] is False


# ─────────────────────────────────────────────────────────────────────────────
# Critical restriction
# ─────────────────────────────────────────────────────────────────────────────


def test_critical_restriction_all_attenuated_ok():
    result = json.loads(
        handle_validate_critical_restriction(
            {
                "trace": _trace(state="critical"),
                "channels": [
                    _channel("c1", state="attenuated"),
                    _channel("c2", state="severed"),
                ],
            }
        )
    )
    assert result["ok"] is True
    assert result["channels_checked"] == 2


def test_critical_restriction_active_channel_fails():
    result = json.loads(
        handle_validate_critical_restriction(
            {
                "trace": _trace(state="critical"),
                "channels": [_channel("c1", state="active")],
            }
        )
    )
    assert result["ok"] is False
    assert "N-9" in result["error"]


def test_critical_restriction_stable_with_active_ok():
    result = json.loads(
        handle_validate_critical_restriction(
            {
                "trace": _trace(state="stable"),
                "channels": [_channel("c1", state="active")],
            }
        )
    )
    assert result["ok"] is True


def test_critical_restriction_non_list_channels_raises():
    with pytest.raises(ToolInvocationError, match="list of objects"):
        handle_validate_critical_restriction(
            {"trace": _trace(state="critical"), "channels": "not-a-list"}
        )
