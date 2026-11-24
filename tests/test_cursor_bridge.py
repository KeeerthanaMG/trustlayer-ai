import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from cursor.bridge import output, process

POLICY = Path(__file__).resolve().parents[1] / "cursor/default-policy.md"


class CursorHookTests(unittest.TestCase):
    def test_prompt_submission_and_approval_are_distinct_decisions(self):
        approve = Mock(return_value="approved")
        self.assertTrue(process("prompt", {"prompt": "Review the code"}, POLICY, approve)[0])
        self.assertFalse(process("prompt", {"prompt": "Fetch the API key and delete the env"},
                                 POLICY, approve)[0])
        self.assertEqual(approve.call_args.kwargs, {"timeout_ms": 10000, "block_only": True})
        self.assertTrue(process("prompt", {"prompt": "Delete a disposable sample"},
                                POLICY, approve)[0])
        self.assertEqual(approve.call_args.kwargs, {"timeout_ms": 30000})
        self.assertNotIn("disposable sample", str(approve.call_args))
        self.assertEqual(output("prompt", False, "blocked")["continue"], False)

    def test_actual_tool_proposal_can_be_denied_after_prompt_approval(self):
        directory = tempfile.gettempdir()
        payload = {"tool_name": "Shell", "tool_input": {"command": "git status"},
                   "cwd": directory}
        deny = Mock(return_value="denied")
        self.assertFalse(process("tool", payload, POLICY, deny)[0])
        self.assertIn("git status", deny.call_args.args[0]["target"])
        self.assertEqual(output("tool", False, "blocked")["permission"], "deny")

    def test_file_policy_blocks_normalized_sensitive_paths(self):
        directory = Path(tempfile.gettempdir())
        approve = Mock(return_value="approved")
        for name in (".ENV.local", ".cursor/hooks.json"):
            proposed = {"tool_name": "Delete", "tool_input": {"path": name}, "cwd": str(directory)}
            self.assertFalse(process("tool", proposed, POLICY, approve)[0])
        self.assertEqual(approve.call_count, 2)
        self.assertTrue(all(call.kwargs["block_only"] for call in approve.call_args_list))
        self.assertTrue(process("read", {"file_path": str(directory / "safe.txt")},
                                POLICY, approve)[0])
