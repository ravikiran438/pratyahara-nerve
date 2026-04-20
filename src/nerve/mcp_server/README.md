# NERVE MCP Server

A reference [Model Context Protocol](https://modelcontextprotocol.io/)
server that exposes NERVE's seven named Core safety-invariant
validators and three Yathartha extension validators as MCP tools. Uses
stdio transport. Works with any MCP-compatible client; see the VSCode
section below for one concrete configuration.

## Install

**For end users (no clone needed):**

Run directly with `uvx` in an ephemeral environment:

```bash
uvx --from 'nerve[mcp] @ git+https://github.com/ravikiran438/pratyahara-nerve.git@v0.1.0' nerve-mcp
```

Or install persistently with `pip` into an existing venv:

```bash
pip install 'nerve[mcp] @ git+https://github.com/ravikiran438/pratyahara-nerve.git@v0.1.0'
```

**For contributors (clone):**

From the repository root:

```bash
pip install -e '.[mcp]'
```

Either path installs the MCP Python SDK alongside the NERVE package
and registers the `nerve-mcp` console script in the active Python
environment.

## Run

```bash
nerve-mcp
```

Or without the script wrapper:

```bash
python -m nerve.mcp_server
```

The server writes MCP protocol messages on stdout and reads requests
on stdin. It is not interactive from a shell; an MCP client starts it
as a subprocess.

## Tools exposed

### NERVE Core (7)

| Tool | NERVE invariant | Purpose |
|---|---|---|
| `validate_dual_coverage` | N-1 | Every agent in the network is observed by at least two distinct MicroglialObservers. |
| `validate_asymmetric_trust` | N-3 | Outgoing and incoming trust weights on a NeuralTrustEnvelope may diverge. |
| `validate_severance_finality` | N-4 | Once a channel is severed, no further message may be delivered. |
| `validate_quarantine_freeze` | N-5 | Quarantined channel myelination cannot exceed the value at quarantine-entry time. |
| `validate_inhibitory_gating` | N-14 | Messages are gated by the sender's confidence threshold. |
| `validate_refractory` | N-15 | No message is attempted while a channel is in its refractory period. |
| `validate_critical_restriction` | N-9 | When a HomeostasisTrace reports critical state, all non-critical channels are closed. |

### Yathartha extension (3)

| Tool | Invariant | Purpose |
|---|---|---|
| `validate_coverage_conditional_drift` | N-16 | A MicroglialObserver may flag drift only for a task whose region is in the agent's covered CapabilitySurface. Tasks outside coverage are jaggedness, handled by the agent's `uncovered_policy`. |
| `validate_probe_battery_maintenance` | N-17 | Two ProbeBatteryResult entries may only be compared if they share the same `battery_version`, `region_id`, and `agent_id`. |
| `validate_capability_surface_integrity` | N-18 | Every change in the covered-regions set (or battery_version, or uncovered_policy) between two snapshots must be accompanied by a matching SurfaceChangeEvent. |

See [`../../../extensions/yathartha/README.md`](../../../extensions/yathartha/README.md)
for the extension's full specification and TLA+ model.

All tools take and return JSON. See `src/nerve/mcp_server/tools.py`
for input schemas and output shapes.

## Wire into VSCode

Add this to `.vscode/mcp.json` at your workspace root (or configure
globally via your VSCode user settings, under the MCP section).

**Option A — `uvx` from git URL (no persistent install):**

```json
{
  "servers": {
    "nerve": {
      "type": "stdio",
      "command": "uvx",
      "args": [
        "--from",
        "nerve[mcp] @ git+https://github.com/ravikiran438/pratyahara-nerve.git@v0.1.0",
        "nerve-mcp"
      ]
    }
  }
}
```

**Option B — absolute path to a pre-installed binary:**

```json
{
  "servers": {
    "nerve": {
      "type": "stdio",
      "command": "/absolute/path/to/your/.venv/bin/nerve-mcp"
    }
  }
}
```

Reload the workspace. The tools appear in any MCP-aware VSCode
extension under the `nerve` server name.

## Sample payloads

See [`EXAMPLES.md`](./EXAMPLES.md) for ready-to-paste JSON per tool,
covering the happy path and the failure variant for each invariant.

## Doctor check

Run a structural self-check (tool registry intact, schemas
well-formed) without spawning the stdio loop:

```bash
nerve-mcp --doctor
```

Exit code is 0 when all tools register correctly, 1 otherwise.

## Testing

```bash
pytest tests/mcp_server/
```

Handler-level tests hit `tools.py` directly; one stdio smoke test
launches the server as a subprocess and completes the MCP handshake,
confirming the end-to-end transport.
