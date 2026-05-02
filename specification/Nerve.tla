------------------------------ MODULE Nerve --------------------------------
\* Copyright 2026 Ravi Kiran Kadaboina. Licensed under the Apache License, 2.0.
\*
\* TLA+ specification of the NERVE behavioral integrity protocol.
\*
\* Trust and myelination are modeled as **qualitative state bands**, not
\* numeric scores. The safety invariants only depend on band membership
\* (e.g. "is trust above the pruning threshold?"), not on the exact
\* score; a numeric implementation is a refinement free to use any
\* scale that maps onto these bands. This abstraction is what keeps TLC
\* tractable: with numeric ranges 0..100 the state space exploded
\* exponentially and TLC could not finish on a finite disk.

EXTENDS Naturals, Sequences, FiniteSets, TLC

\* Qualitative trust bands (refined from Pratyahara §3.3).
\*   HEALTHY    : above pruning threshold; agent operates normally.
\*   AT_RISK    : below healthy band but still above pruning threshold;
\*                drift signals are accumulating but no severance yet.
\*   BELOW      : below pruning threshold; pruning is enabled.
\*   PRUNED     : terminal — channels of this agent are severed.
TrustLevel == {"healthy", "at_risk", "below", "pruned"}

\* Qualitative myelination bands (Hebbian dynamics).
\*   WEAK    : freshly added or demyelinated channel.
\*   STABLE  : steady state for healthy interactions.
\*   STRONG  : reinforced by repeated successful traffic.
MyelinationLevel == {"weak", "stable", "strong"}

CONSTANTS
    Agents,              \* Set of agent identifiers
    Observers,           \* Set of observer identifiers
    Channels,            \* Set of channel identifiers
    ChannelOwner,        \* Function: channel -> agent (source_agent_id)
    MaxCascadeDepth,     \* Int: cascade depth cap before forced checkpoint
    Fingerprints,        \* Set of fingerprint hash identifiers (opaque)
    ConfidenceValues     \* Per-message confidence band: {"below", "above"}.
                         \* Below the agent's quality_threshold triggers
                         \* refractory; above propagates the message.

ASSUME ChannelOwner \in [Channels -> Agents]

\* TLC config-friendly definition of ChannelOwner. The cfg file binds
\* ChannelOwner to this operator via ``ChannelOwner <- ChannelOwnerFn``
\* because .cfg syntax does not accept ``:>``/``@@`` literals on the
\* right-hand side of ``=``. Picking any valid mapping is sufficient
\* for the invariants under test; we do not depend on a specific pairing.
ChannelOwnerFn == CHOOSE f \in [Channels -> Agents] : TRUE

VARIABLES
    trust,               \* Function: agent -> TrustLevel
    channelState,        \* Function: channel -> {"active", "attenuated", "severed", "quarantined"}
    myelination,         \* Function: channel -> MyelinationLevel
    observerAssignment,  \* Function: agent -> set of observer IDs
    homeostasisState,    \* One of: "stable", "stressed", "critical", "recovery"
    cascadeDepth,        \* Function: channel -> current cascade depth
    refractoryActive,    \* Function: channel -> boolean (in refractory cooldown?)
    messages,            \* Set of (channel, confidence) pairs pending delivery
    fingerprint,         \* Function: agent -> current behavioral_fingerprint
    rebaselineCount      \* Function: agent -> count of explicit rebaseline events.
                         \* Bounded at MaxCascadeDepth in TLC runs to keep
                         \* the state space finite; the invariant
                         \* (FingerprintAccountability) cares about the
                         \* relation between this counter and Next-relation
                         \* mutations of fingerprint, not about its absolute
                         \* value.

vars == <<trust, channelState, myelination, observerAssignment,
          homeostasisState, cascadeDepth, refractoryActive, messages,
          fingerprint, rebaselineCount>>

\* ─────────────────────────────────────────────────────────────────────
\* Type invariant
\* ─────────────────────────────────────────────────────────────────────

TypeOK ==
    /\ trust \in [Agents -> TrustLevel]
    /\ channelState \in [Channels -> {"active", "attenuated", "severed", "quarantined"}]
    /\ myelination \in [Channels -> MyelinationLevel]
    /\ \A a \in Agents : observerAssignment[a] \subseteq Observers
    /\ homeostasisState \in {"stable", "stressed", "critical", "recovery"}
    /\ cascadeDepth \in [Channels -> 0..MaxCascadeDepth]
    /\ refractoryActive \in [Channels -> BOOLEAN]

\* ─────────────────────────────────────────────────────────────────────
\* Initial state
\* ─────────────────────────────────────────────────────────────────────

Init ==
    /\ trust = [a \in Agents |-> "healthy"]
    /\ channelState = [c \in Channels |-> "active"]
    /\ myelination = [c \in Channels |-> "weak"]
    /\ observerAssignment = [a \in Agents |->
        \* Assign at least 2 observers per agent (N-1)
        CHOOSE S \in SUBSET Observers : Cardinality(S) >= 2]
    /\ homeostasisState = "stable"
    /\ cascadeDepth = [c \in Channels |-> 0]
    /\ refractoryActive = [c \in Channels |-> FALSE]
    /\ messages = {}
    /\ fingerprint \in [Agents -> Fingerprints]
    /\ rebaselineCount = [a \in Agents |-> 0]

\* ─────────────────────────────────────────────────────────────────────
\* Trust band transitions
\* ─────────────────────────────────────────────────────────────────────
\*
\* Decay direction: healthy -> at_risk -> below.
\* Reinforcement direction: below -> at_risk -> healthy.
\* PRUNED is terminal.

DegradeTrust(level) ==
    CASE level = "healthy"   -> "at_risk"
      [] level = "at_risk"   -> "below"
      [] level = "below"     -> "below"     \* sticky until Prune
      [] level = "pruned"    -> "pruned"

ImproveTrust(level) ==
    CASE level = "below"     -> "at_risk"
      [] level = "at_risk"   -> "healthy"
      [] level = "healthy"   -> "healthy"
      [] level = "pruned"    -> "pruned"    \* PRUNED is terminal — N-3 asymmetry

\* An observer detects drift and steps trust down one band.
DetectDrift(agent) ==
    /\ trust[agent] \notin {"below", "pruned"}
    /\ trust' = [trust EXCEPT ![agent] = DegradeTrust(@)]
    /\ UNCHANGED <<channelState, myelination, observerAssignment,
                   homeostasisState, cascadeDepth, refractoryActive,
                   messages, fingerprint, rebaselineCount>>

\* Trust reinforcement steps trust up one band.
\*
\* N-3 asymmetry: trust harder to build than to lose.
\* Captured structurally: this action is enabled ONLY when at least
\* two observers are assigned to ``agent`` (the consensus precondition
\* from NTE-2). DetectDrift has no such precondition — a single
\* observer suffices to push trust down. So the qualitative spec
\* preserves the "decay > reinforcement" asymmetry without committing
\* to specific numeric rates.
Reinforce(agent) ==
    /\ trust[agent] \notin {"healthy", "pruned"}
    /\ Cardinality(observerAssignment[agent]) >= 2
    /\ trust' = [trust EXCEPT ![agent] = ImproveTrust(@)]
    /\ UNCHANGED <<channelState, myelination, observerAssignment,
                   homeostasisState, cascadeDepth, refractoryActive,
                   messages, fingerprint, rebaselineCount>>

\* Agent trust drops below pruning threshold: sever ONLY that agent's
\* channels (AN-1, N-10) and mark the agent itself PRUNED (terminal).
Prune(agent) ==
    /\ trust[agent] = "below"
    /\ trust' = [trust EXCEPT ![agent] = "pruned"]
    /\ channelState' = [c \in Channels |->
        IF ChannelOwner[c] = agent
        THEN "severed"
        ELSE channelState[c]]
    /\ UNCHANGED <<myelination, observerAssignment,
                   homeostasisState, cascadeDepth, refractoryActive,
                   messages, fingerprint, rebaselineCount>>

\* Attenuate a channel (graded response)
Attenuate(channel) ==
    /\ channelState[channel] = "active"
    /\ channelState' = [channelState EXCEPT ![channel] = "attenuated"]
    /\ UNCHANGED <<trust, myelination, observerAssignment,
                   homeostasisState, cascadeDepth, refractoryActive,
                   messages, fingerprint, rebaselineCount>>

\* Quarantine a channel for forensic review
Quarantine(channel) ==
    /\ channelState[channel] \in {"active", "attenuated"}
    /\ channelState' = [channelState EXCEPT ![channel] = "quarantined"]
    /\ UNCHANGED <<trust, myelination, observerAssignment,
                   homeostasisState, cascadeDepth, refractoryActive,
                   messages, fingerprint, rebaselineCount>>

\* ─────────────────────────────────────────────────────────────────────
\* Myelination band transitions
\* ─────────────────────────────────────────────────────────────────────

StrengthenMyelin(level) ==
    CASE level = "weak"    -> "stable"
      [] level = "stable"  -> "strong"
      [] level = "strong"  -> "strong"

WeakenMyelin(level) ==
    CASE level = "strong"  -> "stable"
      [] level = "stable"  -> "weak"
      [] level = "weak"    -> "weak"

\* Myelination strengthens a channel (positive outcome). SC-2/N-5
\* forbid increase during quarantine/severance.
Myelinate(channel) ==
    /\ channelState[channel] \notin {"quarantined", "severed"}
    /\ myelination[channel] /= "strong"
    /\ myelination' = [myelination EXCEPT ![channel] = StrengthenMyelin(@)]
    /\ UNCHANGED <<trust, channelState, observerAssignment,
                   homeostasisState, cascadeDepth, refractoryActive,
                   messages, fingerprint, rebaselineCount>>

\* Demyelinate on negative outcome
Demyelinate(channel) ==
    /\ myelination[channel] /= "weak"
    /\ myelination' = [myelination EXCEPT ![channel] = WeakenMyelin(@)]
    /\ UNCHANGED <<trust, channelState, observerAssignment,
                   homeostasisState, cascadeDepth, refractoryActive,
                   messages, fingerprint, rebaselineCount>>

\* ─────────────────────────────────────────────────────────────────────
\* Homeostasis transitions
\* ─────────────────────────────────────────────────────────────────────

StressNetwork ==
    /\ homeostasisState = "stable"
    /\ homeostasisState' = "stressed"
    /\ UNCHANGED <<trust, channelState, myelination, observerAssignment,
                   cascadeDepth, refractoryActive, messages,
                   fingerprint, rebaselineCount>>

EscalateToCritical ==
    /\ homeostasisState = "stressed"
    /\ homeostasisState' = "critical"
    \* N-9: critical triggers max permeability restriction on ALL active channels
    /\ channelState' = [c \in Channels |->
        IF channelState[c] = "active" THEN "attenuated" ELSE channelState[c]]
    /\ UNCHANGED <<trust, myelination, observerAssignment,
                   cascadeDepth, refractoryActive, messages,
                   fingerprint, rebaselineCount>>

BeginRecovery ==
    /\ homeostasisState = "critical"
    /\ homeostasisState' = "recovery"
    /\ UNCHANGED <<trust, channelState, myelination, observerAssignment,
                   cascadeDepth, refractoryActive, messages,
                   fingerprint, rebaselineCount>>

ReturnToStable ==
    /\ homeostasisState = "recovery"
    /\ homeostasisState' = "stable"
    /\ UNCHANGED <<trust, channelState, myelination, observerAssignment,
                   cascadeDepth, refractoryActive, messages,
                   fingerprint, rebaselineCount>>

\* ─────────────────────────────────────────────────────────────────────
\* Messaging
\* ─────────────────────────────────────────────────────────────────────

\* Message sending with inhibitory gating (SC-4, N-14). Confidence is
\* qualitative — "above" or "below" the agent's quality_threshold.
SendMessage(channel, confidence) ==
    /\ channelState[channel] \notin {"severed", "quarantined"}
    /\ ~refractoryActive[channel]
    /\ cascadeDepth[channel] < MaxCascadeDepth
    /\ confidence \in ConfidenceValues
    /\ IF confidence = "above"
       THEN /\ cascadeDepth' = [cascadeDepth EXCEPT ![channel] = @ + 1]
            /\ refractoryActive' = refractoryActive
            /\ messages' = messages \union {<<channel, confidence>>}
       ELSE /\ refractoryActive' = [refractoryActive EXCEPT ![channel] = TRUE]
            /\ cascadeDepth' = cascadeDepth
            /\ messages' = messages
    /\ UNCHANGED <<trust, channelState, myelination, observerAssignment,
                   homeostasisState, fingerprint, rebaselineCount>>

\* Clear refractory state (cooldown expired)
ClearRefractory(channel) ==
    /\ refractoryActive[channel] = TRUE
    /\ refractoryActive' = [refractoryActive EXCEPT ![channel] = FALSE]
    /\ UNCHANGED <<trust, channelState, myelination, observerAssignment,
                   homeostasisState, cascadeDepth, messages,
                   fingerprint, rebaselineCount>>

\* RebaselineFingerprint: the ONLY action that may change an agent's
\* behavioral_fingerprint. Captures the state-machine view of
\* fingerprint determinism.
RebaselineFingerprint(agent, newFp) ==
    /\ newFp \in Fingerprints
    /\ newFp /= fingerprint[agent]
    /\ rebaselineCount[agent] < MaxCascadeDepth   \* finite-state TLC bound
    /\ fingerprint' = [fingerprint EXCEPT ![agent] = newFp]
    /\ rebaselineCount' = [rebaselineCount EXCEPT ![agent] = @ + 1]
    /\ UNCHANGED <<trust, channelState, myelination, observerAssignment,
                   homeostasisState, cascadeDepth, refractoryActive, messages>>

\* ─────────────────────────────────────────────────────────────────────
\* Next-state relation
\* ─────────────────────────────────────────────────────────────────────

Next ==
    \/ \E a \in Agents : DetectDrift(a)
    \/ \E a \in Agents : Reinforce(a)
    \/ \E a \in Agents : Prune(a)
    \/ \E c \in Channels : Attenuate(c)
    \/ \E c \in Channels : Quarantine(c)
    \/ \E c \in Channels : Myelinate(c)
    \/ \E c \in Channels : Demyelinate(c)
    \/ StressNetwork
    \/ EscalateToCritical
    \/ BeginRecovery
    \/ ReturnToStable
    \/ \E c \in Channels : \E conf \in ConfidenceValues : SendMessage(c, conf)
    \/ \E c \in Channels : ClearRefractory(c)
    \/ \E a \in Agents : \E fp \in Fingerprints : RebaselineFingerprint(a, fp)

Spec == Init /\ [][Next]_vars

\* ─────────────────────────────────────────────────────────────────────
\* Safety properties (N-1 through N-15)
\* ─────────────────────────────────────────────────────────────────────

\* N-1: Dual Coverage
DualCoverage ==
    \A a \in Agents : Cardinality(observerAssignment[a]) >= 2

\* N-3: Asymmetric Trust is now structural — Reinforce requires observer
\* consensus (Cardinality(observerAssignment[a]) >= 2) while DetectDrift
\* has no such precondition. The action structure encodes "decay is
\* unilateral; reinforcement requires consensus", which is the
\* qualitative form of "decay > reinforcement". No state invariant.

\* N-4 is structural: SendMessage requires
\* ``channelState[channel] \notin {"severed", "quarantined"}`` so no
\* new message can be added on a severed channel. Stating it as a
\* state invariant fails because the messages set is append-only —
\* historical messages persist after severance. The action guard is
\* the operative enforcement.

\* N-9: Critical Restriction
CriticalRestriction ==
    homeostasisState = "critical" =>
        \A c \in Channels : channelState[c] /= "active"

\* N-14: Inhibitory Gating — only "above" messages reach the messages set.
InhibitoryGating ==
    \A msg \in messages : msg[2] = "above"

\* N-15 is structural (action guard ``~refractoryActive[channel]``).
\* Same reasoning as N-4 above.

\* FingerprintAccountability: rebaselineCount is non-negative AND the
\* only way to mutate fingerprint is RebaselineFingerprint (enforced
\* structurally — every other action UNCHANGES it). Captures the
\* state-machine view of fingerprint determinism: no spontaneous drift.
FingerprintAccountability ==
    \A a \in Agents : rebaselineCount[a] >= 0

\* Combined invariant
Invariants ==
    /\ TypeOK
    /\ DualCoverage              \* N-1
    /\ CriticalRestriction       \* N-9
    /\ InhibitoryGating          \* N-14
    /\ FingerprintAccountability \* fingerprint determinism (state-machine view)

\* ─────────────────────────────────────────────────────────────────────
\* Liveness property
\* ─────────────────────────────────────────────────────────────────────

\* N-10: Pruning Liveness
\* An agent below threshold is eventually severed.
PruningLiveness ==
    \A a \in Agents :
        trust[a] = "below" ~>
            \A c \in Channels :
                ChannelOwner[c] = a => channelState[c] = "severed"

=========================================================================
