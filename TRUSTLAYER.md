# TrustLayer policies

Select this file explicitly from a trusted location outside the agent's writable scope.
Only the fenced block below defines rules. Edit the rules to fit your workflow.

Actions are lowercase identifiers or `*`. Resources are case-sensitive identifiers.
A resource `*` matches any characters, including slashes. A resource with no wildcard
matches exactly. A caller supplies normalized action and resource identifiers.

The precedence is BLOCK, REQUIRE_APPROVAL, then ALLOW. With no matching rule,
the result is BLOCK. Rules are evaluated independently of their order.

```trustlayer
{
  "version": 1,
  "rules": [
    {"id": "read-project", "action": "file.read", "resource": "project/*", "decision": "ALLOW"},
    {"id": "review-delete", "action": "file.delete", "resource": "project/*", "decision": "REQUIRE_APPROVAL"},
    {"id": "protect-uploads", "action": "file.delete", "resource": "project/uploads/*", "decision": "BLOCK"}
  ]
}
```
