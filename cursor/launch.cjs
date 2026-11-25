const { spawnSync } = require("node:child_process");

const candidates = process.platform === "win32"
  ? [["py", ["-3"]], ["python", []]]
  : [["python3", []]];

function findPython() {
  for (const [launcher, args] of candidates) {
    const check = spawnSync(launcher, [...args, "-I", "-c",
      "import sys, tkinter; assert sys.version_info >= (3, 10); print(sys.executable)"],
    { encoding: "utf8", timeout: 4000, windowsHide: true });
    if (check.status === 0 && check.stdout.trim()) return check.stdout.trim();
  }
  throw new Error("Install Python 3.10+ with tkinter (the python.org desktop installer works).");
}

function run(mode) {
  try {
    const result = spawnSync(findPython(), ["-I", "-B", require("node:path").join(__dirname, "bridge.py"), mode], {
      stdio: "inherit", timeout: 41000, windowsHide: true,
    });
    process.exit(result.status === 0 ? 0 : 2);
  } catch {
    process.exit(2);
  }
}
if (require.main === module) run(process.argv[2]);
module.exports = { findPython, run };
