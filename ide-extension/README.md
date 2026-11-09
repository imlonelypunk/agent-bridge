# Agent Bridge IDE extension

Agent Bridge connects the inboxes of Antigravity, Codex, and Claude Code from one user-scope IDE extension. It routes each message to a repository key, so open windows for other projects do not take the request.

## Install and configure

Install the VSIX in each VS Code-compatible IDE that should join the mailbox. Run **Agent Bridge: Configure** once in each IDE, choose `Auto-detect IDE` or a mailbox role, and point each installation at the same local channel directory or trusted SSH relay. A packaged VSIX includes the Python bridge runtime. Python 3.10+ is still required on the extension host; the extension probes `python3`/`python` or the Windows `py -3` launcher automatically.

The extension uses the active editor's workspace folder, then the first open folder. You can set `agentBridge.workspacePath` to select a different folder for a window.

## Repository routing

By default, the extension hashes the normalized Git `origin` URL and stores only that hash in mailbox metadata. HTTPS and SSH clones of the same repository therefore share a routing key. For a local repository without a remote, it hashes the Git root's local path; that key works across IDEs on the same machine at that path.

For cloud workspaces, mirrors with different remotes, or a local repository that must match across machines, set the same `agentBridge.repositoryId` value in each participating IDE window. Choose a stable value such as `team/project` and keep it identical. The key routes messages; it does not upload or expose the Git remote URL.

Messages without a repository key are excluded from repository-filtered IDE inboxes. They remain available through an unfiltered mailbox client for explicit recovery; the IDE will not open or acknowledge them in a project.

## Send and receive

Run **Agent Bridge: Send to Agent** from the Command Palette. Choose a recipient, message type, and task; selected editor text is included as context. You can also attach up to four files from the open repository. Attachments must meet the bridge's tracked-file rules. The extension asks for confirmation before sending and queues the request for the recipient IDE.

Incoming requests, notes, and replies appear in **Agent Bridge Inbox**. Choose **Open in IDE** to open a request in the matching agent's IDE surface. Replies open as Markdown in the workspace and remain visible to the sender in the same repository inbox. Reviewing a reply or note acknowledges it. After opening a request, confirm that it reached the chat before acknowledging it; otherwise it remains in the inbox. The IDE still applies its normal permissions and the agent must use the Agent Bridge reply tool with the original message ID.

For unattended delivery to Antigravity, enable `agentBridge.autoAntigravity` in the receiving IDE. The extension polls the matching repository, claims each incoming request or reply once across windows, creates a new Antigravity conversation and submits it. Replies include the earlier request for context and do not request another bridge reply. The agent must have its own Agent Bridge MCP profile and use `reply` for the sender to receive an answer. A queued or submitted request is not a reply. Only one automatically claimed request per role is processed until that agent replies; if the IDE closes or submission fails after a claim, inspect the inbox and handle the request manually. This mode uses undocumented Antigravity commands and may stop working when the IDE changes. It does not automatically start Codex or Claude Code chats.

## IDE adapters and limits

- **Claude Code:** uses the documented `vscode://anthropic.claude-code/open?prompt=...` handler. It pre-fills a new Claude Code chat but does not send it; review the prompt and press Enter. If the encoded link exceeds 2,000 characters or the handler declines it, the request opens in a document and is copied for manual paste. See [Claude Code IDE integrations](https://code.claude.com/docs/en/ide-integrations).
- **Codex:** opens a new chat and uses the available `chatgpt.addFileToThread` command for delivered files, then copies the request to the clipboard. Paste and send it in Codex. The public IDE API does not expose composer submission to third-party extensions. See [Codex IDE extension documentation](https://learn.chatgpt.com/docs/codex/ide).
- **Antigravity:** uses its available chat commands and attaches mailbox files when those commands are present. Antigravity does not publish a stable third-party chat command contract. If unavailable, the extension copies and opens the request for manual paste.

End-to-end correlated replies in the final package and the Codex and Claude Code adapters remain unverified. These adapters open the receiving IDE's chat in the repository context selected by the extension host. They do not bypass login, permissions, approvals, or the recipient's normal send action.

## Settings

- `agentBridge.agent`: `auto`, `codex`, `claude`, or `antigravity`.
- `agentBridge.bridgeScript`: optional override; packaged VSIX includes `bridge.py` and its Python modules.
- `agentBridge.pythonExecutable`: optional explicit Python 3.10+ executable; otherwise the extension probes the standard platform commands.
- `agentBridge.channelDirectory`: shared local mailbox, default `~/.agent-bridge/channel`.
- `agentBridge.sshHost` and `agentBridge.remoteCommand`: trusted SSH relay settings; set both or neither. The remote server must use the same role, a compatible Agent Bridge version, and enable dispatch. An overridden local bridge script must also support the `repository-key` command.
- `agentBridge.repositoryId`: optional stable key for cloud and cross-machine routing.
- `agentBridge.workspacePath`: per-window workspace override.
- `agentBridge.enableDispatch`: allow confirmed sends to create IDE delivery records.
- `agentBridge.autoAntigravity`: opt in to automatically submitting incoming requests to Antigravity.
- `agentBridge.pollSeconds`: mailbox polling interval, 5–60 seconds.

The extension starts `bridge.py` with argument arrays, does not use a shell, and makes no network requests. A configured SSH relay runs only on the trusted host specified by the user.

Message text is passed to the local bridge as a command-line argument and may be visible to other processes on the same host.
