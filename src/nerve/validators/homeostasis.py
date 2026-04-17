# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""N-9: Critical Restriction. Critical homeostasis triggers max permeability restriction."""

from __future__ import annotations

from typing import List

from nerve.types.homeostasis_trace import HomeostasisState, HomeostasisTrace
from nerve.types.synaptic_channel import ChannelState, SynapticChannel


class CriticalRestrictionError(ValueError):
    """N-9: Network is critical but a channel is still fully active."""


def validate_critical_restriction(
    trace: HomeostasisTrace,
    channels: List[SynapticChannel],
) -> None:
    """N-9: When homeostasis is critical, no channel may be in active state.

    All channels must be attenuated, severed, or quarantined.
    """
    if trace.homeostasis_state != HomeostasisState.CRITICAL:
        return

    for ch in channels:
        if ch.state == ChannelState.ACTIVE:
            raise CriticalRestrictionError(
                f"N-9 violated: homeostasis_state is critical but channel "
                f"{ch.channel_id!r} is still active. All channels must be "
                "attenuated or more restrictive during critical state."
            )
