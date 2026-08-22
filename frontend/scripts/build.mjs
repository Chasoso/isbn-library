import { build } from "vite";
import path from "node:path";
import viteConfig from "../vite.config.js";

const outDir = process.env.VITE_BUILD_OUT_DIR
  ? path.resolve(process.env.VITE_BUILD_OUT_DIR)
  : path.join(process.cwd(), "dist");

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
