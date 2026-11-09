const fs = require("node:fs");
const path = require("node:path");

const extensionRoot = path.resolve(__dirname, "..");
const repositoryRoot = path.resolve(extensionRoot, "..");
const runtimeRoot = path.join(extensionRoot, "runtime");

fs.mkdirSync(path.join(runtimeRoot, "plugin"), { recursive: true });
for (const file of ["bridge.py", "bridge_runner.py"]) {
  fs.copyFileSync(path.join(repositoryRoot, file), path.join(runtimeRoot, file));
}
for (const file of ["__init__.py", "mailbox_server.py"]) {
  fs.copyFileSync(path.join(repositoryRoot, "plugin", file), path.join(runtimeRoot, "plugin", file));
}

console.log("Bundled the Agent Bridge Python runtime into ide-extension/runtime.");
