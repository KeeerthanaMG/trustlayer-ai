# TrustLayer AI

**Three safety checks. One call. Catch risky AI actions before they run.**

## Why TrustLayer AI?

- **The problem.** When an agent proposes deleting a file, it needs to identify the action, assess what could be lost, and check the owner's policy before acting. With those checks exposed as separate tools, the agent makes **three calls per action** and has to combine the results itself. A missed check can leave a risky action unreviewed.
- **One tool runs all three checks.** Synapse CLI Custom mode composes action classification, consequence assessment, and policy checks into a single MCP tool. It returns one decision with the reason and matched rules.
- **67% fewer tool calls.** In a live Codex comparison, the same three scenarios took **9 calls with individual tools and 3 with TrustLayer's composed tool**. Both approaches returned the same decisions. [Measured results](synapse/README.md)
- **The user stays in control.** Pause flagged prompts and tool calls in Cursor or Codex. Choose **Block and refine prompt** to get a safer suggestion for the same chat, or **Approve & Proceed** to continue. Edit the local Markdown policy to choose what gets reviewed.

## Install on Windows or macOS

- **You need** a current Cursor or Codex client, Node.js 20+, and [Python 3.10+ with Tk](https://www.python.org/downloads/).
- **Download** `keeerthanamg-trustlayer-ai-0.1.3.tgz`, then run one command from its folder.

| Host | Command |
| --- | --- |
| Cursor | `npx --yes --package ./keeerthanamg-trustlayer-ai-0.1.3.tgz trustlayer-ai install cursor` |
| Codex | `npx --yes --package ./keeerthanamg-trustlayer-ai-0.1.3.tgz trustlayer-ai install codex` |

- **Restart** the host. Open **Agent Chat** in Cursor. In Codex, review and trust the hooks in **Settings > Hooks** or `/hooks`.
- **Windows PowerShell** can use `npx.cmd` if `npx` is blocked by execution policy.
- **Manage** with the same command using `status` or `uninstall` in place of `install`.

## Demo in 30 seconds

1. In a disposable workspace, send **“Delete only the disposable file trustlayer-sample.txt.”**
2. Choose **Block and refine prompt**. The original stops and TrustLayer shows a read-only suggestion.
3. Paste the suggestion into the **current** chat and review it before sending. The host hook APIs do not expose in-place composer editing.

## See it in action

- The Codex hook calls the Synapse-generated evaluator before dispatch. The fixture executor checks the decision again before allowing the operation.

[Synapse build and measured results](synapse/README.md) · [End-to-end demo and test commands](docs/demo.md)

## Privacy and coverage

- **Policy** lives under `~/.cursor/trustlayer/policy.md` or `~/.codex/trustlayer/policy.md`. A custom `CODEX_HOME` takes precedence for the Codex installer.
- **Desktop hooks** retain no prompts, tool inputs, or event logs. The host may keep its own history. Prior releases may have left an `events.jsonl` file.
- **Coverage** depends on host hook events. The desktop rules run locally. The integrated fixture demo uses the Synapse-generated MCP tool and records its test outcomes.
