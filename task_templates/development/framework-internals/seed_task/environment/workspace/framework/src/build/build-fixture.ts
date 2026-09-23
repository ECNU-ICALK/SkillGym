import fs from "node:fs";
import path from "node:path";

import { createBuildEnv } from "./define-env-plugin.js";
import { createRuntimeBundleManifest } from "./runtime-bundle-plan.js";
import { getRuntimeDefineEntries } from "../../next-runtime.webpack-config.js";
import { exportScenarioSummary } from "../export/worker.js";
import { getRuntimeModule as getBuildRuntimeModule } from "../compiled/module.compiled.js";
import {
  OUTPUT_ROOT,
  ensureDir,
  getScenario,
  loadRoutes,
  resolveConfigPath,
  resolveRouteDataPath,
  routeDigest
} from "../shared/task-context.js";
import { loadUserConfig, readRawConfig } from "../server/config-schema.js";
import { resolveConfig } from "../server/config-shared.js";

export interface BuildResult {
  scenarioId: string;
  requestedSegmentCache: boolean;
  resolvedSegmentCache: boolean;
  buildSegmentCache: boolean;
  exportMode: string;
  routeDigest: string;
  groupCount: number;
  reusedSegmentCount: number;
}

export interface BuildDiagnostics {
  appRuntimeDefineKeys: string[];
  serverRuntimeDefineKeys: string[];
}

export function buildScenarioArtifacts(scenarioId?: string): BuildResult {
  const scenario = getScenario(scenarioId);
  const configPath = resolveConfigPath(scenario);
  const routeDataPath = resolveRouteDataPath(scenario);
  const rawConfig = readRawConfig(configPath) as {
    experimental?: { segmentCache?: boolean };
  };
  const resolvedConfig = resolveConfig(loadUserConfig(configPath));
  const routes = loadRoutes(routeDataPath);
  const buildEnv = createBuildEnv(resolvedConfig);
  const buildFlags = {
    cacheComponents: buildEnv.__FRAMEWORK_CACHE_COMPONENTS__ === "true",
    authInterrupts: buildEnv.__FRAMEWORK_AUTH_INTERRUPTS__ === "true",
    segmentCache: (buildEnv as Record<string, string>).__FRAMEWORK_SEGMENT_CACHE__ === "true",
    runtimeVariant: (buildEnv as Record<string, string>).__FRAMEWORK_RUNTIME_VARIANT__ || "baseline"
  };

  const buildDir = path.join(OUTPUT_ROOT, "build", scenario.id);
  ensureDir(buildDir);

  process.env.__FRAMEWORK_CACHE_COMPONENTS__ = buildEnv.__FRAMEWORK_CACHE_COMPONENTS__;
  process.env.__FRAMEWORK_AUTH_INTERRUPTS__ = buildEnv.__FRAMEWORK_AUTH_INTERRUPTS__;
  process.env.__FRAMEWORK_SEGMENT_CACHE__ = buildEnv.__FRAMEWORK_SEGMENT_CACHE__;
  process.env.__FRAMEWORK_RUNTIME_VARIANT__ = buildEnv.__FRAMEWORK_RUNTIME_VARIANT__;
  process.env.__FRAMEWORK_APP_BUNDLE_ID__ = buildEnv.__FRAMEWORK_APP_BUNDLE_ID__;

  const buildPreview = getBuildRuntimeModule().describeRouteGroups(routes, resolvedConfig);
  const runtimeDefineSnapshot = {
    app: getRuntimeDefineEntries("app", {
      segmentCache: buildFlags.segmentCache
    }),
    server: getRuntimeDefineEntries("server", {
      segmentCache: buildFlags.segmentCache
    })
  };

  fs.writeFileSync(
    path.join(buildDir, "runtime-flags.js"),
    `window.__FRAMEWORK_FLAGS__ = ${JSON.stringify(buildFlags, null, 2)};\n`,
    "utf-8"
  );

  fs.writeFileSync(
    path.join(buildDir, "build-manifest.json"),
    `${JSON.stringify(
      {
        scenarioId: scenario.id,
        buildFlags,
        routeDigest: routeDigest(routes)
      },
      null,
      2
    )}\n`,
    "utf-8"
  );

  fs.writeFileSync(
    path.join(buildDir, "runtime-bundle-manifest.json"),
    `${JSON.stringify(createRuntimeBundleManifest(buildFlags.segmentCache), null, 2)}\n`,
    "utf-8"
  );

  fs.writeFileSync(path.join(buildDir, "build-preview.json"), `${JSON.stringify(buildPreview, null, 2)}\n`, "utf-8");

  fs.writeFileSync(
    path.join(buildDir, "runtime-define-snapshot.json"),
    `${JSON.stringify(runtimeDefineSnapshot, null, 2)}\n`,
    "utf-8"
  );

  const exportSummary = exportScenarioSummary(scenario);

  return {
    scenarioId: scenario.id,
    requestedSegmentCache: Boolean(rawConfig.experimental?.segmentCache),
    resolvedSegmentCache: Boolean((resolvedConfig.experimental as Record<string, unknown>).segmentCache),
    buildSegmentCache: buildFlags.segmentCache,
    exportMode: exportSummary.exportMode,
    routeDigest: exportSummary.routeDigest,
    groupCount: exportSummary.groupCount,
    reusedSegmentCount: exportSummary.reusedSegmentCount
  };
}

export function readBuildDiagnostics(scenarioId: string): BuildDiagnostics {
  const buildDir = path.join(OUTPUT_ROOT, "build", scenarioId);
  const snapshot = JSON.parse(
    fs.readFileSync(path.join(buildDir, "runtime-define-snapshot.json"), "utf-8")
  ) as Record<string, Record<string, string>>;

  return {
    appRuntimeDefineKeys: Object.keys(snapshot.app || {}).sort(),
    serverRuntimeDefineKeys: Object.keys(snapshot.server || {}).sort()
  };
}
