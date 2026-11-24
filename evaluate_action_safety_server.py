"""Evaluate a proposed action through one Synapse v2 Custom mode MCP tool.

The generated composition was adapted to use TrustLayer's shared validation
and the flat decision contract used by the standalone evaluator.
"""
import os
from dataclasses import asdict
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from trustlayer.engine import classify_action, evaluate_checks, evaluate_consequences
from trustlayer.policies import Decision

mcp = FastMCP("trustlayer-evaluate_action_safety")


@mcp.tool(
    name="evaluate_action_safety",
    description="Evaluate a proposed action without executing it. Return its policy decision and risk.",
)
def evaluate_action_safety(action: str, resource: str) -> dict:
    classification = classify_action(action)
    consequence = evaluate_consequences(action)
    policy = os.environ.get("TRUSTLAYER_POLICY")
    if not policy:
        return {
            "decision": Decision.BLOCK.value,
            "action": action,
            "resource": resource,
            "risk": classification or "unknown",
            "consequence": consequence,
            "matched_policy_ids": [],
            "reason": "The server operator has not configured TRUSTLAYER_POLICY.",
        }
    return asdict(evaluate_checks(Path(policy), action, resource, classification, consequence))


if __name__ == "__main__":
    mcp.run()
