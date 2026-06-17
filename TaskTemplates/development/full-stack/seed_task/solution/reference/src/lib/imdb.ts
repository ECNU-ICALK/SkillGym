import { readFile } from "node:fs/promises";
import { join } from "node:path";

export type TitleRecord = {
  tconst: string;
  titleType: string;
  primaryTitle: string;
  originalTitle: string;
  startYear: number;
  endYear: number | null;
  runtimeMinutes: number | null;
  genres: string[];
  averageRating: number;
  numVotes: number;
  directors: PersonRecord[];
  writers: PersonRecord[];
  cast: CastRecord[];
};

export type PersonRecord = {
  nconst: string;
  name: string;
};

export type CastRecord = PersonRecord & {
  category: string;
  characters: string[];
};

export type CatalogFilters = {
  query: string;
  titleType: string;
  genre: string;
  yearFrom: string;
  yearTo: string;
  minRating: string;
  minVotes: string;
  sort: string;
  page: number;
  pageSize: number;
};

export type Dataset = {
  titles: TitleRecord[];
  titleMap: Record<string, TitleRecord>;
  titleTypes: string[];
  genres: string[];
};

type BasicRow = {
  tconst: string;
  titleType: string;
  primaryTitle: string;
  originalTitle: string;
  startYear: string;
  endYear: string;
  runtimeMinutes: string;
  genres: string;
};

type RatingRow = {
  tconst: string;
  averageRating: string;
  numVotes: string;
};

type CrewRow = {
  tconst: string;
  directors: string;
  writers: string;
};

type PrincipalRow = {
  tconst: string;
  ordering: string;
  nconst: string;
  category: string;
  characters: string;
};

type NameRow = {
  nconst: string;
  primaryName: string;
};

const datasetCache = new Map<string, Promise<Dataset>>();

function parseTsv<T extends Record<string, string>>(content: string): T[] {
  const lines = content
    .split(/\r?\n/)
    .map((line) => line.replace(/\r$/, ""))
    .filter(Boolean);

  if (lines.length === 0) {
    return [];
  }

  const headers = lines[0].split("\t");
  return lines.slice(1).map((line) => {
    const values = line.split("\t");
    return headers.reduce<Record<string, string>>((row, header, index) => {
      row[header] = values[index] ?? "";
      return row;
    }, {}) as T;
  });
}

function toInt(value: string): number | null {
  if (!value || value === "\\N") {
    return null;
  }
  return Number.parseInt(value, 10);
}

function parseCharacters(rawValue: string): string[] {
  if (!rawValue || rawValue === "\\N") {
    return [];
  }
  try {
    const parsed = JSON.parse(rawValue);
    if (Array.isArray(parsed)) {
      return parsed.map((item) => String(item));
    }
  } catch {
    return [rawValue];
  }
  return [String(rawValue)];
}

function normalizeFilters(params: URLSearchParams): CatalogFilters {
  return {
    query: params.get("query")?.trim() ?? "",
    titleType: params.get("titleType")?.trim() ?? "",
    genre: params.get("genre")?.trim() ?? "",
    yearFrom: params.get("yearFrom")?.trim() ?? "",
    yearTo: params.get("yearTo")?.trim() ?? "",
    minRating: params.get("minRating")?.trim() ?? "",
    minVotes: params.get("minVotes")?.trim() ?? "",
    sort: params.get("sort")?.trim() || "rating_desc",
    page: Math.max(Number.parseInt(params.get("page") ?? "1", 10) || 1, 1),
    pageSize: Math.max(Number.parseInt(params.get("pageSize") ?? "12", 10) || 12, 1),
  };
}

function summarizeTitle(title: TitleRecord) {
  return {
    tconst: title.tconst,
    titleType: title.titleType,
    primaryTitle: title.primaryTitle,
    originalTitle: title.originalTitle,
    startYear: title.startYear,
    endYear: title.endYear,
    runtimeMinutes: title.runtimeMinutes,
    genres: title.genres,
    averageRating: title.averageRating,
    numVotes: title.numVotes,
  };
}

export async function loadDataset(dataRoot = process.env.IMDB_DATA_DIR || "/app/data"): Promise<Dataset> {
  const resolvedRoot = dataRoot;
  if (!datasetCache.has(resolvedRoot)) {
    datasetCache.set(resolvedRoot, loadDatasetInner(resolvedRoot));
  }
  return datasetCache.get(resolvedRoot)!;
}

async function loadDatasetInner(dataRoot: string): Promise<Dataset> {
  const [basicsRaw, ratingsRaw, crewRaw, principalsRaw, namesRaw] = await Promise.all([
    readFile(join(dataRoot, "title_basics_sample.tsv"), "utf8"),
    readFile(join(dataRoot, "title_ratings_sample.tsv"), "utf8"),
    readFile(join(dataRoot, "title_crew_sample.tsv"), "utf8"),
    readFile(join(dataRoot, "title_principals_sample.tsv"), "utf8"),
    readFile(join(dataRoot, "name_basics_sample.tsv"), "utf8"),
  ]);

  const basics = parseTsv<BasicRow>(basicsRaw);
  const ratings = parseTsv<RatingRow>(ratingsRaw);
  const crewRows = parseTsv<CrewRow>(crewRaw);
  const principals = parseTsv<PrincipalRow>(principalsRaw);
  const names = parseTsv<NameRow>(namesRaw);

  const ratingMap = new Map(
    ratings.map((row) => [
      row.tconst,
      {
        averageRating: Number.parseFloat(row.averageRating),
        numVotes: Number.parseInt(row.numVotes, 10),
      },
    ]),
  );

  const crewMap = new Map(crewRows.map((row) => [row.tconst, row]));
  const nameMap = new Map(names.map((row) => [row.nconst, row.primaryName]));
  const principalMap = new Map<string, PrincipalRow[]>();

  for (const row of principals) {
    const bucket = principalMap.get(row.tconst) ?? [];
    bucket.push(row);
    principalMap.set(row.tconst, bucket);
  }

  const titles: TitleRecord[] = basics.map((row) => {
    const rating = ratingMap.get(row.tconst);
    const crew = crewMap.get(row.tconst);
    const cast = (principalMap.get(row.tconst) ?? [])
      .sort((left, right) => Number.parseInt(left.ordering, 10) - Number.parseInt(right.ordering, 10))
      .map((item) => ({
        nconst: item.nconst,
        name: nameMap.get(item.nconst) ?? item.nconst,
        category: item.category,
        characters: parseCharacters(item.characters),
      }));

    const mapPeople = (rawValue: string) =>
      rawValue
        .split(",")
        .filter(Boolean)
        .map((nconst) => ({
          nconst,
          name: nameMap.get(nconst) ?? nconst,
        }));

    return {
      tconst: row.tconst,
      titleType: row.titleType,
      primaryTitle: row.primaryTitle,
      originalTitle: row.originalTitle,
      startYear: toInt(row.startYear) ?? 0,
      endYear: toInt(row.endYear),
      runtimeMinutes: toInt(row.runtimeMinutes),
      genres: row.genres.split(",").filter(Boolean),
      averageRating: rating?.averageRating ?? 0,
      numVotes: rating?.numVotes ?? 0,
      directors: mapPeople(crew?.directors ?? ""),
      writers: mapPeople(crew?.writers ?? ""),
      cast,
    };
  });

  return {
    titles,
    titleMap: Object.fromEntries(titles.map((title) => [title.tconst, title])),
    titleTypes: Array.from(new Set(titles.map((title) => title.titleType))).sort(),
    genres: Array.from(new Set(titles.flatMap((title) => title.genres))).sort(),
  };
}

export function summarizeTitleRecord(title: TitleRecord) {
  return summarizeTitle(title);
}

export function getCatalogControls(dataset: Dataset) {
  return {
    titleTypes: dataset.titleTypes,
    genres: dataset.genres,
    sortOptions: [
      { value: "rating_desc", label: "Rating high to low" },
      { value: "rating_asc", label: "Rating low to high" },
      { value: "votes_desc", label: "Votes high to low" },
      { value: "votes_asc", label: "Votes low to high" },
      { value: "year_desc", label: "Newest first" },
      { value: "year_asc", label: "Oldest first" },
      { value: "title_asc", label: "Title A-Z" },
      { value: "title_desc", label: "Title Z-A" },
    ],
  };
}

export function buildCatalogPayload(dataset: Dataset, params: URLSearchParams) {
  const filters = normalizeFilters(params);
  const query = filters.query.toLowerCase();
  const titleType = filters.titleType;
  const genre = filters.genre;
  const yearFrom = filters.yearFrom ? Number.parseInt(filters.yearFrom, 10) : null;
  const yearTo = filters.yearTo ? Number.parseInt(filters.yearTo, 10) : null;
  const minRating = filters.minRating ? Number.parseFloat(filters.minRating) : null;
  const minVotes = filters.minVotes ? Number.parseInt(filters.minVotes, 10) : null;

  const filtered = dataset.titles.filter((title) => {
    const haystack = `${title.primaryTitle} ${title.originalTitle}`.toLowerCase();
    if (query && !haystack.includes(query)) {
      return false;
    }
    if (titleType && title.titleType !== titleType) {
      return false;
    }
    if (genre && !title.genres.includes(genre)) {
      return false;
    }
    if (yearFrom !== null && title.startYear < yearFrom) {
      return false;
    }
    if (yearTo !== null && title.startYear > yearTo) {
      return false;
    }
    if (minRating !== null && title.averageRating < minRating) {
      return false;
    }
    if (minVotes !== null && title.numVotes < minVotes) {
      return false;
    }
    return true;
  });

  const sorters: Record<string, (left: TitleRecord, right: TitleRecord) => number> = {
    rating_desc: (left, right) =>
      right.averageRating - left.averageRating ||
      right.numVotes - left.numVotes ||
      right.startYear - left.startYear ||
      left.primaryTitle.localeCompare(right.primaryTitle) ||
      left.tconst.localeCompare(right.tconst),
    rating_asc: (left, right) =>
      left.averageRating - right.averageRating ||
      right.numVotes - left.numVotes ||
      left.primaryTitle.localeCompare(right.primaryTitle) ||
      left.tconst.localeCompare(right.tconst),
    votes_desc: (left, right) =>
      right.numVotes - left.numVotes ||
      right.averageRating - left.averageRating ||
      left.primaryTitle.localeCompare(right.primaryTitle) ||
      left.tconst.localeCompare(right.tconst),
    votes_asc: (left, right) =>
      left.numVotes - right.numVotes ||
      right.averageRating - left.averageRating ||
      left.primaryTitle.localeCompare(right.primaryTitle) ||
      left.tconst.localeCompare(right.tconst),
    year_desc: (left, right) =>
      right.startYear - left.startYear ||
      right.averageRating - left.averageRating ||
      left.primaryTitle.localeCompare(right.primaryTitle) ||
      left.tconst.localeCompare(right.tconst),
    year_asc: (left, right) =>
      left.startYear - right.startYear ||
      right.averageRating - left.averageRating ||
      left.primaryTitle.localeCompare(right.primaryTitle) ||
      left.tconst.localeCompare(right.tconst),
    title_asc: (left, right) =>
      left.primaryTitle.localeCompare(right.primaryTitle) ||
      right.averageRating - left.averageRating ||
      left.tconst.localeCompare(right.tconst),
    title_desc: (left, right) =>
      right.primaryTitle.localeCompare(left.primaryTitle) ||
      right.averageRating - left.averageRating ||
      left.tconst.localeCompare(right.tconst),
  };

  const sorted = [...filtered].sort(sorters[filters.sort] ?? sorters.rating_desc);
  const totalItems = sorted.length;
  const totalPages = Math.max(Math.ceil(totalItems / filters.pageSize), 1);
  const page = Math.min(filters.page, totalPages);
  const offset = (page - 1) * filters.pageSize;
  const items = sorted.slice(offset, offset + filters.pageSize).map(summarizeTitle);

  return {
    filters,
    page,
    pageSize: filters.pageSize,
    totalItems,
    totalPages,
    items,
    controls: getCatalogControls(dataset),
  };
}
