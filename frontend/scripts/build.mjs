import { build } from "vite";
import path from "node:path";
import viteConfig from "../vite.config.js";

const outDir = path.join(process.cwd(), "dist");

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
