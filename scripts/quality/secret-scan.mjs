import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import process from "node:process";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
  "..",
);

const mode = process.argv[2] ?? "--all";

if (!["--all", "--staged"].includes(mode)) {
  console.error("Usage: secret-scan.mjs [--all|--staged]");
  process.exit(1);
}

const blockedPathPatterns = [
  /(^|\/)\.env(\.[^/]+)?$/i,
  /(^|\/)\.env\.[^/]+\.local$/i,
  /(^|\/).*\.(?:pem|p12|pfx|key)$/i,
  /(^|\/)(?:id_rsa|id_dsa)(?:\.pub)?$/i,
  /(^|\/).*(?:credential|credentials|secret|secrets|token|private).*\.json$/i,
];

const allowedPathPatterns = [/^(.+\/)?\.env\.example$/i];

const ignorePrefixes = [
  ".git/",
  "node_modules/",
  "backend/.venv/",
  "backend/coverage/",
  "backend/test-results/",
  "frontend/node_modules/",
  "frontend/dist/",
  "frontend/playwright-report/",
  "frontend/test-results/",
  "frontend/.vite/",
  "infrastructure/.venv/",
  "infrastructure/cdk.out/",
  "artifacts/",
  ".coverage",
];

main();

function main() {
  const files = getFiles(mode);

  if (files.length === 0) {
    console.log("No files to scan.");
    return;
  }

  const findings = checkBlockedPaths(files);
  if (findings.length > 0) {
    reportFindings(findings);
  }

  const scanRoot = materializeScanTree(files, mode);

  try {
    runGitleaks(scanRoot);
  } finally {
    fs.rmSync(scanRoot, { recursive: true, force: true });
  }

  console.log(
    `Secret scan passed for ${files.length} file(s) in ${mode === "--staged" ? "staged" : "tracked"} scope.`,
  );
}

function getFiles(scanMode) {
  const args =
    scanMode === "--staged"
      ? ["diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"]
      : ["ls-files", "-z"];

  return runCapture("git", args)
    .split("\0")
    .map((file) => file.trim())
    .filter(Boolean)
    .map(normalizePath)
    .filter((file) => !shouldIgnore(file));
}

function checkBlockedPaths(files) {
  const findings = [];

  for (const file of files) {
    if (allowedPathPatterns.some((pattern) => pattern.test(file))) {
      continue;
    }

    const blockedPattern = blockedPathPatterns.find((pattern) =>
      pattern.test(file),
    );
    if (blockedPattern) {
      findings.push(
        `${file}: matches blocked secret-file pattern ${blockedPattern}`,
      );
    }
  }

  return findings;
}

function materializeScanTree(files, scanMode) {
  const root = fs.mkdtempSync(
    path.join(os.tmpdir(), "isbn-library-gitleaks-"),
  );

  for (const file of files) {
    const targetPath = path.join(root, file);
    fs.mkdirSync(path.dirname(targetPath), { recursive: true });
    fs.writeFileSync(targetPath, readContent(scanMode, file));
  }

  return root;
}

function readContent(scanMode, file) {
  if (scanMode === "--staged") {
    const result = spawnSync("git", ["show", `:${file}`], {
      cwd: repoRoot,
      encoding: null,
      maxBuffer: 1024 * 1024 * 20,
    });

    if (result.status !== 0 || result.stdout === null) {
      const stderr = result.stderr
        ? Buffer.from(result.stderr).toString("utf8")
        : "";
      throw new Error(
        `Failed to read staged file ${file}${stderr ? `: ${stderr.trim()}` : ""}`,
      );
    }

    return result.stdout;
  }

  return fs.readFileSync(path.join(repoRoot, file));
}

function runGitleaks(scanRoot) {
  const gitleaksCommand = resolveGitleaksCommand();
  const gitleaksArgs = [
    "dir",
    "--no-banner",
    "--redact",
    "--no-color",
    scanRoot,
  ];
  const result = spawnSync(gitleaksCommand, gitleaksArgs, {
    cwd: repoRoot,
    stdio: "inherit",
    env: process.env,
    shell: process.platform === "win32",
  });

  if (result.error) {
    throw result.error;
  }

  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

function resolveGitleaksCommand() {
  const override = process.env.GITLEAKS_BIN?.trim();
  if (override) {
    if (!fs.existsSync(override)) {
      throw new Error(
        `GITLEAKS_BIN points to a missing file: ${override}\n` +
          "Install Gitleaks or update GITLEAKS_BIN to the binary path.",
      );
    }

    return override;
  }

  const probe = spawnSync("gitleaks", ["version"], {
    cwd: repoRoot,
    stdio: "ignore",
    env: process.env,
  });

  if (!probe.error && probe.status === 0) {
    return "gitleaks";
  }

  const resolvedPath =
    process.platform === "win32"
      ? resolveExecutableWithWhere("gitleaks")
      : resolveExecutableWithWhich("gitleaks");
  if (resolvedPath) {
    return resolvedPath;
  }

  throw new Error(
    [
      "Gitleaks is not installed or not on PATH.",
      "Install it with `winget install Gitleaks.Gitleaks`, `brew install gitleaks`, or the official release binary.",
      "You can also set GITLEAKS_BIN to the full binary path for local validation.",
    ].join("\n"),
  );
}

function resolveExecutableWithWhere(commandName) {
  const result = spawnSync("where.exe", [commandName], {
    cwd: repoRoot,
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
    env: process.env,
    maxBuffer: 1024 * 1024,
  });

  if (result.error || result.status !== 0) {
    return undefined;
  }

  const candidate = result.stdout
    ?.split(/\r?\n/)
    .map((line) => line.trim())
    .find(Boolean);
  return candidate;
}

function resolveExecutableWithWhich(commandName) {
  const result = spawnSync("which", [commandName], {
    cwd: repoRoot,
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
    env: process.env,
    maxBuffer: 1024 * 1024,
  });

  if (result.error || result.status !== 0) {
    return undefined;
  }

  const candidate = result.stdout?.trim();
  return candidate || undefined;
}

function reportFindings(findings) {
  console.error("Potential secret leaks detected:");
  for (const finding of findings) {
    console.error(`- ${finding}`);
  }
  process.exit(1);
}

function shouldIgnore(file) {
  return ignorePrefixes.some((prefix) => file.startsWith(prefix));
}

function normalizePath(file) {
  return file.replace(/\\/g, "/");
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
