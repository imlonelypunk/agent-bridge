"use strict";

const { execFile } = require("node:child_process");
const { promisify } = require("node:util");

const execFileAsync = promisify(execFile);

function pythonCandidates(configured = "", platform = process.platform) {
  if (configured.trim()) return [{ command: configured.trim(), prefix: [] }];
  return platform === "win32"
    ? [
      { command: "python", prefix: [] },
      { command: "py", prefix: ["-3"] },
      { command: "python3", prefix: [] },
    ]
    : [
      { command: "python3", prefix: [] },
      { command: "python", prefix: [] },
    ];
}

async function probePython(candidate) {
  const { stdout, stderr } = await execFileAsync(
    candidate.command,
    [...candidate.prefix, "--version"],
    { windowsHide: true, timeout: 3000, maxBuffer: 4096 },
  );
  const match = `${stdout}\n${stderr}`.match(/\bPython\s+(\d+)\.(\d+)/i);
  if (!match) throw new Error("could not read Python version");
  return { ...candidate, version: [Number(match[1]), Number(match[2])] };
}

async function resolvePython(configured = "", platform = process.platform, probe = probePython) {
  const candidates = pythonCandidates(configured, platform);
  const errors = [];
  for (const candidate of candidates) {
    try {
      const result = await probe(candidate);
      const [major, minor] = result.version || [];
      if (major > 3 || (major === 3 && minor >= 10)) return candidate;
      errors.push(`${candidate.command} is Python ${major}.${minor}; version 3.10 or later is required`);
    } catch (error) {
      errors.push(`${candidate.command}: ${error.message}`);
    }
    if (configured.trim()) break;
  }
  throw new Error(
    `Could not find Python 3.10 or later${configured.trim() ? ` at ${configured.trim()}` : ""}. `
    + `${errors.join("; ")}. Set agentBridge.pythonExecutable to a Python 3.10+ executable.`,
  );
}

module.exports = { pythonCandidates, resolvePython };
