import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

const roots = ["src", "scripts"];
const checkedFiles = [];
const violations = [];

function walk(dir) {
  for (const entry of readdirSync(dir)) {
    const fullPath = join(dir, entry);
    const stat = statSync(fullPath);
    if (stat.isDirectory()) {
      walk(fullPath);
      continue;
    }

    if (!/\.(ts|mjs|json)$/.test(entry)) {
      continue;
    }

    checkedFiles.push(fullPath);
    const text = readFileSync(fullPath, "utf-8");
    const lines = text.split("\n");
    lines.forEach((line, index) => {
      if (/\s+$/.test(line)) {
        violations.push(`${fullPath}:${index + 1}: trailing whitespace`);
      }
      if (line.includes("\t")) {
        violations.push(`${fullPath}:${index + 1}: tab character`);
      }
    });
  }
}

for (const root of roots) {
  walk(root);
}

if (violations.length > 0) {
  for (const violation of violations) {
    process.stderr.write(violation + "\n");
  }
  process.exit(1);
}

process.stdout.write(`Lint check succeeded across ${checkedFiles.length} source files.\n`);
