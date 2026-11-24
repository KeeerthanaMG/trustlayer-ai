import asyncio
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

MCP_AVAILABLE = importlib.util.find_spec("mcp") is not None
if MCP_AVAILABLE:
    from synapse import protected_demo

REPO = Path(__file__).resolve().parents[1]
ACTION = "file.delete"
RESOURCE = "project/example.txt"


@unittest.skipUnless(MCP_AVAILABLE, "Run in the MCP demo environment")
class IntegrationTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.target = self.root / RESOURCE
        self.target.parent.mkdir()
        self.target.write_text("disposable")
        self.audit = self.root / "audit.jsonl"
        config = patch.dict(os.environ, {
            "TRUSTLAYER_POLICY": str(REPO / "TRUSTLAYER.md"),
            "TRUSTLAYER_FIXTURE_ROOT": str(self.root),
            "TRUSTLAYER_AUDIT": str(self.audit),
        })
        config.start()
        self.addCleanup(config.stop)

    def test_unavailable_evaluator_blocks_execution(self):
        with patch.object(protected_demo, "_synapse_call", side_effect=OSError("offline")):
            with patch.object(protected_demo, "request_approval") as approve:
                result = protected_demo.execute(ACTION, RESOURCE)
        approve.assert_not_called()
        self.assertEqual(result["decision"], "BLOCK")
        self.assertFalse(result["executed"])
        self.assertTrue(self.target.exists())
        final = json.loads(self.audit.read_text().splitlines()[-1])
        self.assertEqual(final["decision"], "BLOCK")
        self.assertNotIn(str(self.target), self.audit.read_text())

    def test_decision_for_a_different_resource_is_rejected(self):
        with patch.object(protected_demo, "_synapse_call", return_value={
            "decision": "ALLOW", "action": ACTION, "resource": "project/uploads/example.txt",
        }):
            result = protected_demo.execute(ACTION, RESOURCE)
        self.assertEqual(result["decision"], "BLOCK")
        self.assertTrue(self.target.exists())

    def test_missing_audit_directory_stops_execution_before_evaluation(self):
        with patch.dict(os.environ, {"TRUSTLAYER_AUDIT": str(self.root / "missing/audit.jsonl")}):
            with patch.object(protected_demo, "evaluate_synapse") as evaluate:
                result = protected_demo.execute(ACTION, RESOURCE)
        evaluate.assert_not_called()
        self.assertEqual(result["decision"], "BLOCK")
        self.assertTrue(self.target.exists())

    def test_async_tool_reads_through_real_synapse_mcp(self):
        result = asyncio.run(protected_demo.read_disposable_fixture(RESOURCE))
        self.assertEqual(result["decision"], "ALLOW", result)
        self.assertTrue(result["executed"])
        self.assertEqual(result["bytes_read"], len(b"disposable"))
