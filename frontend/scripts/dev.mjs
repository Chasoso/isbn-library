import path from "node:path";
import { createServer } from "vite";
import viteConfig from "../vite.config.js";

const args = process.argv.slice(2);

const readFlag = (flag, fallback) => {
  const index = args.indexOf(flag);
  if (index >= 0 && args[index + 1]) {
    return args[index + 1];
  }

  return fallback;
};

const host = readFlag("--host", "127.0.0.1");
const port = Number(readFlag("--port", "5173"));
const tempDir = process.env.TEMP ?? process.env.TMPDIR ?? process.cwd();
const cacheDir = path.join(tempDir, "isbn-library-frontend-vite-cache");

const server = await createServer({
  ...viteConfig,
  configFile: false,
  cacheDir,
  root: process.cwd(),
  server: {
    ...(viteConfig.server ?? {}),
    host,
    port,
    strictPort: true,
  },
});

await server.listen();
server.printUrls();

const shutdown = async () => {
  process.exit(0);
};

process.on("SIGINT", () => {
  void shutdown();
});

process.on("SIGTERM", () => {
  void shutdown();
});
