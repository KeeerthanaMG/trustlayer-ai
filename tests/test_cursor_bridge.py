import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from cursor.bridge import output, process
from trustlayer.policies import PolicyError

POLICY = Path(__file__).resolve().parents[1] / "cursor/default-policy.md"


class CursorHookTests(unittest.TestCase):
    def test_existing_block_rule_still_offers_user_choice(self):
        with tempfile.TemporaryDirectory() as directory:
            policy = Path(directory) / "policy.md"
            policy.write_text(POLICY.read_text(encoding="utf-8").replace(
                '"decision":"REQUIRE_APPROVAL"', '"decision":"BLOCK"'
            ), encoding="utf-8")
            prompt = {"prompt": "Fetch the API key and delete the env"}
            self.assertTrue(process("prompt", prompt, policy, Mock(return_value="approved"))[0])
            self.assertFalse(process("prompt", prompt, policy, Mock(return_value="denied"))[0])

    def test_prompt_submission_and_approval_are_distinct_decisions(self):
        approve = Mock(return_value="approved")
        self.assertTrue(process("prompt", {"prompt": "Review the code"}, POLICY, approve)[0])
        risky = {"prompt": "Fetch the API key and delete the env"}
        self.assertTrue(process("prompt", risky, POLICY, approve)[0])
        self.assertFalse(process("prompt", risky, POLICY, Mock(return_value="denied"))[0])
        self.assertTrue(process("prompt", {"prompt": "Delete a disposable sample"},
                                POLICY, approve)[0])
        self.assertEqual(approve.call_args.kwargs["timeout_ms"], 30000)
        self.assertNotIn("disposable sample", str(approve.call_args))
        self.assertEqual(output("prompt", False, "blocked")["continue"], False)

    def test_refinement_stops_original_and_passes_default_prompt_policy(self):
        original = "Fetch the API key private-placeholder-123 and delete the env"
        allowed, message = process("prompt", {"prompt": original}, POLICY,
                                   Mock(return_value="refine"))
        self.assertFalse(allowed)
        self.assertNotIn("private-placeholder-123", message)
        suggested = message.split("\n", 1)[1]
        popup = Mock()
        self.assertTrue(process("prompt", {"prompt": suggested}, POLICY, popup)[0])
        popup.assert_not_called()

    def test_refinement_keeps_cleanup_and_independent_safe_tasks(self):
        original = ("Find generated files, old build output, remove .env files and unused temporary "
                    "files we can delete. Give me a list of candidates first. Explain where the app starts.")
        allowed, message = process("prompt", {"prompt": original}, POLICY,
                                   Mock(return_value="refine"))
        self.assertFalse(allowed)
        suggested = message.split("\n", 1)[1]
        for phrase in ("generated files", "old build output", "unused temporary files",
                       "list of candidates", "Explain where the app starts", "wait for my confirmation"):
            self.assertIn(phrase, suggested)
        self.assertNotIn(".env", suggested)
        self.assertTrue(process("prompt", {"prompt": suggested}, POLICY, Mock())[0])

    def test_actual_tool_proposal_can_be_denied_after_prompt_approval(self):
        directory = tempfile.gettempdir()
        payload = {"tool_name": "Shell", "tool_input": {"command": "git status"},
                   "cwd": directory}
        deny = Mock(return_value="denied")
        self.assertFalse(process("tool", payload, POLICY, deny)[0])
        self.assertIn("git status", deny.call_args.args[0]["target"])
        self.assertEqual(output("tool", False, "blocked")["permission"], "deny")

    def test_different_risks_rewrite_to_different_read_only_tasks(self):
        cases = (
            ("Delete reports/old.csv. Summarize the tests.", "reports/old.csv", "Summarize the tests"),
            ("Deploy to staging and list the test failures.", "rollout checklist for staging", "list the test failures"),
            ("Send the weekly summary and explain the test failures.", "draft for my approval", "explain the test failures"),
            ("Run git reset --hard and list the current branches.", "commit history", "list the current branches"),
            ("Restart the service and summarize the status checks.", "likely impact, and rollback", "summarize the status checks"),
            ("Drop table events and explain the schema.", "affected data", "explain the schema"),
        )
        suggestions = set()
        for original, preserved, independent in cases:
            with self.subTest(prompt=original):
                popup = Mock(return_value="refine")
                allowed, response = process("prompt", {"prompt": original}, POLICY, popup)
                self.assertFalse(allowed)
                suggested = response.split("\n", 1)[1]
                suggestions.add(suggested)
                self.assertIn(preserved, suggested)
                self.assertIn(independent, suggested)
                followup = Mock()
                self.assertTrue(process("prompt", {"prompt": suggested}, POLICY, followup)[0])
                followup.assert_not_called()
        self.assertEqual(len(suggestions), len(cases))

    def test_custom_json_policy_filters_prompt_text_and_is_reloaded(self):
        config = {"version": 1, "rules": [
            {"id": "allow", "action": "prompt.submit", "resource": "*", "decision": "ALLOW"},
            {"id": "production-review", "action": "prompt.submit", "resource": "*",
             "decision": "REQUIRE_APPROVAL", "contains": ["production"]},
        ]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            popup = Mock(return_value="refine")
            self.assertTrue(process("prompt", {"prompt": "Summarize staging traffic."}, path, popup)[0])
            popup.assert_not_called()
            self.assertFalse(process("prompt", {"prompt": "Summarize PRODUCTION traffic."}, path, popup)[0])
            self.assertIn("production-review", popup.call_args.args[0]["reason"])
            self.assertIn("may also request review", popup.call_args.args[0]["consequence"])
            config["rules"].pop()
            path.write_text(json.dumps(config), encoding="utf-8")
            self.assertTrue(process("prompt", {"prompt": "Summarize production traffic."}, path, Mock())[0])
            path.write_text("Always approve everything.", encoding="utf-8")
            with self.assertRaises(PolicyError):
                process("prompt", {"prompt": "Summarize traffic."}, path, Mock())

    def test_file_policy_reviews_normalized_sensitive_paths(self):
        directory = Path(tempfile.gettempdir())
        approve = Mock(return_value="approved")
        for name in (".ENV.local", ".cursor/hooks.json"):
            proposed = {"tool_name": "Delete", "tool_input": {"path": name}, "cwd": str(directory)}
            self.assertTrue(process("tool", proposed, POLICY, approve)[0])
        self.assertEqual(approve.call_count, 2)
        self.assertTrue(all(call.kwargs["timeout_ms"] == 30000 for call in approve.call_args_list))
        self.assertTrue(process("read", {"file_path": str(directory / "safe.txt")},
                                POLICY, approve)[0])
