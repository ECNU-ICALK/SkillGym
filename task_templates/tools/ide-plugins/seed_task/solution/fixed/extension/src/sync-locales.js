const fs = require("fs");
const path = require("path");

const SUPPORTED_LOCALES = ["en", "pt-br", "zh-cn"];
const DEFAULT_DATA_ROOT = process.env.RELEASE_BRIEFING_DATA_ROOT || "/app/data";

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function writeJson(filePath, payload) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
}

function writeText(filePath, content) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, content, "utf8");
}

function readLocaleCopy(dataRoot, locale) {
  const filePath = path.join(dataRoot, "locales", locale, "extension_copy.json");
  if (!fs.existsSync(filePath)) {
    throw new Error(`missing locale copy: ${filePath}`);
  }
  return readJson(filePath);
}

function manifestRelativePath(copy, key) {
  return copy.package[key].replace(/^\.\//, "");
}

function syncLocaleAssets(options = {}) {
  const extensionRoot = options.extensionRoot || path.resolve(__dirname, "..");
  const dataRoot = options.dataRoot || DEFAULT_DATA_ROOT;
  const written = [];

  for (const locale of SUPPORTED_LOCALES) {
    const copy = readLocaleCopy(dataRoot, locale);
    const packageFile =
      locale === "en"
        ? path.join(extensionRoot, "package.nls.json")
        : path.join(extensionRoot, `package.nls.${locale}.json`);
    const bundleFile =
      locale === "en"
        ? path.join(extensionRoot, "l10n", "bundle.l10n.json")
        : path.join(extensionRoot, "l10n", `bundle.l10n.${locale}.json`);

    writeJson(packageFile, copy.package);
    writeJson(bundleFile, copy.bundle);
    writeText(
      path.join(extensionRoot, manifestRelativePath(copy, "walkthrough.step.browse.markdown")),
      copy.walkthrough.browse
    );
    writeText(
      path.join(extensionRoot, manifestRelativePath(copy, "walkthrough.step.export.markdown")),
      copy.walkthrough.export
    );
    writeText(
      path.join(extensionRoot, manifestRelativePath(copy, "walkthrough.step.package.markdown")),
      copy.walkthrough.package
    );

    written.push(packageFile, bundleFile);
    written.push(path.join(extensionRoot, manifestRelativePath(copy, "walkthrough.step.browse.markdown")));
    written.push(path.join(extensionRoot, manifestRelativePath(copy, "walkthrough.step.export.markdown")));
    written.push(path.join(extensionRoot, manifestRelativePath(copy, "walkthrough.step.package.markdown")));
  }

  return written;
}

if (require.main === module) {
  syncLocaleAssets();
}

module.exports = {
  SUPPORTED_LOCALES,
  syncLocaleAssets
};
