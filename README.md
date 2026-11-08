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

The standalone MCP server and CLI support file snapshots, optional SSH relay, and optional one-shot advisory sessions. They require Python 3.10 or newer. Git is required when sending tracked files. These PowerShell examples register the server for all projects with a shared channel. On macOS or Linux, use the corresponding shell and interpreter path.

```powershell
$bridge = (Resolve-Path ./plugin/bridge.py).Path
$channel = Join-Path $HOME '.agent-bridge/channel'
codex mcp add agent_bridge -- python $bridge --agent codex --channel-dir $channel serve
agy mcp add agent_bridge -- python $bridge --agent antigravity --channel-dir $channel serve
```

Use the Claude Code plugin for text messages, or register the standalone profile for Claude Code if you need files or dispatch. Use one active profile for Claude in each chat.

```powershell
claude mcp add --scope user --transport stdio agent_bridge -- python $bridge --agent claude --channel-dir $channel serve
```

Start a fresh session after registration. Ask an agent to send a short question or check its inbox. To attach a tracked file, name the exact workspace-relative path and explicitly approve sending it. Use a fixed `--workspace` if the client starts the MCP server outside the intended checkout.

For unattended advisory replies, add `--enable-dispatch` before `serve` in the sender's standalone profile. The target CLI must be installed and signed in on the mailbox host. A dispatch starts a separate CLI session in a temporary workspace. It passes the selected message and eligible UTF-8 file snapshots to the selected model provider. Each message can start one session with a 240-second deadline. CLI dispatch and interactive IDE conversations use separate sessions.

For a mailbox on another machine, run the standalone bridge on a trusted SSH host with a local mailbox directory. Configure each client with `--ssh-host HOST --remote-command 'python3 /path/to/bridge.py --agent ROLE --channel-dir /path/to/channel --accept-relay serve' serve` in place of its local channel and `serve` arguments. Use the same role at both ends and verify the host key in advance. Real multi-host operation has not been verified for this release draft.

## Claude Desktop package

```powershell
python desktop/package_bridge.py --out dist/AgentBridge-0.1.0.mcpb
```

Install the `.mcpb` through Claude Desktop's extension settings. Set the Python executable, shared mailbox and attachment workspace. This package uses the full bridge and enables on-demand dispatch in its profile. Remove the extension to revoke that profile's access. The Claude Code directory plugin has a separate text-only entry point.

## Local verification

```powershell
claude plugin validate --strict ./plugin
$env:PYTHONPATH = (Resolve-Path ./plugin).Path
python -m unittest discover -s tests -v
```

Windows is the tested platform for this release draft. See [data handling](plugin/PRIVACY.md) for storage and removal details. Report installation issues through this repository's Issues tab and include a version and reproduction steps without mailbox content.
