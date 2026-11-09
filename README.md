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

To allow a sender to create IDE delivery records, add `--enable-dispatch` before `serve` in its standalone profile. By default, `dispatch` queues the request for the recipient's IDE extension; it does not launch an agent. For an isolated advisory CLI session, pass `--surface headless` to `dispatch`. The target CLI must be installed and signed in on the mailbox host; the worker uses a temporary workspace and a 240-second deadline. A headless reply can include up to 256 KiB of UTF-8 attachments in total; larger snapshots remain in the mailbox for the recipient to open in its IDE.

For repository-scoped work in IDE chats, install the [Agent Bridge IDE extension](ide-extension/README.md) in each participating IDE. It supports a shared repository key for local and cloud workspaces, an inbox with replies, and adapters for Antigravity, Codex, and Claude Code. Claude Code pre-fills a chat but requires the user to press Enter; Codex opens its chat and copies the prompt because its public extension API does not expose composer submission. Antigravity's chat command remains undocumented and must be verified in the installed IDE. The CLI's `dispatch` queues to IDE by default; use `--surface headless` only for an isolated advisory CLI session. See [publishing instructions](ide-extension/PUBLISHING.md) for the VS Code Marketplace and Open VSX setup.

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
