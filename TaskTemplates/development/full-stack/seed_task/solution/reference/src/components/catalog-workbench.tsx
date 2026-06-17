"use client";

import Link from "next/link";
import { useEffect, useState, useTransition } from "react";
import { useRouter, useSearchParams } from "next/navigation";

type TitleSummary = {
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
};

type CatalogResponse = {
  filters: Record<string, string | number>;
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
  items: TitleSummary[];
  controls: {
    titleTypes: string[];
    genres: string[];
    sortOptions: Array<{ value: string; label: string }>;
  };
};

type FilterDraft = {
  query: string;
  titleType: string;
  genre: string;
  yearFrom: string;
  yearTo: string;
  minRating: string;
  minVotes: string;
  sort: string;
  page: string;
  pageSize: string;
};

const defaultDraft: FilterDraft = {
  query: "",
  titleType: "",
  genre: "",
  yearFrom: "",
  yearTo: "",
  minRating: "",
  minVotes: "",
  sort: "rating_desc",
  page: "1",
  pageSize: "12",
};

const defaultControls = {
  titleTypes: ["movie", "tvMiniSeries", "tvSeries"],
  genres: [],
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

function draftFromParams(params: URLSearchParams): FilterDraft {
  return {
    query: params.get("query") ?? "",
    titleType: params.get("titleType") ?? "",
    genre: params.get("genre") ?? "",
    yearFrom: params.get("yearFrom") ?? "",
    yearTo: params.get("yearTo") ?? "",
    minRating: params.get("minRating") ?? "",
    minVotes: params.get("minVotes") ?? "",
    sort: params.get("sort") ?? "rating_desc",
    page: params.get("page") ?? "1",
    pageSize: params.get("pageSize") ?? "12",
  };
}

function buildQueryString(draft: FilterDraft) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(draft)) {
    if (value) {
      params.set(key, value);
    }
  }
  if (!params.has("page")) {
    params.set("page", "1");
  }
  if (!params.has("pageSize")) {
    params.set("pageSize", "12");
  }
  return params.toString();
}

export function CatalogWorkbench() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const searchKey = searchParams.toString();
  const [draft, setDraft] = useState<FilterDraft>(defaultDraft);
  const [data, setData] = useState<CatalogResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    const nextDraft = draftFromParams(new URLSearchParams(searchKey));
    setDraft(nextDraft);
    let cancelled = false;

    setLoading(true);
    setError("");
    fetch(`/api/titles?${buildQueryString(nextDraft)}`, { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`catalog request failed with ${response.status}`);
        }
        return (await response.json()) as CatalogResponse;
      })
      .then((payload) => {
        if (!cancelled) {
          setData(payload);
        }
      })
      .catch((fetchError: Error) => {
        if (!cancelled) {
          setError(fetchError.message);
          setData(null);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [searchKey]);

  function updateField(field: keyof FilterDraft, value: string) {
    setDraft((current) => ({
      ...current,
      [field]: value,
    }));
  }

  function applyDraft(page = "1") {
    const nextDraft = {
      ...draft,
      page,
    };
    startTransition(() => {
      router.push(`/?${buildQueryString(nextDraft)}`);
    });
  }

  const controls = data?.controls ?? defaultControls;

  return (
    <main className="page-grid">
      <section className="hero">
        <article className="panel">
          <p className="eyebrow">Scenario</p>
          <h2>Candidate title review for the next shortlist meeting</h2>
          <p className="muted">
            Filter the local IMDb snapshot, inspect title details, and promote candidates into the team shortlist
            without leaving the same Next.js workspace.
          </p>
        </article>
        <aside className="panel">
          <div className="stat-grid">
            <div className="stat-card">
              <p>Matching titles</p>
              <strong>{data?.totalItems ?? "..."}</strong>
            </div>
            <div className="stat-card">
              <p>Current page</p>
              <strong>{data ? `${data.page}/${data.totalPages}` : "..."}</strong>
            </div>
          </div>
        </aside>
      </section>

      <section className="panel">
        <h3>Catalog filters</h3>
        <div className="filters">
          <div className="field">
            <label htmlFor="query">Search</label>
            <input
              id="query"
              data-testid="filter-query"
              placeholder="Search by title"
              value={draft.query}
              onChange={(event) => updateField("query", event.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="titleType">Title type</label>
            <select
              id="titleType"
              value={draft.titleType}
              onChange={(event) => updateField("titleType", event.target.value)}
            >
              <option value="">All</option>
              {controls.titleTypes.map((titleType) => (
                <option key={titleType} value={titleType}>
                  {titleType}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="genre">Genre</label>
            <select id="genre" value={draft.genre} onChange={(event) => updateField("genre", event.target.value)}>
              <option value="">All</option>
              {controls.genres.map((genre) => (
                <option key={genre} value={genre}>
                  {genre}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="yearFrom">Year from</label>
            <input id="yearFrom" value={draft.yearFrom} onChange={(event) => updateField("yearFrom", event.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="yearTo">Year to</label>
            <input id="yearTo" value={draft.yearTo} onChange={(event) => updateField("yearTo", event.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="minRating">Min rating</label>
            <input
              id="minRating"
              value={draft.minRating}
              onChange={(event) => updateField("minRating", event.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="minVotes">Min votes</label>
            <input id="minVotes" value={draft.minVotes} onChange={(event) => updateField("minVotes", event.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="sort">Sort</label>
            <select id="sort" value={draft.sort} onChange={(event) => updateField("sort", event.target.value)}>
              {controls.sortOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="pageSize">Page size</label>
            <select id="pageSize" value={draft.pageSize} onChange={(event) => updateField("pageSize", event.target.value)}>
              {["6", "12", "20"].map((pageSize) => (
                <option key={pageSize} value={pageSize}>
                  {pageSize}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="button-row">
          <button
            type="button"
            className="button-primary"
            data-testid="apply-filters"
            onClick={() => applyDraft("1")}
            disabled={loading || isPending}
          >
            Apply Filters
          </button>
          <Link className="button-secondary" href="/shortlist">
            Open shortlist
          </Link>
        </div>
        {error ? <p className="error">{error}</p> : null}
      </section>

      <section className="panel">
        <div className="button-row">
          <button
            type="button"
            className="button-secondary"
            onClick={() => applyDraft(String(Math.max(Number.parseInt(draft.page, 10) - 1, 1)))}
            disabled={loading || Number.parseInt(draft.page, 10) <= 1}
          >
            Previous
          </button>
          <button
            type="button"
            className="button-secondary"
            onClick={() => applyDraft(String(Number.parseInt(draft.page, 10) + 1))}
            disabled={loading || !data || data.page >= data.totalPages}
          >
            Next
          </button>
        </div>

        {loading ? <p className="muted">Loading catalog...</p> : null}

        <div className="catalog-grid">
          {data?.items.map((item) => (
            <article key={item.tconst} className="title-card" data-testid={`title-card-${item.tconst}`}>
              <p className="eyebrow">{item.titleType}</p>
              <h3>{item.primaryTitle}</h3>
              <p className="muted">
                {item.startYear}
                {item.endYear ? `-${item.endYear}` : ""}
                {item.runtimeMinutes ? ` • ${item.runtimeMinutes} min` : ""}
              </p>
              <div className="scoreline">
                <div>
                  <p>IMDb rating</p>
                  <strong>{item.averageRating.toFixed(1)}</strong>
                </div>
                <div>
                  <p>Votes</p>
                  <strong>{item.numVotes.toLocaleString()}</strong>
                </div>
              </div>
              <div className="chip-row">
                {item.genres.map((genre) => (
                  <span key={genre} className="chip">
                    {genre}
                  </span>
                ))}
              </div>
              <div className="button-row">
                <Link className="button-primary" data-testid={`open-detail-${item.tconst}`} href={`/titles/${item.tconst}`}>
                  View details
                </Link>
              </div>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
