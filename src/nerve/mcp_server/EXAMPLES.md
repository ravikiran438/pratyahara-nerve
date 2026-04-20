# NERVE MCP Server — Sample Payloads

Ready-to-paste JSON for every tool exposed by `nerve-mcp`. Drop any
block at an MCP client with an invocation like:

> Call `validate_dual_coverage` with this input: `<paste>`

Each tool maps 1:1 to a named NERVE safety invariant. Happy-path
payloads return `"ok": true`; the failure variants trip the invariant
and return the diagnostic message.

---

## validate_dual_coverage (N-1)

**What it checks:** every agent is observed by at least two distinct
MicroglialObservers.

```json
{
  "agent_to_observers": {
    "a1": ["o1", "o2"],
    "a2": ["o2", "o3"]
  }
}
```

**Failure variant:** one agent with only one observer:

```json
{
  "agent_to_observers": {"a1": ["o1"]}
}
```

---

## validate_asymmetric_trust (N-3)

**What it checks:** outgoing and incoming trust weights on a
NeuralTrustEnvelope are allowed to diverge (enforced at construction).

```json
{
  "envelope": {
    "envelope_id": "nte1",
    "agent_id": "a1",
    "decay_rate": 0.05,
    "reinforcement_rate": 0.01
  }
}
```

**Failure variant:** set both rates equal
(`"decay_rate": 0.03, "reinforcement_rate": 0.03`) — Pydantic rejects
at construction with an invalid-envelope error.

---

## validate_severance_finality (N-4)

**What it checks:** once a channel is severed, no message may be
delivered on it.

```json
{
  "channel": {
    "channel_id": "c1",
    "source_agent_id": "a1",
    "target_agent_id": "a2",
    "channel_type": "a2a_task",
    "state": "severed",
    "myelination_level": 0.5,
    "quality_threshold": 0.7
  },
  "message_delivered": false
}
```

**Failure variant:** set `"message_delivered": true` with the same
severed channel — trips N-4.

---

## validate_quarantine_freeze (N-5)

**What it checks:** a quarantined channel's myelination cannot exceed
the value at quarantine-entry time.

```json
{
  "channel": {
    "channel_id": "c1",
    "source_agent_id": "a1",
    "target_agent_id": "a2",
    "channel_type": "a2a_task",
    "state": "quarantined",
    "myelination_level": 0.5,
    "quality_threshold": 0.7
  },
  "previous_myelination": 0.5
}
```

**Failure variant:** set `"myelination_level": 0.7` while keeping
`"previous_myelination": 0.5` — myelination increased, trips N-5.

---

## validate_inhibitory_gating (N-14)

**What it checks:** sender confidence must meet the channel's quality
threshold before a message is admitted.

```json
{
  "channel": {
    "channel_id": "c1",
    "source_agent_id": "a1",
    "target_agent_id": "a2",
    "channel_type": "a2a_task",
    "state": "active",
    "myelination_level": 0.5,
    "quality_threshold": 0.7
  },
  "sender_confidence": 0.85
}
```

**Failure variant:** set `"sender_confidence": 0.3` — below the
threshold, trips N-14.

---

## validate_refractory (N-15)

**What it checks:** no message is attempted while a channel is in its
refractory period.

```json
{
  "channel": {
    "channel_id": "c1",
    "source_agent_id": "a1",
    "target_agent_id": "a2",
    "channel_type": "a2a_task",
    "state": "active",
    "myelination_level": 0.5,
    "quality_threshold": 0.7
  },
  "is_in_refractory": false,
  "message_attempted": true
}
```

**Failure variant:** set `"is_in_refractory": true` with
`"message_attempted": true` — trips N-15.

---

## validate_critical_restriction (N-9)

**What it checks:** when network homeostasis is critical, all
non-critical channels must be closed (attenuated or severed).

```json
{
  "trace": {
    "network_id": "net1",
    "computed_at": "2026-04-17T10:00:00Z",
    "network_entropy": 2.0,
    "homeostasis_state": "critical"
  },
  "channels": [
    {"channel_id": "c1", "source_agent_id": "a1", "target_agent_id": "a2", "channel_type": "a2a_task", "state": "attenuated", "myelination_level": 0.5, "quality_threshold": 0.7},
    {"channel_id": "c2", "source_agent_id": "a1", "target_agent_id": "a3", "channel_type": "a2a_task", "state": "severed", "myelination_level": 0.5, "quality_threshold": 0.7}
  ]
}
```

**Failure variant:** set one channel's `"state": "active"` while
homeostasis is `"critical"` — trips N-9.

---

# Yathartha Extension (N-16, N-17, N-18)

The Yathartha capability-surface extension lives under
[`extensions/yathartha/`](../../../extensions/yathartha/). The three
invariants condition drift detection on an observed baseline so that
jaggedness (unknown competence) is not mistaken for drift (lost
competence).

Timestamps below use ISO 8601 UTC. `run_at` and
`last_full_refresh_at` should be close to the current time so regions
are considered fresh (within `refresh_cadence_hours`).

---

## validate_coverage_conditional_drift (N-16)

**What it checks:** a MicroglialObserver may raise a drift flag only
if the task's region is in the agent's covered set AND the region is
not stale. Tasks outside coverage (jaggedness) are handed off to the
agent's `uncovered_policy`.

**Happy path** — drift flagging is allowed:

```json
{
  "surface": {
    "agent_id": "agent-1",
    "regions": {
      "arithmetic": {
        "id": "00000000-0000-4000-8000-000000000001",
        "region_id": "arithmetic",
        "agent_id": "agent-1",
        "battery_version": 1,
        "run_at": "2026-04-20T00:00:00+00:00",
        "task_results": [
          {"task_id": "t1", "passed": true, "score": 0.9},
          {"task_id": "t2", "passed": true, "score": 0.9}
        ],
        "aggregate_score": 0.9,
        "covered": true,
        "confidence": 0.95
      }
    },
    "uncovered_policy": "defer",
    "refresh_cadence_hours": 24,
    "battery_version": 1,
    "last_full_refresh_at": "2026-04-20T00:00:00+00:00"
  },
  "task_region": "arithmetic"
}
```

Returns `{"allowed_to_flag_drift": true, "reason": "covered and fresh"}`.

**Jaggedness variant:** change `task_region` to `"letter-counting"` —
not in covered set, returns `allowed_to_flag_drift=false` with reason
`apply uncovered_policy=defer`.

**Staleness variant:** set `run_at` to more than 24 hours in the past
(the refresh cadence) — returns `allowed_to_flag_drift=false` with
reason `re-probe before flagging drift`.

---

## validate_probe_battery_maintenance (N-17)

**What it checks:** two ProbeBatteryResult entries can only be
compared if they share the same `battery_version`, `region_id`, and
`agent_id`. A battery version bump requires a full re-baseline.

**Happy path** — compatible versions:

```json
{
  "old_result": {
    "id": "00000000-0000-4000-8000-000000000010",
    "region_id": "arithmetic",
    "agent_id": "agent-1",
    "battery_version": 1,
    "run_at": "2026-04-19T00:00:00+00:00",
    "task_results": [
      {"task_id": "t1", "passed": true, "score": 0.9},
      {"task_id": "t2", "passed": true, "score": 0.9}
    ],
    "aggregate_score": 0.9,
    "covered": true,
    "confidence": 0.95
  },
  "new_result": {
    "id": "00000000-0000-4000-8000-000000000011",
    "region_id": "arithmetic",
    "agent_id": "agent-1",
    "battery_version": 1,
    "run_at": "2026-04-20T00:00:00+00:00",
    "task_results": [
      {"task_id": "t1", "passed": true, "score": 0.85},
      {"task_id": "t2", "passed": true, "score": 0.85}
    ],
    "aggregate_score": 0.85,
    "covered": true,
    "confidence": 0.95
  }
}
```

**Failure variant:** set `new_result.battery_version` to `2` — trips
N-17 with the "full re-baseline required" diagnostic.

---

## validate_capability_surface_integrity (N-18)

**What it checks:** every change in the covered-regions set (or
battery_version, or uncovered_policy) between two CapabilitySurface
snapshots must be accompanied by a matching SurfaceChangeEvent.

**Happy path** — new region entered, with a matching event:

```json
{
  "before": {
    "agent_id": "agent-1",
    "regions": {
      "arithmetic": {
        "id": "00000000-0000-4000-8000-000000000020",
        "region_id": "arithmetic",
        "agent_id": "agent-1",
        "battery_version": 1,
        "run_at": "2026-04-20T00:00:00+00:00",
        "task_results": [
          {"task_id": "t1", "passed": true, "score": 0.9},
          {"task_id": "t2", "passed": true, "score": 0.9}
        ],
        "aggregate_score": 0.9,
        "covered": true,
        "confidence": 0.95
      }
    },
    "uncovered_policy": "defer",
    "refresh_cadence_hours": 24,
    "battery_version": 1,
    "last_full_refresh_at": "2026-04-20T00:00:00+00:00"
  },
  "after": {
    "agent_id": "agent-1",
    "regions": {
      "arithmetic": {
        "id": "00000000-0000-4000-8000-000000000020",
        "region_id": "arithmetic",
        "agent_id": "agent-1",
        "battery_version": 1,
        "run_at": "2026-04-20T00:00:00+00:00",
        "task_results": [
          {"task_id": "t1", "passed": true, "score": 0.9},
          {"task_id": "t2", "passed": true, "score": 0.9}
        ],
        "aggregate_score": 0.9,
        "covered": true,
        "confidence": 0.95
      },
      "scheduling": {
        "id": "00000000-0000-4000-8000-000000000021",
        "region_id": "scheduling",
        "agent_id": "agent-1",
        "battery_version": 1,
        "run_at": "2026-04-20T00:00:00+00:00",
        "task_results": [
          {"task_id": "s1", "passed": true, "score": 0.88},
          {"task_id": "s2", "passed": true, "score": 0.88}
        ],
        "aggregate_score": 0.88,
        "covered": true,
        "confidence": 0.95
      }
    },
    "uncovered_policy": "defer",
    "refresh_cadence_hours": 24,
    "battery_version": 1,
    "last_full_refresh_at": "2026-04-20T00:00:00+00:00"
  },
  "events": [
    {
      "id": "00000000-0000-4000-8000-000000000030",
      "agent_id": "agent-1",
      "region_id": "scheduling",
      "kind": "entered",
      "at": "2026-04-20T00:00:00+00:00"
    }
  ]
}
```

**Failure variant:** drop the event from `"events"` — trips N-18 with
"region 'scheduling' entered coverage without a matching
SurfaceChangeEvent".
