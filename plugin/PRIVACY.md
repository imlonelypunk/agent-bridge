# Agent Bridge data handling

The Claude Code plugin reads and writes the chosen local mailbox. It stores message text, routing metadata, timestamps, repository routing keys, acknowledgment state and any caller-supplied retry key in `mailbox.sqlite3`. It handles only the message data provided through its tools. The plugin runs local Git commands to identify the workspace; it opens no network connection and sends no telemetry. Content supplied to or returned from tools is visible to the Claude Code session and is subject to the Claude service's data handling.

Use a local channel shared only with trusted operators. Mailbox data is readable to anyone with filesystem access. Agent Bridge does not apply its own encryption. Messages persist until you remove the channel. To remove it, close the clients first, then remove the mailbox directory and any copies or backups you no longer want. Removing the plugin alone leaves the shared mailbox in place.

For privacy or security concerns, use the repository's private security reporting channel if available. Use a public issue only for non-sensitive questions.
