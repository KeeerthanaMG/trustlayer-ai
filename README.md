# TrustLayer AI

**Catch risky AI actions before they happen, then turn the warning into a safer next prompt.**

## What you get

- **Review before it runs.** Pause flagged prompts and tool calls in Cursor or Codex.
- **Keep your context.** Choose **Block and refine prompt**, then paste the suggested prompt into the same chat. Choose **Approve & Proceed** to continue with the original.
- **Set your own rules.** Edit a local Markdown policy. The desktop hooks keep no runtime logs.

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

## Why Synapse matters · Vibe-a-thon Track 2

- **Generated with Synapse CLI Custom mode.** One MCP tool combines action classification, consequence assessment, and policy checks.
- **Measured live in Codex.** The same three cases took **9 individual calls vs. 3 composed calls**, with identical decisions.
- **Enforced in the integrated demo.** The Codex hook calls the generated evaluator before dispatch. The fixture executor uses it again to enforce policy and approval.

[Synapse build and measured results](synapse/README.md) · [End-to-end demo and test commands](docs/demo.md)

## Privacy and coverage

- **Policy** lives under `~/.cursor/trustlayer/policy.md` or `~/.codex/trustlayer/policy.md`. A custom `CODEX_HOME` takes precedence for the Codex installer.
- **Desktop hooks** retain no prompts, tool inputs, or event logs. The host may keep its own history. Prior releases may have left an `events.jsonl` file.
- **Coverage** depends on host hook events. The standalone desktop rules run locally. The separate Track 2 fixture demo uses the Synapse-generated MCP tool and records its test outcomes.
