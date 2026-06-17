const fs = require("fs");
const path = require("path");
const { syncLocaleAssets } = require("./sync-locales");

const SUPPORTED_LOCALES = ["en", "pt-br", "zh-cn"];
const FALLBACK_LOCALE = "en";
const DEFAULT_DATA_ROOT = process.env.RELEASE_BRIEFING_DATA_ROOT || "/app/data";
const DEFAULT_OUTPUT_ROOT =
  process.env.RELEASE_BRIEFING_OUTPUT_ROOT || "/app/workspace/output";

function normalizeLocale(locale) {
  return String(locale || FALLBACK_LOCALE)
    .trim()
    .toLowerCase()
    .replace(/_/g, "-");
}

function resolveSupportedLocale(locale) {
  const normalized = normalizeLocale(locale);
  if (SUPPORTED_LOCALES.includes(normalized)) {
    return normalized;
  }

  if (normalized === "pt" || normalized.startsWith("pt-")) {
    return "pt-br";
  }
  if (normalized === "zh" || normalized.startsWith("zh-")) {
    return "zh-cn";
  }
  if (normalized === "en" || normalized.startsWith("en-")) {
    return "en";
  }

  return FALLBACK_LOCALE;
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function readRequest(dataRoot = DEFAULT_DATA_ROOT, requestPath) {
  const resolved = requestPath || path.join(dataRoot, "briefing_request.json");
  return readJson(resolved);
}

function readRelease(dataRoot = DEFAULT_DATA_ROOT, version) {
  return readJson(path.join(dataRoot, "releases", `${version}.json`));
}

function readTerms(dataRoot = DEFAULT_DATA_ROOT, locale) {
  const resolvedLocale = resolveSupportedLocale(locale);
  const localizedPath = path.join(dataRoot, "locales", resolvedLocale, "briefing_terms.json");
  if (fs.existsSync(localizedPath)) {
    return readJson(localizedPath);
  }

  return readJson(path.join(dataRoot, "locales", FALLBACK_LOCALE, "briefing_terms.json"));
}

function readBundle(extensionRoot, locale) {
  const englishPath = path.join(extensionRoot, "l10n", "bundle.l10n.json");
  const english = readJson(englishPath);
  const resolvedLocale = resolveSupportedLocale(locale);
  const localizedPath =
    resolvedLocale === FALLBACK_LOCALE
      ? englishPath
      : path.join(extensionRoot, "l10n", `bundle.l10n.${resolvedLocale}.json`);

  if (localizedPath === englishPath || !fs.existsSync(localizedPath)) {
    return english;
  }

  return {
    ...english,
    ...readJson(localizedPath)
  };
}

function pickText(entry, locale) {
  if (typeof entry === "string") {
    return entry;
  }
  if (!entry || typeof entry !== "object") {
    return "";
  }

  const resolvedLocale = resolveSupportedLocale(locale);
  const normalizedEntries = Object.fromEntries(
    Object.entries(entry).map(([key, value]) => [normalizeLocale(key), value])
  );

  if (normalizedEntries[resolvedLocale]) {
    return normalizedEntries[resolvedLocale];
  }

  const base = resolvedLocale.split("-")[0];
  const baseMatch = Object.entries(normalizedEntries).find(
    ([key]) => key === base || key.startsWith(`${base}-`)
  );
  if (baseMatch) {
    return baseMatch[1];
  }

  return normalizedEntries[FALLBACK_LOCALE] || Object.values(normalizedEntries)[0] || "";
}

function formatPattern(pattern, values) {
  return values.reduce(
    (output, value, index) => output.replaceAll(`{${index}}`, String(value)),
    pattern
  );
}

function resolveOutputRoot(options = {}) {
  if (options.outputRoot) {
    return options.outputRoot;
  }
  if (process.env.RELEASE_BRIEFING_OUTPUT_ROOT) {
    return process.env.RELEASE_BRIEFING_OUTPUT_ROOT;
  }
  if (options.workspaceRoot && options.outputFolder) {
    return path.isAbsolute(options.outputFolder)
      ? options.outputFolder
      : path.join(options.workspaceRoot, options.outputFolder);
  }
  return DEFAULT_OUTPUT_ROOT;
}

function getRequestedLocales(request) {
  const configured =
    Array.isArray(request?.target_locales) && request.target_locales.length > 0
      ? request.target_locales
      : SUPPORTED_LOCALES;
  const seen = new Set();
  const locales = [];

  for (const locale of configured) {
    const resolved = resolveSupportedLocale(locale);
    if (!seen.has(resolved)) {
      seen.add(resolved);
      locales.push(resolved);
    }
  }

  return locales;
}

function getFocusNames(request, terms) {
  return request.focus_areas.map((focus) => terms.focus_names[focus] || focus);
}

function selectHighlights(release, request) {
  return release.highlights
    .filter((highlight) => request.focus_areas.includes(highlight.focus))
    .slice(0, request.max_highlights_per_version);
}

function renderHighlightBlock(highlight, locale, terms, bundle, lines) {
  lines.push(`### ${pickText(highlight.title, locale)}`);
  lines.push("");
  lines.push(formatPattern(bundle["Focus: {0}"], [terms.focus_names[highlight.focus] || highlight.focus]));
  lines.push("");
  lines.push(pickText(highlight.summary, locale));
  lines.push("");
  lines.push(`- ${formatPattern(bundle["Recommended action: {0}"], [pickText(highlight.action, locale)])}`);
  lines.push("");
}

function renderBriefing(locale, request, releases, terms, bundle) {
  const lines = [];

  lines.push(`# ${pickText(request.title, locale)}`);
  lines.push("");
  lines.push(`- ${terms.labels.audience}: ${pickText(request.audience, locale)}`);
  lines.push(`- ${terms.labels.versions}: ${request.versions.join(", ")}`);
  lines.push(`- ${terms.labels.focus_areas}: ${getFocusNames(request, terms).join(", ")}`);
  lines.push("");
  lines.push(`## ${bundle["Overview"]}`);
  lines.push(terms.summary_template.replace("{audience}", pickText(request.audience, locale)));
  lines.push("");
  lines.push(`## ${bundle["Highlights"]}`);
  lines.push("");

  for (const release of releases) {
    const selected = selectHighlights(release, request);
    lines.push(`### VS Code ${release.version}`);
    lines.push(`- ${bundle["Published"]}: ${release.published}`);
    if (selected.length === 0) {
      lines.push(`- ${bundle["No highlights matched the selected focus areas."]}`);
    } else {
      for (const highlight of selected) {
        lines.push(`- **${pickText(highlight.title, locale)}**: ${pickText(highlight.summary, locale)}`);
      }
    }
    lines.push("");
  }

  lines.push(`## ${bundle["Action items"]}`);
  for (const release of releases) {
    for (const highlight of selectHighlights(release, request)) {
      lines.push(`- ${pickText(highlight.action, locale)}`);
    }
  }
  lines.push("");
  lines.push(`> ${bundle["Generated with"]}: ${bundle["Release Briefing Explorer"]}`);
  lines.push("");
  return lines.join("\n");
}

function buildBriefings(options = {}) {
  const extensionRoot = options.extensionRoot || path.resolve(__dirname, "..");
  const dataRoot = options.dataRoot || DEFAULT_DATA_ROOT;
  syncLocaleAssets({ extensionRoot, dataRoot });
  const request = readRequest(dataRoot, options.requestPath);
  const outputRoot = resolveOutputRoot(options);
  const releases = request.versions.map((version) => readRelease(dataRoot, version));

  fs.mkdirSync(outputRoot, { recursive: true });
  const results = [];

  for (const locale of getRequestedLocales(request)) {
    const terms = readTerms(dataRoot, locale);
    const bundle = readBundle(extensionRoot, locale);
    const content = renderBriefing(locale, request, releases, terms, bundle);
    const outputPath = path.join(outputRoot, `release-briefing.${locale}.md`);
    fs.writeFileSync(outputPath, content, "utf8");
    results.push(outputPath);
  }

  return results;
}

function getReleaseIndex(dataRoot = DEFAULT_DATA_ROOT, requestPath) {
  const request = readRequest(dataRoot, requestPath);
  return request.versions.map((version) => {
    const release = readRelease(dataRoot, version);
    return {
      version: release.version,
      published: release.published,
      highlightCount: release.highlights.length
    };
  });
}

function renderReleaseNote(
  version,
  locale,
  dataRoot = DEFAULT_DATA_ROOT,
  extensionRoot = path.resolve(__dirname, ".."),
  requestPath
) {
  const request = readRequest(dataRoot, requestPath);
  const release = readRelease(dataRoot, version);
  syncLocaleAssets({ extensionRoot, dataRoot });
  const terms = readTerms(dataRoot, locale);
  const bundle = readBundle(extensionRoot, locale);
  const lines = [];
  const inScope = selectHighlights(release, request);
  const additional = release.highlights.filter((highlight) => !inScope.includes(highlight));

  lines.push(`# VS Code ${release.version}`);
  lines.push("");
  lines.push(`- ${bundle["Published"]}: ${release.published}`);
  lines.push(`- ${terms.labels.focus_areas}: ${getFocusNames(request, terms).join(", ")}`);
  lines.push("");
  lines.push(`## ${bundle["Highlights in briefing scope"]}`);
  lines.push("");

  if (inScope.length === 0) {
    lines.push(bundle["No highlights matched the selected focus areas."]);
    lines.push("");
  } else {
    for (const highlight of inScope) {
      renderHighlightBlock(highlight, locale, terms, bundle, lines);
    }
  }

  if (additional.length > 0) {
    lines.push(`## ${bundle["Additional snapshot highlights"]}`);
    lines.push("");
    for (const highlight of additional) {
      renderHighlightBlock(highlight, locale, terms, bundle, lines);
    }
  }

  return lines.join("\n");
}

module.exports = {
  DEFAULT_DATA_ROOT,
  DEFAULT_OUTPUT_ROOT,
  FALLBACK_LOCALE,
  SUPPORTED_LOCALES,
  buildBriefings,
  formatPattern,
  getReleaseIndex,
  getRequestedLocales,
  normalizeLocale,
  pickText,
  readBundle,
  readRequest,
  readTerms,
  renderBriefing,
  renderReleaseNote,
  resolveOutputRoot,
  resolveSupportedLocale,
  selectHighlights
};
