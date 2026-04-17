# ADR 001: Neural Tissue Defense Over Immune System Defense

**Status:** Accepted
**Date:** 2026-04-17
**Authors:** Ravi Kiran Kadaboina

---

## Context

Multi-agent networks need internal integrity monitoring. The most
natural biological analogy is the immune system, which is well
established in the artificial-immune-systems (AIS) literature for
network intrusion detection (Forrest et al. 1996, Dasgupta 1999,
Greensmith et al. 2008). BioDefense (Schauer 2026) applies immune
concepts to LLM agent prompt injection defense.

We considered two biological defense models:

1. **Immune system model.** Binary self/non-self discrimination,
   reactive detection after infection, kill-or-tolerate decisions,
   no mechanism for trust reinforcement.
2. **Neural tissue defense model.** Graded response (attenuate before
   severing), continuous baseline comparison (cumulative drift), active
   trust reinforcement (myelination), network-level health monitoring
   (astrocyte homeostasis), and intent-agnostic detection.

## Decision

NERVE uses the neural tissue defense model, not the immune system
model.

## Rationale

**Against the immune model:**

- Binary decisions (kill/tolerate) do not fit the multi-agent case.
  An agent that has drifted due to RL misalignment should be
  attenuated and re-evaluated, not destroyed.
- Reactive detection fires after the damage has occurred. Drift
  detection via cumulative baseline comparison fires before the
  downstream principal is harmed.
- No immune mechanism actively strengthens healthy agents. The immune
  system is purely defensive. Multi-agent networks benefit from
  positive reinforcement of working pathways.
- Immune models do not address correlated drift (supply chain
  compromise). The immune system monitors individual cells, not
  tissue-wide activation distributions.

**For the neural model:**

- Graded response (active, attenuated, severed, quarantined) matches
  the operational needs of production multi-agent systems.
- Myelination is the only biological defense mechanism that actively
  reinforces healthy function. Priority routing for high-myelination
  channels makes the network faster on its healthy paths.
- Astrocyte homeostasis provides network-level awareness that per-agent
  monitoring cannot. Supply chain compromise is invisible to
  individual observers but visible in the activation distribution.
- Intent-agnostic detection means the same mechanism catches malicious
  compromise, RL misalignment, self-healing side effects, and model
  update artifacts. The defense does not need to diagnose cause.

## Consequences

- The biological vocabulary is unfamiliar to most security engineers.
  The paper includes a mapping table (Section 2) and a reading guide
  to mitigate this.
- The neural model is more complex than the immune model (five
  primitives plus two extensions vs. three AIS primitives). This is a
  deliberate trade for the richer response vocabulary.
- We position BioDefense as complementary: immune defense at the
  perimeter, neural defense inside the network.
