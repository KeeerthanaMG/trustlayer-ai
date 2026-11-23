"""Disposable MCP fixture for verifying Codex pre-execution hooks."""
import json
import sys
from pathlib import Path

TOOLS = [
    {
        "name": f"{probe}_probe",
        "description": f"Record the {probe} milestone-one probe.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    }
    for probe in ("allow", "block")
]


def result_for(method, params):
    if method == "initialize":
        return {
            "protocolVersion": params["protocolVersion"],
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "trustlayer-probe", "version": "1"},
        }
    if method == "tools/list":
        return {"tools": TOOLS}
    if method == "ping":
        return {}
    if method == "tools/call" and params["name"] in {"allow_probe", "block_probe"}:
        name = params["name"]
        with Path(__file__).with_name("probe-effects.log").open("a", encoding="utf-8") as log:
            print(name, file=log)
        return {"content": [{"type": "text", "text": f"Executed {name}"}]}
    raise ValueError("Unsupported fixture request")


for line in sys.stdin:
    request = json.loads(line)
    if "id" not in request:
        continue
    response = {"jsonrpc": "2.0", "id": request["id"]}
    try:
        response["result"] = result_for(request["method"], request.get("params", {}))
    except (KeyError, ValueError):
        response["error"] = {"code": -32601, "message": "Unsupported fixture request"}
    print(json.dumps(response), flush=True)
