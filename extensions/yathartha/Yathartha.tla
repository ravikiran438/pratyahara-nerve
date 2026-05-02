---------------------------- MODULE Yathartha ------------------------------
\* Copyright 2026 Ravi Kiran Kadaboina. Licensed under the Apache License, 2.0.
\*
\* TLA+ specification of the Yathartha capability-surface extension to NERVE.
\* Paper: Yathartha: A Protocol-Layer Treatment of Jagged Intelligence in
\* Autonomous Agent Networks.
\*
\* This module extends Nerve.tla with three safety invariants that condition
\* behavioral drift detection on an observed capability surface:
\*
\*   N-16 Coverage-Conditional Drift  : drift flags only inside covered regions
\*   N-17 Probe Battery Maintenance  : battery changes require full re-baseline
\*   N-18 Capability Surface Integrity: surface transitions are their own signal

EXTENDS Naturals, Sequences, FiniteSets, TLC

CONSTANTS
    Agents,              \* Set of agent identifiers (shared with Nerve.tla)
    Regions,             \* Set of capability region identifiers
    BatteryVersions,     \* Ordered set of probe battery versions (Nat)
    RefreshCadence,      \* Max age (in abstract ticks) before surface is stale
    AcceptanceThreshold  \* Minimum probe score (0..100) for "covered" (default 85)

ASSUME AcceptanceThreshold \in 0..100
ASSUME RefreshCadence \in Nat

VARIABLES
    surface,         \* Function: (agent, region) -> probe score (0..100, scaled)
    covered,         \* Function: agent -> set of regions marked covered
    batteryVersion,  \* Function: agent -> current battery version (Nat)
    lastRefreshAt,   \* Function: (agent, region) -> abstract tick of last probe
    uncoveredPolicy, \* Function: agent -> {"observe", "defer", "reject"}
    clockTick,       \* Abstract monotonic tick used for staleness
    driftFlags,      \* Set of (agent, region, tick) drift events raised by observers
    surfaceEvents    \* Set of SurfaceChangeEvent records

yVars == <<surface, covered, batteryVersion, lastRefreshAt,
           uncoveredPolicy, clockTick, driftFlags, surfaceEvents>>

\* ─────────────────────────────────────────────────────────────────────
\* Type invariant
\* ─────────────────────────────────────────────────────────────────────

TypeOK ==
    /\ surface \in [Agents \X Regions -> 0..100]
    /\ covered \in [Agents -> SUBSET Regions]
    /\ batteryVersion \in [Agents -> BatteryVersions]
    /\ lastRefreshAt \in [Agents \X Regions -> Nat]
    /\ uncoveredPolicy \in [Agents -> {"observe", "defer", "reject"}]
    /\ clockTick \in Nat
    /\ driftFlags \subseteq (Agents \X Regions \X Nat)
    /\ surfaceEvents \subseteq [agent: Agents, region: Regions,
                                kind: {"entered", "left", "policy", "battery"},
                                at: Nat]

\* ─────────────────────────────────────────────────────────────────────
\* Initial state
\* ─────────────────────────────────────────────────────────────────────

Init ==
    /\ surface = [<<a, r>> \in Agents \X Regions |-> 0]
    /\ covered = [a \in Agents |-> {}]
    /\ batteryVersion = [a \in Agents |-> 1]
    /\ lastRefreshAt = [<<a, r>> \in Agents \X Regions |-> 0]
    /\ uncoveredPolicy = [a \in Agents |-> "defer"]
    /\ clockTick = 0
    /\ driftFlags = {}
    /\ surfaceEvents = {}

\* ─────────────────────────────────────────────────────────────────────
\* Actions
\* ─────────────────────────────────────────────────────────────────────

\* Baseline or refresh a single (agent, region) probe result.
Probe(a, r, score) ==
    /\ a \in Agents /\ r \in Regions /\ score \in 0..100
    /\ LET wasCovered == r \in covered[a]
           nowCovered == score >= AcceptanceThreshold
           newCovered == IF nowCovered
                         THEN covered[a] \cup {r}
                         ELSE covered[a] \ {r}
           kind == CASE wasCovered /\ ~nowCovered -> "left"
                     [] ~wasCovered /\ nowCovered -> "entered"
                     [] OTHER -> "stable"
           event == [agent |-> a, region |-> r, kind |-> kind, at |-> clockTick]
       IN /\ surface' = [surface EXCEPT ![<<a, r>>] = score]
          /\ covered' = [covered EXCEPT ![a] = newCovered]
          /\ lastRefreshAt' = [lastRefreshAt EXCEPT ![<<a, r>>] = clockTick]
          /\ surfaceEvents' = IF kind \in {"entered", "left"}
                              THEN surfaceEvents \cup {event}
                              ELSE surfaceEvents
    /\ UNCHANGED <<batteryVersion, uncoveredPolicy, clockTick, driftFlags>>

\* Tick the abstract clock (used for staleness checks).
\*
\* TLC bound: ``clockTick`` is bounded at 2 * RefreshCadence so the
\* state space stays finite. The invariants under test only depend on
\* whether the clock has crossed the staleness boundary, so this bound
\* is sufficient. Production deployments use unbounded Naturals.
Tick ==
    /\ clockTick < 2 * RefreshCadence
    /\ clockTick' = clockTick + 1
    /\ UNCHANGED <<surface, covered, batteryVersion, lastRefreshAt,
                   uncoveredPolicy, driftFlags, surfaceEvents>>

\* Change battery version; forces all regions to move out of coverage
\* until they are re-baselined.
ChangeBattery(a, v) ==
    /\ a \in Agents
    /\ v \in BatteryVersions
    /\ v > batteryVersion[a]
    /\ batteryVersion' = [batteryVersion EXCEPT ![a] = v]
    /\ covered' = [covered EXCEPT ![a] = {}]
    /\ surfaceEvents' = surfaceEvents \cup {[agent |-> a, region |-> r,
                                             kind |-> "battery", at |-> clockTick]
                                            : r \in covered[a]}
    /\ UNCHANGED <<surface, lastRefreshAt, uncoveredPolicy, clockTick, driftFlags>>

\* Change uncovered policy; recorded as a distinct event.
ChangePolicy(a, p) ==
    /\ a \in Agents
    /\ p \in {"observe", "defer", "reject"}
    /\ p # uncoveredPolicy[a]
    /\ uncoveredPolicy' = [uncoveredPolicy EXCEPT ![a] = p]
    /\ surfaceEvents' = surfaceEvents \cup {[agent |-> a, region |-> r,
                                             kind |-> "policy", at |-> clockTick]
                                            : r \in Regions}
    /\ UNCHANGED <<surface, covered, batteryVersion, lastRefreshAt,
                   clockTick, driftFlags>>

\* An observer attempts to raise a drift flag for (agent, region).
\* Under N-16 this is only allowed when the region is in coverage AND not stale.
RaiseDrift(a, r) ==
    /\ a \in Agents /\ r \in Regions
    /\ r \in covered[a]
    /\ (clockTick - lastRefreshAt[<<a, r>>]) <= RefreshCadence
    /\ driftFlags' = driftFlags \cup {<<a, r, clockTick>>}
    /\ UNCHANGED <<surface, covered, batteryVersion, lastRefreshAt,
                   uncoveredPolicy, clockTick, surfaceEvents>>

Next ==
    \/ \E a \in Agents, r \in Regions, score \in {0, 50, 100}: Probe(a, r, score)
    \/ \E a \in Agents, r \in Regions: RaiseDrift(a, r)
    \/ \E a \in Agents, v \in BatteryVersions: ChangeBattery(a, v)
    \/ \E a \in Agents, p \in {"observe", "defer", "reject"}: ChangePolicy(a, p)
    \/ Tick

Spec == Init /\ [][Next]_yVars

\* ─────────────────────────────────────────────────────────────────────
\* Safety properties (N-16, N-17, N-18)
\* ─────────────────────────────────────────────────────────────────────

\* N-16 Coverage-Conditional Drift is a STRUCTURAL property of the
\* RaiseDrift action's enabling guard:
\*
\*     RaiseDrift(a, r) ==
\*         /\ r \in covered[a]                                    (i)
\*         /\ (clockTick - lastRefreshAt[<<a, r>>]) <= RefreshCadence  (ii)
\*         /\ ...
\*
\* Earlier drafts expressed N-16 as a state invariant (∀f ∈ driftFlags:
\* f's region is currently covered AND fresh), but ``driftFlags`` is
\* append-only while ``covered`` and ``clockTick`` are mutable. After
\* a flag is legitimately raised, a subsequent Probe can shrink
\* coverage (or Tick can advance time past the freshness window) and
\* historically-correct flags falsify the state-only form.
\*
\* The action guard is the operative enforcement: a flag can only be
\* RAISED on a covered + fresh region; once raised it remains as a
\* historical record. We no longer assert N-16 at the state level.

\* N-17 Probe Battery Maintenance: after a battery version change, all
\* regions for that agent must be removed from coverage until re-probed.
ProbeBatteryMaintenance ==
    \A e \in surfaceEvents :
        (e.kind = "battery") =>
            (e.region \notin covered[e.agent]
             \/ lastRefreshAt[<<e.agent, e.region>>] >= e.at)

\* N-18 Capability Surface Integrity: every covered-set change produces a
\* SurfaceChangeEvent. Stated as: if a region is covered now but not at
\* tick 0, there exists an "entered" event for it; if it is uncovered now
\* but was initially never covered, no negative check is owed. Practically
\* checked on state transitions via the Probe action's event emission.
CapabilitySurfaceIntegrity ==
    \A a \in Agents :
        \A r \in covered[a] :
            \E e \in surfaceEvents :
                /\ e.agent = a
                /\ e.region = r
                /\ e.kind = "entered"
                /\ e.at <= lastRefreshAt[<<a, r>>]

=============================================================================
