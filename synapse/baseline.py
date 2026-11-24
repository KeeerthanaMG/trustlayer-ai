"""Low-level MCP tools for the Track 2 comparison."""
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from trustlayer.engine import check_permissions, classify_action, evaluate_consequences
from trustlayer.policies import load_policies

server = FastMCP("TrustLayer individual checks")


@server.tool()
def classify(action: str) -> dict:
    """Check whether this typed action is supported and return its risk."""
    return {"risk": classify_action(action)}


@server.tool()
def consequences(action: str) -> dict:
    """Describe the possible impact of this action."""
    return {"consequence": evaluate_consequences(action)}


@server.tool()
def permissions(action: str, resource: str) -> dict:
    """Match policy rules for a supported action and normalized resource."""
    rules = load_policies(Path(os.environ["TRUSTLAYER_POLICY"]))
    decision, matches, reason = check_permissions(rules, action, resource)
    return {
        "decision": decision.value,
        "matched_policy_ids": [rule.id for rule in matches],
        "reason": reason,
    }


if __name__ == "__main__":
    server.run()
