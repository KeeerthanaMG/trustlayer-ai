"""MCP entry point for the approval-gated disposable action."""
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from trustlayer.approval import delete_fixture

server = FastMCP("TrustLayer approval demo")


@server.tool()
def delete_disposable_fixture(resource: str) -> dict:
    """Ask TrustLayer whether to delete a named disposable test file."""
    policy = os.environ.get("TRUSTLAYER_POLICY")
    root = os.environ.get("TRUSTLAYER_FIXTURE_ROOT")
    if not policy or not root:
        return {"decision": "BLOCK", "executed": False, "reason": "Demo configuration is missing."}
    return delete_fixture(Path(policy), Path(root), resource)


if __name__ == "__main__":
    server.run()
