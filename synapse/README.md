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

## Generate and compare

In the Synapse console, create an API key under your own account. In a local
PowerShell window, run the build script and paste the key at its masked prompt.
Hosted Custom mode sends selected function details or source to Synapse.
Only use the repository source and sample policy in the demonstration.

```powershell
.\synapse\build-custom.ps1
& $python -m synapse.compare --generated .\evaluate_action_safety_server.py
```

Use the actual filename and, if different, the tool name printed by Synapse.
Review the generated source before running it. Then register the generated
server in the agent using the Synapse connection settings, the isolated Python
path above, and an operator-controlled TRUSTLAYER_POLICY environment variable.

Status for this checkpoint is baseline verified. Generated server, comparison,
and live agent invocation require a successful Synapse Custom build.
