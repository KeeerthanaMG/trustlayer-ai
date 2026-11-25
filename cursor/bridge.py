"""Cursor desktop hook adapter. No prompt or tool payload is persisted."""
import json
import os
import re
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE))
from trustlayer.approval_dialog import ask
from trustlayer.policies import Decision, PolicyError, load_policies, match_policies

from cursor.prompt_policy import SECRET, prompt_category, refine_prompt

SENSITIVE_FILENAMES = {".npmrc", ".netrc", "credentials", "id_rsa", "id_ed25519"}
FILE_TOOLS = {"Read": "file.read", "Write": "file.write", "Delete": "file.delete"}


def classify_prompt(payload):
    prompt = payload["prompt"]
    if not isinstance(prompt, str):
        raise ValueError("Invalid prompt")
    category = prompt_category(prompt)
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
    rules = load_policies(policy)
    prompt = payload["prompt"] if event == "prompt" else ""
    decision, matches = match_policies(rules, action, resource, prompt=prompt)
    decisive = ", ".join(rule.id for rule in matches if rule.decision == decision)
    explanation = f"Matched policy: {decisive}" if decisive else "No matching policy rule."
    if decision != Decision.ALLOW:
        review = {
            "action": action, "resource": target, "target": target,
            "risk": "review required", "reason": explanation,
            "consequence": "This decision applies only to the pending request.",
        }
        if event == "prompt":
            refinement = refine_prompt(prompt)
            refined_decision, _ = match_policies(rules, action, prompt_category(refinement),
                                                 prompt=refinement)
            if refined_decision != Decision.ALLOW:
                review["consequence"] = "Your policy may also request review of the suggested draft."
            choice = show(review, timeout_ms=30000, refinement=refinement)
            if choice == "refine":
                return False, "Suggested prompt:\n" + refinement
        else:
            choice = show(review, timeout_ms=30000)
        return choice == "approved", "Approval declined or expired."
    return True, ""


def output(event, allowed, reason):
    result = {"continue": allowed} if event == "prompt" else {
        "permission": "allow" if allowed else "deny"
    }
    if not allowed:
        result["user_message"] = reason
    return result


def main():
    mode = sys.argv[1]
    if mode == "policy-check":
        try:
            rules = load_policies(Path(sys.argv[2]))
        except IndexError:
            print("Provide a policy file path.", file=sys.stderr)
            raise SystemExit(2)
        except PolicyError as error:
            print(f"Invalid TrustLayer policy: {error}", file=sys.stderr)
            raise SystemExit(2)
        print(f"Valid TrustLayer policy ({len(rules)} rules).")
        return
    codex = mode.startswith("codex-")
    event = mode.removeprefix("codex-")
    if not codex and event in {"tool", "read"}:
        # Old Cursor registrations must stay silent even before a host restart.
        print(json.dumps({"permission": "allow"}))
        return
    default_policy = PACKAGE / "cursor" / "default-policy.md"
    host_dir = ".codex" if codex else ".cursor"
    user_policy = Path.home() / host_dir / "trustlayer" / "policy.md"
    if len(sys.argv) > 2:
        user_policy = Path(sys.argv[2])
    json_policy = user_policy.with_suffix(".json")
    if os.path.lexists(json_policy):
        policy = json_policy
    elif len(sys.argv) > 2 or os.path.lexists(user_policy):
        policy = user_policy
    else:
        policy = default_policy
    try:
        payload = json.load(sys.stdin)
        if codex and event == "tool" and payload.get("tool_name") in {"Bash", "exec_command"}:
            payload["tool_name"] = "Shell"
            arguments = payload["tool_input"]
            arguments["command"] = arguments.get("command") or arguments.get("cmd")
            arguments["working_directory"] = arguments.get("working_directory") or arguments.get("workdir")
        allowed, reason = process(event, payload, policy)
    except PolicyError:
        allowed, reason = False, "TrustLayer could not load your policy. Run the policy check and correct the file."
    except Exception:
        allowed, reason = False, "TrustLayer could not safely evaluate the request."
    if codex:
        if allowed:
            response = {}
        elif event == "prompt":
            response = {"decision": "block", "reason": reason}
        else:
            response = {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                        "permissionDecision": "deny", "permissionDecisionReason": reason}}
    else:
        response = output(event, allowed, reason)
    print(json.dumps(response), flush=True)


if __name__ == "__main__":
    main()
