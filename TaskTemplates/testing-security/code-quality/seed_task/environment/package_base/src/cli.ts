import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";

import { buildDigest } from "./digest.js";

function readOption(name: string): string | undefined {
  const index = process.argv.indexOf(name);
  if (index === -1) {
    return undefined;
  }
  return process.argv[index + 1];
}

async function main(): Promise<void> {
  const outFile = readOption("--out");
  if (!outFile) {
    throw new Error("Expected --out <path>.");
  }

  const repoRoot = resolve(process.cwd());
  const workspaceRoot = resolve(repoRoot, "..");
  const npmDir = join(workspaceRoot, "data", "npm");
  const githubDir = join(workspaceRoot, "data", "github");

  const digest = await buildDigest({
    npmFiles: [
      join(npmDir, "typescript_latest.json"),
      join(npmDir, "eslint_latest.json"),
      join(npmDir, "prettier_latest.json"),
    ],
    githubFiles: [
      join(githubDir, "typescript_releases.json"),
      join(githubDir, "eslint_releases.json"),
      join(githubDir, "prettier_releases.json"),
    ],
    githubRepos: {
      typescript: "microsoft/TypeScript",
      eslint: "eslint/eslint",
      prettier: "prettier/prettier",
    },
  });

  const target = resolve(outFile);
  await mkdir(dirname(target), { recursive: true });
  await writeFile(target, JSON.stringify(digest, null, 2) + "\n", "utf-8");
}

main().catch((error: unknown) => {
  const message = error instanceof Error ? error.stack ?? error.message : String(error);
  process.stderr.write(message + "\n");
  process.exitCode = 1;
});
