import { build } from "vite";
import path from "node:path";
import viteConfig from "../vite.config.js";

const tempDir = process.env.TEMP ?? process.env.TMPDIR ?? process.cwd();
const outDir = path.join(tempDir, "isbn-library-frontend-build");

await build({
  ...viteConfig,
  configFile: false,
  build: {
    ...(viteConfig.build ?? {}),
    outDir,
    emptyOutDir: true,
  },
  root: process.cwd(),
});
