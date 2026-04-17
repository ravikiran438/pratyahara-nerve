# Pratyahara NERVE

**Status:** Draft v0.1.0
**Paper:** [Pratyahara: A Neural Tissue Defense Model for Detecting Compromised Agents in Multi-Agent Networks](https://doi.org/10.5281/zenodo.PENDING)
**Extension URI:** `https://github.com/ravikiran438/pratyahara-nerve/v1`
**License:** Apache 2.0

Pratyahara (Sanskrit for *withdrawal of the senses; turning awareness
inward*) defines the **NERVE** specification: **N**eural **E**valuation
for **R**ogue Agent **V**erification in **E**cosystems.

NERVE detects and responds to behavioral drift in multi-agent networks,
whether the drift is caused by adversarial compromise, reinforcement
learning misalignment, self-healing side effects, or model update
artifacts. The design draws on neural tissue defense mechanisms, which
are intent-agnostic: they detect deviation from baseline regardless of
cause.

## The Five Primitives

| Primitive | What it does |
|---|---|
| `AgentNeuron` | Behavioral baseline and trust state per agent |
| `SynapticChannel` | Communication link with selective permeability, myelination, and inhibitory gating |
| `MicroglialObserver` | Lightweight surveillance agent detecting behavioral drift and collusion |
| `NeuralTrustEnvelope` | Asymmetric trust dynamics (trust harder to earn than to lose) |
| `HomeostasisTrace` | Network-level health monitoring detecting systemic attacks |

Plus two extended mechanisms on `SynapticChannel`:
- **GlymphaticPolicy** for context hygiene (stale context clearance)
- **Inhibitory Gating** for error cascade prevention

## Relationship to Other Protocols

NERVE is an extension to A2A and MCP. It uses the standard
`capabilities.extensions` mechanism so that no core spec change is
required.

## Repository Layout

```
pratyahara-nerve/
├── specification/
│   ├── Nerve.tla            # TLA+ model (15 safety properties, full state machine)
│   └── Nerve.cfg            # TLC configuration
├── src/nerve/
│   ├── types/               # Pydantic type library (all 5 primitives + extensions)
│   └── validators/          # Runtime invariant validators (N-1 through N-15)
├── tests/                   # pytest suite
├── figures/                 # Mermaid diagram sources
└── adrs/                    # Architecture Decision Records
```

## Formal Safety Properties

| ID | Property | Kind |
|---|---|---|
| N-1 | Dual Coverage: every agent assigned to >= 2 observers | Safety |
| N-2 | Observer Independence: no observer shares infra with monitored agents | Safety |
| N-3 | Asymmetric Trust: decay_rate > reinforcement_rate | Safety |
| N-4 | Severance Finality: severed channel transmits zero messages | Safety |
| N-5 | Quarantine Freeze: myelination cannot increase during quarantine | Safety |
| N-6 | Consensus Evaluation: trust updates require all assigned observers | Safety |
| N-7 | Fingerprint Privacy: no raw prompt/principal data in fingerprint | Safety |
| N-8 | Homeostasis Isolation: HomeostasisTrace computed by non-participating agent | Safety |
| N-9 | Critical Restriction: critical state triggers max permeability restriction | Safety |
| N-10 | Pruning Liveness: agent below threshold severed within one cycle | Liveness |
| N-11 | Context Expiry: stale context purged before next message | Safety |
| N-12 | Provenance Compression: deep provenance chains summarized | Safety |
| N-13 | Excitotoxicity Bound: context/payload ratio triggers alert | Safety |
| N-14 | Inhibitory Gating: low-confidence output not propagated | Safety |
| N-15 | Refractory Enforcement: rejected sender enters cooldown | Safety |

The TLA+ specification in [specification/Nerve.tla](./specification/Nerve.tla)
models a subset of these properties (N-1, N-3, N-4, N-9, N-10, N-14, N-15)
with a full `Init`/`Next`/`Spec` state machine suitable for TLC model
checking. N-5 (Quarantine Freeze) requires pre/post comparison that the
current TLA+ encoding does not capture; it is enforced by the Pydantic
validator and test suite instead.

## Running Tests

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[test]"
pytest -v
```

39 tests covering type construction, bounds, invariant violations, and
validator behavior.

## Citation

```bibtex
@misc{kadaboina2026pratyahara,
  author       = {Kadaboina, Ravi Kiran},
  title        = {Pratyahara: A Neural Tissue Defense Model for Detecting
                  Compromised Agents in Multi-Agent Networks},
  year         = {2026},
  publisher    = {Zenodo},
  doi          = {},
  url          = {}
}
```

DOI will be added once the paper is published on Zenodo.

## Contributing

Contributions welcome. Please use GitHub Issues for proposals and bug
reports.

## License

Apache 2.0. See [LICENSE](./LICENSE).
