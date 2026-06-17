import path from "node:path";
import { getAppRuntimeBundle } from "../../next-runtime.webpack-config.js";

import { getRuntimeModule } from "../server/render-runtime.js";
import {
  OUTPUT_ROOT,
  ensureDir,
  loadRoutes,
  resolveConfigPath,
  resolveRouteDataPath,
  routeDigest,
  writeJsonFile,
  type ScenarioDefinition
} from "../shared/task-context.js";
import { loadUserConfig, readRawConfig } from "../server/config-schema.js";
import { resolveConfig, toRuntimeConfig } from "../server/config-shared.js";

export interface ExportSummary {
  scenarioId: string;
  requestedSegmentCache: boolean;
  resolvedSegmentCache: boolean;
  exportMode: string;
  routeDigest: string;
  groupCount: number;
  reusedSegmentCount: number;
}

export function applyExportEnv(config: ReturnType<typeof toRuntimeConfig>): void {
  const runtimeBundle = getAppRuntimeBundle({
    segmentCache: config.experimental.segmentCache
  });

  process.env.__FRAMEWORK_CACHE_COMPONENTS__ = String(config.experimental.cacheComponents);
  process.env.__FRAMEWORK_AUTH_INTERRUPTS__ = String(config.experimental.authInterrupts);
  process.env.__FRAMEWORK_SEGMENT_CACHE__ = String(config.experimental.segmentCache);
  process.env.__FRAMEWORK_RUNTIME_VARIANT__ = runtimeBundle.runtimeVariant;
  process.env.__FRAMEWORK_APP_BUNDLE_ID__ = runtimeBundle.bundleId;
}

export function exportScenarioSummary(scenario: ScenarioDefinition): ExportSummary {
  const configPath = resolveConfigPath(scenario);
  const routeDataPath = resolveRouteDataPath(scenario);
  const rawConfig = readRawConfig(configPath) as {
    experimental?: { segmentCache?: boolean };
  };
  const resolvedConfig = resolveConfig(loadUserConfig(configPath));
  const runtimeConfig = toRuntimeConfig(resolvedConfig);
  const routes = loadRoutes(routeDataPath);

  applyExportEnv(runtimeConfig);

  const runtimeModule = getRuntimeModule();
  const summary = runtimeModule.describeRouteGroups(routes, runtimeConfig);
  const outputDir = path.join(OUTPUT_ROOT, "export", scenario.id);
  ensureDir(outputDir);

  const payload: ExportSummary = {
    scenarioId: scenario.id,
    requestedSegmentCache: Boolean(rawConfig.experimental?.segmentCache),
    resolvedSegmentCache: Boolean(resolvedConfig.experimental.segmentCache),
    exportMode: summary.mode,
    routeDigest: routeDigest(routes),
    groupCount: summary.groupCount,
    reusedSegmentCount: summary.reusedSegmentCount
  };

  writeJsonFile(path.join(outputDir, "segment-summary.json"), payload);
  return payload;
}
