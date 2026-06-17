import { readFile } from "node:fs/promises";
import { basename } from "node:path";

import type {
  DigestPackageSummary,
  GitHubReleaseSnapshot,
  NpmLatestSnapshot,
  ToolchainDigest,
} from "./types.js";

function normalizeTag(tag: string): string {
  return tag.startsWith("v") ? tag.slice(1) : tag;
}

function tarballHost(snapshot: NpmLatestSnapshot): string | null {
  const tarball = snapshot.dist?.tarball;
  if (!tarball) {
    return null;
  }

  return new URL(tarball).host;
}

function selectLatestStableRelease(releases: GitHubReleaseSnapshot[]): GitHubReleaseSnapshot {
  const stable = releases.find((release) => !release.draft && !release.prerelease);
  if (!stable) {
    throw new Error("No stable GitHub release was found in the provided snapshot window.");
  }
  return stable;
}

async function readJsonFile<T>(filePath: string): Promise<T> {
  const text = await readFile(filePath, "utf-8");
  return JSON.parse(text) as T;
}

export interface BuildDigestInput {
  npmFiles: string[];
  githubFiles: string[];
  githubRepos: Record<string, string>;
}

export async function buildDigest(input: BuildDigestInput): Promise<ToolchainDigest> {
  const npmSnapshots = new Map<string, NpmLatestSnapshot>();
  for (const file of input.npmFiles) {
    const snapshot = await readJsonFile<NpmLatestSnapshot>(file);
    npmSnapshots.set(snapshot.name, snapshot);
  }

  const githubSnapshots = new Map<string, GitHubReleaseSnapshot[]>();
  for (const file of input.githubFiles) {
    const key = basename(file).replace(/_releases\.json$/, "");
    const releases = await readJsonFile<GitHubReleaseSnapshot[]>(file);
    githubSnapshots.set(key, releases);
  }

  const packages: DigestPackageSummary[] = [...npmSnapshots.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([packageName, npmSnapshot]) => {
      const releases = githubSnapshots.get(packageName);
      if (!releases) {
        throw new Error(`Missing GitHub releases snapshot for ${packageName}.`);
      }

      const latestStable = selectLatestStableRelease(releases);
      return {
        package_name: packageName,
        npm_version: npmSnapshot.version,
        npm_license: npmSnapshot.license ?? null,
        npm_tarball_host: tarballHost(npmSnapshot),
        github_repo: input.githubRepos[packageName],
        github_latest_stable_tag: latestStable.tag_name,
        github_latest_stable_published_at: latestStable.published_at,
        github_asset_count: latestStable.assets.length,
        stable_tag_matches_npm_latest: normalizeTag(latestStable.tag_name) === npmSnapshot.version,
        prerelease_present_in_window: releases.some((release) => release.prerelease),
      };
    });

  return {
    project_id: "code-quality__toolchain-release-readiness-audit",
    package_count: packages.length,
    packages,
  };
}
