# Agent Bridge data handling

The Claude Code plugin reads and writes the chosen local mailbox. It stores message text, routing metadata, timestamps, acknowledgment state and any caller-supplied retry key in `mailbox.sqlite3`. It handles only the message data provided through its tools. The plugin opens no network connection and sends no telemetry. Content supplied to or returned from tools is visible to the Claude Code session and is subject to the Claude service's data handling.

Use a local channel shared only with trusted operators. Mailbox data is readable to anyone with filesystem access. Agent Bridge does not apply its own encryption. Messages persist until you remove the channel. To remove it, close the clients first, then remove the mailbox directory and any copies or backups you no longer want. Removing the plugin alone leaves the shared mailbox in place.

The separately installed full bridge can store selected file snapshots and materialize them under `received/`. SSH clients may also keep received snapshots under `~/.agent-bridge/`. The optional SSH transport passes messages and snapshots to the host you configure. The optional dispatch workflow passes the selected request and eligible text attachments to the selected agent's model provider using that vendor's signed-in CLI. Replies, attachments, run status and diagnostic logs can persist on the mailbox host. Model providers apply their own terms and retention to data they receive. Remove cached snapshots and logs separately where needed.

For privacy or security concerns, use the repository's private security reporting channel if available. Use a public issue only for non-sensitive questions.
