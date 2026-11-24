# Track 2 MCP comparison

The official participant guide requires a Synapse Custom-generated tool, an
agent that calls it, and a comparison with individual tool calls. Human
confirmation for data-changing actions is part of the final demonstration.
These tools evaluate proposed actions without performing them.

Run the comparison from the repository root. Install MCP only in the isolated
benchmark environment. The standalone TrustLayer CLI has no MCP dependency.

```powershell
$env:npm_config_cache = Join-Path $PWD '.synapse-npm-cache'
npm.cmd install --prefix .synapse-npm-cache/cli --ignore-scripts --no-audit --no-fund @2ndbrainlabs-ai/synapse-cli@0.1.9
python -m venv .synapse-npm-cache/mcp-venv
$python = '.\.synapse-npm-cache\mcp-venv\Scripts\python.exe'
& $python -m pip install -r synapse/requirements.txt
& $python -m synapse.compare
```

The baseline calls classification, consequences and permissions through MCP.
Its report includes per-case round-trip time after the MCP session has
initialized, call counts, decisions and matched rule IDs. This deterministic
client measures MCP calls without model inference or server startup time.

On this Windows machine, Tree-sitter crashed under Node 20.17.0 and loaded
successfully under Node 24.11.1. The project-local install uses the native
binary bundled with the official package. The build script uses the portable
Node 24.11.1 distribution when present in
`.synapse-npm-cache/node-v24.11.1-win-x64/` and otherwise uses Node from PATH.

## Run the composed tool and compare

The reviewed, generated server is checked into the repository. Running it and
the comparison requires the isolated Python environment above. Generation is
only needed when changing the tool composition.

```powershell
& $python -m synapse.compare --generated .\evaluate_action_safety_server.py
```

## Regenerate with Synapse

In the Synapse console, create an API key under your own account. In a local
PowerShell window, run the build script and paste the key at its masked prompt.
Hosted Custom mode sends selected function details or source to Synapse.
Only use the repository source and sample policy in the demonstration.

```powershell
.\synapse\build-custom.ps1
```

Regenerate in a disposable checkout. Use the filename and tool name printed
by Synapse, then review the generated composition and apply the shared
validation and response contract described below before replacing the reviewed
server. Register it in the agent using the Synapse connection settings, the
isolated Python path above, and an operator-controlled TRUSTLAYER_POLICY
environment variable.

## Verified comparison

Synapse CLI 0.1.9 generated `evaluate_action_safety_server.py` in Custom mode.
The checked-in version keeps the generated three-part composition and uses the
standalone engine's validation and structured response. The server operator
selects the Markdown policy. The MCP caller supplies the action and resource.

| Case | Decision | Individual calls | Composed calls | Individual ms | Composed ms |
| --- | --- | ---: | ---: | ---: | ---: |
| Read a project file | ALLOW | 3 | 1 | 13.41 | 17.48 |
| Delete a project file | REQUIRE_APPROVAL | 3 | 1 | 9.93 | 3.89 |
| Delete a protected upload | BLOCK | 3 | 1 | 7.43 | 2.94 |
| Write without a matching rule | BLOCK | 3 | 1 | 7.06 | 2.72 |

These are single-run Windows MCP round-trip observations. Both paths agreed on
all four decisions and their matched rule IDs. A separate live Codex session
used nine individual calls and three composed calls to evaluate the same
read, delete and protected-delete scenarios. A fourth composed call returned
BLOCK for an unsupported shell action. All 13 calls completed without tool
errors. The deterministic comparison also verified BLOCK for a malformed
resource identifier.

The baseline is a fixture for supported, normalized inputs. The composed
tool returns approval requirements for the enforcement layer to handle.
