# TrustLayer AI

TrustLayer reviews prompts and proposed tool calls locally, using a user-owned
Markdown policy. A flagged prompt offers **Block and refine prompt** or
**Approve & Proceed**. The original prompt stops when you choose to refine.

## Install on Windows or macOS

Install a current local Codex or Cursor client, Node.js 20+, and
[Python 3.10+ with Tk](https://www.python.org/downloads/). Download the
TrustLayer npm archive and open a terminal in the folder containing it.

| Host | Install command |
| --- | --- |
| Cursor desktop | `npx --yes --package ./keeerthanamg-trustlayer-ai-0.1.2.tgz trustlayer-ai install cursor` |
| Codex desktop or CLI | `npx --yes --package ./keeerthanamg-trustlayer-ai-0.1.2.tgz trustlayer-ai install codex` |

On Windows PowerShell, use `npx.cmd` if `npx` resolves to a disabled PowerShell
script. Restart the host. In Codex, review the hook commands before trusting
them. Use `/hooks` in the CLI or **Settings > Hooks** in the desktop app.
In Cursor, open local **Agent Chat**. Start with a fresh chat in a disposable
workspace.

Use the same command with `status` for registration status or `uninstall`
to remove TrustLayer's entries. The installer preserves existing hooks
and the configured policy. Edit `~/.cursor/trustlayer/policy.md` for Cursor
or `~/.codex/trustlayer/policy.md` for Codex. If you use `CODEX_HOME`, the
Codex policy lives under that directory instead.

## Try prompt refinement

Send a harmless request such as **Delete only the disposable file
trustlayer-sample.txt** in an empty workspace. Choose **Block and refine
prompt**. TrustLayer stops the original and supplies a read-only replacement.
Cursor opens a prefilled draft via its prompt link when the operating system
can open Cursor links. Cursor may ask you to confirm opening the draft. If
that fails, the hook message includes the same suggestion. Codex does not
expose a supported way to replace the composer draft. Copy the suggestion
from the block message into the chat. Review the replacement before sending.

The suggested text comes from local templates and leaves out original
prompt contents. Choosing **Approve & Proceed** lets the original prompt
continue. A later flagged tool call gets its own review. Closing or timing
out cancels the pending request.

The installed hooks do not write event logs, copy prompts to the clipboard,
or transmit hook input to a TrustLayer service. Installation stores only
the hook registration, runtime files and your policy. The host may retain
its own conversation, draft or diagnostic data. Older installations may
still have an `events.jsonl` file from the previous release.

The plugin covers events the local host sends to it. It uses deterministic
prompt heuristics and reviews exact pending events. It cannot guarantee
control over every side effect of a shell command or other tool.

## Synapse and Vibe-a-thon Track 2

Synapse CLI Custom mode generated the Python MCP server
[`evaluate_action_safety_server.py`](evaluate_action_safety_server.py). It
composes classification, consequence assessment and policy evaluation into
one tool. The integrated Codex demo calls that generated server before
dispatch and again before executing a protected fixture operation. The
same workflow needs three calls in the comparison baseline and one call
with the composed tool. See the [Synapse build, comparison and live results](synapse/README.md).

The installable desktop hooks use the same policy matcher locally and run
without a Synapse account or network service. The separate Track 2 demo uses
the generated MCP server and an optional stage-level fixture audit.
## Standalone evaluator

The standalone evaluator and the Track 2 demonstrations below run from the
repository checkout.

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

## Try the approval popup on Windows

From the repository root, create two disposable files in a fresh test directory:

```powershell
$fixtureRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("trustlayer-demo-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path (Join-Path $fixtureRoot 'project/uploads') -Force | Out-Null
Set-Content -LiteralPath (Join-Path $fixtureRoot 'project/example.txt') -Value 'disposable'
Set-Content -LiteralPath (Join-Path $fixtureRoot 'project/uploads/example.txt') -Value 'protected fixture'
python -m trustlayer.approval --policy TRUSTLAYER.md --fixture-root $fixtureRoot project/example.txt
```

Choose **Block** and verify the file remains. Rerun the same command and choose
**Approve & Proceed** to delete only that test file. Closing the popup or waiting
30 seconds denies the request. To verify a hard block, run the command with
`project/uploads/example.txt`. The sample policy denies it immediately.

The demo acts on two fixed fixture names in an operator-controlled directory.
Keep both the fixture directory and the policy outside the agent workspace.
The demo checks target metadata and reevaluates applicable policy before
deleting. An operator-controlled directory is required for protection against
concurrent path replacement.

For a Codex fixture session, register `python -m synapse.approval_demo` as a
local MCP server using the Python environment in [the MCP setup](synapse/README.md).
Set its working directory to this repository and supply absolute paths for
`TRUSTLAYER_POLICY` and `TRUSTLAYER_FIXTURE_ROOT` in the server environment.
Ask Codex to call `delete_disposable_fixture` with `project/example.txt`.
The popup gates this MCP tool's file operation. It leaves other Codex tools
under their existing controls. The demo uses the shared Python evaluator.
Routing live interception through the Synapse server is the next milestone.

## Integrated Codex demo

Use the isolated Python environment from [the MCP setup](synapse/README.md).
From the repository root in PowerShell, create a fresh disposable Codex project:

```powershell
$python = '.\.synapse-npm-cache\mcp-venv\Scripts\python.exe'
$demo = "D:\trustlayer-demo-" + [guid]::NewGuid().ToString('N')
& $python -m synapse.setup_demo $demo
codex -C $demo -s read-only
```

In the new session, review the freshly generated project configuration and
trust the fixture project and its hook in Codex. Use `/hooks` to verify the
hook is active. Then paste the following prompt:

> Use only the TrustLayer protected MCP tools. Read project/example.txt, then
> request deletion of project/uploads/example.txt, then request deletion of
> project/example.txt. Use one tool call per action and do not retry.

The read proceeds silently. The upload deletion is blocked before the tool
runs. The regular deletion prompts for approval. First choose **Block**, then
request it again and choose **Approve & Proceed**. Check the disposable file
and the audit records:

```powershell
Test-Path (Join-Path $demo 'fixtures/project/example.txt')
Test-Path (Join-Path $demo 'fixtures/project/uploads/example.txt')
Get-Content (Join-Path $demo 'audit.jsonl')
```

The hook calls the generated Synapse MCP evaluator before dispatch. The
fixture executor independently calls the same evaluator and owns approval
and the file operation. An unavailable evaluator, invalid response, or
unwritable audit log prevents a new operation. After approval, the executor
checks the decision and target again. The audit stores the stage, logical
fixture, decision and execution status. It omits file contents and absolute
target paths.

Coverage is limited to the two protected fixture tools. This demo assumes
an operator-controlled fixture directory, policy and code. Native shell and
other Codex or MCP tools retain their own controls. Run the full automated
test suite in the MCP environment with
`& $python -m unittest discover -s tests -v`.
