import { DEFAULT_REGION } from "./workbench-state.js";

function matchesSearch(country, search) {
  if (!search) {
    return true;
  }

  const query = search.toLowerCase();
  return (
    country.name.toLowerCase().includes(query) ||
    country.isoCode.toLowerCase().includes(query) ||
    country.region.toLowerCase().includes(query)
  );
}

function sortCountries(rows, sort) {
  const copy = [...rows];
  switch (sort) {
    case "generation-desc":
      return copy.sort((left, right) => right.generationTwh - left.generationTwh);
    case "delta-renewables-desc":
      return copy.sort((left, right) => right.deltaRenewables - left.deltaRenewables);
    case "name-asc":
      return copy.sort((left, right) => left.name.localeCompare(right.name));
    case "renewables-desc":
    default:
      return copy.sort((left, right) => right.renewablesShare - left.renewablesShare);
  }
}

export function deriveOverviewCountries(countries, { region, search, sort }) {
  const filtered = countries
    .filter((country) => region === DEFAULT_REGION || country.region === region)
    .filter((country) => matchesSearch(country, search));

  return sortCountries(filtered, sort);
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
