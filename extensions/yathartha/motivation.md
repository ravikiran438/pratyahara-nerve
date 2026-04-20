# Yathartha: Why This Extension Exists

This document explains the motivation for the Yathartha capability-surface
extension to the Pratyahara NERVE specification. Section 1 describes the
false-positive problem that appears the moment NERVE drift detection is
deployed against a realistic generative agent. Section 2 describes why
NERVE Core alone cannot resolve the problem without weakening the
integrity guarantee that makes Pratyahara useful in the first place.
Section 3 describes our approach: a published, refresh-cadenced capability
surface and three derived invariants. Section 4 compares the approach
against alternatives we considered. Section 5 fences off what this
extension does not attempt.

## 1. The problem

NERVE's `MicroglialObserver` maintains a single `behavioral_fingerprint`
per `AgentNeuron` and flags drift when current behavior deviates from that
fingerprint by more than a declared threshold. This is what gives
Pratyahara its integrity guarantee: behavior that moves away from
baseline is caught, and caught quickly, without the observer needing to
know anything about the semantic content of the agent's work.

So the invariant is load-bearing for integrity. It is also load-bearing
for false-positive volume once the agent under observation is a
generative language model.

Dell'Acqua et al.'s 2023 field experiment with BCG consultants recorded
two numbers that matter for this extension. On tasks inside an AI's
capability frontier, knowledge workers gained 40 percent higher output
quality. On tasks outside the frontier, they produced output 19
percentage points less likely to be correct than workers who did not use
AI at all. The authors named the uneven capability profile the *jagged
frontier* and described it as a structural property of current
generative models: pattern density in training data does not match human
task difficulty, such that an LLM that can solve differential medical
diagnosis can also fail to count letters in a word.

A single fingerprint cannot record the shape of this unevenness. It
records the mean. A `MicroglialObserver` watching an agent whose
capability is 95 percent on code review and 35 percent on date arithmetic
sees an average fingerprint somewhere in the middle. When the agent
handles an incoming date-arithmetic task and predictably fails, the
observed behavior falls below the single aggregate fingerprint by a wide
margin. The observer flags drift. Nothing has drifted. The agent was
always that way in that region. The signal is a false positive, and it
is a false positive the operator will see many times per day per agent.

We have seen the pattern of this failure in other monitoring systems.
When a monitor fires often and is wrong often, operators learn to widen
the threshold or to ignore the alerts. Either response defeats the
monitor. That is the outcome NERVE Core was designed to prevent, and it
is the outcome an honest implementation of Core will produce in the
absence of capability-surface conditioning.

## 2. Why core alone is insufficient

One response to the false-positive problem is to relax the drift
threshold, allowing a wider band of per-action variation before the
observer fires. We considered this and rejected it. The threshold is
the entire integrity guarantee, such that widening it to accommodate
the jagged profile also accommodates real drift in a range that matters
for security. The two signals we want to separate are precisely the two
signals the relaxed threshold conflates.

A second response is to let the observer train a smarter classifier
that learns, over time, which regions of the agent's behavior are
normally low and which are normally high. This is operationally
plausible but produces two problems. The first is that the classifier
itself has a capability surface, which is jagged, which means drift
detection now depends on the classifier's own jagged valleys matching
the agent's jagged valleys, which is recursive and unauditable. The
second is that the classifier is learning silently from the agent's
observed behavior, such that an adversary who can shape the observed
behavior can shape what the classifier treats as normal.

A third response is to rely on the operator to mark individual tasks
as "known weak" and suppress observer alerts on those tasks. This puts
the burden on the operator to enumerate jagged valleys by hand, which
is precisely the cognitive work the protocol should do. It also rebuilds
the click-through model every alerting system already has: after the
first dozen manual suppressions, the operator clicks through the rest.

What NERVE Core cannot do alone is produce an auditable record of what
the agent is *actually competent at*, independent of what the agent is
currently doing, such that the observer has a principled way to
distinguish a weak region from a drifting region. That is the gap this
extension fills.

## 3. Our approach

We propose a primitive, the `CapabilitySurface`, that records the
agent's observed competence across declared capability regions. Each
region carries a content-addressed probe battery, a set of standardized
tasks that sample the region. The battery is run once at intake to
establish baseline and re-run on a declared cadence to maintain
freshness. The result of each run is an immutable `ProbeBatteryResult`
that carries the per-task outcomes and a derived `covered` flag against
a declared acceptance threshold.

The `MicroglialObserver` consults the surface on every action. If the
incoming task classifies into a region that is covered and fresh,
drift detection runs against that region's fingerprint. If the
classified region is uncovered or stale, the observer does not flag
drift; it routes the decision through the agent's declared
`uncovered_policy`, which is one of `observe`, `defer`, or `reject`.
The distinction between "drift against a baseline that exists" and
"behavior in a region the baseline does not cover" becomes mechanical
instead of heuristic.

Three invariants formalize the behavior and extend the NERVE
specification.

- **N-16 Coverage-Conditional Drift** requires that drift flags
  reference only regions that are in `covered_regions` and have been
  refreshed within the declared cadence. Behavior in uncovered or
  stale regions is not drift; it is unknown.
- **N-17 Probe Battery Maintenance** requires the probe battery to be
  content-addressed (SHA-256 over a JSON canonicalization per RFC 8785)
  and versioned. A battery version change triggers a full baseline
  re-run, because results across battery versions measure different
  things.
- **N-18 Capability Surface Integrity** requires coverage transitions
  (regions entering or leaving `covered_regions`) to be recorded as
  a distinct `SurfaceChangeEvent` class, separate from fingerprint
  drift within a region, so that an auditor can distinguish "the
  agent's capable regions shifted" from "the agent's behavior in a
  capable region shifted."

Our approach has four properties that matter for deployment.

First, the surface is agent-published and queryable. A peer agent or a
principal asking whether the target agent is reliable for a particular
task class receives a per-region answer, not an aggregate score. This
is the protocol-level answer to Gans's information-economics argument
that rational trust depends on local reliability signals rather than
aggregate benchmarks.

Second, the surface is opt-in. Agents that do not declare a
`CapabilitySurface` continue to operate under the single-fingerprint
NERVE Core model, with the false-positive risk this extension documents
as the known trade-off. Yathartha refines, it does not replace.

Third, the probe-battery loop and the observer loop run on different
timescales by design. The battery is scheduled, cadenced, and expensive;
the observer is continuous, per-action, and cheap. The observer does
not execute probes; it consults the fingerprint the most recent probe
run left behind. This decoupling is what makes the combined system
practical at production request volumes.

Fourth, the three invariants are formally modeled. The
`Yathartha.tla` specification encodes the state machine together with
N-16, N-17, and N-18 as TLA+ safety properties. TLC verifies them
under a small bounded model (2 agents × 3 regions × 3 battery versions
× 3-tick refresh cadence). The Pydantic reference implementation
enforces the same invariants at runtime, with twenty-one pytest
scenarios covering the drift-vs-uncovered routing, battery-version
monotonicity, and surface-change recording requirements.

## 4. Alternatives considered

We considered four alternatives to the published-surface model before
settling on it.

**Per-task trust weighting.** The observer maintains a per-task-type
confidence score that decays slowly, and drift flags fire only when
behavior deviates from the task-weighted expectation. This moves the
surface into the observer as a private, learned representation. We
rejected it because the representation is not auditable from outside
and because an adversary who shapes the agent's training data can also
shape the observer's learned weights.

**Ensemble-of-observers agreement.** Several observers run in parallel
with independent fingerprints and flag drift only on majority agreement.
This reduces false positives from noise but does not separate jaggedness
from drift; if all observers share the same aggregate fingerprint they
share the same false-positive structure on jagged valleys. We kept the
ensemble option available as a future refinement on top of Yathartha,
but it is not a substitute for per-region baselines.

**LLM-as-judge review of observer alerts.** A second model reads the
alert and decides whether the flagged behavior is real drift or a
known weakness. This inherits the second model's own jagged surface in
exactly the regions the first model is weak on, which is the recursion
problem of Section 2. We kept it out of the core design.

**Operator-declared capability tiers.** Operators manually mark each
agent's capability regions at deployment, and the observer suppresses
alerts in regions the operator has marked as weak. This is the current
state of practice. It places the cost of enumeration on the operator,
does not refresh as capability shifts, and produces unauditable tiers
because the operator's incentives are not aligned with the
principal's. Out.

## 5. Out of scope

This extension proposes a minimal base. It does not standardize how
probe batteries are designed for specific domains, how a region
classifier assigns an incoming task to a region at query time, how
capability regions are discovered or versioned across an agent network,
how probe runs are scheduled at network scale, or how the probe battery
itself is attested by an independent third party. Each of these is a
real problem and each deserves its own specification.

The third-party attestation problem is the most urgent of the five. A
`ProbeBatteryResult` published by the agent itself is a contract between
honest parties; in an open multi-organization network the result needs
an independent signature. Four open-source evaluation frameworks
(Inspect, LM Evaluation Harness, Promptfoo, HELM) can serve as the
execution runtime, but the prober service architecture, attestation
format, and trust anchor that sit above the runtime are beyond the
scope of Yathartha. Commercial implementations that want to run
trusted prober services, or regulatory bodies such as AI Safety
Institutes that want to anchor attestation trust, have a clean seam
to build on without renegotiating the surface primitive or the three
invariants.

## References

The jagged-frontier empirical evidence is Dell'Acqua et al.,
[Navigating the Jagged Technological Frontier](https://www.hbs.edu/faculty/Pages/item.aspx?num=64700)
(HBS Working Paper 24-013, September 2023). The framing was popularized
in Mollick and Euchner, *The Jagged Frontier* (Research-Technology
Management, 2024). The information-economics treatment is Gans,
[*A Model of Artificial Jagged Intelligence*](https://arxiv.org/abs/2601.07573)
(arXiv:2601.07573, 2026). For the Pratyahara NERVE specification this
extension refines, see the paper at
[Zenodo DOI 10.5281/zenodo.19628589](https://doi.org/10.5281/zenodo.19628589).
The Yathartha paper itself ([Zenodo DOI 10.5281/zenodo.19659633](https://doi.org/10.5281/zenodo.19659633)) carries the full
specification, the TLA+ model, and the reference-implementation
pointer.
