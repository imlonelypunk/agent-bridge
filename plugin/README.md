# Agent Bridge for Claude Code

Send text messages to Codex and Antigravity from Claude Code using a shared local mailbox. Each agent runs in its own session and reads the same mailbox directory. Start or switch to the recipient's session to read the message and reply.

## Try it locally

Install Python 3.10 or newer and check that `python --version` works in the environment that starts Claude Code. Launch Claude Code with the plugin directory.

```powershell
claude --plugin-dir ./plugin
```

Point at least one peer at the same `~/.agent-bridge/channel` mailbox. The [standalone installation instructions](https://github.com/imlonelypunk/agent-bridge#full-bridge) show the Codex and Antigravity setup. To use another trusted local directory, set `AGENT_BRIDGE_CHANNEL` to its absolute path in Claude Code's environment and use the same directory for each peer. Use one mailbox you control. Role names route messages and do not authenticate participants.

## Repository routing

For each new outgoing message, the plugin resolves the repository from the Claude Code MCP server’s working directory. Agent Bridge derives a routing key from the Git origin, or from the local workspace path if there is no usable origin. The IDE extension and full bridge use the same key. Git is needed to detect an origin; without Git, the local path key may not match peers using an origin. Restart the Claude Code session in the intended workspace when switching repositories.

For cloud workspaces or repositories with different remotes, give the `repository_id` argument the same stable alias configured as `agentBridge.repositoryId` in the recipient IDE. You can pass that key to `inbox`, `read`, and `ack` to restrict those operations; without it, the inbox includes messages across repositories and older unscoped messages. Replies inherit the original message's repository key. Send and reply results report the resulting `repository_id`. Retrying an older unscoped send with the same request ID assigns the current route to that existing message. The key is routing metadata, not a security boundary or participant authentication.

## Example prompts

- “Send Codex this question through Agent Bridge. Does the API need a retry key?”
- “Check my Agent Bridge inbox for repository key `team/project` and show me the newest message.”
- “Reply to Antigravity's message with ‘I reproduced the failure on Windows.’”

The plugin exposes five text operations. Use it to send, list, read, reply and acknowledge. This profile has no attachment access, CLI dispatch or SSH tools. Acknowledging a message hides it from the default pending view and preserves it in the mailbox.

The plugin also includes the `agent-bridge` skill with instructions for coordinating messages and replies. Ask Claude to use Agent Bridge when contacting another agent. The skill does not add attachment or dispatch capabilities to this text-only profile.

If the plugin does not connect, confirm that Claude Code can find `python`. If peers see different messages, check that their channel paths match and point to a directory they can read and write. Windows is the tested platform for this release draft.

See [data handling](PRIVACY.md) and the [MIT License](LICENSE). For support, open an issue in the Agent Bridge repository with your plugin version, platform and steps to reproduce. Keep private messages, files and credentials out of issue reports.
