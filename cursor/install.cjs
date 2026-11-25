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

function update(action, home = os.homedir(), python, host = "cursor") {
  const codex = host === "codex";
  const selectedEvents = codex ? { UserPromptSubmit: "codex-prompt", PreToolUse: "codex-tool" }
    : { beforeSubmitPrompt: "prompt" };
  const managedEvents = codex ? Object.keys(selectedEvents) : Object.keys(events);
  const cursor = codex && process.env.CODEX_HOME && home === os.homedir()
    ? process.env.CODEX_HOME : path.join(home, "." + host);
  const folder = path.join(cursor, "trustlayer");
  const runtime = path.join(folder, "runtime");
  const bridge = path.join(runtime, "cursor", "bridge.py");
  const policy = path.join(folder, "policy.md");
  const configPath = path.join(cursor, "hooks.json");
  const previous = fs.existsSync(configPath) ? fs.readFileSync(configPath, "utf8") : null;
  const config = previous ? JSON.parse(previous.replace(/^\uFEFF/, "")) : (codex ? { hooks: {} } : { version: 1, hooks: {} });
  if ((!codex && config.version !== 1) || !config.hooks || typeof config.hooks !== "object" || Array.isArray(config.hooks)) {
    throw new Error("Unsupported hooks.json; existing configuration was preserved.");
  }

  const ours = entry => typeof entry?.command === "string" && entry.command.includes(quote(bridge));
  for (const event of managedEvents) {
    if (event in config.hooks && !Array.isArray(config.hooks[event])) {
      throw new Error("Invalid hook list for " + event);
    }
  }
  if (action === "status") {
    return { installed: Object.keys(selectedEvents).every(event => (config.hooks[event] ?? []).some(entry =>
      ours(codex ? entry.hooks?.[0] : entry))), policy };
  }
  if (action === "uninstall" && !managedEvents.some(
    event => (config.hooks[event] ?? []).some(entry => ours(codex ? entry.hooks?.[0] : entry))
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

  for (const event of managedEvents) {
    const mode = selectedEvents[event];
    const other = (config.hooks[event] ?? []).filter(entry => !ours(codex ? entry.hooks?.[0] : entry));
    if (action === "install" && mode) {
      const prefix = process.platform === "win32" ? "& " : "";
      const command = prefix + [python, "-I", "-B", bridge, mode, policy].map(quote).join(" ");
      other.push(codex ? { hooks: [{ type: "command", command, timeout: 45 }] }
        : { command, timeout: 45, failClosed: true });
    }
    if (other.length) config.hooks[event] = other;
    else delete config.hooks[event];
  }

  const id = crypto.randomUUID();
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
  const host = process.argv[3] ?? "cursor";
  try {
    if (!["install", "status", "uninstall"].includes(action) || !["cursor", "codex"].includes(host) || process.argv.length > 4) {
      throw new Error("Usage: trustlayer-ai <install|status|uninstall> [cursor|codex]");
    }
    const result = update(action, os.homedir(), undefined, host);
    console.log(JSON.stringify(result, null, 2));
    if (action !== "status") console.log(host === "codex"
      ? "Restart Codex and review the registered hooks before trusting them."
      : "Restart Cursor to reload hooks.");
  } catch (error) {
    console.error("TrustLayer: " + error.message);
    process.exitCode = 1;
  }
}
module.exports = { update };
