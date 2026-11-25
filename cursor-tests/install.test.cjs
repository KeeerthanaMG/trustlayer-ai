const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const { update } = require("../cursor/install.cjs");
const { findPython } = require("../cursor/launch.cjs");

test("install preserves other hooks and custom policy across reinstall and uninstall", t => {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), "trustlayer install "));
  t.after(() => fs.rmSync(home, { recursive: true, force: true }));
  const folder = path.join(home, ".cursor");
  fs.mkdirSync(folder);
  const configPath = path.join(folder, "hooks.json");
  const original = { version: 1, hooks: { preToolUse: [{ command: "user hook" }] } };
  fs.writeFileSync(configPath, JSON.stringify(original));
  const python = findPython();
  const install = update("install", home, python);
  const legacy = JSON.parse(fs.readFileSync(configPath));
  const promptHook = legacy.hooks.beforeSubmitPrompt[0];
  legacy.hooks.preToolUse.push({ command: promptHook.command.replace("'prompt'", "'tool'") });
  legacy.hooks.beforeReadFile = [{ command: promptHook.command.replace("'prompt'", "'read'") }];
  fs.writeFileSync(configPath, JSON.stringify(legacy));
  fs.appendFileSync(install.policy, "\nUser documentation\n");
  update("install", home, python);
  assert.equal(update("status", home).installed, true);
  const config = JSON.parse(fs.readFileSync(configPath));
  assert.equal(config.hooks.preToolUse.length, 1);
  assert.equal(config.hooks.beforeReadFile, undefined);
  assert.deepEqual(config.hooks.preToolUse[0], original.hooks.preToolUse[0]);
  assert.equal(config.hooks.beforeSubmitPrompt[0].failClosed, true);
  assert.match(fs.readFileSync(install.policy, "utf8"), /User documentation/);
  const hook = config.hooks.beforeSubmitPrompt[0].command;
  const execution = process.platform === "win32"
    ? ["powershell.exe", ["-NoProfile", "-Command", hook]]
    : ["/bin/sh", ["-c", hook]];
  const allowed = spawnSync(...execution, {
    input: JSON.stringify({ prompt: "Explain the workspace" }),
    encoding: "utf8", cwd: home,
  });
  assert.equal(allowed.status, 0, allowed.stderr);
  assert.equal(JSON.parse(allowed.stdout).continue, true);
  update("uninstall", home);
  assert.deepEqual(JSON.parse(fs.readFileSync(configPath)), original);
  assert.equal(fs.existsSync(install.policy), true);
});

test("a missing interpreter does not clobber malformed user configuration", t => {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), "trustlayer invalid "));
  t.after(() => fs.rmSync(home, { recursive: true, force: true }));
  fs.mkdirSync(path.join(home, ".cursor"));
  const config = path.join(home, ".cursor", "hooks.json");
  fs.writeFileSync(config, "{ broken");
  assert.throws(() => update("install", home, "missing-python"));
  assert.equal(fs.readFileSync(config, "utf8"), "{ broken");
});

test("Codex installs native hook definitions and processes a safe prompt without an audit file", t => {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), "trustlayer codex "));
  t.after(() => fs.rmSync(home, { recursive: true, force: true }));
  const result = update("install", home, findPython(), "codex");
  const config = JSON.parse(fs.readFileSync(path.join(home, ".codex", "hooks.json")));
  const command = config.hooks.UserPromptSubmit[0].hooks[0].command;
  assert.equal(config.hooks.PreToolUse[0].hooks[0].type, "command");
  const execution = process.platform === "win32"
    ? ["powershell.exe", ["-NoProfile", "-Command", command]]
    : ["/bin/sh", ["-c", command]];
  const processResult = spawnSync(...execution, {
    input: JSON.stringify({ prompt: "Explain the workspace" }),
    encoding: "utf8", cwd: home,
  });
  assert.equal(processResult.status, 0, processResult.stderr);
  assert.deepEqual(JSON.parse(processResult.stdout), {});
  assert.equal(fs.existsSync(path.join(path.dirname(result.policy), "events.jsonl")), false);
  assert.equal(update("status", home, undefined, "codex").installed, true);
});
