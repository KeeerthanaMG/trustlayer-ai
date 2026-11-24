import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from trustlayer.engine import evaluate_action
from trustlayer.policies import Decision

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "TRUSTLAYER.md"


class EngineTests(unittest.TestCase):
    def test_cli_results(self):
        for action, resource, expected, exit_code, matched_ids in (
            ("file.read", "project/example.txt", "ALLOW", 0, ["read-project"]),
            ("file.delete", "project/example.txt", "REQUIRE_APPROVAL", 3, ["review-delete"]),
            ("file.delete", "project/uploads/example.txt", "BLOCK", 4,
             ["review-delete", "protect-uploads"]),
            ("file.write", "project/example.txt", "BLOCK", 4, []),
        ):
            with self.subTest(action=action, resource=resource):
                completed = subprocess.run(
                    [sys.executable, "-m", "trustlayer", "--policy", str(POLICY), action, resource],
                    cwd=ROOT, capture_output=True, text=True,
                )
                self.assertEqual(completed.returncode, exit_code, completed.stderr)
                result = json.loads(completed.stdout)
                self.assertEqual(result["decision"], expected)
                self.assertEqual(result["matched_policy_ids"], matched_ids)
                self.assertTrue(result["reason"])
                self.assertTrue(result["consequence"])

    def test_rejects_noncanonical_resources(self):
        for resource in ("project/../file", "/project/file", "project//file",
                         "project\\file", "project/file.", "project/file:stream"):
            with self.subTest(resource=resource):
                result = evaluate_action(POLICY, "file.read", resource)
                self.assertEqual(result.decision, Decision.BLOCK)
                self.assertIn("normalized", result.reason)

    def test_unknown_action_blocks_even_with_wildcard_allow(self):
        with tempfile.TemporaryDirectory() as directory:
            policy = Path(directory) / "policy.md"
            policy.write_text(
                '```trustlayer\n{"version":1,"rules":[{"id":"all","action":"*",'
                '"resource":"*","decision":"ALLOW"}]}\n```\n',
                encoding="utf-8",
            )
            result = evaluate_action(policy, "shell.run", "project/item")
            self.assertEqual(result.decision, Decision.BLOCK)
            self.assertIn("Unsupported", result.reason)
            result = evaluate_action(policy, "file.delete", "project/item")
            self.assertEqual(result.decision, Decision.ALLOW)
            self.assertEqual(result.risk, "high")
            policy.write_text(policy.read_text(encoding="utf-8").replace(
                '"action":"*"', '"action":"shell.run"'
            ), encoding="utf-8")
            result = evaluate_action(policy, "file.delete", "project/item")
            self.assertEqual(result.decision, Decision.BLOCK)
            self.assertIn("unsupported action type", result.reason)

    def test_unavailable_policy_blocks_with_reason(self):
        with tempfile.TemporaryDirectory() as directory:
            result = evaluate_action(Path(directory) / "missing.md", "file.read", "project/item")
            self.assertEqual(result.decision, Decision.BLOCK)
            self.assertIn("Policy error", result.reason)
