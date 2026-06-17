import { readFile } from "node:fs/promises";

const mode = process.argv[2] || "lint";

const dockerfile = await readFile(new URL("../../Dockerfile", import.meta.url), "utf8");
const server = await readFile(new URL("../../app/server.mjs", import.meta.url), "utf8");

if (!dockerfile.includes("USER node")) {
  throw new Error("Dockerfile must run as the node user");
}

if (!server.includes("/healthz")) {
  throw new Error("server is missing the documented health endpoint");
}

if (mode === "lint" && server.includes("TODO")) {
  throw new Error("server source still contains TODO markers");
}

process.stdout.write(`validate-release-source ${mode} ok\n`);
