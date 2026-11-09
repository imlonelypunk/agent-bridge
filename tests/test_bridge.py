import hashlib
import json
from contextlib import closing
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

import bridge
import bridge_runner


class BridgeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.workspace = self.base / "workspace"
        self.workspace.mkdir()
        self.channel = self.base / "coordinator"
        self.script = Path(bridge.__file__)
        self.file = self.workspace / "packet.bin"
        self.file.write_bytes(b"\x00\xff\x01")
        for arguments in (("init", "-q"), ("add", "packet.bin")):
            self.assertEqual(bridge.git(self.workspace, *arguments).returncode, 0)

    def command(self, agent, *extra):
        return [
            sys.executable, str(self.script), "--agent", agent, "--workspace", str(self.workspace),
            "--channel-dir", str(self.channel), *extra,
        ]

    def cli(self, agent, *args, **kwargs):
        result = subprocess.run(
            [*self.command(agent), *args], capture_output=True, timeout=15, check=False, **kwargs,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))
        return json.loads(result.stdout)

    def profile(self, agent):
        return bridge.Mailbox(self.workspace, agent, self.channel)

    def test_ide_claim_is_scoped_unique_and_waits_for_reply(self):
        sender = self.profile("codex")
        recipient = self.profile("antigravity")
        first = sender.call("send", {"to": "antigravity", "kind": "question", "body": "First"})
        second = sender.call("send", {"to": "antigravity", "kind": "request", "body": "Second"})
        key = bridge.repository_id_for_workspace(self.workspace)
        args = {"message_id": first["message_id"], "repository_id": key}
        with self.assertRaises(bridge.BridgeError):
            recipient.call("claim_ide", {**args, "repository_id": "other"})
        self.assertTrue(recipient.call("claim_ide", args)["claimed"])
        self.assertFalse(recipient.call("claim_ide", args)["claimed"])
        second_args = {"message_id": second["message_id"], "repository_id": key}
        self.assertFalse(recipient.call("claim_ide", second_args)["claimed"])
        reply = recipient.call("reply", {"message_id": first["message_id"], "body": "Done"})
        reply_args = {"message_id": reply["message_id"], "repository_id": key}
        self.assertTrue(sender.call("claim_ide", reply_args)["claimed"])
        self.assertFalse(sender.call("claim_ide", reply_args)["claimed"])
        self.assertFalse(recipient.call("claim_ide", args)["claimed"])
        self.assertTrue(recipient.call("claim_ide", second_args)["claimed"])

    def test_repository_key_cli_matches_routed_message_with_and_without_origin(self):
        for remote in (None, "https://github.com/Example/Repo.git"):
            if remote:
                self.assertEqual(bridge.git(self.workspace, "remote", "add", "origin", remote).returncode, 0)
            key = self.cli("codex", "repository-key")["repository_id"]
            sent = self.cli("codex", "send", "--to", "claude", "--kind", "request", "--body", "route check")
            message = self.cli("claude", "read", "--message-id", sent["message_id"])
            self.assertEqual(message["repository_id"], key)

    def test_cross_machine_protocol_returns_local_snapshot(self):
        def client(agent):
            return bridge.RelayClient(
                self.workspace, agent, self.base / f"cache-{agent}",
                self.command(agent, "--accept-relay", "serve"),
            )

        codex, claude, antigravity = (client(agent) for agent in bridge.AGENTS)
        sent = codex.call("send", {
            "to": "claude", "kind": "question", "body": "Що у файлі?",
            "files": ["packet.bin"], "request_id": "fixture-1",
        })
        message_id = sent["message_id"]
        self.assertEqual(claude.call("inbox", {})["messages"][0]["id"], message_id)
        with self.assertRaisesRegex(bridge.BridgeError, "message not found"):
            antigravity.call("read", {"message_id": message_id})
        self.file.write_bytes(b"edited")
        item = claude.call("read", {"message_id": message_id})
        snapshot = item["attachments"][0]
        self.assertEqual(item["body"], "Що у файлі?")
        self.assertEqual(Path(snapshot["path"]).read_bytes(), b"\x00\xff\x01")
        self.assertTrue(Path(snapshot["path"]).is_relative_to(self.base / "cache-claude"))
        self.assertEqual(snapshot["sha256"], hashlib.sha256(b"\x00\xff\x01").hexdigest())
        reply = claude.call("reply", {"message_id": message_id, "body": "Три байти."})
        self.assertEqual(codex.call("inbox", {})["messages"][0]["id"], reply["message_id"])
        claude.call("ack", {"message_id": message_id})
        self.assertEqual(claude.call("inbox", {})["messages"], [])

    def test_handoff_checks_kinesis_board_in_portable_profile(self):
        board = self.workspace / ".agents" / "BOARD.md"
        board.parent.mkdir()
        board.write_text(
            "# Kinesis — Team Board\n- [ ] FIX-1 Inspect → **TODO → @antigravity**\n",
            encoding="utf-8",
        )
        request = {"to": "antigravity", "kind": "handoff", "body": "Inspect", "task_id": "FIX-1"}
        with self.assertRaisesRegex(bridge.BridgeError, "Codex must supply"):
            self.profile("claude").call("send", request)
        with self.assertRaisesRegex(bridge.BridgeError, "not currently routed"):
            self.profile("codex").call("send", {**request, "to": "claude"})
        sent = self.profile("codex").call("send", request)
        self.assertEqual(self.profile("antigravity").call("inbox", {})["messages"][0]["id"],
                         sent["message_id"])

    def test_retry_and_invalid_attachment_leave_consistent_inbox(self):
        sender = self.profile("codex")
        args = {"to": "claude", "kind": "question", "body": "Check", "request_id": "same"}
        sent = sender.call("send", args)
        self.assertEqual(sender.call("send", args), sent)
        with self.assertRaisesRegex(bridge.BridgeError, "different message"):
            sender.call("send", {**args, "body": "Different"})
        for filename in ("../outside.txt", ".git/config", "private.txt", "packet.bin:stream"):
            with self.subTest(filename=filename), self.assertRaises(bridge.BridgeError):
                sender.call("send", {**args, "request_id": "unsafe", "files": [filename]})
        self.assertEqual(len(self.profile("claude").call("inbox", {})["messages"]), 1)

    def test_repository_scoped_ide_dispatch_ack_reply_and_idempotency(self):
        repository_id = "team:project-victoria3"
        sender = self.profile("codex")
        recipient = self.profile("claude")
        sent = sender.call("send", {
            "to": "claude", "kind": "request", "body": "Review this repository.",
            "request_id": "ide-route-1", "repository_id": repository_id,
        })
        message_id = sent["message_id"]
        with closing(sender.connect()) as db, db:
            legacy = sender.enqueue(
                db, "claude", "request", "Legacy message without a route.",
                None, None, (), None, repository_id=None,
            )
        dispatched = self.cli(
            "codex", "--enable-dispatch", "dispatch", "--message-id", message_id,
        )
        self.assertEqual(dispatched["state"], "queued_for_ide")
        repeated = self.cli(
            "codex", "--enable-dispatch", "dispatch", "--message-id", message_id,
        )
        self.assertEqual(repeated, dispatched)

        self.assertEqual(recipient.call("inbox", {"repository_id": "team:other"})["messages"], [])
        routed = recipient.call("inbox", {"repository_id": repository_id})["messages"]
        self.assertEqual([item["id"] for item in routed], [message_id])
        with self.assertRaisesRegex(bridge.BridgeError, "does not belong to this repository"):
            recipient.call("read", {"message_id": legacy["message_id"], "repository_id": repository_id})
        with self.assertRaisesRegex(bridge.BridgeError, "does not belong to this repository"):
            recipient.call("ack", {"message_id": legacy["message_id"], "repository_id": repository_id})
        incoming = recipient.call("read", {"message_id": message_id})
        self.assertEqual(incoming["repository_id"], repository_id)
        recipient.call("ack", {"message_id": message_id})
        self.assertEqual(sender.call("dispatch_status", {"message_id": message_id})["state"], "opened")

        reply = recipient.call("reply", {"message_id": message_id, "body": "Review complete."})
        status = sender.call("dispatch_status", {"message_id": message_id})
        self.assertEqual((status["state"], status["reply_id"]), ("replied", reply["message_id"]))
        reply_message = sender.call("read", {"message_id": reply["message_id"]})
        self.assertEqual((reply_message["repository_id"], reply_message["body"]),
                         (repository_id, "Review complete."))

    def test_repository_key_uses_git_origin_or_local_root(self):
        root = self.workspace
        local = bridge.repository_id_for_workspace(root)
        bridge.git(root, "remote", "add", "origin", "git@github.com:Example/Project.git")
        ssh = bridge.repository_id_for_workspace(root)
        bridge.git(root, "remote", "set-url", "origin", "https://github.com/example/project.git")
        https = bridge.repository_id_for_workspace(root)
        self.assertEqual(ssh, https)
        self.assertTrue(ssh.startswith("git:"))
        bridge.git(root, "remote", "remove", "origin")
        self.assertEqual(bridge.repository_id_for_workspace(root), local)

    def test_repository_normalization_matches_shared_vectors(self):
        vectors = json.loads((Path(__file__).parent / "repository_keys.json").read_text(encoding="utf-8"))
        for vector in vectors:
            with self.subTest(remote=vector["remote"]):
                self.assertEqual(bridge.normalized_repository(vector["remote"]), vector["normalized"])

    def test_late_reply_updates_an_expired_ide_dispatch(self):
        sender = self.profile("codex")
        recipient = self.profile("claude")
        sent = sender.call("send", {
            "to": "claude", "kind": "request", "body": "Reply after expiry.",
            "repository_id": "team:late-reply",
        })
        message_id = sent["message_id"]
        self.cli("codex", "--enable-dispatch", "dispatch", "--message-id", message_id)
        with closing(sender.connect()) as db, db:
            db.execute("UPDATE runs SET deadline = ? WHERE message_id = ?", (time.time() - 1, message_id))
        self.assertEqual(sender.call("dispatch_status", {"message_id": message_id})["state"], "expired")
        reply = recipient.call("reply", {"message_id": message_id, "body": "Late but delivered."})
        status = sender.call("dispatch_status", {"message_id": message_id})
        self.assertEqual((status["state"], status["reply_id"]), ("replied", reply["message_id"]))

    def test_stdio_handshake_and_tool_calls(self):
        def request(method, number, params):
            return json.dumps({"jsonrpc": "2.0", "id": number, "method": method, "params": params})
        input_text = "\n".join([
            request("initialize", 1, {"protocolVersion": "2025-06-18"}),
            '{"jsonrpc":"2.0","method":"notifications/initialized"}',
            request("tools/list", 2, {}),
            request("tools/call", 3, {"name": "inbox", "arguments": {}}),
            request("tools/call", 4, {"name": [], "arguments": {}}),
        ]) + "\n"
        result = subprocess.run(
            self.command("codex", "serve"), input=input_text.encode(), capture_output=True,
            timeout=15, check=True,
        )
        initialized, tools, inbox, malformed = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(initialized["result"]["protocolVersion"], "2025-06-18")
        self.assertEqual({entry["name"] for entry in tools["result"]["tools"]}, bridge.TOOLS.keys())
        self.assertEqual(json.loads(inbox["result"]["content"][0]["text"])["messages"], [])
        self.assertTrue(malformed["result"]["isError"])

    def test_detached_dispatch_and_no_duplicate_launch(self):
        bundle = self.base / "app"
        bundle.mkdir()
        (bundle / "plugin").mkdir()
        for name in ("__init__.py", "mailbox_server.py"):
            shutil.copy2(self.script.parent / "plugin" / name, bundle / "plugin")
        self.script = Path(shutil.copy2(self.script, bundle))
        (bundle / "bridge_runner.py").write_text(
            "TIMEOUT = 2\nNO_WINDOW = 0\n"
            "class RunError(ValueError): pass\n"
            "def executable(agent, store): return agent\n"
            "def prompt_for(message, files): return message['body']\n"
            "def run(agent, binary, prompt, log):\n"
            "    if prompt == 'fail': raise RunError('fixture auth error')\n"
            "    return 'Answer from ' + agent, 'fixture-session'\n",
            encoding="utf-8",
        )
        for sender, target, prompt in (
            ("antigravity", "codex", "answer"), ("codex", "claude", "answer"),
            ("claude", "antigravity", "answer"), ("codex", "claude", "fail"),
        ):
            with self.subTest(sender=sender, target=target, prompt=prompt):
                sent = self.cli(sender, "send", "--to", target, "--kind", "question", "--body", prompt)
                message_id = sent["message_id"]
                run = self.cli(sender, "--enable-dispatch", "dispatch", "--message-id", message_id,
                               "--surface", "headless")
                self.assertEqual(run["state"], "scheduled")
                for _ in range(50):
                    run = self.cli(sender, "dispatch_status", "--message-id", message_id)
                    if run["state"] not in ("scheduled", "running"):
                        break
                    time.sleep(0.05)
                repeat = self.cli(sender, "--enable-dispatch", "dispatch", "--message-id", message_id,
                                  "--surface", "headless")
                self.assertEqual(run, repeat)
                if prompt == "fail":
                    self.assertEqual((run["state"], run["detail"]), ("failed", "fixture auth error"))
                else:
                    self.assertEqual(run["state"], "replied")
                    reply = self.cli(sender, "read", "--message-id", run["reply_id"])
                    self.assertEqual((reply["reply_to"], reply["body"]),
                                     (message_id, "Answer from " + target))

    def test_cli_output_parsers(self):
        for agent, payload in (
            ("codex", b'{"type":"thread.started","thread_id":"id"}\n'
             b'{"type":"item.completed","item":{"type":"agent_message","text":"yes"}}\n'
             b'{"type":"turn.completed"}\n'),
            ("claude", b'{"subtype":"success","is_error":false,"result":"yes","session_id":"id"}'),
            ("antigravity", b'{"event":"result","result":{"status":"SUCCESS","response":"yes",'
             b'"conversation_id":"id"}}\n'),
        ):
            with self.subTest(agent=agent):
                self.assertEqual(bridge_runner.response_from(agent, payload), ("yes", "id"))

    def test_headless_prompt_accepts_256_kib_total_utf8_attachments(self):
        message = {
            "id": "request-1", "sender": "codex", "recipient": "claude",
            "kind": "request", "task_id": None, "body": "Review the attached source.",
        }
        half = bridge_runner.MAX_CONTEXT // 2
        exact_limit = [
            {"name": "first.py", "data": b"a" * half},
            {"name": "second.py", "data": b"b" * half},
        ]
        prompt = bridge_runner.prompt_for(message, exact_limit)
        self.assertIn('"name": "first.py"', prompt)
        self.assertIn('"name": "second.py"', prompt)

        over_limit = [{"name": "large.py", "data": b"a" * (bridge_runner.MAX_CONTEXT + 1)}]
        with self.assertRaisesRegex(bridge_runner.RunError, "256 KiB"):
            bridge_runner.prompt_for(message, over_limit)

    def test_antigravity_dispatch_rejects_hooks(self):
        home = self.base / "profile"
        plugin = home / ".gemini" / "config" / "plugins" / "plugin"
        plugin.mkdir(parents=True)
        bridge_runner.check_antigravity_hooks(home)
        hook = plugin / "hooks.json"
        hook.write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(bridge_runner.RunError, "without global or plugin hooks"):
            bridge_runner.check_antigravity_hooks(home)
        hook.unlink()
        manifest = plugin.parent.parent / "plugins.json"
        manifest.write_text("{}", encoding="utf-8")
        with self.assertRaises(bridge_runner.RunError):
            bridge_runner.check_antigravity_hooks(home)
        manifest.unlink()
        (plugin.parent.parent / "hooks.json").write_text("{}", encoding="utf-8")
        with self.assertRaises(bridge_runner.RunError):
            bridge_runner.check_antigravity_hooks(home)

    def test_dispatch_rejects_project_temporary_directory(self):
        scratch = self.workspace / "temp" / "session"
        scratch.mkdir(parents=True)
        with self.assertRaisesRegex(bridge_runner.RunError, "outside project"):
            bridge_runner.check_isolated_workspace(scratch)


if __name__ == "__main__":
    unittest.main()
