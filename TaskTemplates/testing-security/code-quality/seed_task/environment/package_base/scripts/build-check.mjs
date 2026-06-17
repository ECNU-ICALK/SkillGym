import { mkdtempSync, rmSync, existsSync, readdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

const outDir = mkdtempSync(join(tmpdir(), "toolchain-release-build-"));
const result = spawnSync(
  "npx",
  ["tsc", "--project", "tsconfig.json", "--outDir", outDir, "--pretty", "false"],
  {
    stdio: "pipe",
    encoding: "utf-8",
  }
);

if (result.stdout) {
  process.stdout.write(result.stdout);
}
if (result.stderr) {
  process.stderr.write(result.stderr);
}

if (result.status !== 0) {
  rmSync(outDir, { recursive: true, force: true });
  process.exit(result.status ?? 1);
}

const srcOutDir = join(outDir, "src");
const builtFiles = existsSync(srcOutDir)
  ? readdirSync(srcOutDir).filter((entry) => entry.endsWith(".js")).length
  : 0;
process.stdout.write(`Build check succeeded. Temporary output: ${outDir}. Built JS files: ${builtFiles}.\n`);
rmSync(outDir, { recursive: true, force: true });
