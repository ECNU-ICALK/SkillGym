import express from "express";
import { getAppRuntimeBundle } from "../../next-runtime.webpack-config.js";

import { getRuntimeModule } from "./render-runtime.js";
import {
  getScenario,
  loadRoutes,
  resolveConfigPath,
  resolveRouteDataPath,
  routeDigest
} from "../shared/task-context.js";
import { loadUserConfig, readRawConfig } from "./config-schema.js";
import { resolveConfig, toRuntimeConfig } from "./config-shared.js";

export function applyRuntimeEnv(config: ReturnType<typeof toRuntimeConfig>): void {
  const runtimeBundle = getAppRuntimeBundle({
    segmentCache: config.experimental.segmentCache
  });

  process.env.__FRAMEWORK_CACHE_COMPONENTS__ = String(config.experimental.cacheComponents);
  process.env.__FRAMEWORK_AUTH_INTERRUPTS__ = String(config.experimental.authInterrupts);
  process.env.__FRAMEWORK_SEGMENT_CACHE__ = String(config.experimental.segmentCache);
  process.env.__FRAMEWORK_RUNTIME_VARIANT__ = runtimeBundle.runtimeVariant;
  process.env.__FRAMEWORK_APP_BUNDLE_ID__ = runtimeBundle.bundleId;
}

export function createRuntimeReport(scenarioId?: string) {
  const scenario = getScenario(scenarioId);
  const configPath = resolveConfigPath(scenario);
  const routeDataPath = resolveRouteDataPath(scenario);
  const rawConfig = readRawConfig(configPath) as {
    experimental?: { segmentCache?: boolean };
  };
  const resolvedConfig = resolveConfig(loadUserConfig(configPath));
  const runtimeConfig = toRuntimeConfig(resolvedConfig);
  const routes = loadRoutes(routeDataPath);

  applyRuntimeEnv(runtimeConfig);

  const runtimeModule = getRuntimeModule();
  const summary = runtimeModule.describeRouteGroups(routes, runtimeConfig);

  return {
    scenarioId: scenario.id,
    routeDigest: routeDigest(routes),
    requestedSegmentCache: Boolean(rawConfig.experimental?.segmentCache),
    resolvedSegmentCache: Boolean(resolvedConfig.experimental.segmentCache),
    runtimeSegmentCache: process.env.__FRAMEWORK_SEGMENT_CACHE__ === "true",
    routeCount: routes.length,
    summary
  };
}

export function startDevServer(): void {
  const app = express();
  const port = Number(process.env.PORT || "3000");

  app.get("/health", (_request, response) => {
    response.json({ ok: true });
  });

  app.get("/api/runtime-report", (_request, response) => {
    response.json(createRuntimeReport());
  });

  app.listen(port, () => {
    console.log(`framework dev server listening on ${port}`);
  });
}
