import * as baselineRuntime from "./baseline-runtime.js";

const runtimeVariants = {
  baseline: baselineRuntime
};

export function getRuntimeModule() {
  const bundleId = process.env.__FRAMEWORK_APP_BUNDLE_ID__;
  if (bundleId && runtimeVariants[bundleId]) {
    return runtimeVariants[bundleId];
  }

  const variant = process.env.__FRAMEWORK_RUNTIME_VARIANT__ || "baseline";
  return runtimeVariants[variant] || baselineRuntime;
}
