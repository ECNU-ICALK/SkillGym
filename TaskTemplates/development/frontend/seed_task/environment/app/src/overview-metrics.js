import { DEFAULT_REGION } from "./workbench-state.js";

export function deriveOverviewCountries(countries, { region }) {
  const filtered = countries.filter((country) => region === DEFAULT_REGION || country.region === region);
  return [...filtered].sort((left, right) => right.renewablesShare - left.renewablesShare);
}

export function summarizeOverview(countries) {
  const averageRenewables = countries.length
    ? countries.reduce((sum, country) => sum + country.renewablesShare, 0) / countries.length
    : 0;

  return {
    visibleCount: countries.length,
    averageRenewables,
    topCountry: countries[0] || null
  };
}
