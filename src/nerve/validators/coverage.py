# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""N-1: Dual Coverage. Every AgentNeuron assigned to >= 2 MicroglialObserver instances."""

from __future__ import annotations

from typing import Dict, List


class DualCoverageError(ValueError):
    """Raised when an agent has fewer than 2 assigned observers."""


def validate_dual_coverage(
    agent_to_observers: Dict[str, List[str]],
) -> None:
    """Check that every agent is monitored by at least 2 observers.

    ``agent_to_observers`` maps agent_id to a list of observer_ids.
    """
    for agent_id, observers in agent_to_observers.items():
        if len(set(observers)) < 2:
            raise DualCoverageError(
                f"N-1 violated: agent {agent_id!r} has {len(set(observers))} "
                f"observer(s), minimum is 2"
            )
