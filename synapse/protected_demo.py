"""Codex preflight and execution for the controlled Synapse fixture tools."""
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent

from trustlayer.approval import FIXTURES, request_approval, run_fixture
from trustlayer.engine import Evaluation
from trustlayer.policies import Decision

SERVER = Path(__file__).resolve().parents[1] / "evaluate_action_safety_server.py"
ACTIONS = {
    "read_disposable_fixture": "file.read",
    "delete_disposable_fixture": "file.delete",
}
server = FastMCP("TrustLayer protected fixtures")


async def _synapse_call(policy, action, resource):
    parameters = StdioServerParameters(
        command=sys.executable, args=[str(SERVER)],
        env={"TRUSTLAYER_POLICY": str(policy.absolute())},
    )
    timeout = timedelta(seconds=8)
    async with stdio_client(parameters) as (reader, writer):
        async with ClientSession(reader, writer, read_timeout_seconds=timeout) as session:
            await session.initialize()
            response = await session.call_tool(
                "evaluate_action_safety", {"action": action, "resource": resource}
            )
            if response.isError:
                raise ValueError("MCP evaluation failed.")
            data = response.structuredContent
            if data is None and len(response.content) == 1 and isinstance(response.content[0], TextContent):
                data = json.loads(response.content[0].text)
            if not isinstance(data, dict):
                raise ValueError("Missing JSON MCP decision.")
            return data.get("result", data)


def evaluate_synapse(policy, action, resource):
    try:
        data = asyncio.run(_synapse_call(policy, action, resource))
        decision = Decision(data["decision"])
        if (data["action"], data["resource"]) != (action, resource):
            raise ValueError("MCP decision does not match the proposed action.")
        if not all(isinstance(data[key], str) and data[key] for key in (
            "risk", "consequence", "reason"
        )):
            raise ValueError("Missing decision explanation.")
        ids = data["matched_policy_ids"]
        if not isinstance(ids, list) or not all(isinstance(rule, str) for rule in ids):
            raise ValueError("Invalid policy rule identifiers.")
        return Evaluation(decision, action, resource, data["risk"], data["consequence"],
                          tuple(ids), data["reason"])
    except Exception:
        # This adapter is an authorization boundary. Transport, startup and schema
        # failures deny the action and leave the proposed resource untouched.
        return Evaluation(Decision.BLOCK, action, resource, "unknown",
                          "Evaluation unavailable.", (), "Synapse evaluation failed.")


def audit(stage, action, resource, decision, executed=None):
    record = {
        "time": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "action": action if action in ACTIONS.values() else None,
        "resource": resource if isinstance(resource, str) and resource in FIXTURES else None,
        "decision": decision,
        "executed": executed,
    }
    with Path(os.environ["TRUSTLAYER_AUDIT"]).open("a", encoding="utf-8") as log:
        log.write(json.dumps(record) + "\n")


def execute(action, resource):
    try:
        policy = Path(os.environ["TRUSTLAYER_POLICY"])
        root = Path(os.environ["TRUSTLAYER_FIXTURE_ROOT"])
        audit("execution_requested", action, resource, None)
    except (KeyError, OSError, ValueError):
        return {"decision": "BLOCK", "executed": False, "reason": "Demo configuration or audit unavailable."}
    result = run_fixture(policy, root, action, resource, request_approval, evaluate_synapse)
    try:
        audit("execution_result", action, resource, result["decision"], result["executed"])
    except (KeyError, OSError, ValueError):
        result["audit_error"] = "Outcome could not be recorded."
    return result


@server.tool()
async def read_disposable_fixture(resource: str) -> dict:
    """Read up to 4096 bytes of a fixed disposable fixture and return its byte count."""
    return await asyncio.to_thread(execute, "file.read", resource)


@server.tool()
async def delete_disposable_fixture(resource: str) -> dict:
    """Request deletion of a fixed disposable fixture under TrustLayer policy."""
    return await asyncio.to_thread(execute, "file.delete", resource)


def hook():
    reason = "Invalid or unrecognized fixture tool request."
    try:
        event = json.load(sys.stdin)
        prefix = "mcp__trustlayer_protected__"
        tool = event["tool_name"]
        action = ACTIONS[tool.removeprefix(prefix)] if tool.startswith(prefix) else None
        args = event["tool_input"]
        resource = args["resource"]
        if action and args.keys() == {"resource"} and resource in FIXTURES:
            evaluation = evaluate_synapse(Path(os.environ["TRUSTLAYER_POLICY"]), action, resource)
            audit("codex_preflight", action, resource, evaluation.decision)
            if evaluation.decision != Decision.BLOCK:
                return
            reason = evaluation.reason
        else:
            audit("codex_preflight", action, None, Decision.BLOCK)
    except (KeyError, OSError, TypeError, ValueError, AttributeError):
        reason = "TrustLayer preflight inputs, configuration, or audit are unavailable."
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}))


if __name__ == "__main__":
    if sys.argv[1:] == ["--hook"]:
        hook()
    else:
        server.run()
