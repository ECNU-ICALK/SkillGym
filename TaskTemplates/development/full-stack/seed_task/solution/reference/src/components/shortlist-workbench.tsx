"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

type ShortlistPayload = {
  items: Array<{
    tconst: string;
    priority: string;
    status: string;
    note: string;
    title: {
      primaryTitle: string;
      titleType: string;
      startYear: number;
      averageRating: number;
      numVotes: number;
      genres: string[];
    } | null;
  }>;
  summary: {
    totalItems: number;
    countsByStatus: Record<string, number>;
    averageRating: number | null;
    highestRated:
      | {
          primaryTitle: string;
          averageRating: number;
          priority: string;
          status: string;
        }
      | null;
  };
  controls: {
    priorities: string[];
    statuses: string[];
  };
};

export function ShortlistWorkbench() {
  const [data, setData] = useState<ShortlistPayload | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function loadShortlist() {
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/shortlist", { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`shortlist request failed with ${response.status}`);
      }
      setData((await response.json()) as ShortlistPayload);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "failed to load shortlist");
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadShortlist();
  }, []);

  return (
    <main className="page-grid">
      <section className="panel">
        <h2>Shortlist dashboard</h2>
        <div className="stat-grid">
          <div className="stat-card">
            <p>Total shortlist rows</p>
            <strong>{data?.summary.totalItems ?? "..."}</strong>
          </div>
          <div className="stat-card">
            <p>Average rating</p>
            <strong>{data?.summary.averageRating?.toFixed(2) ?? "n/a"}</strong>
          </div>
          <div className="stat-card">
            <p>Top rated pick</p>
            <strong>{data?.summary.highestRated?.primaryTitle ?? "n/a"}</strong>
          </div>
        </div>
      </section>

      <section className="panel">
        <h3>Status distribution</h3>
        <div className="status-grid">
          {Object.entries(data?.summary.countsByStatus ?? {}).map(([statusKey, count]) => (
            <div key={statusKey} className="stat-card">
              <p>{statusKey}</p>
              <strong>{count}</strong>
            </div>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="button-row">
          <Link className="button-secondary" href="/">
            Back to catalog
          </Link>
        </div>
        {loading ? <p className="muted">Loading shortlist...</p> : null}
        {error ? <p className="error">{error}</p> : null}
        <div className="shortlist-grid">
          {data?.items.map((item) => (
            <article key={item.tconst} className="shortlist-card">
              <p className="eyebrow">{item.priority}</p>
              <h3>{item.title?.primaryTitle ?? item.tconst}</h3>
              <p className="muted">
                {item.status} • {item.title?.titleType ?? "unknown"} • {item.title?.startYear ?? "n/a"}
              </p>
              <div className="scoreline">
                <div>
                  <p>Rating</p>
                  <strong>{item.title ? item.title.averageRating.toFixed(1) : "n/a"}</strong>
                </div>
                <div>
                  <p>Votes</p>
                  <strong>{item.title ? item.title.numVotes.toLocaleString() : "n/a"}</strong>
                </div>
              </div>
              <p>{item.note || "No note provided."}</p>
              <div className="chip-row">
                {item.title?.genres.map((genre) => (
                  <span key={genre} className="chip">
                    {genre}
                  </span>
                ))}
              </div>
              <div className="button-row">
                <Link className="button-primary" href={`/titles/${item.tconst}`}>
                  Edit in detail view
                </Link>
              </div>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
