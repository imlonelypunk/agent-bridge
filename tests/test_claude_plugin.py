import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

import bridge


PLUGIN = Path(bridge.__file__).resolve().parent


class ClaudePluginTests(unittest.TestCase):
    def test_manifest_entry_round_trip_and_text_only_contract(self):
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            channel = workspace / "channel"
            codex = bridge.Mailbox(workspace, "codex", channel)
            message = codex.call("send", {
                "to": "claude", "kind": "question", "body": "Відповіси?",
            }, uploaded=[("private.txt", "unused-by-plugin", b"SYNTHETIC_PRIVATE_FILE")])
            mid = message["message_id"]
            requests = [
                ("initialize", {"protocolVersion": "2025-11-25"}),
                ("tools/list", {}),
                ("tools/call", {"name": "inbox"}),
                ("tools/call", {"name": "read", "arguments": {"message_id": mid}}),
                ("tools/call", {"name": "reply", "arguments": {"message_id": mid, "body": "Так."}}),
                ("tools/call", {"name": "ack", "arguments": {"message_id": mid}}),
                ("tools/call", {"name": "inbox"}),
            ]
            send = {"to": "codex", "kind": "note", "body": "Hello"}
            for name, arguments in (
                ("send", {**send, "files": ["private.txt"]}),
                ("send", {**send, "kind": "handoff", "task_id": "TEST-1"}),
                ("reply", {"message_id": mid, "body": "Extra", "files": ["private.txt"]}),
                ("dispatch", {"message_id": mid}),
                ("dispatch_status", {"message_id": mid}),
            ):
                requests.append(("tools/call", {"name": name, "arguments": arguments}))
            requests.append(("bridge/relay-call", {"name": "read", "arguments": {"message_id": mid}}))
            requests.append(("tools/call", {"name": "send", "arguments": send}))

            manifest = json.loads((PLUGIN / ".mcp.json").read_text(encoding="utf-8"))
            config = manifest["mcpServers"]["mailbox"]
            self.assertEqual(config["command"], "python")
            args = [arg.replace("${CLAUDE_PLUGIN_ROOT}", str(PLUGIN)) for arg in config["args"]]
            result = subprocess.run(
                [sys.executable, *args], cwd=workspace,
                env={**os.environ, "AGENT_BRIDGE_CHANNEL": str(channel)},
                input="".join(json.dumps({"jsonrpc": "2.0", "id": idx, "method": method, "params": params})
                              + "\n" for idx, (method, params) in enumerate(requests)),
                text=True, encoding="utf-8", capture_output=True, timeout=15,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            responses = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual([r["id"] for r in responses], list(range(len(requests))))
            self.assertEqual(responses[0]["result"]["serverInfo"]["name"], "agent-bridge")
            tools = {t["name"]: t for t in responses[1]["result"]["tools"]}
            self.assertEqual(set(tools), {"send", "inbox", "read", "reply", "ack"})
            self.assertNotIn("files", tools["send"]["inputSchema"]["properties"])
            self.assertTrue(tools["read"]["annotations"]["readOnlyHint"])
            self.assertFalse(tools["send"]["annotations"]["openWorldHint"])

            def payload(index):
                return json.loads(responses[index]["result"]["content"][0]["text"])

            self.assertEqual(payload(2)["messages"][0]["id"], mid)
            self.assertEqual(payload(3)["body"], "Відповіси?")
            self.assertNotIn("attachments", payload(3))
            self.assertNotIn("request_json", payload(3))
            self.assertFalse((channel / "received").exists())
            self.assertEqual(codex.call("read", {"message_id": payload(4)["message_id"]})["body"], "Так.")
            self.assertTrue(payload(5)["acknowledged"])
            self.assertEqual(payload(6)["messages"], [])
            for rejected in responses[7:12]:
                self.assertTrue(rejected["result"]["isError"])
            self.assertEqual(responses[12]["error"]["code"], -32601)
            self.assertEqual(codex.call("read", {"message_id": payload(13)["message_id"]})["body"], "Hello")
            self.assertFalse((channel / "runs").exists())
