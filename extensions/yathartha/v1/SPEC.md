# Yathartha Capability-Surface Extension — Wire Specification

> Generated from `v1/manifest.json`. Re-render after the manifest changes; do not hand-edit.

- **Extension URI:** `https://ravikiran438.github.io/pratyahara-nerve/extensions/yathartha/v1`
- **Protocol version:** 1.0.0
- **Manifest envelope version:** 1.0.0
- **Publisher:** Ravi Kiran Kadaboina
- **Paper / human-readable spec:** https://doi.org/10.5281/zenodo.19659633

Distinguishes drift from jaggedness by requiring an observed capability baseline before flagging behavioral anomalies.

## AgentCard payload

This extension declares itself by URI presence and does not constrain the AgentCard payload. Validators accept any object in the entry's `params`.

## Invariants

- N-16: drift is flagged only for tasks in covered, non-stale CapabilityRegions.
- N-17: a battery_version change requires a full re-baseline; cross-version comparisons are forbidden.
- N-18: every covered_regions transition is accompanied by a SurfaceChangeEvent.

---

_Drift between this `SPEC.md` and the protocol's pydantic models indicates the manifest needs regenerating. CI may compare a freshly-rendered version against the committed one._
