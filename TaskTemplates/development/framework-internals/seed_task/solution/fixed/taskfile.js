const sharedRuntimeTasks = [
  {
    bundleType: "server",
    bundleId: "server-baseline",
    runtimeVariant: "baseline"
  },
  {
    bundleType: "server",
    bundleId: "server-dev",
    runtimeVariant: "baseline"
  },
  {
    bundleType: "server",
    bundleId: "server-prod",
    runtimeVariant: "baseline"
  },
  {
    bundleType: "server",
    bundleId: "server-experimental",
    runtimeVariant: "experimental"
  },
  {
    bundleType: "pages",
    bundleId: "pages-baseline",
    runtimeVariant: "baseline"
  },
  {
    bundleType: "pages",
    bundleId: "pages-dev",
    runtimeVariant: "baseline"
  },
  {
    bundleType: "app-route",
    bundleId: "app-route-baseline",
    runtimeVariant: "baseline"
  },
  {
    bundleType: "app-route",
    bundleId: "app-route-dev",
    runtimeVariant: "baseline"
  }
];

export function getRuntimeBundleTasks() {
  return [
    ...sharedRuntimeTasks,
    {
      bundleType: "app",
      bundleId: "app-baseline",
      runtimeVariant: "baseline"
    },
    {
      bundleType: "app",
      bundleId: "app-segment-cache",
      runtimeVariant: "segment-cache"
    }
  ];
}
