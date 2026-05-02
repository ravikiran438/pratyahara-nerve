# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Permeability clearance: extensible context-type enum.

The NERVE preprint references ``permeability_clearance`` as the set of
context types a SynapticChannel allows to cross its boundary. The paper
shows ``["task_data", "routing_metadata"]`` as the two example values.

This module mirrors *only those two paper-named values* as canonical.
Deployments are expected to extend the vocabulary with vendor-prefixed
values (e.g. ``"acme:internal_state"``) to match their threat model.
The enum stays small because the paper's design intentionally leaves
the policy detail to deployments.
"""

from __future__ import annotations

from enum import Enum


class ClearanceLevel(str, Enum):
    """The two clearance levels named in the NERVE preprint.

    Other values are valid as plain strings; this enum is the canonical
    label for the paper-defined ones only.
    """

    TASK_DATA = "task_data"
    ROUTING_METADATA = "routing_metadata"


CANONICAL_CLEARANCE_LEVELS: frozenset[str] = frozenset(
    {member.value for member in ClearanceLevel}
)


def is_canonical_clearance(value: str) -> bool:
    """True if ``value`` is one of the paper-named canonical clearance levels."""
    return value in CANONICAL_CLEARANCE_LEVELS
