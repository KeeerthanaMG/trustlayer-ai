import json
import sys
from pathlib import Path


def main():
    try:
        event = json.load(sys.stdin)
        tool_input = event["tool_input"]
        command = tool_input.get("command") or tool_input.get("cmd")
        tool_name = event.get("tool_name")
        allowed = tool_name == "mcp__trustlayer_probe__allow_probe" or (
            command == "Write-Output TRUSTLAYER_ALLOW_PROBE"
        )
        audit_path = Path(__file__).with_name("probe-audit.jsonl")
        with audit_path.open("a", encoding="utf-8") as audit:
            marker = "TRUSTLAYER_BLOCK_PROBE"
            blocked_probe = tool_name == "mcp__trustlayer_probe__block_probe" or marker in str(command)
            probe = "allow" if allowed else "block" if blocked_probe else "other"
            audit.write(json.dumps({"probe": probe, "decision": "allow" if allowed else "block", "tool": tool_name}) + "\n")
        if allowed:
            return 0
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        pass
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "TrustLayer probe denied this action.",
        }
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
