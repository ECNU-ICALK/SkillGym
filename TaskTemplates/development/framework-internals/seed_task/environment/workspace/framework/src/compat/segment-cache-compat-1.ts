export const segmentCacheCompatMatrix1 = {
  experimentalFlag: "segmentCache",
  baseline: {
    runtimeVariant: "baseline",
    exportMode: "baseline"
  },
  enabled: {
    runtimeVariant: "segment-cache",
    exportMode: "segment-cache"
  }
} as const;
