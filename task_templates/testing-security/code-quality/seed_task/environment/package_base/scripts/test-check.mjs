import { readFileSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

const workDir = mkdtempSync(join(tmpdir(), "toolchain-release-test-"));
const outFile = join(workDir, "generated_digest.json");

const cliResult = spawnSync("npx", ["tsx", "src/cli.ts", "--out", outFile], {
  stdio: "pipe",
  encoding: "utf-8",
});

if (cliResult.stdout) {
  process.stdout.write(cliResult.stdout);
}
if (cliResult.stderr) {
  process.stderr.write(cliResult.stderr);
}

if (cliResult.status !== 0) {
  rmSync(workDir, { recursive: true, force: true });
  process.exit(cliResult.status ?? 1);
}

const actual = JSON.parse(readFileSync(outFile, "utf-8"));
const expected = JSON.parse(readFileSync("fixtures/expected_digest.json", "utf-8"));

const checks = [
  ["project_id", actual.project_id === expected.project_id],
  ["package_count", actual.package_count === expected.package_count],
  ["package_names", JSON.stringify(actual.packages.map((entry) => entry.package_name)) === JSON.stringify(expected.packages.map((entry) => entry.package_name))],
  ["version_alignment", JSON.stringify(actual.packages.map((entry) => entry.npm_version)) === JSON.stringify(expected.packages.map((entry) => entry.npm_version))],
  ["tag_alignment", JSON.stringify(actual.packages.map((entry) => entry.github_latest_stable_tag)) === JSON.stringify(expected.packages.map((entry) => entry.github_latest_stable_tag))],
  ["payload_exact_match", JSON.stringify(actual) === JSON.stringify(expected)],
];

const failed = checks.filter(([, passed]) => !passed);
for (const [name, passed] of checks) {
  process.stdout.write(`${passed ? "PASS" : "FAIL"} ${name}\n`);
}

process.stdout.write(`Total checks: ${checks.length}\n`);
process.stdout.write(`Passed: ${checks.length - failed.length}\n`);
process.stdout.write(`Failed: ${failed.length}\n`);

rmSync(workDir, { recursive: true, force: true });

if (failed.length > 0) {
  process.exit(1);
}
