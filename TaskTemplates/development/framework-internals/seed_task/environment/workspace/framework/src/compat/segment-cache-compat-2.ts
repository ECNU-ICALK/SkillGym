export const segmentCacheCompatMatrix2 = {
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
