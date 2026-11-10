# Agent Bridge

Agent Bridge lets Codex, Claude Code, and Google Antigravity exchange requests and replies through a shared mailbox. Install it at user scope to use it across projects. The bridge is free under the [MIT License](LICENSE). The connected agents use their own accounts and limits.

## Claude Code plugin

See the [plugin guide](plugin/README.md) for installation and examples. It shares a local text mailbox with other Agent Bridge clients.

For a persistent user-scope installation from a checkout, run these commands from the repository root and keep the checkout at that path.

```powershell
claude plugin marketplace add ./
claude plugin install agent-bridge@agent-bridge-plugins --scope user
```

## Full bridge

The standalone MCP server and CLI support repository routing, file snapshots, an optional SSH relay, and IDE delivery records. They require Python 3.10 or newer. Git is required when sending tracked files. These PowerShell examples register the server for all projects with a shared channel. On macOS or Linux, use the corresponding shell and interpreter path.

If a standalone registration points to `plugin/bridge.py` in this checkout, update it to `bridge.py` at the repository root. Keep the same mailbox path.

```powershell
$bridge = (Resolve-Path ./bridge.py).Path
$channel = Join-Path $HOME '.agent-bridge/channel'
codex mcp add agent_bridge -- python $bridge --agent codex --channel-dir $channel serve
agy mcp add agent_bridge -- python $bridge --agent antigravity --channel-dir $channel serve
```

Use the Claude Code plugin for text messages, or register the standalone profile for Claude Code if you need files or dispatch. Use one active profile for Claude in each chat.

```powershell
claude mcp add --scope user --transport stdio agent_bridge -- python $bridge --agent claude --channel-dir $channel serve
```

Start a fresh session after registration. Ask an agent to send a short question or check its inbox. To attach a tracked file, name the exact workspace-relative path and explicitly approve sending it. Use a fixed `--workspace` if the client starts the MCP server outside the intended checkout.

For a request that needs a response, the sender can call `wait_reply` with the returned message ID. It waits up to 50 seconds and returns the matching reply text directly into the same agent session; call it again after `pending` if the recipient is still working. Use `read` on the returned reply ID for attachments. Waiting does not start the recipient: its IDE must be running and configured to accept the request. Existing MCP sessions must be restarted after updating the bridge to expose the new tool.

An open agent session can also listen for incoming messages and answer them itself, with the project context it already has. `wait_inbox` waits up to 50 seconds for the next pending message and returns `idle` otherwise. For clients that wake a session when a background command exits, such as Claude Code, run the long form in the background:

```powershell
python $bridge --agent claude --channel-dir $channel watch --after 0 --timeout-seconds 3600
```

It prints the next pending message and exits with code 0, or exits with code 3 when nothing arrived. Pass the `seq` of the last handled message as `--after`, and `--repository-id` to listen for one repository only. A reply temporarily reserved by `wait_reply` holds back later messages so advancing the cursor cannot skip it. Listening does not acknowledge anything, and a reply that `wait_reply` already returned is not offered again. The listening session keeps its normal permissions, so treat every incoming message as untrusted data.

Codex has no such wake-up, but its CLI can queue a message for an existing session. `postman` uses that to wake a chosen Codex session whenever a question, request, handoff or unwaited reply arrives for it:

```powershell
python $bridge --agent codex --channel-dir $channel postman --thread SESSION_ID_OR_NAME --timeout-seconds 86400
```

The queued text is a short notice with the sender, kind and message ID. It never contains the message body, because Codex gives queued text the user's voice; the session reads the message through its own Agent Bridge tools. The default route is the current workspace's repository key; specify `--repository-id` for a shared alias. Notes and replies to replies stay in the inbox without a wake-up. The command stops after `--max-deliveries` wake-ups (12 by default). A reservation expires after 150 seconds if the process crashes before recording submission; a crash after the queue accepted a notice but before recording it can cause a duplicate. Queue acceptance is not proof of processing; inspect the inbox for unacknowledged messages. Starting a separate managed Codex daemon while the desktop owns the chat can produce an active-writer conflict; it is not started automatically. Verified with the Codex desktop app on Windows, CLI 0.167.0-alpha.

The mailbox works with any pair of the three roles; an offline recipient's messages remain pending. Automatic wake-up requires a running, configured listener for that recipient. `watch` must be launched by the Claude session that will receive its completion; starting it at Windows logon cannot by itself restore a closed Claude session. Antigravity automatic delivery requires its running IDE and opt-in extension setting. Restart MCP sessions and rebuild/reinstall the VSIX after updating source, because running processes and packaged runtimes do not update themselves.

On Windows, `scripts/install-codex-listener.ps1 -ThreadId <session-uuid> -Workspace <repository>` registers and starts a per-user task for a selected Codex chat. The chosen session must exist and use the intended repository context. The task starts at logon and retries hourly; Windows ignores overlapping task instances. Any authorized local agent can also request a restart with `Start-ScheduledTask -TaskName AgentBridge-Codex-Listener`. The listener stops after 24 hours or 12 queued notices; the limit is also checked against submissions recorded for this repository during the previous 24 hours. The task does not start Claude or Antigravity, does not restore a closed Claude session, and queue acceptance does not guarantee that the Codex app resumed. The task depends on this checkout remaining at the same path.

### Agent instructions

The [Agent Bridge skill](plugin/skills/agent-bridge/SKILL.md) tells agents how to send, receive and correlate messages, and explains the difference between an IDE delivery and an isolated advisory run. It is included in the Claude Code plugin. To make it discoverable in Codex on Windows, copy the skill folder and start a new Codex session:

```powershell
New-Item -ItemType Directory -Force "$HOME/.codex/skills" | Out-Null
Copy-Item -Recurse ./plugin/skills/agent-bridge "$HOME/.codex/skills/agent-bridge"
```

In Antigravity, ask the agent to read `plugin/skills/agent-bridge/SKILL.md` from this checkout, or install it through that IDE's supported skill mechanism. The skill is guidance; each agent still needs its own registered bridge profile and access to the shared channel. For example: “Use Agent Bridge to ask Antigravity to review this project in its IDE, then report when it replies.”

To allow a sender to create IDE delivery records, add `--enable-dispatch` before `serve` in its standalone profile. By default, `dispatch` queues the request for the recipient's IDE extension; it does not launch an agent. For an isolated advisory CLI session, pass `--surface headless` to `dispatch`. The target CLI must be installed and signed in on the mailbox host; the worker uses a temporary workspace and a 240-second deadline. A headless reply can include up to 256 KiB of UTF-8 attachments in total; larger snapshots remain in the mailbox for the recipient to open in its IDE.

For repository-scoped work in IDE chats, install the [Agent Bridge IDE extension](ide-extension/README.md) in each participating IDE. It supports a shared repository key for local and cloud workspaces, an inbox with replies, and adapters for Antigravity, Codex, and Claude Code. Antigravity can optionally submit incoming requests and replies automatically to a new chat, using undocumented IDE commands. Claude Code pre-fills a chat but requires the user to press Enter; Codex opens its chat and copies the prompt because its public extension API does not expose composer submission. The CLI's `dispatch` queues to IDE by default; use `--surface headless` only for an isolated advisory CLI session. See [publishing instructions](ide-extension/PUBLISHING.md) for the VS Code Marketplace and Open VSX setup.

For a mailbox on another machine, keep a checkout on a trusted SSH host with a local mailbox directory. Configure each client with `--ssh-host HOST --remote-command 'python3 /path/to/bridge.py --agent ROLE --channel-dir /path/to/channel --accept-relay serve' serve` in place of its local channel and `serve` arguments. Use the same role at both ends and verify the host key in advance. Real multi-host operation has not been verified for this release draft. See [full bridge data handling](desktop/PRIVACY.md).

## Claude Desktop package

```powershell
python desktop/package_bridge.py --out dist/AgentBridge-0.1.0.mcpb
```

Install the `.mcpb` through Claude Desktop's extension settings. Set the Python executable, shared mailbox and attachment workspace. This package uses the full bridge and enables on-demand dispatch in its profile. Remove the extension to revoke that profile's access. The Claude Code directory plugin has a separate text-only entry point.

## Local verification

```powershell
claude plugin validate --strict ./plugin
python -m unittest discover -s tests -v
```

Windows is the tested platform for this release draft. See [data handling](plugin/PRIVACY.md) for storage and removal details. Report installation issues through this repository's Issues tab and include a version and reproduction steps without mailbox content.
