"""Create a fresh, isolated Codex fixture project for the integrated demo."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="New directory for the disposable demo")
    args = parser.parse_args()
    demo = args.directory.absolute()
    demo.mkdir()
    dotcodex = demo / ".codex"
    dotcodex.mkdir()
    subprocess.run(["git", "init", "-q", str(demo)], check=True)
    fixtures = demo / "fixtures"
    for resource in ("project/example.txt", "project/uploads/example.txt"):
        target = fixtures / resource
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("Disposable TrustLayer demo fixture.\n", encoding="utf-8")
    policy = demo / "TRUSTLAYER.md"
    policy.write_bytes((REPO / "TRUSTLAYER.md").read_bytes())
    settings = {
        "TRUSTLAYER_POLICY": str(policy),
        "TRUSTLAYER_FIXTURE_ROOT": str(fixtures),
        "TRUSTLAYER_AUDIT": str(demo / "audit.jsonl"),
    }
    bootstrap = dotcodex / "preflight.py"
    bootstrap.write_text(
        "import os\nimport sys\n"
        f"sys.path.insert(0, {str(REPO)!r})\n"
        f"os.environ.update({settings!r})\n"
        "from synapse.protected_demo import hook\n"
        "hook()\n",
        encoding="utf-8",
    )
    config = [
        "[mcp_servers.trustlayer_protected]",
        f"command = {json.dumps(sys.executable)}",
        'args = ["-m", "synapse.protected_demo"]',
        f"cwd = {json.dumps(str(REPO))}",
        'default_tools_approval_mode = "approve"',
        "env = { " + ", ".join(f"{key} = {json.dumps(value)}" for key, value in settings.items()) + " }",
    ]
    (dotcodex / "config.toml").write_text("\n".join(config) + "\n", encoding="utf-8")
    hooks = {"hooks": {"PreToolUse": [{
        "matcher": "^mcp__trustlayer_protected__",
        "hooks": [{
            "type": "command",
            "command": subprocess.list2cmdline([sys.executable, str(bootstrap)]),
            "timeout": 20,
        }],
    }]}}
    (dotcodex / "hooks.json").write_text(json.dumps(hooks, indent=2) + "\n", encoding="utf-8")
    print(demo)


if __name__ == "__main__":
    main()
