import { execFileSync } from "node:child_process";

try {
  execFileSync("git", ["config", "--local", "core.hooksPath", ".husky"], {
    stdio: "inherit",
  });
  console.log("Configured git hooks path to .husky.");
} catch (error) {
  console.error("Failed to configure git hooks path.");
  throw error;
}

