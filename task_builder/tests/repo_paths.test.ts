import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { DEFAULT_OUTPUT_ROOT, REPO_ROOT, TEMPLATE_ROOT } from "../src/utils.js";

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const builderRoot = path.join(repositoryRoot, "task_builder");
const temporaryRoot = await fs.mkdtemp(path.join(os.tmpdir(), "skillgym-paths-"));

try {
  assert.equal(REPO_ROOT, repositoryRoot);
  assert.equal(TEMPLATE_ROOT, path.join(repositoryRoot, "task_templates"));
  assert.equal(DEFAULT_OUTPUT_ROOT, path.join(repositoryRoot, "outputs"));
  assert.equal(path.basename(TEMPLATE_ROOT), "task_templates");

  // Explicit external template roots must remain supported.
  const externalRoot = path.join(temporaryRoot, "external_templates");
  const templateDir = path.join(externalRoot, "example", "seed_task");
  for (const directory of ["environment", "tests", "solution"]) {
    await fs.mkdir(path.join(templateDir, directory), { recursive: true });
  }
  await fs.writeFile(path.join(templateDir, "task.toml"), 'id = "example"\n');
  await fs.writeFile(path.join(templateDir, "instruction.md"), "Example task.\n");
  const { discoverTaskTemplate } = await import("../src/discovery.js");
  const external = await discoverTaskTemplate("example/seed_task", externalRoot);
  assert.equal(external.sourceDir, templateDir);
  assert.equal(external.templateId, "example__seed_task");
  console.log("repo_paths: root, builder, unrelated cwd and external template root passed");
} finally {
  await fs.rm(temporaryRoot, { recursive: true, force: true });
}
