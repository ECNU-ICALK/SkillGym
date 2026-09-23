import type { FrameworkConfig } from "../server/config-shared.js";
import { getRuntimeDefineEntries } from "../../next-runtime.webpack-config.js";

export interface BuildEnvMap {
  __FRAMEWORK_CACHE_COMPONENTS__: string;
  __FRAMEWORK_AUTH_INTERRUPTS__: string;
  __FRAMEWORK_SEGMENT_CACHE__: string;
  __FRAMEWORK_RUNTIME_VARIANT__: string;
  __FRAMEWORK_APP_BUNDLE_ID__: string;
}

export function createBuildEnv(config: FrameworkConfig): BuildEnvMap {
  const runtimeDefines = getRuntimeDefineEntries("app", {
    segmentCache: config.experimental.segmentCache
  });

  return {
    __FRAMEWORK_CACHE_COMPONENTS__: String(config.experimental.cacheComponents),
    __FRAMEWORK_AUTH_INTERRUPTS__: String(config.experimental.authInterrupts),
    __FRAMEWORK_SEGMENT_CACHE__: runtimeDefines.__FRAMEWORK_SEGMENT_CACHE__ || String(config.experimental.segmentCache),
    __FRAMEWORK_RUNTIME_VARIANT__: runtimeDefines.__FRAMEWORK_RUNTIME_VARIANT__ || "baseline",
    __FRAMEWORK_APP_BUNDLE_ID__: runtimeDefines.__FRAMEWORK_APP_BUNDLE_ID__ || "app-baseline"
  };
}
