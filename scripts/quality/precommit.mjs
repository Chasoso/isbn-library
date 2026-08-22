import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
  "..",
);
const frontendRoot = path.join(repoRoot, "frontend");
const secretScanScript = path.join(repoRoot, "scripts/quality/secret-scan.mjs");

const frontendLintExtensions = new Set([
  ".js",
  ".jsx",
  ".mjs",
  ".ts",
  ".tsx",
]);

const pythonExtensions = new Set([".py"]);

main();

function main() {
  const stagedFiles = getStagedFiles();

  if (stagedFiles.length === 0) {
    console.log("No staged files to check.");
    return;
  }

  runNode(secretScanScript, ["--staged"]);

  const frontendFiles = [];
  const pythonFiles = [];

  for (const file of stagedFiles) {
    if (shouldSkip(file)) {
      continue;
    }

    if (isFrontendLintTarget(file)) {
      frontendFiles.push(relativeToWorkspace(frontendRoot, file));
    }

    if (isPythonTarget(file)) {
      pythonFiles.push(file);
    }
  }

  if (frontendFiles.length > 0) {
    runNpmBinary(frontendRoot, "eslint", ["--max-warnings=0", ...frontendFiles]);
  }

  if (pythonFiles.length > 0) {
    runPythonCompile(pythonFiles);
  }

  console.log(
    `Pre-commit quality checks passed for ${stagedFiles.length} staged file(s).`,
  );
}

function getStagedFiles() {
  const output = runCapture("git", [
    "diff",
    "--cached",
    "--name-only",
    "--diff-filter=ACMR",
    "-z",
  ]);

  return output
    .split("\0")
    .map((item) => item.trim())
    .filter(Boolean)
    .map(normalizePath);
}

function isFrontendLintTarget(filePath) {
  if (!filePath.startsWith("frontend/")) {
    return false;
  }

  const extension = path.extname(filePath).toLowerCase();
  return frontendLintExtensions.has(extension);
}

function isPythonTarget(filePath) {
  const extension = path.extname(filePath).toLowerCase();
  return pythonExtensions.has(extension);
}

function shouldSkip(filePath) {
  return (
    filePath.endsWith("package-lock.json") ||
    filePath.startsWith("frontend/node_modules/") ||
    filePath.startsWith("backend/.venv/") ||
    filePath.startsWith("infrastructure/.venv/")
  );
}

function normalizePath(filePath) {
  return filePath.replace(/\\/g, "/");
}

function relativeToWorkspace(workspaceRoot, filePath) {
  return normalizePath(
    path.relative(workspaceRoot, path.join(repoRoot, filePath)),
  );
}

function runNode(scriptPath, args) {
  const result = spawnSync(process.execPath, [scriptPath, ...args], {
    cwd: repoRoot,
    stdio: "inherit",
    env: process.env,
  });

  if (result.error) {
    throw result.error;
  }

  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

function runNpmBinary(cwd, binaryName, args) {
  const result =
    process.platform === "win32"
      ? spawnSync(
          "cmd.exe",
          ["/d", "/s", "/c", "npm.cmd", "exec", "--", binaryName, ...args],
          {
            cwd,
            stdio: "inherit",
            env: process.env,
          },
        )
      : spawnSync("npm", ["exec", "--", binaryName, ...args], {
          cwd,
          stdio: "inherit",
          env: process.env,
        });

  if (result.error) {
    throw result.error;
  }

  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

function runPythonCompile(files) {
  const pythonCommand = resolvePythonCommand();
  const absoluteFiles = files.map((file) => path.join(repoRoot, file));
  const compileScript = [
    "import os",
    "import py_compile",
    "import sys",
    "import tempfile",
    "",
    "for source in sys.argv[1:]:",
    "    fd, cfile = tempfile.mkstemp(suffix='.pyc')",
    "    os.close(fd)",
    "    try:",
    "        py_compile.compile(source, cfile=cfile, doraise=True)",
    "    finally:",
    "        try:",
    "            os.remove(cfile)",
    "        except FileNotFoundError:",
    "            pass",
  ].join("\n");

  const result = spawnSync(pythonCommand, ["-c", compileScript, ...absoluteFiles], {
    cwd: repoRoot,
    stdio: "inherit",
    env: process.env,
  });

  if (result.error) {
    throw result.error;
  }

  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

function resolvePythonCommand() {
  const candidates = [];

  if (process.env.PYTHON?.trim()) {
    candidates.push(process.env.PYTHON.trim());
  }

  candidates.push(
    path.join(repoRoot, "backend", ".venv", "Scripts", "python.exe"),
    path.join(repoRoot, "infrastructure", ".venv", "Scripts", "python.exe"),
    "python3",
    "python",
  );

  for (const candidate of candidates) {
    if (!candidate) {
      continue;
    }

    if (!fs.existsSync(candidate) && candidate.includes(path.sep)) {
      continue;
    }

    const result = spawnSync(candidate, ["--version"], {
      cwd: repoRoot,
      stdio: "ignore",
      env: process.env,
    });

    if (!result.error && result.status === 0) {
      return candidate;
    }
  }

  throw new Error(
    "No usable Python interpreter was found for pre-commit syntax checks.",
  );
}

function runCapture(command, args) {
  const result = spawnSync(command, args, {
    cwd: repoRoot,
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
    env: process.env,
    maxBuffer: 1024 * 1024 * 10,
  });

  if (result.error) {
    throw result.error;
  }

  if (result.status !== 0) {
    process.stderr.write(result.stderr ?? "");
    process.exit(result.status ?? 1);
  }

  return result.stdout ?? "";
}
