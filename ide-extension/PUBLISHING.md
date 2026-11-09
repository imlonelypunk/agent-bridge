# Publishing Agent Bridge

The IDE extension ID is `imlonelypunk.agent-bridge`; the current package version is `0.1.2`. Its VSIX is registry-independent, and the release workflow publishes the same package to the Visual Studio Marketplace and Open VSX.

## One-time publisher setup

### Visual Studio Marketplace

Create or confirm a publisher with the exact ID `imlonelypunk` in the [publisher management portal](https://marketplace.visualstudio.com/manage). The repository currently has no VS Code Marketplace publishing credentials configured on the build machine.

Create GitHub Environments named `marketplace` and `open-vsx`. Require a human reviewer for each environment before adding credentials or publishing. Configure the Visual Studio Marketplace Trusted Publishing policy for this GitHub repository:

- Repository owner: `imlonelypunk`
- Repository: `agent-bridge`
- Workflow: `publish-ide-extension.yml`
- Environment: `marketplace`

The workflow uses GitHub OIDC, so no Marketplace token is stored in GitHub. Microsoft recommends federated publishing; global Azure DevOps PATs are scheduled to retire on December 1, 2026. See [VS Code publishing and Trusted Publishing](https://code.visualstudio.com/api/working-with-extensions/publishing-extension).

### Open VSX

The `imlonelypunk` namespace does not exist on Open VSX yet, so it must be created before the first release. Open VSX requires an Eclipse account and an accepted Publisher Agreement. Create a personal access token and run `npx ovsx create-namespace imlonelypunk -p <token>` once. Store the token as the `OVSX_PAT` secret on the `open-vsx` GitHub Environment for the initial release.

The first version of a new extension must be published with an access token. After it is live, claim ownership of the namespace and register a Trusted Publisher for this extension with:

- Provider: GitHub Actions
- Repository owner: `imlonelypunk`
- Repository: `agent-bridge`
- Workflow: `publish-ide-extension.yml`
- Environment: `open-vsx`

Then remove `OVSX_PAT` from the environment. Later releases use Open VSX Trusted Publishing with GitHub OIDC. This prevents storing a long-lived registry token in GitHub Actions. See the official [Open VSX publishing guide](https://github.com/eclipse-openvsx/openvsx/wiki/Publishing-Extensions) and [Trusted Publishing guide](https://github.com/eclipse-openvsx/openvsx/wiki/Trusted-Publishing).

Creating the namespace assigns contributor access but does not automatically verify ownership; Open VSX documents a separate public ownership claim.

## Release checklist

1. Bump `version` in `package.json`, update `package-lock.json`, and add matching release notes to `CHANGELOG.md`.
2. Run `npm ci`, `npm run build:icon`, `npm test`, `npx --no-install vsce package --no-dependencies`, and `python scripts/verify_vsix.py agent-bridge-<version>.vsix` from `ide-extension/`.
3. Confirm the publisher accounts, both protected GitHub Environments, and the Open VSX namespace are ready.
4. Create and publish a stable GitHub release tagged `v<package-version>` (for example, `v0.1.1`). The workflow verifies the commit is on the default branch, builds and smoke-tests one VSIX, attaches that artifact to the release, and passes the same artifact to independent registry jobs. If one registry fails after the other succeeds, rerun only the failed job.

The same VSIX can also be installed directly with Antigravity IDE's `antigravity-ide --install-extension <file.vsix>` command.
