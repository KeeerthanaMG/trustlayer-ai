#!/usr/bin/env node
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const crypto = require("node:crypto");
const { findPython } = require("./launch.cjs");

const source = path.resolve(__dirname, "..");
const events = {
  beforeSubmitPrompt: "prompt",
  preToolUse: "tool",
  beforeReadFile: "read",
};
const runtimeFiles = [
  "cursor/bridge.py", "cursor/default-policy.md", "trustlayer/__init__.py",
  "trustlayer/policies.py", "trustlayer/approval_dialog.py",
];

function quote(value) {
  return "'" + value.replace(/'/g, process.platform === "win32" ? "''" : "'\"'\"'") + "'";
}

function update(action, home = os.homedir(), python) {
  const cursor = path.join(home, ".cursor");
  const folder = path.join(cursor, "trustlayer");
  const runtime = path.join(folder, "runtime");
  const bridge = path.join(runtime, "cursor", "bridge.py");
  const policy = path.join(folder, "policy.md");
  const configPath = path.join(cursor, "hooks.json");
  const previous = fs.existsSync(configPath) ? fs.readFileSync(configPath, "utf8") : null;
  const config = previous ? JSON.parse(previous.replace(/^\uFEFF/, "")) : { version: 1, hooks: {} };
  if (config.version !== 1 || !config.hooks || typeof config.hooks !== "object" || Array.isArray(config.hooks)) {
    throw new Error("Unsupported Cursor hooks.json; existing configuration was preserved.");
  }

  const ours = entry => typeof entry?.command === "string" && entry.command.includes(quote(bridge));
  for (const event of Object.keys(events)) {
    if (event in config.hooks && !Array.isArray(config.hooks[event])) {
      throw new Error("Invalid hook list for " + event);
    }
  }
  if (action === "status") {
    return { installed: Object.keys(events).every(event => (config.hooks[event] ?? []).some(ours)), policy };
  }
  if (action === "uninstall" && !Object.keys(events).some(
    event => (config.hooks[event] ?? []).some(ours)
  )) return { installed: false, policy };

  if (action === "install") {
    python = python ?? findPython();
    for (const file of runtimeFiles) {
      const destination = path.join(runtime, file);
      fs.mkdirSync(path.dirname(destination), { recursive: true });
      fs.copyFileSync(path.join(source, file), destination);
    }
    try {
      fs.copyFileSync(path.join(source, "cursor/default-policy.md"), policy, fs.constants.COPYFILE_EXCL);
    } catch (error) {
      if (error.code !== "EEXIST") throw error;
    }
  }

  for (const [event, mode] of Object.entries(events)) {
    const other = (config.hooks[event] ?? []).filter(entry => !ours(entry));
    if (action === "install") {
      const prefix = process.platform === "win32" ? "& " : "";
      const command = prefix + [python, "-I", bridge, mode, policy].map(quote).join(" ");
      other.push({ command, timeout: 45, failClosed: true });
    }
    if (other.length) config.hooks[event] = other;
    else delete config.hooks[event];
  }

  const id = crypto.randomUUID();
  if (previous !== null) fs.writeFileSync(path.join(folder, "hooks-backup-" + id + ".json"), previous, { flag: "wx" });
  const temp = path.join(cursor, "hooks-" + id + ".tmp");
  try {
    fs.writeFileSync(temp, JSON.stringify(config, null, 2) + "\n", { flag: "wx" });
    fs.renameSync(temp, configPath);
  } finally {
    if (fs.existsSync(temp)) fs.unlinkSync(temp);
  }
  return { installed: action === "install", policy };
}

if (require.main === module) {
  const action = process.argv[2];
  try {
    if (!["install", "status", "uninstall"].includes(action) || process.argv.length !== 3) {
      throw new Error("Usage: trustlayer-ai <install|status|uninstall>");
    }
    const result = update(action);
    console.log(JSON.stringify(result, null, 2));
    if (action !== "status") console.log("Restart Cursor to reload hooks.");
  } catch (error) {
    console.error("TrustLayer: " + error.message);
    process.exitCode = 1;
  }
}
module.exports = { update };
