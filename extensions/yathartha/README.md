# Yathartha: Capability Surface Extension

**Paper:** *Yathartha: A Protocol-Layer Treatment of Jagged Intelligence in
Autonomous Agent Networks* ([Zenodo DOI 10.5281/zenodo.19659633](https://doi.org/10.5281/zenodo.19659633)).

Yathartha extends the NERVE specification with a `CapabilitySurface`
primitive and three derived safety invariants that condition behavioral
drift detection on an observed baseline. Without this extension, a
`MicroglialObserver` cannot distinguish between:

- *jaggedness*: the agent was always incompetent at this task (no baseline)
- *drift*: the agent used to be competent at this task and now is not

Yathartha makes the distinction explicit at the protocol layer.

## Primitives

This extension adds three primitives to the NERVE type library.

- `CapabilityRegion`: a named, documented region of the task space in which
  the agent claims competence. Backed by a declared probe battery.
- `ProbeBatteryResult`: the outcome of running a region's probe battery at
  a specific time. Immutable, append-only.
- `CapabilitySurface`: the agent's published capability map composed of
  the most recent `ProbeBatteryResult` for each declared region, plus
  refresh cadence and uncovered-policy metadata.

## Invariants

The extension adds three invariants on top of the 15 NERVE invariants.

- **N-16 Coverage-Conditional Drift.** A `MicroglialObserver` MUST NOT
  flag drift for a task that does not map to a region in the agent's
  `covered_regions` set. Tasks outside coverage are handled by the
  agent's declared `uncovered_policy`, not by the drift threshold.

- **N-17 Probe Battery Maintenance.** Each agent MUST declare a
  content-addressed probe battery. A battery version change triggers a
  full baseline re-run; the new battery and the old battery are not
  comparable.

- **N-18 Capability Surface Integrity.** A change in the `covered_regions`
  set MUST be recorded as a distinct `SurfaceChangeEvent`, separate from
  fingerprint drift within a region.

## Files

| File | Purpose |
|---|---|
| [`README.md`](./README.md) | This file |
| [`STATUS.md`](./STATUS.md) | Stage, URI, and scope |
| [`Yathartha.tla`](./Yathartha.tla) | TLA+ specification of the three invariants |
| [`Yathartha.cfg`](./Yathartha.cfg) | Small-model TLC configuration |

Python implementation lives under [`src/nerve/extensions/yathartha/`](../../src/nerve/extensions/yathartha/),
tests under [`tests/extensions/test_yathartha.py`](../../tests/extensions/test_yathartha.py).
This mirrors the ACAP extensions layout: spec documents at
`extensions/<name>/`, code under `src/<package>/extensions/<name>/`.

## Usage

From inside `pratyahara-nerve`:

```python
from nerve.extensions.yathartha import (
    CapabilityRegion,
    ProbeBatteryResult,
    CapabilitySurface,
    check_coverage_conditional_drift,
)

# Agent declares its regions
surface = CapabilitySurface(
    agent_id="service-router-v1",
    regions={
        "arithmetic": ProbeBatteryResult(...),
        "scheduling": ProbeBatteryResult(...),
    },
    uncovered_policy="defer",
    refresh_cadence_hours=24,
)

# Observer attempts to flag drift
ok, reason = check_coverage_conditional_drift(
    surface, task_region="letter-counting", now=...
)
# ok is False because letter-counting is not in covered_regions.
# The observer defers to uncovered_policy rather than raising a drift alert.
```

## Relationship to NERVE

Yathartha is additive. Agents that do not declare a `CapabilitySurface`
continue to operate under NERVE's existing single-fingerprint drift
model. Agents that do declare one get capability-conditional drift
detection without losing any existing NERVE guarantees.

## License

Apache 2.0. See [../../LICENSE](../../LICENSE).
