# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Tests for ClearanceLevel and the NERVE AgentCard extension."""

from __future__ import annotations

import pytest

from nerve.types import (
    CANONICAL_CLEARANCE_LEVELS,
    NERVE_EXTENSION_URI,
    ClearanceLevel,
    NeuralPostureRef,
    NerveEnvelope,
    NeuronType,
    compute_behavioral_fingerprint,
    is_canonical_clearance,
)


def test_extension_uri_is_stable():
    assert NERVE_EXTENSION_URI == (
        "https://ravikiran438.github.io/pratyahara-nerve/v1"
    )


def test_clearance_levels_match_paper():
    expected = {"task_data", "routing_metadata"}
    assert expected == CANONICAL_CLEARANCE_LEVELS


def test_is_canonical_clearance_filters_typos():
    assert is_canonical_clearance("task_data")
    assert not is_canonical_clearance("taskdata")
    assert not is_canonical_clearance("task-data")
    assert not is_canonical_clearance("")
    # Vendor extensions remain valid as plain strings; canonical check
    # returns False for them, signalling "this isn't a paper-named value"
    # without rejecting them outright.
    assert not is_canonical_clearance("acme:internal_state")


def test_clearance_enum_value_matches_string():
    assert ClearanceLevel.TASK_DATA.value == "task_data"
    assert ClearanceLevel.ROUTING_METADATA.value == "routing_metadata"


def _good_card_args(**overrides):
    base = dict(
        version="1.0.0",
        neuron_type=NeuronType.PROCESSING,
        behavioral_fingerprint=compute_behavioral_fingerprint([0.1, 0.2, 0.3]),
        trust_score=0.7,
        observer_ids=["obs-a", "obs-b"],
        myelination_levels={"chan-1": 0.5},
        homeostasis_state="STABLE",
    )
    base.update(overrides)
    return base


def test_agent_card_extension_round_trip():
    card = NeuralPostureRef(**_good_card_args())
    blob = card.model_dump_json()
    parsed = NeuralPostureRef.model_validate_json(blob)
    assert parsed.trust_score == 0.7
    assert parsed.observer_ids == ["obs-a", "obs-b"]


def test_agent_card_requires_two_observers():
    with pytest.raises(ValueError):
        NeuralPostureRef(**_good_card_args(observer_ids=["only-one"]))


def test_agent_card_rejects_malformed_fingerprint():
    with pytest.raises(ValueError, match="behavioral_fingerprint"):
        NeuralPostureRef(
            **_good_card_args(behavioral_fingerprint="sha256:tooshort")
        )


def test_nerve_envelope_round_trip():
    env = NerveEnvelope(
        sender_trust_score=0.8,
        sender_confidence=0.92,
        channel_myelination=0.5,
        channel_state="active",
        homeostasis_state="STABLE",
        cascade_depth=2,
        permeability_clearance=[
            ClearanceLevel.TASK_DATA.value,
            ClearanceLevel.ROUTING_METADATA.value,
        ],
    )
    blob = env.model_dump_json()
    parsed = NerveEnvelope.model_validate_json(blob)
    assert parsed.cascade_depth == 2
    for c in parsed.permeability_clearance:
        assert is_canonical_clearance(c)
