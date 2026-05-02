# Yathartha: Status

**Stage:** Reference implementation
**Extension URI:** https://ravikiran438.github.io/pratyahara-nerve/extensions/yathartha/v1
**First published:** 2026-04-19
**Depends on:** NERVE Core v0.1+
**Maintainer:** Ravi Kiran Kadaboina (@ravikiran438)
**License:** Apache 2.0

## Scope

This extension adds a capability-surface primitive and three safety
invariants (N-16, N-17, N-18) to NERVE, conditioning behavioral drift
detection on a recorded baseline surface rather than a single aggregate
fingerprint. The motivation is the *jagged frontier* phenomenon
described by Mollick, Kellogg, and Gans: generative AI capability is
structurally uneven across tasks, and aggregate drift detection without
surface conditioning produces false positives on tasks the agent was
never competent at.

## Primitives this extension adds

- `CapabilityRegion`: a declared region of the task space with a probe
  battery and acceptance criteria.
- `ProbeBatteryResult`: the outcome of running a region's probe battery
  at a specific time (append-only, SHA-256-addressed).
- `CapabilitySurface`: the agent's published map of covered regions plus
  refresh cadence and `uncovered_policy`.
- `SurfaceChangeEvent`: a distinct event type recording region coverage
  transitions.

## Invariants this extension adds

- **N-16 Coverage-Conditional Drift**: drift flags only within
  `covered_regions`.
- **N-17 Probe Battery Maintenance**: battery version changes trigger a
  full baseline re-run.
- **N-18 Capability Surface Integrity**: coverage transitions are their
  own event type.

## Interop points with NERVE Core

- `AgentNeuron.behavioral_fingerprint` remains; Yathartha complements
  rather than replaces it.
- `MicroglialObserver` gains a capability-region classifier and consults
  the `CapabilitySurface` before raising drift flags.
- A `SurfaceChangeEvent` is routed to the same observer pool as
  behavioral drift but is processed as a distinct signal class.

## What exists today

- Full TLA+ specification of N-16/N-17/N-18 invariants under `Yathartha.tla`
- TLC configuration for a small model (2 agents, 3 regions)
- Pydantic types for `CapabilityRegion`, `ProbeBatteryResult`,
  `CapabilitySurface`
- Runtime validators for the three invariants
- Test suite covering the invariants

## What is open

- Probe-battery design templates for specific domains (coding,
  summarization, arithmetic, scheduling)
- Registry proposal for trusted third-party probe batteries
- Empirical study comparing surface-conditioned drift detection against
  aggregate drift detection (false positive rate under injected drift)

## Not in scope

- Training-time techniques for reducing jaggedness
- Capability evaluation benchmark design (MMLU, BIG-Bench, etc., are
  orthogonal)
- Probe-task classification from raw task inputs (remains agent-local)

## Feedback

Open an issue or a PR on the parent repository. Reference this extension
in the title: `[yathartha] <your topic>`.
