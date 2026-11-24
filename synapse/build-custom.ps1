# Supply a Synapse key for this build without writing it to disk or history.
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
$cli = Join-Path $PWD '.synapse-npm-cache/cli/node_modules/.bin/synapse.cmd'
if (-not (Test-Path $cli)) { throw 'Install the project-local Synapse CLI first.' }

$previousKey = $env:SYNAPSE_API_KEY
$previousTelemetry = $env:SYNAPSE_TELEMETRY
$previousPath = $env:Path
$portableNode = Join-Path $PWD '.synapse-npm-cache/node-v24.11.1-win-x64'
if (Test-Path (Join-Path $portableNode 'node.exe')) {
    $env:Path = "$portableNode;$previousPath"
}
try {
    if (-not $previousKey) {
        $secret = Read-Host 'Paste your Synapse API key (input is hidden)' -AsSecureString
        $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
        try {
            $env:SYNAPSE_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
        } finally {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
            $secret.Dispose()
        }
    }
    if (-not $env:SYNAPSE_API_KEY) { throw 'A Synapse API key is required.' }
    $env:SYNAPSE_TELEMETRY = '0'
    if (-not (Test-Path '.synapse/config.json')) {
        & $cli init
        if ($LASTEXITCODE -ne 0) { throw 'Synapse initialization failed.' }
    }

    $query = @"
Compose one stdio MCP tool named evaluate_action_safety(action: str, resource: str).
Use the existing TrustLayer Python evaluation workflow in trustlayer/engine.py,
including action classification, consequence assessment, policy loading and
permission matching, fail-closed validation and explanations. Invoke
trustlayer.engine.evaluate_action(Path(os.environ["TRUSTLAYER_POLICY"]), action, resource)
and serialize the returned dataclass as a JSON object. The policy path comes
exclusively from the server operator environment. No tool parameter for a
policy path. Return decision, action, resource, risk, consequence,
matched_policy_ids, and reason. Do not execute the proposed operation or
duplicate the policy logic.
"@
    & $cli build --custom --discover --query $query
    if ($LASTEXITCODE -ne 0) { throw 'Synapse Custom generation failed.' }
} finally {
    $env:SYNAPSE_API_KEY = $previousKey
    $env:SYNAPSE_TELEMETRY = $previousTelemetry
    $env:Path = $previousPath
}
