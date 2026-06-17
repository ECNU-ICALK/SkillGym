import * as baselineRuntime from "./baseline-runtime.js";
import * as segmentCacheRuntime from "./segment-cache-runtime.js";

const runtimeVariants = {
  "app-baseline": baselineRuntime,
  "app-segment-cache": segmentCacheRuntime,
  baseline: baselineRuntime,
  "segment-cache": segmentCacheRuntime
};

export function getRuntimeModule() {
  const bundleId = process.env.__FRAMEWORK_APP_BUNDLE_ID__;
  if (bundleId && runtimeVariants[bundleId]) {
    return runtimeVariants[bundleId];
  }

  const variant = process.env.__FRAMEWORK_RUNTIME_VARIANT__ || "baseline";
  return runtimeVariants[variant] || baselineRuntime;
}
