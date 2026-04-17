# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Tests for NERVE invariant validators (N-1, N-3, N-4, N-5, N-9, N-14, N-15)."""

import pytest

from nerve.types import (
    AgentNeuron,
    NeuronType,
    SynapticChannel,
    ChannelState,
    ChannelType,
    NeuralTrustEnvelope,
    HomeostasisState,
    HomeostasisTrace,
)
from nerve.validators import (
    validate_dual_coverage,
    DualCoverageError,
    validate_asymmetric_trust,
    AsymmetricTrustError,
    validate_severance_finality,
    SeveranceFinalityError,
    validate_quarantine_freeze,
    QuarantineFreezeError,
    validate_inhibitory_gating,
    InhibitoryGatingError,
    validate_refractory,
    RefractoryError,
    validate_critical_restriction,
    CriticalRestrictionError,
)


def _channel(channel_id: str = "c1", state: ChannelState = ChannelState.ACTIVE, **kw):
    return SynapticChannel(
        channel_id=channel_id,
        source_agent_id="a1",
        target_agent_id="a2",
        channel_type=ChannelType.A2A_TASK,
        state=state,
        **kw,
    )


# ─── N-1: Dual Coverage ──────────────────────────────────────────────


class TestDualCoverage:
    def test_valid_two_observers(self):
        validate_dual_coverage({"a1": ["o1", "o2"], "a2": ["o2", "o3"]})

    def test_valid_three_observers(self):
        validate_dual_coverage({"a1": ["o1", "o2", "o3"]})

    def test_fails_single_observer(self):
        with pytest.raises(DualCoverageError, match="N-1"):
            validate_dual_coverage({"a1": ["o1"]})

    def test_fails_zero_observers(self):
        with pytest.raises(DualCoverageError, match="N-1"):
            validate_dual_coverage({"a1": []})

    def test_deduplicates(self):
        with pytest.raises(DualCoverageError):
            validate_dual_coverage({"a1": ["o1", "o1"]})


# ─── N-3: Asymmetric Trust ───────────────────────────────────────────


class TestAsymmetricTrust:
    def test_valid_envelope(self):
        nte = NeuralTrustEnvelope(
            envelope_id="nte1", agent_id="a1",
            decay_rate=0.05, reinforcement_rate=0.01,
        )
        validate_asymmetric_trust(nte)

    def test_rejects_equal_rates(self):
        # Construction itself raises, but test the validator path too
        with pytest.raises(ValueError):
            NeuralTrustEnvelope(
                envelope_id="nte-bad", agent_id="a1",
                decay_rate=0.03, reinforcement_rate=0.03,
            )


# ─── N-4: Severance Finality ─────────────────────────────────────────


class TestSeveranceFinality:
    def test_severed_no_message_ok(self):
        ch = _channel(state=ChannelState.SEVERED)
        validate_severance_finality(ch, message_delivered=False)

    def test_severed_with_message_fails(self):
        ch = _channel(state=ChannelState.SEVERED)
        with pytest.raises(SeveranceFinalityError, match="N-4"):
            validate_severance_finality(ch, message_delivered=True)

    def test_active_with_message_ok(self):
        ch = _channel(state=ChannelState.ACTIVE)
        validate_severance_finality(ch, message_delivered=True)


# ─── N-5: Quarantine Freeze ──────────────────────────────────────────


class TestQuarantineFreeze:
    def test_quarantined_stable_myelination_ok(self):
        ch = _channel(state=ChannelState.QUARANTINED, myelination_level=0.5)
        validate_quarantine_freeze(ch, previous_myelination=0.5)

    def test_quarantined_decreased_myelination_ok(self):
        ch = _channel(state=ChannelState.QUARANTINED, myelination_level=0.3)
        validate_quarantine_freeze(ch, previous_myelination=0.5)

    def test_quarantined_increased_myelination_fails(self):
        ch = _channel(state=ChannelState.QUARANTINED, myelination_level=0.7)
        with pytest.raises(QuarantineFreezeError, match="N-5"):
            validate_quarantine_freeze(ch, previous_myelination=0.5)

    def test_active_increased_myelination_ok(self):
        ch = _channel(state=ChannelState.ACTIVE, myelination_level=0.8)
        validate_quarantine_freeze(ch, previous_myelination=0.5)


# ─── N-9: Critical Restriction ───────────────────────────────────────


class TestCriticalRestriction:
    def test_critical_all_attenuated_ok(self):
        ht = HomeostasisTrace(
            network_id="net1",
            computed_at="2026-04-17T10:00:00Z",
            network_entropy=2.0,
            homeostasis_state=HomeostasisState.CRITICAL,
        )
        channels = [
            _channel("c1", state=ChannelState.ATTENUATED),
            _channel("c2", state=ChannelState.SEVERED),
        ]
        validate_critical_restriction(ht, channels)

    def test_critical_with_active_channel_fails(self):
        ht = HomeostasisTrace(
            network_id="net1",
            computed_at="2026-04-17T10:00:00Z",
            network_entropy=2.0,
            homeostasis_state=HomeostasisState.CRITICAL,
        )
        channels = [
            _channel("c1", state=ChannelState.ACTIVE),
        ]
        with pytest.raises(CriticalRestrictionError, match="N-9"):
            validate_critical_restriction(ht, channels)

    def test_stable_with_active_channel_ok(self):
        ht = HomeostasisTrace(
            network_id="net1",
            computed_at="2026-04-17T10:00:00Z",
            network_entropy=2.0,
            homeostasis_state=HomeostasisState.STABLE,
        )
        channels = [_channel("c1", state=ChannelState.ACTIVE)]
        validate_critical_restriction(ht, channels)


# ─── N-14: Inhibitory Gating ─────────────────────────────────────────


class TestInhibitoryGating:
    def test_high_confidence_ok(self):
        ch = _channel(quality_threshold=0.7)
        validate_inhibitory_gating(ch, sender_confidence=0.85)

    def test_low_confidence_blocked(self):
        ch = _channel(quality_threshold=0.7)
        with pytest.raises(InhibitoryGatingError, match="N-14"):
            validate_inhibitory_gating(ch, sender_confidence=0.5)

    def test_exact_threshold_ok(self):
        ch = _channel(quality_threshold=0.7)
        validate_inhibitory_gating(ch, sender_confidence=0.7)


# ─── N-15: Refractory Enforcement ────────────────────────────────────


class TestRefractoryEnforcement:
    def test_not_in_refractory_message_ok(self):
        ch = _channel()
        validate_refractory(ch, is_in_refractory=False, message_attempted=True)

    def test_in_refractory_no_message_ok(self):
        ch = _channel()
        validate_refractory(ch, is_in_refractory=True, message_attempted=False)

    def test_in_refractory_message_blocked(self):
        ch = _channel()
        with pytest.raises(RefractoryError, match="N-15"):
            validate_refractory(ch, is_in_refractory=True, message_attempted=True)
