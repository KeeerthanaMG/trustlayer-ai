# TrustLayer tester guide

## Install the release candidate

- Use current Cursor or Codex, Node.js 20+, and Python 3.10+ with Tk.
- Download `keeerthanamg-trustlayer-ai-0.2.0-rc.1.tgz`. From that folder, run:

```text
npx --yes --package ./keeerthanamg-trustlayer-ai-0.2.0-rc.1.tgz trustlayer-ai install cursor
```

- Use `install codex` for Codex. Restart the host. In Codex, review and trust
  the hooks via `/hooks` or Settings.
- On Windows PowerShell, use `npx.cmd` if `npx` is blocked.
- Upgrading preserves your existing Markdown policy. Use the stable installer
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
