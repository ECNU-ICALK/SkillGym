export function getAppRuntimeBundle({ segmentCache = false } = {}) {
  return segmentCache
    ? {
        bundleType: "app",
        bundleId: "app-segment-cache",
        runtimeVariant: "segment-cache"
      }
    : {
        bundleType: "app",
        bundleId: "app-baseline",
        runtimeVariant: "baseline"
      };
}

export function getRuntimeDefineEntries(bundleType, { segmentCache = false } = {}) {
  const runtimeBundle = getAppRuntimeBundle({ segmentCache });
  const bundleDefines = {
    __FRAMEWORK_SEGMENT_CACHE__: String(segmentCache)
  };

  if (bundleType !== "app") {
    return bundleDefines;
  }

  return {
    ...bundleDefines,
    __FRAMEWORK_RUNTIME_VARIANT__: runtimeBundle.runtimeVariant,
    __FRAMEWORK_APP_BUNDLE_ID__: runtimeBundle.bundleId
  };
}
