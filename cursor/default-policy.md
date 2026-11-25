# TrustLayer Cursor policy

This user-owned policy evaluates prompt categories and actual tool proposals.
Rules use case-normalized resources. The first configuration ships conservative
shell and external-tool defaults. Unmatched requests require review.

```trustlayer
{
  "version": 1,
  "rules": [
    {"id":"ordinary-prompt","action":"prompt.submit","resource":"ordinary","decision":"ALLOW"},
    {"id":"review-destructive-prompt","action":"prompt.submit","resource":"destructive","decision":"REQUIRE_APPROVAL"},
    {"id":"protect-secrets-prompt","action":"prompt.submit","resource":"secret-destructive","decision":"REQUIRE_APPROVAL"},
    {"id":"review-git-prompt","action":"prompt.submit","resource":"git-risk","decision":"REQUIRE_APPROVAL"},
    {"id":"review-external-prompt","action":"prompt.submit","resource":"external-action","decision":"REQUIRE_APPROVAL"},
    {"id":"review-system-prompt","action":"prompt.submit","resource":"system-change","decision":"REQUIRE_APPROVAL"},
    {"id":"ordinary-file-read","action":"file.read","resource":"*","decision":"ALLOW"},
    {"id":"ordinary-file-write","action":"file.write","resource":"*","decision":"ALLOW"},
    {"id":"review-file-delete","action":"file.delete","resource":"*","decision":"REQUIRE_APPROVAL"},
    {"id":"protect-secret-targets","action":"*","resource":"sensitive/*","decision":"REQUIRE_APPROVAL"},
    {"id":"review-shell","action":"shell.run","resource":"shell","decision":"REQUIRE_APPROVAL"},
    {"id":"review-external-tools","action":"tool.invoke","resource":"*","decision":"REQUIRE_APPROVAL"}
  ]
}
```
