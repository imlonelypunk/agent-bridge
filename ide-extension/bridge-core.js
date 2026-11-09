const crypto = require("node:crypto");
const path = require("node:path");

function normalizedRepository(remote) {
  const value = String(remote || "").trim();
  if (!value) return null;

  let host;
  let repositoryPath;
  const scp = value.match(/^(?:[^@/]+@)?([^:/]+):(.+)$/);
  if (scp && !value.includes("://")) {
    [, host, repositoryPath] = scp;
  } else {
    try {
      const parsed = new URL(value.includes("://") ? value : `https://${value}`);
      host = parsed.hostname;
      repositoryPath = parsed.pathname;
    } catch {
      return null;
    }
  }

  host = String(host || "").toLowerCase();
  repositoryPath = String(repositoryPath || "").replace(/\.git\/?$/i, "").replace(/^\/+|\/+$/g, "").toLowerCase();
  if (!host || !repositoryPath) return null;
  return `${host}/${repositoryPath}`;
}

function repositoryIdFromRemote(remote) {
  const normalized = normalizedRepository(remote);
  if (!normalized) return null;
  return `git:${crypto.createHash("sha256").update(normalized, "utf8").digest("hex")}`;
}

function repositoryIdFromPath(workspace) {
  const normalized = path.resolve(workspace).replace(/\\/g, "/").toLowerCase();
  return `local:${crypto.createHash("sha256").update(normalized, "utf8").digest("hex")}`;
}

function messageLabel(message) {
  const sender = typeof message?.sender === "string" && message.sender ? message.sender : "unknown";
  const kind = typeof message?.kind === "string" && message.kind ? message.kind : "message";
  return `@${sender} · ${kind}${message?.task_id ? ` · ${message.task_id}` : ""}`;
}

module.exports = { normalizedRepository, repositoryIdFromRemote, repositoryIdFromPath, messageLabel };
