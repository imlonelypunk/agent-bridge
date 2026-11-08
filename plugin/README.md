# Agent Bridge for Claude Code

Send text messages to Codex and Antigravity from Claude Code using a shared local mailbox. Each agent runs in its own session and reads the same mailbox directory. Start or switch to the recipient's session to read the message and reply.

## Try it locally

Install Python 3.10 or newer and check that `python --version` works in the environment that starts Claude Code. Launch Claude Code with the plugin directory.

```powershell
claude --plugin-dir ./plugin
```

Point at least one peer at the same `~/.agent-bridge/channel` mailbox. The [standalone installation instructions](../README.md#full-bridge) show the Codex and Antigravity setup. To use another trusted local directory, set `AGENT_BRIDGE_CHANNEL` to its absolute path in Claude Code's environment and use the same directory for each peer. Use one mailbox you control. Role names route messages and do not authenticate participants.

## Example prompts

- “Send Codex this question through Agent Bridge. Does the API need a retry key?”
- “Check my Agent Bridge inbox and show me the newest message.”
- “Reply to Antigravity's message with ‘I reproduced the failure on Windows.’”

The plugin exposes five text operations. Use it to send, list, read, reply and acknowledge. This profile has no attachment access, CLI dispatch or SSH tools. Acknowledging a message hides it from the default pending view and preserves it in the mailbox.

If the plugin does not connect, confirm that Claude Code can find `python`. If peers see different messages, check that their channel paths match and point to a directory they can read and write. Windows is the tested platform for this release draft.

See [data handling](PRIVACY.md) and the [MIT License](LICENSE). For support, open an issue in the Agent Bridge repository with your plugin version, platform and steps to reproduce. Keep private messages, files and credentials out of issue reports.
