export interface ExperimentalFlags {
  cacheComponents: boolean;
  authInterrupts: boolean;
  segmentCache: boolean;
}

export interface FrameworkConfig {
  siteName: string;
  experimental: ExperimentalFlags;
  render: {
    articleLimit: number;
    defaultSection: string;
  };
}

export interface FrameworkConfigRuntime {
  experimental: Pick<ExperimentalFlags, "cacheComponents" | "authInterrupts" | "segmentCache">;
  render: FrameworkConfig["render"];
}

export const DEFAULT_CONFIG: FrameworkConfig = {
  siteName: "Next Docs Snapshot",
  experimental: {
    cacheComponents: true,
    authInterrupts: false,
    segmentCache: false
  },
  render: {
    articleLimit: 6,
    defaultSection: "config"
  }
};

export function resolveConfig(userConfig: Partial<FrameworkConfig>): FrameworkConfig {
  return {
    siteName: userConfig.siteName ?? DEFAULT_CONFIG.siteName,
    experimental: {
      cacheComponents: userConfig.experimental?.cacheComponents ?? DEFAULT_CONFIG.experimental.cacheComponents,
      authInterrupts: userConfig.experimental?.authInterrupts ?? DEFAULT_CONFIG.experimental.authInterrupts,
      segmentCache: userConfig.experimental?.segmentCache ?? DEFAULT_CONFIG.experimental.segmentCache
    },
    render: {
      articleLimit: userConfig.render?.articleLimit ?? DEFAULT_CONFIG.render.articleLimit,
      defaultSection: userConfig.render?.defaultSection ?? DEFAULT_CONFIG.render.defaultSection
    }
  };
}

export function toRuntimeConfig(config: FrameworkConfig): FrameworkConfigRuntime {
  return {
    experimental: {
      cacheComponents: config.experimental.cacheComponents,
      authInterrupts: config.experimental.authInterrupts,
      segmentCache: config.experimental.segmentCache
    },
    render: {
      articleLimit: config.render.articleLimit,
      defaultSection: config.render.defaultSection
    }
  };
}
