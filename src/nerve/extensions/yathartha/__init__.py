"""Yathartha: capability-surface extension to NERVE.

Public surface of the Yathartha extension. Importing from here keeps
downstream code isolated from the internal module layout.
"""

from .types import (
    CapabilityRegion,
    CapabilitySurface,
    ProbeBatteryResult,
    SurfaceChangeEvent,
    TaskResult,
    UncoveredPolicy,
)
from .validators import (
    YatharthaInvariantError,
    check_capability_surface_integrity,
    check_coverage_conditional_drift,
    check_probe_battery_maintenance,
)

__all__ = [
    "EXTENSION_URI",
    "CapabilityRegion",
    "CapabilitySurface",
    "ProbeBatteryResult",
    "SurfaceChangeEvent",
    "TaskResult",
    "UncoveredPolicy",
    "YatharthaInvariantError",
    "check_capability_surface_integrity",
    "check_coverage_conditional_drift",
    "check_probe_battery_maintenance",
]

EXTENSION_URI = (
    "https://github.com/ravikiran438/pratyahara-nerve/"
    "extensions/yathartha/v1"
)
