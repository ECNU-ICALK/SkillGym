import fs from "node:fs";
import { z } from "zod";

import type { FrameworkConfig } from "./config-shared.js";

const experimentalSchema = z
  .object({
    cacheComponents: z.boolean().optional(),
    authInterrupts: z.boolean().optional(),
    segmentCache: z.boolean().optional()
  })
  .strip();

const frameworkConfigSchema = z
  .object({
    siteName: z.string().min(1),
    experimental: experimentalSchema.default({}),
    render: z
      .object({
        articleLimit: z.number().int().positive().optional(),
        defaultSection: z.string().min(1).optional()
      })
      .default({})
  })
  .strip();

export function readRawConfig(configPath: string): unknown {
  return JSON.parse(fs.readFileSync(configPath, "utf-8"));
}

export function loadUserConfig(configPath: string): Partial<FrameworkConfig> {
  return frameworkConfigSchema.parse(readRawConfig(configPath)) as Partial<FrameworkConfig>;
}
