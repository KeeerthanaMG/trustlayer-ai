# TrustLayer tester guide

## Install the current release

- Use current Cursor or Codex, Node.js 20+, and Python 3.10+ with Tk.
- Download [the current installer](https://github.com/KeeerthanaMG/trustlayer-ai/releases/download/v0.2.0/keeerthanamg-trustlayer-ai-0.2.0.tgz). From that folder, run:

```text
npx --yes --package ./keeerthanamg-trustlayer-ai-0.2.0.tgz trustlayer-ai install cursor
```

- Use `install codex` for Codex. Restart the host. In Codex, review and trust
  the hooks via `/hooks` or Settings.
- On Windows PowerShell, use `npx.cmd` if `npx` is blocked.
- Upgrading preserves your existing Markdown policy. Use the [v0.1.6 installer](https://github.com/KeeerthanaMG/trustlayer-ai/releases/tag/v0.1.6)
  again if you need to roll back.

## Customize policy

- Edit `~/.cursor/trustlayer/policy.md` or `~/.codex/trustlayer/policy.md`.
  Codex uses its configured `CODEX_HOME` when set.
- Use one fenced `trustlayer` JSON block in Markdown, or put the same JSON in
  `policy.json` beside it. When both are present, JSON takes precedence.
- For prompt rules, use action `prompt.submit`. Supported resources are
  `ordinary`, `destructive`, `secret-destructive`, `git-risk`,
  `external-action`, `system-change`, and `*`.
- `contains` optionally matches any of the listed literal phrases,
  case-insensitively. Omit it for category-wide rules. Review rules take
  precedence over matching allow rules. In desktop prompt review, the user
  has the final choice.
- From the source checkout, validate a file with
  `python cursor/bridge.py policy-check path/to/policy.json`.
- Natural-language prose is available for explaining your policy. Write the
  enforceable rules in the structured block. Invalid policies stop the
  request with a configuration message.

Example JSON policy that reviews production and destructive requests:

```json
{
  "version": 1,
  "rules": [
    {"id": "ordinary", "action": "prompt.submit", "resource": "ordinary", "decision": "ALLOW"},
    {
      "id": "production-review",
      "action": "prompt.submit",
      "resource": "*",
      "contains": ["production", "customer data"],
      "decision": "REQUIRE_APPROVAL"
    }
  ]
}
```

## Test it in a disposable workspace

### macOS smoke test: v0.2.0-rc.1

#### Run the test

Use a disposable macOS account, a disposable repository workspace, and Cursor
Agent Chat. The clean account ensures the installer uses the default policy;
existing custom policies can change which prompts require review. Have current
Cursor, Node.js 20+, and Python 3.10+ with Tk available.

1. Download and verify the published prerelease archive:

   ```sh
   mkdir -p "$HOME/trustlayer-macos-smoke"
   cd "$HOME/trustlayer-macos-smoke"
   curl -fLO https://github.com/KeeerthanaMG/trustlayer-ai/releases/download/v0.2.0-rc.1/keeerthanamg-trustlayer-ai-0.2.0-rc.1.tgz
   curl -fLO https://github.com/KeeerthanaMG/trustlayer-ai/releases/download/v0.2.0-rc.1/keeerthanamg-trustlayer-ai-0.2.0-rc.1.tgz.sha256
   shasum -a 256 -c keeerthanamg-trustlayer-ai-0.2.0-rc.1.tgz.sha256
   ```

   Continue only if the checksum reports `OK`.
2. Install and confirm the registration:

   ```sh
   npx --yes --package ./keeerthanamg-trustlayer-ai-0.2.0-rc.1.tgz trustlayer-ai install cursor
   npx --yes --package ./keeerthanamg-trustlayer-ai-0.2.0-rc.1.tgz trustlayer-ai status cursor
   ```

   Confirm the status reports `installed: true`, then fully restart Cursor.
   Open Agent Chat in the disposable repository.
3. Send this read-only repository walkthrough:

   > Walk me through this repository's structure and summarize what its main
   > components do. Read files only; do not make changes or run commands.

   **Pass:** the walkthrough proceeds with no TrustLayer popup.
4. In the same chat, send:

   > Deploy to staging and list the test failures.

   **Pass:** exactly one TrustLayer review appears before submission. Choose
   **Block and refine prompt** (copy the suggestion first if the dialog offers
   a separate copy action). The original request must remain blocked.
5. Inspect the suggested rewrite. It must keep the test-failure request and
   replace deployment with a staging rollout checklist. With the default
   policy, the expected text is:

   > list the test failures. Prepare a rollout checklist for staging covering
   > validation, impact, and rollback. Leave the workspace unchanged and wait
   > for my confirmation before making changes.

6. Paste that suggestion into the same chat and submit it. **Pass:** Cursor
   starts working, and no TrustLayer popup appears while it does so. Do not
   approve or execute any deployment; the rewrite should only produce the
   checklist and test-failure request.

Record the macOS and Cursor versions, test date, checksum result, and any
deviation from the expected behavior below. A pass requires all three Agent
Chat checks (walkthrough, one pre-submit review with the expected rewrite, and
no popups after resubmission).

#### Result record

| Check | Result | Observation |
| --- | --- | --- |
| Release metadata and checksum asset lookup | PASS | GitHub lists the `v0.2.0-rc.1` archive and checksum assets; the checksum text was retrieved. The archive was not downloaded or hashed here. |
| macOS archive checksum verification | NOT RUN | Requires downloading the archive on the macOS test machine. |
| macOS installation and Cursor restart | BLOCKED | This session has Windows access only and no macOS/Cursor desktop environment. |
| Read-only repository walkthrough has no popup | NOT RUN | No macOS Cursor Agent Chat session was available. |
| One review, Block and refine, and expected rewrite | NOT RUN | No macOS Cursor Agent Chat session was available. |
| No TrustLayer popups after resubmission | NOT RUN | No macOS Cursor Agent Chat session was available. |

No macOS product-behavior pass or failure is claimed until the checklist above
is run on macOS.

### Prompt refinement examples

| Paste into Agent Chat | Expected |
| --- | --- |
| Summarize the project structure and list key files. | The default policy lets it through. |
| Delete reports/old.csv and summarize the test failures. | The rewrite keeps the test summary and asks whether the file is a cleanup candidate. |
| Deploy to staging and list the test failures. | The rewrite asks for a staging rollout checklist and keeps the test request. |
| Run git reset --hard and list the current branches. | The rewrite asks for a read-only Git assessment and keeps the branch list. |
| Summarize production traffic. | The example custom policy requests review. |

Refinement runs locally using deterministic rules. It carries forward
recognizable read-only requests and turns supported risky steps into review
plans. Ambiguous wording can require clarification. The popup tells you if
your custom policy would also review the suggestion. No prompt, policy, or
refinement is sent to a TrustLayer service. Cursor review ends at submission.
