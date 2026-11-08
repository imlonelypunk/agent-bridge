"use strict";

const { spawn } = require("node:child_process");
const path = require("node:path");

const python = process.env.AGENT_BRIDGE_PYTHON;
const channel = process.env.AGENT_BRIDGE_CHANNEL;
if (!python || !channel) {
  process.stderr.write("Configure the Python executable and shared mailbox in Agent Bridge settings.\n");
  process.exit(1);
}

const args = [
  path.join(__dirname, "bridge.py"),
  "--agent", "claude",
  "--channel-dir", channel,
  "--enable-dispatch",
];
if (process.env.AGENT_BRIDGE_WORKSPACE) {
  args.push("--workspace", process.env.AGENT_BRIDGE_WORKSPACE);
}
args.push("serve");

const child = spawn(python, args, { stdio: ["pipe", "pipe", "pipe"], windowsHide: true });
process.stdin.pipe(child.stdin);
child.stdout.pipe(process.stdout);
child.stderr.pipe(process.stderr);
child.stdin.on("error", (error) => {
  if (error.code !== "EPIPE") {
    process.stderr.write("Agent Bridge input failed. " + error.message + "\n");
  }
});

child.on("error", (error) => {
  process.stderr.write("Agent Bridge could not start Python. " + error.message + "\n");
  process.exitCode = 1;
});

child.on("exit", (code, signal) => {
  process.stdin.unpipe(child.stdin);
  process.stdin.pause();
  process.exitCode = code === null ? 1 : code;
  if (signal) {
    process.stderr.write("Agent Bridge Python process stopped with " + signal + ".\n");
  }
});

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => child.kill(signal));
}
