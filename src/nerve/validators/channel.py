# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Channel-level validators for N-4, N-5, N-14, N-15."""

from __future__ import annotations

from typing import List

from nerve.types.synaptic_channel import ChannelState, SynapticChannel


class SeveranceFinalityError(ValueError):
    """N-4: A severed channel carried a message."""


class QuarantineFreezeError(ValueError):
    """N-5: Myelination increased during quarantine."""


class InhibitoryGatingError(ValueError):
    """N-14: A low-confidence message was propagated."""


class RefractoryError(ValueError):
    """N-15: A message was sent during refractory cooldown."""


def validate_severance_finality(
    channel: SynapticChannel,
    message_delivered: bool,
) -> None:
    """N-4: A severed channel MUST transmit zero messages."""
    if channel.state == ChannelState.SEVERED and message_delivered:
        raise SeveranceFinalityError(
            f"N-4 violated: channel {channel.channel_id!r} is severed but "
            "a message was delivered"
        )


def validate_quarantine_freeze(
    channel: SynapticChannel,
    previous_myelination: float,
) -> None:
    """N-5: Myelination cannot increase during quarantined state."""
    if (
        channel.state == ChannelState.QUARANTINED
        and channel.myelination_level > previous_myelination
    ):
        raise QuarantineFreezeError(
            f"N-5 violated: channel {channel.channel_id!r} is quarantined but "
            f"myelination increased from {previous_myelination} to "
            f"{channel.myelination_level}"
        )


def validate_inhibitory_gating(
    channel: SynapticChannel,
    sender_confidence: float,
) -> None:
    """N-14: Output below quality_threshold MUST NOT propagate."""
    if sender_confidence < channel.quality_threshold:
        raise InhibitoryGatingError(
            f"N-14 violated: channel {channel.channel_id!r} received message "
            f"with confidence {sender_confidence} below threshold "
            f"{channel.quality_threshold}"
        )


def validate_refractory(
    channel: SynapticChannel,
    is_in_refractory: bool,
    message_attempted: bool,
) -> None:
    """N-15: No messages during refractory cooldown."""
    if is_in_refractory and message_attempted:
        raise RefractoryError(
            f"N-15 violated: channel {channel.channel_id!r} is in refractory "
            "state but a message transmission was attempted"
        )
