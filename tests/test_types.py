# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Tests for NERVE type construction, bounds, and invariants."""

import pytest

from nerve.types import (
    AgentNeuron,
    NeuronType,
    SynapticChannel,
    ChannelState,
    ChannelType,
    GlymphaticPolicy,
    PermeabilityPolicy,
    MicroglialObserver,
    ActivationState,
    DetectionThresholds,
    NeuralTrustEnvelope,
    HomeostasisState,
    HomeostasisTrace,
)


# ─── AgentNeuron ──────────────────────────────────────────────────────


class TestAgentNeuron:
    def test_basic_construction(self):
        an = AgentNeuron(
            agent_id="a1",
            neuron_type=NeuronType.PROCESSING,
            activation_baseline=1.0,
            current_activation=1.2,
            behavioral_fingerprint="sha256:abc123",
        )
        assert an.trust_score == 0.5
        assert an.myelination_level == 0.3

    def test_trust_bounds(self):
        with pytest.raises(Exception):
            AgentNeuron(
                agent_id="a1",
                neuron_type=NeuronType.PROCESSING,
                activation_baseline=1.0,
                current_activation=1.2,
                trust_score=1.5,  # out of [0, 1]
                behavioral_fingerprint="sha256:abc123",
            )

    def test_all_neuron_types(self):
        for nt in NeuronType:
            an = AgentNeuron(
                agent_id=f"a-{nt.value}",
                neuron_type=nt,
                activation_baseline=1.0,
                current_activation=1.0,
                behavioral_fingerprint="sha256:test",
            )
            assert an.neuron_type == nt


# ─── SynapticChannel ─────────────────────────────────────────────────


class TestSynapticChannel:
    def test_basic_construction(self):
        sc = SynapticChannel(
            channel_id="c1",
            source_agent_id="a1",
            target_agent_id="a2",
            channel_type=ChannelType.A2A_TASK,
        )
        assert sc.state == ChannelState.ACTIVE
        assert sc.myelination_level == 0.3
        assert sc.quality_threshold == 0.7

    def test_myelination_bounds(self):
        with pytest.raises(Exception):
            SynapticChannel(
                channel_id="c1",
                source_agent_id="a1",
                target_agent_id="a2",
                channel_type=ChannelType.MCP_TOOL,
                myelination_level=1.5,
            )

    def test_all_channel_states(self):
        for state in ChannelState:
            sc = SynapticChannel(
                channel_id="c1",
                source_agent_id="a1",
                target_agent_id="a2",
                channel_type=ChannelType.A2A_TASK,
                state=state,
            )
            assert sc.state == state

    def test_glymphatic_policy(self):
        gp = GlymphaticPolicy(
            max_context_age_seconds=1800,
            max_provenance_depth=2,
            excitotoxicity_threshold=3.0,
        )
        assert gp.context_compression_required is True
        assert gp.excitotoxicity_threshold == 3.0


# ─── MicroglialObserver ──────────────────────────────────────────────


class TestMicroglialObserver:
    def test_basic_construction(self):
        mo = MicroglialObserver(
            observer_id="o1",
            assigned_agents=["a1", "a2"],
        )
        assert mo.activation_state == ActivationState.SURVEILLING
        assert mo.detection_thresholds.fingerprint_drift == 0.15

    def test_requires_at_least_one_agent(self):
        with pytest.raises(Exception):
            MicroglialObserver(
                observer_id="o1",
                assigned_agents=[],
            )

    def test_custom_thresholds(self):
        dt = DetectionThresholds(
            activation_deviation=3.0,
            fingerprint_drift=0.20,
            collusion_correlation=0.8,
        )
        assert dt.activation_deviation == 3.0
        assert dt.fingerprint_drift == 0.20


# ─── NeuralTrustEnvelope ─────────────────────────────────────────────


class TestNeuralTrustEnvelope:
    def test_basic_construction(self):
        nte = NeuralTrustEnvelope(
            envelope_id="nte1",
            agent_id="a1",
        )
        assert nte.decay_rate == 0.05
        assert nte.reinforcement_rate == 0.01

    def test_nte1_asymmetric_trust_enforced(self):
        """NTE-1: decay_rate must exceed reinforcement_rate."""
        with pytest.raises(ValueError, match="NTE-1"):
            NeuralTrustEnvelope(
                envelope_id="nte-bad",
                agent_id="a1",
                decay_rate=0.01,
                reinforcement_rate=0.05,
            )

    def test_nte1_equal_rates_rejected(self):
        with pytest.raises(ValueError, match="NTE-1"):
            NeuralTrustEnvelope(
                envelope_id="nte-bad",
                agent_id="a1",
                decay_rate=0.03,
                reinforcement_rate=0.03,
            )

    def test_valid_asymmetric_rates(self):
        nte = NeuralTrustEnvelope(
            envelope_id="nte-ok",
            agent_id="a1",
            decay_rate=0.10,
            reinforcement_rate=0.02,
        )
        assert nte.decay_rate > nte.reinforcement_rate


# ─── HomeostasisTrace ─────────────────────────────────────────────────


class TestHomeostasisTrace:
    def test_basic_construction(self):
        ht = HomeostasisTrace(
            network_id="net1",
            computed_at="2026-04-17T10:00:00Z",
            network_entropy=2.5,
        )
        assert ht.homeostasis_state == HomeostasisState.STABLE
        assert ht.observer_consensus_rate == 1.0

    def test_all_homeostasis_states(self):
        for state in HomeostasisState:
            ht = HomeostasisTrace(
                network_id="net1",
                computed_at="2026-04-17T10:00:00Z",
                network_entropy=2.0,
                homeostasis_state=state,
            )
            assert ht.homeostasis_state == state
