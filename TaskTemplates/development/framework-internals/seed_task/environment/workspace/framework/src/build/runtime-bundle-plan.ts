import { getRuntimeBundleTasks } from "../../taskfile.js";
import { getAppRuntimeBundle } from "../../next-runtime.webpack-config.js";

export interface RuntimeBundleManifest {
  selected: {
    bundleType: string;
    bundleId: string;
    runtimeVariant: string;
  };
  availableAppBundles: Array<{
    bundleId: string;
    runtimeVariant: string;
  }>;
  selectedBundleAvailable: boolean;
}

export function createRuntimeBundleManifest(segmentCache: boolean): RuntimeBundleManifest {
  const selected = getAppRuntimeBundle({ segmentCache });
  const availableAppBundles = getRuntimeBundleTasks()
    .filter((task) => task.bundleType === "app")
    .map((task) => ({
      bundleId: task.bundleId,
      runtimeVariant: task.runtimeVariant
    }));

  return {
    selected,
    availableAppBundles,
    selectedBundleAvailable: availableAppBundles.some((task) => task.bundleId === selected.bundleId)
  };
}
