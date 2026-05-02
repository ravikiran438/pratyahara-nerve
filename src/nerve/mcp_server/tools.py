# Copyright 2026 Ravi Kiran Kadaboina
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tool registrations for the NERVE MCP server.

Each tool wraps one of the seven named safety-invariant validators from
the NERVE specification. Invariants that fail return ``{"ok": false,
"error": ...}`` carrying the validator's own diagnostic message.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from nerve.types import (
    HomeostasisTrace,
    NerveEnvelope,
    NeuralPostureRef,
    NeuralTrustEnvelope,
    SynapticChannel,
    is_well_formed_fingerprint,
    verify_behavioral_fingerprint,
)
from nerve.validators import (
    AsymmetricTrustError,
    CriticalRestrictionError,
    DualCoverageError,
    InhibitoryGatingError,
    QuarantineFreezeError,
    RefractoryError,
    SeveranceFinalityError,
    validate_asymmetric_trust,
    validate_critical_restriction,
    validate_dual_coverage,
    validate_inhibitory_gating,
    validate_quarantine_freeze,
    validate_refractory,
    validate_severance_finality,
)

# Yathartha extension (N-16, N-17, N-18). See extensions/yathartha/.
from nerve.extensions.yathartha import (
    CapabilitySurface,
    ProbeBatteryResult,
    SurfaceChangeEvent,
    YatharthaInvariantError,
    check_capability_surface_integrity,
    check_coverage_conditional_drift,
    check_probe_battery_maintenance,
)


# ─────────────────────────────────────────────────────────────────────────────
# Generic MCP glue — portable across sibling protocol repos.
# Keep these four symbols (ToolInvocationError, _parse, _ok, _fail) in sync
# by convention when copying to acap, phala, or sauvidya-pace.
# ─────────────────────────────────────────────────────────────────────────────


class ToolInvocationError(Exception):
    """Raised when a tool's handler rejects its input or runtime fails."""


def _parse(cls, payload: Any, label: str):
    try:
        return cls.model_validate(payload)
    except ValidationError as exc:
        raise ToolInvocationError(f"invalid {label}: {exc}") from exc


def _ok(payload: dict[str, Any]) -> str:
    return json.dumps({"ok": True, **payload}, default=str, indent=2)


def _fail(message: str) -> str:
    return json.dumps({"ok": False, "error": message}, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# Tool handlers (repo-specific; everything below this line is NERVE-only).
# ─────────────────────────────────────────────────────────────────────────────


TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "validate_dual_coverage": {
        "description": (
            "Verify that every agent in the network is observed by at "
            "least two distinct MicroglialObservers. Enforces NERVE "
            "N-1 (dual-coverage)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_to_observers": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "description": "Map from agent id → list of observer "
                    "ids watching that agent.",
                },
            },
            "required": ["agent_to_observers"],
        },
    },
    "validate_asymmetric_trust": {
        "description": (
            "Verify that outgoing and incoming trust weights on a "
            "NeuralTrustEnvelope are allowed to diverge. Enforces the "
            "asymmetric-trust invariant."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "envelope": {
                    "type": "object",
                    "description": "NeuralTrustEnvelope object.",
                },
            },
            "required": ["envelope"],
        },
    },
    "validate_severance_finality": {
        "description": (
            "Verify that a severed SynapticChannel did not deliver the "
            "most recent message. Enforces the severance-finality "
            "invariant: once a channel is severed, no further message "
            "may be delivered."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel": {"type": "object"},
                "message_delivered": {
                    "type": "boolean",
                    "description": "Whether the message under test was "
                    "actually delivered.",
                },
            },
            "required": ["channel", "message_delivered"],
        },
    },
    "validate_quarantine_freeze": {
        "description": (
            "Verify that a quarantined SynapticChannel's myelination "
            "matches the value at quarantine-entry time. Enforces the "
            "quarantine-freeze invariant."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel": {"type": "object"},
                "previous_myelination": {
                    "type": "number",
                    "description": "Myelination value recorded when the "
                    "channel entered quarantine.",
                },
            },
            "required": ["channel", "previous_myelination"],
        },
    },
    "validate_inhibitory_gating": {
        "description": (
            "Verify that messages on a channel are gated by the "
            "sender's confidence (inhibitory-gating invariant)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel": {"type": "object"},
                "sender_confidence": {
                    "type": "number",
                    "description": "Sender's current confidence score "
                    "for the message under test.",
                },
            },
            "required": ["channel", "sender_confidence"],
        },
    },
    "validate_refractory": {
        "description": (
            "Verify that no message is attempted while a channel is in "
            "its refractory period. Enforces the refractory invariant."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel": {"type": "object"},
                "is_in_refractory": {"type": "boolean"},
                "message_attempted": {"type": "boolean"},
            },
            "required": [
                "channel",
                "is_in_refractory",
                "message_attempted",
            ],
        },
    },
    "validate_critical_restriction": {
        "description": (
            "Verify that when a HomeostasisTrace reports critical "
            "state, all non-critical channels are closed (critical-"
            "restriction invariant)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "trace": {"type": "object"},
                "channels": {
                    "type": "array",
                    "items": {"type": "object"},
                },
            },
            "required": ["trace", "channels"],
        },
    },
    # ── Yathartha extension (N-16, N-17, N-18) ────────────────────────────
    "validate_coverage_conditional_drift": {
        "description": (
            "Yathartha N-16: given a CapabilitySurface and a task region, "
            "decide whether a MicroglialObserver may raise a drift flag. "
            "Returns allowed_to_flag_drift (bool) plus the reason. A "
            "task outside the covered set (jaggedness) is NOT drift and "
            "must be handled by the agent's uncovered_policy."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "surface": {"type": "object"},
                "task_region": {"type": "string"},
            },
            "required": ["surface", "task_region"],
        },
    },
    "validate_probe_battery_maintenance": {
        "description": (
            "Yathartha N-17: verify that two ProbeBatteryResult entries "
            "can be compared. Raises if battery_version differs (triggers "
            "full re-baseline) or if region/agent identifiers mismatch."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "old_result": {"type": "object"},
                "new_result": {"type": "object"},
            },
            "required": ["old_result", "new_result"],
        },
    },
    "validate_capability_surface_integrity": {
        "description": (
            "Yathartha N-18: verify that every change in the "
            "covered_regions set (or battery_version, or "
            "uncovered_policy) between two CapabilitySurface snapshots "
            "is accompanied by a matching SurfaceChangeEvent."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "before": {"type": "object"},
                "after": {"type": "object"},
                "events": {
                    "type": "array",
                    "items": {"type": "object"},
                },
            },
            "required": ["before", "after", "events"],
        },
    },
    "validate_neural_posture_ref": {
        "description": (
            "Validate a NeuralPostureRef payload (the body of the "
            "AgentCard.capabilities.extensions[] entry whose URI equals "
            "NERVE_EXTENSION_URI). Verifies version + neuron_type + the "
            "well-formed fingerprint shape + N-1 (≥2 distinct observers)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"ref": {"type": "object"}},
            "required": ["ref"],
        },
    },
    "validate_nerve_envelope": {
        "description": (
            "Validate a NerveEnvelope payload (the per-message metadata "
            "block carried under message.metadata[NERVE_EXTENSION_URI]). "
            "Verifies the typed structure of trust, channel, and "
            "permeability_clearance fields."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"envelope": {"type": "object"}},
            "required": ["envelope"],
        },
    },
    "validate_behavioral_fingerprint": {
        "description": (
            "Verify a behavioral_fingerprint string. If only "
            "'fingerprint' is supplied, performs the structural "
            "well-formedness check (sha256:<64-hex>). If 'embedding' "
            "is also supplied, recomputes the canonical fingerprint and "
            "rejects on mismatch."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "fingerprint": {"type": "string"},
                "embedding": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": (
                        "Optional. When present, the canonical fingerprint "
                        "is recomputed and compared against the claim."
                    ),
                },
            },
            "required": ["fingerprint"],
        },
    },
}


def _parse_channel(payload: Any, label: str) -> SynapticChannel:
    if not isinstance(payload, dict):
        raise ToolInvocationError(f"expected object under key {label!r}")
    return _parse(SynapticChannel, payload, label)


def _parse_bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise ToolInvocationError(f"{label} must be a boolean")
    return value


def _parse_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ToolInvocationError(f"{label} must be a number")
    return float(value)


def handle_validate_dual_coverage(arguments: dict[str, Any]) -> str:
    raw = arguments.get("agent_to_observers")
    if not isinstance(raw, dict):
        raise ToolInvocationError("expected object under 'agent_to_observers'")
    # normalize to str → list[str]
    normalized: dict[str, list[str]] = {}
    for agent, observers in raw.items():
        if not isinstance(observers, list) or not all(
            isinstance(o, str) for o in observers
        ):
            raise ToolInvocationError(
                f"agent_to_observers[{agent!r}] must be a list of strings"
            )
        normalized[agent] = list(observers)

    try:
        validate_dual_coverage(normalized)
    except DualCoverageError as exc:
        return _fail(str(exc))
    return _ok({"agents_checked": len(normalized)})


def handle_validate_asymmetric_trust(arguments: dict[str, Any]) -> str:
    envelope = _parse(
        NeuralTrustEnvelope, arguments.get("envelope"), "envelope"
    )
    try:
        validate_asymmetric_trust(envelope)
    except AsymmetricTrustError as exc:
        return _fail(str(exc))
    return _ok({"envelope": "valid"})


def handle_validate_severance_finality(arguments: dict[str, Any]) -> str:
    channel = _parse_channel(arguments.get("channel"), "channel")
    delivered = _parse_bool(
        arguments.get("message_delivered"), "message_delivered"
    )
    try:
        validate_severance_finality(channel, delivered)
    except SeveranceFinalityError as exc:
        return _fail(str(exc))
    return _ok({"channel": "severance-finality-honored"})


def handle_validate_quarantine_freeze(arguments: dict[str, Any]) -> str:
    channel = _parse_channel(arguments.get("channel"), "channel")
    prev = _parse_number(
        arguments.get("previous_myelination"), "previous_myelination"
    )
    try:
        validate_quarantine_freeze(channel, prev)
    except QuarantineFreezeError as exc:
        return _fail(str(exc))
    return _ok({"channel": "quarantine-freeze-honored"})


def handle_validate_inhibitory_gating(arguments: dict[str, Any]) -> str:
    channel = _parse_channel(arguments.get("channel"), "channel")
    confidence = _parse_number(
        arguments.get("sender_confidence"), "sender_confidence"
    )
    try:
        validate_inhibitory_gating(channel, confidence)
    except InhibitoryGatingError as exc:
        return _fail(str(exc))
    return _ok({"channel": "inhibitory-gating-honored"})


def handle_validate_refractory(arguments: dict[str, Any]) -> str:
    channel = _parse_channel(arguments.get("channel"), "channel")
    is_in_refractory = _parse_bool(
        arguments.get("is_in_refractory"), "is_in_refractory"
    )
    message_attempted = _parse_bool(
        arguments.get("message_attempted"), "message_attempted"
    )
    try:
        validate_refractory(channel, is_in_refractory, message_attempted)
    except RefractoryError as exc:
        return _fail(str(exc))
    return _ok({"channel": "refractory-honored"})


def handle_validate_critical_restriction(arguments: dict[str, Any]) -> str:
    trace = _parse(HomeostasisTrace, arguments.get("trace"), "trace")
    channels_raw = arguments.get("channels")
    if not isinstance(channels_raw, list):
        raise ToolInvocationError("channels must be a list of objects")
    channels = [
        _parse_channel(c, f"channels[{i}]")
        for i, c in enumerate(channels_raw)
    ]
    try:
        validate_critical_restriction(trace, channels)
    except CriticalRestrictionError as exc:
        return _fail(str(exc))
    return _ok({"channels_checked": len(channels)})


# ── Yathartha extension handlers (N-16, N-17, N-18) ───────────────────────


def handle_validate_coverage_conditional_drift(arguments: dict[str, Any]) -> str:
    surface = _parse(CapabilitySurface, arguments.get("surface"), "surface")
    task_region = arguments.get("task_region")
    if not isinstance(task_region, str) or not task_region:
        raise ToolInvocationError("task_region must be a non-empty string")
    allowed, reason = check_coverage_conditional_drift(surface, task_region)
    return _ok(
        {"allowed_to_flag_drift": allowed, "reason": reason}
    )


def handle_validate_probe_battery_maintenance(arguments: dict[str, Any]) -> str:
    old = _parse(ProbeBatteryResult, arguments.get("old_result"), "old_result")
    new = _parse(ProbeBatteryResult, arguments.get("new_result"), "new_result")
    try:
        check_probe_battery_maintenance(old, new)
    except YatharthaInvariantError as exc:
        return _fail(str(exc))
    return _ok({"comparison": "compatible"})


def handle_validate_neural_posture_ref(arguments: dict[str, Any]) -> str:
    ref_payload = arguments.get("ref")
    if not isinstance(ref_payload, dict):
        raise ToolInvocationError("expected object under key 'ref'")
    _parse(NeuralPostureRef, ref_payload, "ref")
    return _ok({"ref": "valid"})


def handle_validate_nerve_envelope(arguments: dict[str, Any]) -> str:
    env_payload = arguments.get("envelope")
    if not isinstance(env_payload, dict):
        raise ToolInvocationError("expected object under key 'envelope'")
    _parse(NerveEnvelope, env_payload, "envelope")
    return _ok({"envelope": "valid"})


def handle_validate_behavioral_fingerprint(arguments: dict[str, Any]) -> str:
    fp = arguments.get("fingerprint")
    if not isinstance(fp, str) or not fp:
        raise ToolInvocationError("fingerprint must be a non-empty string")
    if not is_well_formed_fingerprint(fp):
        return _fail(
            f"fingerprint {fp!r} is not a well-formed sha256:<64-hex> value"
        )
    embedding = arguments.get("embedding")
    if embedding is not None:
        if not isinstance(embedding, list) or not all(
            isinstance(x, (int, float)) and not isinstance(x, bool)
            for x in embedding
        ):
            raise ToolInvocationError("embedding must be a list of numbers")
        if not embedding:
            raise ToolInvocationError("embedding must be non-empty")
        if not verify_behavioral_fingerprint(fp, embedding):
            return _fail(
                "fingerprint does not match canonical computation over "
                "the supplied embedding"
            )
        return _ok({"fingerprint": "matches embedding"})
    return _ok({"fingerprint": "well-formed"})


def handle_validate_capability_surface_integrity(
    arguments: dict[str, Any],
) -> str:
    before = _parse(CapabilitySurface, arguments.get("before"), "before")
    after = _parse(CapabilitySurface, arguments.get("after"), "after")
    events_raw = arguments.get("events")
    if not isinstance(events_raw, list):
        raise ToolInvocationError("events must be a list of objects")
    events = [
        _parse(SurfaceChangeEvent, e, f"events[{i}]")
        for i, e in enumerate(events_raw)
    ]
    try:
        check_capability_surface_integrity(before, after, events)
    except YatharthaInvariantError as exc:
        return _fail(str(exc))
    return _ok({"surface_integrity": "honored"})


HANDLERS: dict[str, Any] = {
    "validate_dual_coverage": handle_validate_dual_coverage,
    "validate_asymmetric_trust": handle_validate_asymmetric_trust,
    "validate_severance_finality": handle_validate_severance_finality,
    "validate_quarantine_freeze": handle_validate_quarantine_freeze,
    "validate_inhibitory_gating": handle_validate_inhibitory_gating,
    "validate_refractory": handle_validate_refractory,
    "validate_critical_restriction": handle_validate_critical_restriction,
    # Yathartha extension
    "validate_coverage_conditional_drift": handle_validate_coverage_conditional_drift,
    "validate_probe_battery_maintenance": handle_validate_probe_battery_maintenance,
    "validate_capability_surface_integrity": handle_validate_capability_surface_integrity,
    # AgentCard descriptor + per-message envelope + fingerprint
    "validate_neural_posture_ref": handle_validate_neural_posture_ref,
    "validate_nerve_envelope": handle_validate_nerve_envelope,
    "validate_behavioral_fingerprint": handle_validate_behavioral_fingerprint,
}


def list_tool_names() -> list[str]:
    return list(TOOL_SCHEMAS.keys())
