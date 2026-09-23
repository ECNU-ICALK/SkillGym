import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { discoverTaskTemplate } from "../src/discovery.js";
import { DEFAULT_OUTPUT_ROOT, REPO_ROOT, TEMPLATE_ROOT } from "../src/utils.js";

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const builderRoot = path.join(repositoryRoot, "task_builder");
const temporaryRoot = await fs.mkdtemp(path.join(os.tmpdir(), "skillgym-paths-"));

try {
  assert.equal(REPO_ROOT, repositoryRoot);
  assert.equal(TEMPLATE_ROOT, path.join(repositoryRoot, "task_templates"));
  assert.equal(DEFAULT_OUTPUT_ROOT, path.join(repositoryRoot, "outputs"));

  const utilsUrl = new URL("../src/utils.ts", import.meta.url).href;
  const discoveryUrl = new URL("../src/discovery.ts", import.meta.url).href;
  const probe = `
    import { REPO_ROOT, TEMPLATE_ROOT, DEFAULT_OUTPUT_ROOT } from ${JSON.stringify(utilsUrl)};
    import { discoverTaskTemplate } from ${JSON.stringify(discoveryUrl)};
    const template = await discoverTaskTemplate("development/frontend/seed_task");
    console.log(JSON.stringify({
      repositoryRoot: REPO_ROOT,
      templateRoot: TEMPLATE_ROOT,
      outputRoot: DEFAULT_OUTPUT_ROOT,
      templateId: template.templateId,
      sourceDir: template.sourceDir,
    }));
  `;

  for (const cwd of [repositoryRoot, builderRoot, temporaryRoot]) {
    const result = spawnSync(
      process.execPath,
      ["--import", import.meta.resolve("tsx"), "--input-type=module", "-e", probe],
      { cwd, encoding: "utf8", timeout: 30_000 },
    );
    assert.ifError(result.error);
    assert.equal(result.status, 0, `Path probe failed from ${cwd}: ${result.stderr}`);
    assert.deepEqual(JSON.parse(result.stdout.trim()), {
      repositoryRoot,
      templateRoot: path.join(repositoryRoot, "task_templates"),
      outputRoot: path.join(repositoryRoot, "outputs"),
      templateId: "development__frontend__seed_task",
      sourceDir: path.join(repositoryRoot, "task_templates", "development/frontend/seed_task"),
    });
  }

  // Explicit external template roots must remain supported.
  const externalRoot = path.join(temporaryRoot, "external_templates");
  const templateDir = path.join(externalRoot, "example", "seed_task");
  for (const directory of ["environment", "tests", "solution"]) {
    await fs.mkdir(path.join(templateDir, directory), { recursive: true });
  }
  await fs.writeFile(path.join(templateDir, "task.toml"), 'id = "example"\n');
  await fs.writeFile(path.join(templateDir, "instruction.md"), "Example task.\n");
  const external = await discoverTaskTemplate("example/seed_task", externalRoot);
  assert.equal(external.sourceDir, templateDir);
  assert.equal(external.templateId, "example__seed_task");
  console.log("repo_paths: root, builder, unrelated cwd and external template root passed");
} finally {
  await fs.rm(temporaryRoot, { recursive: true, force: true });
}
