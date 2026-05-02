# Pratyahara NERVE Framework — Wire Specification

> Generated from `v1/manifest.json`. Re-render after the manifest changes; do not hand-edit.

- **Extension URI:** `https://ravikiran438.github.io/pratyahara-nerve/v1`
- **Protocol version:** 1.0.0
- **Manifest envelope version:** 1.0.0
- **Publisher:** Ravi Kiran Kadaboina
- **Paper / human-readable spec:** https://doi.org/10.5281/zenodo.19628589

Neural-defense substrate: behavioral fingerprints, observer cohorts, trust posture.

## AgentCard payload

**Required fields:** `behavioral_fingerprint`, `neuron_type`, `observer_ids`, `trust_score`, `version`

| Field | Type | Required | Notes |
|---|---|---|---|
| `behavioral_fingerprint` | string | yes | Current ``sha256:<hex>`` fingerprint of this agent's output distribution embedding, computed per nerve.types.fingerprint. Validators check format only; semantic verification requires the embedding which lives with the observer. |
| `homeostasis_state` | string | no | The network homeostasis_state observed at last evaluation. One of STABLE | STRESSED | CRITICAL | RECOVERY (see HomeostasisState). |
| `last_evaluated_at` | any | no | ISO 8601 UTC of the most recent trust evaluation. |
| `myelination_levels` | dict<string, number> | no | Per-channel myelination map (channel_id -> level in [0, 1]). Empty when the agent has no established channels yet. |
| `neuron_type` | `$NeuronType` | yes | The role this agent plays in the network: SENSORY accepts external inputs; PROCESSING transforms; MOTOR drives external side-effects; INTERNEURON routes between others. |
| `observer_ids` | array<string> | yes | Identifiers of the MicroglialObservers monitoring this agent. Per N-1 each agent MUST be observed by at least 2 observers. |
| `trust_score` | number | yes | Last observer-consensus trust value in [0, 1]. |
| `version` | string | yes | NERVE protocol semver this agent implements. |

## Invariants

- N-1: every AgentNeuron is observed by at least 2 MicroglialObservers.
- N-7: behavioral_fingerprint contains no raw prompt or principal data.
- NTE-1: decay_rate MUST exceed reinforcement_rate.

---

_Drift between this `SPEC.md` and the protocol's pydantic models indicates the manifest needs regenerating. CI may compare a freshly-rendered version against the committed one._
