const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const repositoryVectors = require("../../tests/repository_keys.json");
const manifest = require("../package.json");
const {
  normalizedRepository,
  repositoryIdFromRemote,
  repositoryIdFromPath,
  messageLabel,
} = require("../bridge-core");

test("HTTPS and SSH forms produce one repository route", () => {
  const expected = repositoryIdFromRemote("https://github.com/Example/AgentBridge.git");
  assert.equal(repositoryIdFromRemote("git@github.com:example/agentbridge.git"), expected);
  assert.equal(repositoryIdFromRemote("ssh://git@github.com/example/agentbridge"), expected);
  assert.equal(repositoryIdFromRemote("https://github.com/example/agentbridge.git/"), expected);
});

test("normalizes supported hosted remotes and rejects malformed paths", () => {
  assert.equal(normalizedRepository("github.com/Example/Repo.git/"), "github.com/example/repo");
  assert.equal(normalizedRepository(""), null);
  assert.equal(repositoryIdFromRemote("https://github.com/"), null);
});

test("repository normalization matches shared Python and JavaScript vectors", () => {
  for (const vector of repositoryVectors) {
    assert.equal(normalizedRepository(vector.remote), vector.normalized, vector.remote);
  }
});

test("local repository key is stable for the same resolved path", () => {
  assert.equal(repositoryIdFromPath("./repo"), repositoryIdFromPath("repo"));
  assert.match(repositoryIdFromPath("repo"), /^local:[0-9a-f]{64}$/);
});

test("inbox labels use message data and never render undefined", () => {
  assert.equal(messageLabel({ sender: "codex", kind: "request", task_id: "BRIDGE-1" }),
    "@codex · request · BRIDGE-1");
  assert.equal(messageLabel({}), "@unknown · message");
});

test("marketplace manifest points to a valid free MIT VSIX listing", () => {
  assert.equal(`${manifest.publisher}.${manifest.name}`, "imlonelypunk.agent-bridge");
  assert.equal(manifest.pricing, "Free");
  assert.equal(manifest.license, "MIT");
  assert.equal(manifest.contributes.configuration.properties["agentBridge.pythonExecutable"].default, "");
  assert.equal(manifest.icon, "icon.png");
  const icon = fs.readFileSync(path.join(__dirname, "..", manifest.icon));
  assert.deepEqual([...icon.subarray(0, 8)], [137, 80, 78, 71, 13, 10, 26, 10]);
  assert.equal(icon.readUInt32BE(16), 128);
  assert.equal(icon.readUInt32BE(20), 128);
});
