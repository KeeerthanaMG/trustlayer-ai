# TrustLayer AI

TrustLayer evaluates typed actions against an operator-selected Markdown policy.
The standalone evaluator uses Python 3.10 or later and the standard library.

## Evaluate an action

From the repository root in PowerShell:

```powershell
python -m trustlayer --policy TRUSTLAYER.md file.read project/example.txt
python -m trustlayer --policy TRUSTLAYER.md file.delete project/example.txt
python -m trustlayer --policy TRUSTLAYER.md file.delete project/uploads/example.txt
```

The CLI prints a JSON decision with the action, resource, risk, possible
consequence, matched rule IDs, and reason. Exit codes are 0 for ALLOW, 3 for
REQUIRE_APPROVAL, and 4 for BLOCK. Command-line usage errors use exit code 2.

Supported actions are file.read, file.write, and file.delete. Resources are
case-sensitive logical identifiers with slash-separated segments containing
ASCII letters, digits, periods, underscores, or hyphens. Segments cannot end
with a period. A future enforcement adapter must resolve and bind each logical
identifier to the actual operation before trusting the decision.

Copy TRUSTLAYER.md to an operator-controlled location and pass that file with
--policy. Risk describes the potential impact. The configured policy decides
which supported actions to allow, send for approval, or block.

The CLI evaluates one action and one resource per call. Live execution and
human approval belong to the enforcement adapter.

## Tests

```powershell
python -m unittest discover -s tests -v
```
