const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function ensureFile(filePath, message) {
  assert(fs.existsSync(filePath), message || `missing file: ${path.relative(ROOT, filePath)}`);
}

function walkthroughPaths(payload) {
  return [
    payload["walkthrough.step.browse.markdown"],
    payload["walkthrough.step.export.markdown"],
    payload["walkthrough.step.package.markdown"],
  ].map((value) => path.join(ROOT, value.replace(/^\.\//, "")));
}

function validateStructure() {
  const manifest = readJson(path.join(ROOT, "package.json"));
  const commandIds = manifest.contributes.commands.map((command) => command.command);
  const activationEvents = new Set(manifest.activationEvents);

  assert(manifest.name, "package.json must define a name");
  assert(manifest.main === "./src/extension.js", "package.json main must point to ./src/extension.js");
  assert(commandIds.includes("releaseBriefing.exportBriefings"), "missing export command");
  assert(commandIds.includes("releaseBriefing.refreshReleaseIndex"), "missing refresh command");
  assert(commandIds.includes("releaseBriefing.openReleaseNote"), "missing open command");
  assert(
    activationEvents.has("onCommand:releaseBriefing.refreshReleaseIndex"),
    "package.json must activate on releaseBriefing.refreshReleaseIndex"
  );

  for (const filePath of [
    "src/extension.js",
    "src/core.js",
    "src/cli-export.js",
    "src/sync-locales.js",
    "package.nls.json",
    "package.nls.pt-br.json",
    "package.nls.zh-cn.json",
    "l10n/bundle.l10n.json",
    "l10n/bundle.l10n.pt-br.json",
    "l10n/bundle.l10n.zh-cn.json"
  ]) {
    ensureFile(path.join(ROOT, filePath), "localized extension resources are incomplete");
  }

  for (const localeFile of [
    "package.nls.json",
    "package.nls.pt-br.json",
    "package.nls.zh-cn.json",
    "l10n/bundle.l10n.json",
    "l10n/bundle.l10n.pt-br.json",
    "l10n/bundle.l10n.zh-cn.json"
  ]) {
    readJson(path.join(ROOT, localeFile));
  }

  for (const localeFile of ["package.nls.json", "package.nls.pt-br.json", "package.nls.zh-cn.json"]) {
    const payload = readJson(path.join(ROOT, localeFile));
    for (const walkthroughPath of walkthroughPaths(payload)) {
      ensureFile(walkthroughPath, "walkthrough localization assets are incomplete");
    }
  }
}

validateStructure();
console.log("validation passed");
