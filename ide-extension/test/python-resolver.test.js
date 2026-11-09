const test = require("node:test");
const assert = require("node:assert/strict");
const { pythonCandidates, resolvePython } = require("../python-resolver");

test("automatic Python candidates follow platform conventions", () => {
  assert.deepEqual(pythonCandidates("", "win32"), [
    { command: "python", prefix: [] },
    { command: "py", prefix: ["-3"] },
    { command: "python3", prefix: [] },
  ]);
  assert.deepEqual(pythonCandidates("", "linux"), [
    { command: "python3", prefix: [] },
    { command: "python", prefix: [] },
  ]);
});

test("automatic resolution skips missing and too-old interpreters", async () => {
  const attempts = [];
  const resolved = await resolvePython("", "win32", async (candidate) => {
    attempts.push(candidate.command);
    if (candidate.command === "python") throw new Error("not installed");
    if (candidate.command === "py") return { ...candidate, version: [3, 9] };
    return { ...candidate, version: [3, 12] };
  });
  assert.deepEqual(attempts, ["python", "py", "python3"]);
  assert.deepEqual(resolved, { command: "python3", prefix: [] });
});

test("an explicit interpreter override is checked without fallback", async () => {
  const attempts = [];
  await assert.rejects(
    resolvePython("/custom/python", "linux", async (candidate) => {
      attempts.push(candidate.command);
      return { ...candidate, version: [3, 9] };
    }),
    /Python 3\.10 or later/,
  );
  assert.deepEqual(attempts, ["/custom/python"]);
});
