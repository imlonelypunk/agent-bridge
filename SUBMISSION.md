# Claude directory submission draft

- Listing name and version are Agent Bridge 0.1.2. Submit the `plugin/` folder as a Plugin bundle. The standalone CLI and Desktop package are outside the submitted folder.
- This is an update to the existing listing. Confirm its tracked branch or tag in the Claude developer portal; the repository and `plugin` path must match the existing listing. Do not push or publish until the owner chooses to release.
- Run `claude plugin validate --strict ./plugin`. In the [developer portal](https://claude.ai/directory/manage), open the existing listing and check its tracked branch or tag and validation status. Review the listing preview and provide the publisher's verified contact, support and privacy links.
- The plugin stores text and routing metadata on the user's filesystem until the user removes the channel. Text in tool requests and results is visible to Claude. The plugin runs local Git commands to identify the workspace. Its entry point opens no network connection, requests no credentials, and does not launch vendor sessions. The root repository documents the separately installed full bridge and its additional data flows. Use the public URL for `plugin/PRIVACY.md` when the repository is public.
- For the review fixture, use two roles on a new local channel with synthetic messages. Python is required. Test sending to Codex, reading the Claude inbox, and replying to an Antigravity message. The [plugin guide](plugin/README.md) includes all three example prompts.
- Review the directory terms and data-handling answers in the portal before submitting. The `.mcpb` is a separate manual installation package. Each directory version is scanned; whether a reviewer must publish it depends on the listing settings.

[Anthropic's submission guide](https://claude.com/docs/plugins/submit) · [Pre-submission checklist](https://claude.com/docs/plugins/pre-submission-checklist)
