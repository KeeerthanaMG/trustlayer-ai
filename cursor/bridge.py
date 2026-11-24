"""Cursor desktop hook adapter. No prompt or tool payload is persisted."""
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE))
from trustlayer.approval_dialog import ask
from trustlayer.policies import Decision, load_policies, match_policies

SECRET = re.compile(
    r"(?<![\w.])\.env(?:\b|(?=\.))|\b(?:api[ _-]?keys?|tokens?|credentials?|passwords?|secrets?)\b"
    r"|\bprintenv\b|\benv:|(?:^|[/\\])(?:\.npmrc|\.netrc|\.ssh|\.aws|id_rsa|id_ed25519)(?:$|[/\\])",
    re.IGNORECASE,
)
DESTRUCTIVE = re.compile(
    r"\b(?:delete|remove|erase|wipe|destroy|truncate)\b|\breset\s+--hard\b", re.IGNORECASE
)
DISCLOSURE = re.compile(
    r"\b(?:fetch|dump|print|reveal|show|send|upload|extract|display|expose|read|copy)\b",
    re.IGNORECASE,
)
SENSITIVE_FILENAMES = {".npmrc", ".netrc", "credentials", "id_rsa", "id_ed25519"}
FILE_TOOLS = {"Read": "file.read", "Write": "file.write", "Delete": "file.delete"}


def classify_prompt(payload):
    prompt = payload["prompt"]
    if not isinstance(prompt, str):
        raise ValueError("Invalid prompt")
    destructive = DESTRUCTIVE.search(prompt)
    if SECRET.search(prompt) and (destructive or DISCLOSURE.search(prompt)):
        category = "secret-destructive"
    else:
        category = "destructive" if destructive else "ordinary"
    return "prompt.submit", category, "Prompt category: " + category


def classify_file(path, base, action):
    if not isinstance(path, str) or not path.strip():
        raise ValueError("Missing file target")
    path = Path(path)
    if not path.is_absolute():
        if not isinstance(base, str) or not Path(base).is_absolute():
            raise ValueError("Missing absolute working directory")
        path = Path(base) / path
    resolved = path.resolve()
    parts = {part.split(":", 1)[0].rstrip(" .").casefold()
             for part in (*path.parts, *resolved.parts)}
    sensitive = (
        bool(parts & (SENSITIVE_FILENAMES | {".ssh", ".aws", ".cursor"}))
        or any(part == ".env" or part.startswith(".env.") for part in parts)
    )
    scope = "sensitive" if sensitive else "file"
    return action, f"{scope}/{resolved.as_posix().casefold()}", str(path)


def classify_tool(payload):
    tool = payload["tool_name"]
    arguments = payload["tool_input"]
    if not isinstance(tool, str) or not isinstance(arguments, dict):
        raise ValueError("Invalid tool proposal")
    if tool in FILE_TOOLS:
        paths = {arguments[key] for key in ("path", "file_path") if key in arguments}
        if len(paths) != 1:
            raise ValueError("Expected exactly one file target")
        return classify_file(paths.pop(), payload.get("cwd"), FILE_TOOLS[tool])
    if tool == "Shell":
        command = arguments["command"]
        if not isinstance(command, str) or not command.strip():
            raise ValueError("Missing shell command")
        directory = arguments.get("working_directory") or payload.get("cwd")
        if not isinstance(directory, str) or not Path(directory).is_absolute():
            raise ValueError("Missing shell working directory")
        if SECRET.search(command):
            return "shell.run", "sensitive/shell", "Shell command references credential material."
        if len(command) > 1500:
            raise ValueError("Command too large for exact review")
        return "shell.run", "shell", f"Working directory: {directory}\nCommand: {command}"
    details = json.dumps(arguments, ensure_ascii=True)
    if SECRET.search(details):
        return "tool.invoke", "sensitive/external", "Tool arguments reference credential material."
    if len(details) > 1500:
        raise ValueError("Arguments too large for exact review")
    return "tool.invoke", "external", f"{tool}\nArguments: {details}"


def process(event, payload, policy, show=ask):
    if event == "prompt":
        proposed = classify_prompt(payload)
    elif event == "read":
        proposed = classify_file(payload["file_path"], None, "file.read")
    elif event == "tool":
        proposed = classify_tool(payload)
    else:
        raise ValueError("Unknown event")

    action, resource, target = proposed
    decision, matches = match_policies(load_policies(policy), action, resource)
    decisive = ", ".join(rule.id for rule in matches if rule.decision == decision)
    explanation = f"Matched policy: {decisive}" if decisive else "No matching policy rule."
    if decision != Decision.ALLOW:
        review = {
            "action": action, "resource": target, "target": target,
            "risk": "review required", "reason": explanation,
            "consequence": "This decision applies only to the pending Cursor event.",
        }
        return show(review, timeout_ms=30000) == "approved", "Approval declined or expired."
    return True, ""


def output(event, allowed, reason):
    result = {"continue": allowed} if event == "prompt" else {
        "permission": "allow" if allowed else "deny"
    }
    if not allowed:
        result["user_message"] = reason
    return result


def main():
    event = sys.argv[1]
    default_policy = PACKAGE / "cursor" / "default-policy.md"
    user_policy = Path.home() / ".cursor" / "trustlayer" / "policy.md"
    policy = Path(sys.argv[2]) if len(sys.argv) > 2 else (
        user_policy if os.path.lexists(user_policy) else default_policy
    )
    try:
        payload = json.load(sys.stdin)
        allowed, reason = process(event, payload, policy)
    except Exception:
        allowed, reason = False, "TrustLayer could not safely evaluate the request."
    if len(sys.argv) > 2:
        try:
            with policy.with_name("events.jsonl").open("a", encoding="utf-8") as log:
                log.write(json.dumps({"time": datetime.now(timezone.utc).isoformat(),
                                      "event": event, "allowed": allowed}) + "\n")
        except OSError:
            pass
    print(json.dumps(output(event, allowed, reason)))


if __name__ == "__main__":
    main()
