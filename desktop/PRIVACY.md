# Full Agent Bridge data handling

The full bridge stores message text, routing metadata, timestamps, acknowledgment state, retry keys and selected file snapshots in the configured local mailbox. It can materialize snapshots under `received/`. Data persists until you remove the mailbox and any local copies. Agent Bridge does not apply its own encryption or send telemetry. Use a mailbox shared only with trusted operators.

The optional SSH transport passes messages and snapshots to the host you configure. SSH clients may also keep received snapshots under `~/.agent-bridge/`. The optional dispatch workflow passes the selected request and eligible text attachments to the selected agent's model provider using that vendor's signed-in CLI. Replies, attachments, run status and diagnostic logs can persist on the mailbox host. Model providers apply their own terms and retention to data they receive.

Close all clients before removing the mailbox. Remove local caches, logs and backups separately where needed. Uninstalling the Desktop extension leaves the shared mailbox in place.
