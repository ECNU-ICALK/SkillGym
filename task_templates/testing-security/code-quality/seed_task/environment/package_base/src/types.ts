export interface NpmLatestSnapshot {
  name: string;
  version: string;
  license?: string;
  homepage?: string;
  repository?: string | { type?: string; url?: string };
  dist?: {
    tarball?: string;
  };
}

export interface GitHubReleaseSnapshot {
  tag_name: string;
  name: string | null;
  draft: boolean;
  prerelease: boolean;
  published_at: string | null;
  html_url: string;
  assets: Array<{
    name: string;
  }>;
}

export interface DigestPackageSummary {
  package_name: string;
  npm_version: string;
  npm_license: string | null;
  npm_tarball_host: string | null;
  github_repo: string;
  github_latest_stable_tag: string;
  github_latest_stable_published_at: string | null;
  github_asset_count: number;
  stable_tag_matches_npm_latest: boolean;
  prerelease_present_in_window: boolean;
}

export interface ToolchainDigest {
  project_id: string;
  package_count: number;
  packages: DigestPackageSummary[];
}
