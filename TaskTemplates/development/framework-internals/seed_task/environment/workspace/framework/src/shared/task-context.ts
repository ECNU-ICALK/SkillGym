import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export interface RouteRecord {
  route: string;
  title: string;
  section: string;
  docType: string;
  pathSegments: string[];
  sourceUrl: string;
  wordCount: number;
}

export interface ScenarioDefinition {
  id: string;
  label: string;
  configPath: string;
  routeDataPath: string;
}

interface FixtureMatrix {
  defaultDevScenarioId: string;
  reportFields: string[];
  scenarios: ScenarioDefinition[];
}

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export const WORKSPACE_ROOT = path.resolve(__dirname, "../../..");
export const FRAMEWORK_ROOT = path.join(WORKSPACE_ROOT, "framework");
export const OUTPUT_ROOT = path.join(WORKSPACE_ROOT, "output");
export const DATA_ROOT = path.join(WORKSPACE_ROOT, "data", "upstream");

export function workspacePath(...parts: string[]): string {
  return path.join(WORKSPACE_ROOT, ...parts);
}

export function ensureDir(dirPath: string): void {
  fs.mkdirSync(dirPath, { recursive: true });
}

export function loadJsonFile<T>(filePath: string): T {
  return JSON.parse(fs.readFileSync(filePath, "utf-8")) as T;
}

export function writeJsonFile(filePath: string, value: unknown): void {
  ensureDir(path.dirname(filePath));
  fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`, "utf-8");
}

export function loadFixtureMatrix(): FixtureMatrix {
  return loadJsonFile<FixtureMatrix>(workspacePath("data", "upstream", "fixture_matrix.json"));
}

export function getScenario(scenarioId?: string): ScenarioDefinition {
  const matrix = loadFixtureMatrix();
  const targetId = scenarioId || process.env.SCENARIO_ID || matrix.defaultDevScenarioId;
  const scenario = matrix.scenarios.find((item) => item.id === targetId);
  if (!scenario) {
    throw new Error(`Unknown scenario: ${targetId}`);
  }
  return scenario;
}

export function resolveConfigPath(scenario: ScenarioDefinition): string {
  return workspacePath(...scenario.configPath.split("/"));
}

export function resolveRouteDataPath(scenario: ScenarioDefinition): string {
  const override = process.env.FRAMEWORK_ROUTE_DATA_PATH;
  if (override) {
    return override;
  }
  return workspacePath(...scenario.routeDataPath.split("/"));
}

export function loadRoutes(routeDataPath: string): RouteRecord[] {
  return loadJsonFile<RouteRecord[]>(routeDataPath);
}

export function routeDigest(routes: RouteRecord[]): string {
  return crypto
    .createHash("sha256")
    .update(JSON.stringify(routes))
    .digest("hex");
}

export function parseCliArg(flagName: string): string | undefined {
  const index = process.argv.indexOf(flagName);
  if (index === -1 || index + 1 >= process.argv.length) {
    return undefined;
  }
  return process.argv[index + 1];
}
