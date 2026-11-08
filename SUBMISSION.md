# Claude directory submission draft

- Listing name and version are Agent Bridge 0.1.0. Submit the `plugin/` folder as a Plugin bundle. The repository should contain Agent Bridge source and documentation only.
- Upload the source to a GitHub repository the publisher can push to. Connect that GitHub account in the Claude developer portal. The repository can be private during validation and must be public for a live listing.
- Run `claude plugin validate --strict ./plugin`. In the [developer portal](https://claude.ai/directory/manage), choose the repository and `plugin` path, then validate the selected revision. Review the listing preview and provide the publisher's verified contact, support and privacy links.
- The plugin stores text and routing metadata on the user's filesystem until the user removes the channel. Text in tool requests and results is visible to Claude. The plugin entry point opens no network connection, requests no credentials, and does not launch vendor sessions. The root repository documents the separately installed full bridge and its additional data flows. Use the public URL for `plugin/PRIVACY.md` when the repository is public.
- For the review fixture, use two roles on a new local channel with synthetic messages. Python is required. Test sending to Codex, reading the Claude inbox, and replying to an Antigravity message. The [plugin guide](plugin/README.md) includes all three example prompts.
- Review the directory terms and data-handling answers in the portal before submitting. The `.mcpb` is a separate manual installation package. Anthropic reviews each directory version.

[Anthropic's submission guide](https://claude.com/docs/plugins/submit) · [Pre-submission checklist](https://claude.com/docs/plugins/pre-submission-checklist)
