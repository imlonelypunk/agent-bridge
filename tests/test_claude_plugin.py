import json
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from plugin.mailbox_server import TextMailbox, BridgeError as PluginBridgeError, repository_id_for_workspace

import bridge


PLUGIN = Path(bridge.__file__).resolve().parent / "plugin"


class ClaudePluginTests(unittest.TestCase):
    def test_text_plugin_waits_for_full_bridge_reply(self):
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "repo"
            workspace.mkdir()
            channel = Path(tmp) / "channel"
            plugin = TextMailbox("claude", channel)
            other = bridge.Mailbox(workspace, "antigravity", channel)
            request = plugin.call("send", {"to": "antigravity", "kind": "question", "body": "Check"})
            reply = other.call("reply", {"message_id": request["message_id"], "body": "Готово"})
            result = plugin.call("wait_reply", {"message_id": request["message_id"], "timeout_seconds": 1})
            self.assertEqual(result["reply"]["id"], reply["message_id"])
            self.assertEqual(result["reply"]["body"], "Готово")

    def test_repository_key_matches_shared_vectors(self):
        vectors = json.loads((PLUGIN.parent / "tests" / "repository_keys.json").read_text(encoding="utf-8"))
        for vector in vectors:
            remote = vector["remote"]
            if vector["normalized"] is None:
                continue
            result = SimpleNamespace(returncode=0, stdout=remote.encode("utf-8"))
            with self.subTest(remote=remote), patch("plugin.mailbox_server.subprocess.run", return_value=result):
                expected = "git:" + hashlib.sha256(vector["normalized"].encode("utf-8")).hexdigest()
                self.assertEqual(repository_id_for_workspace(Path.cwd()), expected)
                self.assertEqual(bridge.repository_id_from_remote(remote), expected)

    def test_repository_scoped_interoperation_and_legacy_access(self):
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "repo"
            workspace.mkdir()
            subprocess.run(["git", "init", "-q", str(workspace)], check=True)
            subprocess.run(["git", "-C", str(workspace), "remote", "add", "origin",
                            "https://github.com/Example/Project.git"], check=True)
            channel = Path(tmp) / "channel"
            plugin = TextMailbox("claude", channel)
            codex = bridge.Mailbox(workspace, "codex", channel)
            route = bridge.repository_id_for_workspace(workspace)
            with patch("plugin.mailbox_server.Path.cwd", return_value=workspace):
                sent = plugin.call("send", {"to": "codex", "kind": "request", "body": "Route me", "request_id": "route-1"})
            self.assertEqual(sent["repository_id"], route)
            self.assertEqual(codex.call("inbox", {"repository_id": route})["messages"][0]["id"], sent["message_id"])
            with self.assertRaises(PluginBridgeError):
                plugin.call("send", {"to": "codex", "kind": "request", "body": "Route me", "request_id": "route-1", "repository_id": "other"})
            incoming = codex.call("send", {"to": "claude", "kind": "request", "body": "Hello", "repository_id": route})
            mid = incoming["message_id"]
            self.assertEqual(plugin.call("inbox", {"repository_id": route})["messages"][0]["id"], mid)
            self.assertEqual(plugin.call("inbox", {"repository_id": "other"})["messages"], [])
            for operation in ("read", "ack"):
                with self.assertRaises(PluginBridgeError):
                    plugin.call(operation, {"message_id": mid, "repository_id": "other"})
            codex.dispatch_enabled = True
            codex.call("dispatch", {"message_id": mid, "surface": "ide"})
            self.assertTrue(plugin.call("ack", {"message_id": mid, "repository_id": route})["acknowledged"])
            self.assertEqual(codex.call("dispatch_status", {"message_id": mid})["state"], "opened")
            reply = plugin.call("reply", {"message_id": mid, "body": "Reply"})
            self.assertEqual(reply["repository_id"], route)
            self.assertEqual(codex.call("read", {"message_id": reply["message_id"], "repository_id": route})["body"], "Reply")
            self.assertEqual(codex.call("dispatch_status", {"message_id": mid})["state"], "replied")
            # Messages from older clients without a route remain accessible without a filter.
            from contextlib import closing
            with closing(plugin.connect()) as db, db:
                legacy_id, request = plugin.prepare_message(db, "claude", "note", "legacy", None, None, None)
                plugin.insert_message(db, legacy_id, "claude", "note", "legacy", None, None, None, request)
            self.assertEqual(plugin.call("read", {"message_id": legacy_id})["body"], "legacy")
            self.assertIn(legacy_id, [m["id"] for m in plugin.call("inbox", {})["messages"]])
            self.assertNotIn(legacy_id, [m["id"] for m in plugin.call("inbox", {"repository_id": route})["messages"]])
            with closing(plugin.connect()) as db, db:
                old_id, request = plugin.prepare_message(db, "codex", "note", "retry", None, None, "old-retry")
                plugin.insert_message(db, old_id, "codex", "note", "retry", None, None, "old-retry", request)
            migrated = plugin.call("send", {"to": "codex", "kind": "note", "body": "retry", "request_id": "old-retry", "repository_id": route})
            self.assertEqual((migrated["message_id"], migrated["repository_id"]), (old_id, route))

    def test_manifest_entry_round_trip_and_text_only_contract(self):
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            channel = workspace / "channel"
            installed = workspace / "installed-plugin"
            shutil.copytree(PLUGIN, installed, ignore=shutil.ignore_patterns("__pycache__"))
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
            send = {"to": "codex", "kind": "note", "body": "Hello", "request_id": "text-retry"}
            prior = bridge.Mailbox(workspace, "claude", channel).call("send", send)
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

            manifest = json.loads((installed / ".mcp.json").read_text(encoding="utf-8"))
            config = manifest["mcpServers"]["mailbox"]
            self.assertEqual(config["command"], "python")
            args = [arg.replace("${CLAUDE_PLUGIN_ROOT}", str(installed)) for arg in config["args"]]
            result = subprocess.run(
                [sys.executable, *args], cwd=workspace,
                env={**os.environ, "AGENT_BRIDGE_CHANNEL": str(channel), "PYTHONPATH": ""},
                input="".join(json.dumps({"jsonrpc": "2.0", "id": idx, "method": method, "params": params})
                              + "\n" for idx, (method, params) in enumerate(requests)),
                text=True, encoding="utf-8", capture_output=True, timeout=15,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            responses = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual([r["id"] for r in responses], list(range(len(requests))))
            self.assertEqual(responses[0]["result"]["serverInfo"]["name"], "agent-bridge")
            self.assertEqual(responses[0]["result"]["serverInfo"]["version"], "0.1.5")
            tools = {t["name"]: t for t in responses[1]["result"]["tools"]}
            self.assertEqual(set(tools), {"send", "inbox", "read", "reply", "ack", "wait_reply", "wait_inbox"})
            self.assertTrue(tools["wait_inbox"]["annotations"]["readOnlyHint"])
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
            self.assertEqual(payload(13)["message_id"], prior["message_id"])
            self.assertIsNotNone(payload(13)["repository_id"])
            self.assertEqual(codex.call("read", {"message_id": prior["message_id"]})["body"], "Hello")
            self.assertFalse((channel / "runs").exists())
