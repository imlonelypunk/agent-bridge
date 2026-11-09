"""Check the VSIX contents and exercise the bundled Python runtime in isolation."""

import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import zipfile


EXPECTED_FILES = {
    "[Content_Types].xml",
    "extension.vsixmanifest",
    "extension/LICENSE.txt",
    "extension/bridge-core.js",
    "extension/changelog.md",
    "extension/extension.js",
    "extension/icon.png",
    "extension/package.json",
    "extension/python-resolver.js",
    "extension/readme.md",
    "extension/runtime/bridge.py",
    "extension/runtime/bridge_runner.py",
    "extension/runtime/plugin/__init__.py",
    "extension/runtime/plugin/mailbox_server.py",
}


def run_bridge(script, workspace, channel, agent, command, *arguments):
    isolated_launcher = (
        "import runpy,sys; runtime=sys.argv[1]; script=sys.argv[2]; "
        "sys.path.insert(0,runtime); sys.argv=sys.argv[2:]; runpy.run_path(script,run_name='__main__')"
    )
    result = subprocess.run(
        [
            sys.executable, "-I", "-c", isolated_launcher, str(script.parent), str(script),
            "--agent", agent, "--workspace", str(workspace),
            "--channel-dir", str(channel), command, *arguments,
        ],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"bridge {command} failed")
    return json.loads(result.stdout)


def verify(path):
    path = Path(path).resolve()
    with zipfile.ZipFile(path) as package:
        names = set(package.namelist())
        missing = EXPECTED_FILES - names
        unexpected = names - EXPECTED_FILES
        if missing or unexpected:
            raise RuntimeError(f"VSIX entry mismatch; missing={sorted(missing)}, unexpected={sorted(unexpected)}")
        if any("__pycache__" in name or name.endswith(".pyc") for name in names):
            raise RuntimeError("VSIX contains generated Python cache files")
        manifest = json.loads(package.read("extension/package.json"))
        if manifest.get("license") != "MIT":
            raise RuntimeError("VSIX manifest must use SPDX license MIT")
        with TemporaryDirectory(prefix="agent-bridge-vsix-") as scratch:
            root = Path(scratch).resolve()
            for entry in package.infolist():
                destination = (root / entry.filename).resolve()
                if not destination.is_relative_to(root):
                    raise RuntimeError(f"Unsafe VSIX entry: {entry.filename}")
            package.extractall(root)

            workspace = root / "smoke-repository"
            workspace.mkdir()
            subprocess.run(["git", "init", "-q", str(workspace)], check=True, timeout=20)
            channel = root / "smoke-channel"
            bridge = root / "extension" / "runtime" / "bridge.py"
            sent = run_bridge(
                bridge, workspace, channel, "codex", "send",
                "--to", "claude", "--kind", "request", "--body", "Packaged runtime smoke.",
            )
            messages = run_bridge(bridge, workspace, channel, "claude", "inbox")["messages"]
            received = next((message for message in messages if message["id"] == sent["message_id"]), None)
            if received is None or not received.get("repository_id"):
                raise RuntimeError("Packaged inbox did not return the repository-routed message")
            resolved_key = run_bridge(bridge, workspace, channel, "codex", "repository-key")
            if resolved_key.get("repository_id") != received["repository_id"]:
                raise RuntimeError("Packaged repository-key does not match the message route")
            filtered = run_bridge(
                bridge, workspace, channel, "claude", "inbox",
                "--repository-id", received["repository_id"],
            )["messages"]
            if [message["id"] for message in filtered] != [sent["message_id"]]:
                raise RuntimeError("Packaged repository-filtered inbox smoke failed")
            read = run_bridge(
                bridge, workspace, channel, "claude", "read",
                "--message-id", sent["message_id"], "--repository-id", received["repository_id"],
            )
            if read.get("body") != "Packaged runtime smoke." or read.get("repository_id") != received["repository_id"]:
                raise RuntimeError("Packaged read smoke failed")

    print(f"Verified {path.name}: {len(EXPECTED_FILES)} entries; isolated send/inbox/read passed.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python verify_vsix.py <extension.vsix>")
    verify(sys.argv[1])
