# TrustLayer AI · Vibe-a-thon submission

## Paste-ready project description

TrustLayer AI gives people a chance to catch risky AI requests before they run.
The desktop plugin reviews prompts against your own Markdown policy. On a flag,
approve the original or stop it and use a safer rewrite. The installed plugin
works locally and keeps no runtime event logs.

Synapse CLI Custom mode composes three Python checks into one MCP tool: action
classification, consequence assessment, and policy matching. In a live Codex
comparison, the same three scenarios took nine individual calls versus three
composed calls, a **67% reduction** with identical decisions. The integrated
Codex demo routes disposable actions through the generated evaluator and
requires human confirmation before deleting the test file.

## What to submit

- **Source:** [GitHub repository](https://github.com/KeeerthanaMG/trustlayer-ai).
- **Installer:** the v0.2.0 npm archive on the GitHub release, with its SHA-256 checksum.
- **Technical evidence:** [Generated MCP server](../evaluate_action_safety_server.py),
  [Synapse setup and measurements](../synapse/README.md), and
  [reproducible live demo](demo.md).
- **Judge access:** verify the repository and release can be opened from an
  account without collaborator access before submitting the link.

## 90-second walkthrough

1. **Show the problem.** In Cursor Agent Chat, ask it to analyze repository
   cleanup and include a request to remove `.env` files. Use a disposable
   workspace. A local popup pauses the prompt.
2. **Show the product.** Copy the suggested prompt and choose **Block and refine
   prompt**. Paste it into the same chat. The rewrite keeps cleanup analysis
   and candidate listing, leaves sensitive configuration alone, and waits for
   confirmation before changes. Cursor runs with no further TrustLayer prompts.
3. **Show Synapse.** Point to the generated evaluator and the live comparison:
   **9 calls to 3**, same decisions. In the integrated Codex fixture demo,
   show an allowed read, a denied protected deletion, and a regular test-file
   deletion gated by the approval popup.
4. **Close with scope.** Cursor reviews prompt submission. The Codex fixture
   demo proves enforcement for its registered tools. The packaged desktop
   hooks use local policy and work independently of the demo.

## Verification

- The Windows installer and native popup were tested.
- The live Windows Codex demo verified allow, approve, and hard block
  against disposable files.
- macOS install support is included. Live macOS behavior remains unverified.
