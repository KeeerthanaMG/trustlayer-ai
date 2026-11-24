import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from trustlayer.approval import delete_fixture, request_approval
from trustlayer.engine import evaluate_action

POLICY = Path(__file__).resolve().parents[1] / "TRUSTLAYER.md"
RESOURCE = "project/example.txt"
PROTECTED = "project/uploads/example.txt"


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        for resource in (RESOURCE, PROTECTED):
            path = self.root / resource
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("disposable", encoding="utf-8")

    def test_denial_and_approval_have_different_effects(self):
        target = self.root / RESOURCE
        self.assertFalse(delete_fixture(POLICY, self.root, RESOURCE, lambda *_: False)["executed"])
        self.assertTrue(target.exists())
        def approve(evaluation, reviewed_target):
            self.assertEqual(evaluation.resource, RESOURCE)
            self.assertEqual(reviewed_target, target)
            self.assertTrue(target.exists())
            return True
        self.assertTrue(delete_fixture(POLICY, self.root, RESOURCE, approve)["executed"])
        self.assertFalse(target.exists())
        self.assertTrue((self.root / PROTECTED).exists())

    def test_hard_block_never_prompts(self):
        def unexpected_prompt(*_):
            self.fail("A hard block must not prompt")
        result = delete_fixture(POLICY, self.root, PROTECTED, unexpected_prompt)
        self.assertEqual(result["decision"], "BLOCK")
        self.assertTrue((self.root / PROTECTED).exists())

    def test_changed_target_cancels_approval(self):
        target = self.root / RESOURCE
        def change_target(*_):
            target.write_text("replacement content", encoding="utf-8")
            return True
        self.assertFalse(delete_fixture(POLICY, self.root, RESOURCE, change_target)["executed"])
        self.assertEqual(target.read_text(encoding="utf-8"), "replacement content")

    def test_changed_policy_cancels_approval(self):
        local_policy = self.root / "policy.md"
        local_policy.write_text(POLICY.read_text(encoding="utf-8"), encoding="utf-8")

        def change_policy(*_):
            new_policy = local_policy.read_text(encoding="utf-8").replace("REQUIRE_APPROVAL", "BLOCK")
            local_policy.write_text(new_policy, encoding="utf-8")
            return True

        self.assertFalse(delete_fixture(local_policy, self.root, RESOURCE, change_policy)["executed"])
        self.assertTrue((self.root / RESOURCE).exists())

    def test_timeout_and_failed_process_cannot_approve(self):
        evaluation = evaluate_action(POLICY, "file.delete", RESOURCE)
        with patch("trustlayer.approval.subprocess.run", side_effect=subprocess.TimeoutExpired("dialog", 1)):
            self.assertFalse(request_approval(evaluation, self.root / RESOURCE))
        with patch("trustlayer.approval.subprocess.run", return_value=subprocess.CompletedProcess([], 1, "approved")):
            self.assertFalse(request_approval(evaluation, self.root / RESOURCE))
