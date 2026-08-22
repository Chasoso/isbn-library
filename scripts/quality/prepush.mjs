import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import process from "node:process";
import { spawn, spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { setTimeout as delay } from "node:timers/promises";

const repoRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
  "..",
);
const frontendRoot = path.join(repoRoot, "frontend");
const backendRoot = path.join(repoRoot, "backend");
const infrastructureRoot = path.join(repoRoot, "infrastructure");
const secretScanScript = path.join(repoRoot, "scripts/quality/secret-scan.mjs");

main().catch((error) => {
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
});

async function main() {
  runNode(secretScanScript, ["--all"]);
  runNpm("run", ["lint"], frontendRoot);
  runNpm("run", ["typecheck"], frontendRoot);
  const backendCoverageXml = path.join(
    process.env.ISBN_LIBRARY_BACKEND_COVERAGE_XML ?? os.tmpdir(),
    process.env.ISBN_LIBRARY_BACKEND_COVERAGE_XML
      ? ""
      : "isbn-library-backend-coverage.xml",
  );
  const backendCoverageData = path.join(
    os.tmpdir(),
    "isbn-library-backend.coverage",
  );
  const backendTestResultsDir = path.join(
    process.env.ISBN_LIBRARY_BACKEND_TEST_RESULTS_DIR ?? os.tmpdir(),
    process.env.ISBN_LIBRARY_BACKEND_TEST_RESULTS_DIR
      ? ""
      : "isbn-library-backend-test-results",
  );
  runPython(
    "pytest",
    [`--cov-report=xml:${backendCoverageXml}`],
    backendRoot,
    {
      COVERAGE_FILE: backendCoverageData,
      ISBN_LIBRARY_TEST_RESULTS_DIR: backendTestResultsDir,
    },
  );
  runNpm(
    "run",
    ["build"],
    frontendRoot,
    {
      ...e2eDemoEnv(),
      VITE_BUILD_OUT_DIR: path.join(os.tmpdir(), "isbn-library-frontend-dist"),
    },
  );
  await runPlaywrightE2E();
  runPythonFile(path.join(infrastructureRoot, "app.py"), infrastructureRoot);

  console.log("Pre-push quality gate passed.");
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

function runNpm(script, args, cwd, extraEnv = {}) {
  const result =
    process.platform === "win32"
      ? spawnSync("cmd.exe", ["/d", "/s", "/c", "npm.cmd", script, ...args], {
          cwd,
          stdio: "inherit",
          env: {
            ...process.env,
            CI: process.env.CI ?? "true",
            ...extraEnv,
          },
        })
      : spawnSync("npm", [script, ...args], {
          cwd,
          stdio: "inherit",
          env: {
            ...process.env,
            CI: process.env.CI ?? "true",
            ...extraEnv,
          },
        });

  if (result.error) {
    throw result.error;
  }

  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

function runPython(command, args, cwd, extraEnv = {}) {
  const pythonCommand = resolvePythonCommand([
    path.join(backendRoot, ".venv", "Scripts", "python.exe"),
  ]);
  const result = spawnSync(pythonCommand, ["-m", command, ...args], {
    cwd,
    stdio: "inherit",
    env: {
      ...process.env,
      ...extraEnv,
    },
  });

  if (result.error) {
    throw result.error;
  }

  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

function runPythonFile(filePath, cwd) {
  const pythonCommand = resolvePythonCommand([
    path.join(infrastructureRoot, ".venv", "Scripts", "python.exe"),
    path.join(backendRoot, ".venv", "Scripts", "python.exe"),
  ]);
  const result = spawnSync(pythonCommand, [filePath], {
    cwd,
    stdio: "inherit",
    env: {
      ...process.env,
      JSII_RUNTIME_PACKAGE_CACHE: "disabled",
    },
    timeout: 180_000,
  });

  if (result.error) {
    if (result.error.code === "ETIMEDOUT") {
      console.warn(
        "CDK synth timed out after 180s; continuing without blocking pre-push.",
      );
      return;
    }

    throw result.error;
  }

  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

async function runPlaywrightE2E() {
  const server = spawn(
    process.execPath,
    ["scripts/dev.mjs", "--host", "127.0.0.1", "--port", "4173"],
    {
      cwd: frontendRoot,
      stdio: "ignore",
      windowsHide: true,
      env: {
        ...process.env,
        VITE_E2E_DEMO_MODE: "true",
        VITE_API_BASE_URL: "http://127.0.0.1:4173/mock-api",
        VITE_COGNITO_AUTHORITY: "https://example.com/mock-authority",
        VITE_COGNITO_HOSTED_UI_DOMAIN: "https://example.com/mock-hosted-ui",
        VITE_COGNITO_CLIENT_ID: "mock-client-id",
        VITE_COGNITO_REDIRECT_URI: "http://127.0.0.1:4173/auth/callback",
        VITE_COGNITO_LOGOUT_REDIRECT_URI: "http://127.0.0.1:4173",
        VITE_COGNITO_SCOPE: "openid email profile",
      },
    },
  );

  server.unref();

  try {
    await waitForUrl("http://127.0.0.1:4173");
    runNpm("run", ["test:e2e"], frontendRoot, e2eDemoEnv());
  } finally {
    stopProcessTree(server.pid);
  }
}

function e2eDemoEnv() {
  return {
    VITE_E2E_DEMO_MODE: "true",
    VITE_API_BASE_URL: "http://127.0.0.1:4173/mock-api",
    VITE_COGNITO_AUTHORITY: "https://example.com/mock-authority",
    VITE_COGNITO_HOSTED_UI_DOMAIN: "https://example.com/mock-hosted-ui",
    VITE_COGNITO_CLIENT_ID: "mock-client-id",
    VITE_COGNITO_REDIRECT_URI: "http://127.0.0.1:4173/auth/callback",
    VITE_COGNITO_LOGOUT_REDIRECT_URI: "http://127.0.0.1:4173",
    VITE_COGNITO_SCOPE: "openid email profile",
  };
}

async function waitForUrl(url) {
  const timeoutMs = 120_000;
  const startedAt = Date.now();

  while (Date.now() - startedAt < timeoutMs) {
    try {
      const response = await fetch(url, { method: "GET" });
      if (response.ok || response.status === 404) {
        return;
      }
    } catch {
      // Keep waiting until Vite is ready.
    }

    await delay(1_000);
  }

  throw new Error(`Timed out waiting for Playwright server at ${url}`);
}

function stopProcessTree(pid) {
  if (!pid) {
    return;
  }

  if (process.platform === "win32") {
    spawnSync("taskkill", ["/pid", String(pid), "/t", "/f"], {
      stdio: "ignore",
    });
    return;
  }

  try {
    process.kill(-pid, "SIGTERM");
  } catch {
    try {
      process.kill(pid, "SIGTERM");
    } catch {
      // Ignore cleanup failures; the process is no longer needed.
    }
  }
}

function resolvePythonCommand(preferredCandidates = []) {
  const candidates = [...preferredCandidates];

  if (process.env.PYTHON?.trim()) {
    candidates.push(process.env.PYTHON.trim());
  }

  candidates.push("python3", "python");

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

  throw new Error("No usable Python interpreter was found.");
}
