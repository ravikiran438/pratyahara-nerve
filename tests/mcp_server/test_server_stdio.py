# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""End-to-end stdio smoke test for the NERVE MCP server."""

from __future__ import annotations

import json
import sys

import pytest

pytest.importorskip("mcp")

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@pytest.mark.asyncio
async def test_server_lists_tools_over_stdio():
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "nerve.mcp_server"]
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()

    names = {t.name for t in tools.tools}
    expected = {
        # Core (7)
        "validate_dual_coverage",
        "validate_asymmetric_trust",
        "validate_severance_finality",
        "validate_quarantine_freeze",
        "validate_inhibitory_gating",
        "validate_refractory",
        "validate_critical_restriction",
        # Yathartha extension (3)
        "validate_coverage_conditional_drift",
        "validate_probe_battery_maintenance",
        "validate_capability_surface_integrity",
    }
    assert names == expected


@pytest.mark.asyncio
async def test_server_call_dual_coverage_over_stdio():
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "nerve.mcp_server"]
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "validate_dual_coverage",
                {"agent_to_observers": {"a1": ["o1"]}},  # only 1 observer → fail
            )

    assert result.content
    body = json.loads(result.content[0].text)
    assert body["ok"] is False
    assert "N-1" in body["error"]
