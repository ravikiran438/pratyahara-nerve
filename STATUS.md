# NERVE — repository status

Internal snapshot. The canonical references are this repo's README and the
published papers: NERVE (Zenodo DOI 10.5281/zenodo.19628588) and the Yathartha
capability-surface extension (Zenodo DOI 10.5281/zenodo.19659632).

## Last touched

May 1, 2026 — major TLA+ refactor (numeric → qualitative state), added the
canonical fingerprint algorithm + `NeuralPostureRef` + `NerveEnvelope` +
`ClearanceLevel`, wired 3 new MCP validators.

## What works (verified)

- 118 tests passing.
- TLA+ model `specification/Nerve.tla` checks clean under TLC after the
  qualitative-state refactor (~73K distinct states, depth 18, no invariant
  violations).
- TLA+ model `extensions/yathartha/Yathartha.tla` parses cleanly via SANY; a
  full TLC run is intractable for non-trivial models due to monotonic
  `surfaceEvents` set growth. The N-16 invariant is explicitly action-level,
  not a state invariant.
- MCP server at `nerve.mcp_server` exposes 13 validator tools including the 3
  new ones (`validate_neural_posture_ref`, `validate_nerve_envelope`,
  `validate_behavioral_fingerprint`).
- ExtensionManifest published at `v1/manifest.json`, auto-generated from
  `nerve.types.NeuralPostureRef`.
- Yathartha sub-extension has a URI constant + manifest at
  `extensions/yathartha/v1/manifest.json`.

## Verify

1. `python -m pytest -q` — expect 118/118.
2. Run NERVE TLC: `cd specification && java -Xmx4g -cp "$TLA2TOOLS" tlc2.TLC
   -workers auto -deadlock Nerve` — expect "no error" in <1s.
3. SANY-parse Yathartha: `cd extensions/yathartha && java -cp "$TLA2TOOLS"
   tla2sany.SANY Yathartha.tla` — expect no semantic errors.

## Files to look at first

- `src/nerve/types/neural_posture_ref.py` — AgentCard descriptor;
  `behavioral_fingerprint` is field-validated against
  `is_well_formed_fingerprint`.
- `src/nerve/types/fingerprint.py` — canonical algorithm
  (`FINGERPRINT_VERSION="v1"`): `compute_behavioral_fingerprint`,
  `verify_behavioral_fingerprint`, `is_well_formed_fingerprint`.
- `src/nerve/types/clearance.py` — `ClearanceLevel` enum (only the two
  paper-named values; vendor extensions allowed as plain strings).
- `specification/Nerve.tla` — qualitative trust/myelination model.
- `extensions/yathartha/Yathartha.tla` — N-16 is structural (action-level).
- `v1/manifest.json` and `extensions/yathartha/v1/manifest.json`.

## Known gaps / future work

- Yathartha TLA+ exhaustive verification is currently impractical due to
  `surfaceEvents` monotonic-set growth. A bounded model or a different
  abstraction would close this.
- The qualitative TLA+ refactor preserves N-3 (decay > reinforcement)
  structurally via the consensus precondition on `Reinforce`. To verify the
  asymmetry empirically rather than structurally, add a temporal property and
  re-run.
