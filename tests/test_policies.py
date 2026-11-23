import json
import tempfile
import unittest
from pathlib import Path

from trustlayer.policies import Decision, PolicyError, load_policies, match_policies


class PolicyTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "TRUSTLAYER.md"

    def write_policy(self, rules):
        self.write_block(json.dumps({"version": 1, "rules": rules}))

    def write_block(self, payload):
        self.path.write_text(f"# Policy\n\n```trustlayer\n{payload}\n```\n", encoding="utf-8")

    def test_sample_policy(self):
        rules = load_policies(Path(__file__).resolve().parents[1] / "TRUSTLAYER.md")
        for action, resource, expected in (
            ("file.read", "project/example.txt", Decision.ALLOW),
            ("file.delete", "project/example.txt", Decision.REQUIRE_APPROVAL),
            ("file.delete", "project/uploads/example.txt", Decision.BLOCK),
            ("file.write", "project/example.txt", Decision.BLOCK),
        ):
            with self.subTest(action=action, resource=resource):
                self.assertEqual(match_policies(rules, action, resource)[0], expected)
        self.assertEqual(len(match_policies(rules, "file.delete", "project/uploads/item")[1]), 2)

    def test_edit_changes_same_actions_decision(self):
        rule = {"id": "delete", "action": "file.delete", "resource": "project/*", "decision": "BLOCK"}
        for decision in (Decision.BLOCK, Decision.REQUIRE_APPROVAL, Decision.ALLOW):
            self.write_policy([{**rule, "decision": decision.value}])
            self.assertEqual(match_policies(load_policies(self.path), "file.delete", "project/item")[0], decision)

    def test_precedence_is_independent_of_rule_order(self):
        rules = [
            {"id": decision.value, "action": "*", "resource": "*", "decision": decision.value}
            for decision in Decision
        ]
        self.write_policy(list(reversed(rules)))
        self.assertEqual(match_policies(load_policies(self.path), "file.read", "item")[0], Decision.BLOCK)
        self.write_policy(rules[1:])
        self.assertEqual(match_policies(load_policies(self.path), "file.read", "item")[0], Decision.REQUIRE_APPROVAL)

    def test_invalid_rule_fails_entire_policy(self):
        rule = {"id": "read", "action": "file.read", "resource": "*", "decision": "ALLOW"}
        for invalid in ({"decision": "SKIP"}, {"resource": "project/?"}, {"action": "file.*"}, {"extra": True}):
            with self.subTest(invalid=invalid):
                self.write_policy([rule, {**rule, "id": "invalid", **invalid}])
                with self.assertRaises(PolicyError):
                    load_policies(self.path)
        self.write_policy([rule, rule])
        with self.assertRaisesRegex(PolicyError, "Duplicate rule id"):
            load_policies(self.path)

    def test_rejects_duplicate_keys_missing_and_unreadable_policy(self):
        with self.assertRaises(PolicyError):
            load_policies(self.path)
        self.path.write_text("Allow everything.", encoding="utf-8")
        with self.assertRaises(PolicyError):
            load_policies(self.path)
        self.write_block('{"version": 1, "version": 1, "rules": []}')
        with self.assertRaisesRegex(PolicyError, "Duplicate JSON key"):
            load_policies(self.path)


if __name__ == "__main__":
    unittest.main()
