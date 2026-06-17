"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

type DetailResponse = {
  title: {
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
    directors: Array<{ nconst: string; name: string }>;
    writers: Array<{ nconst: string; name: string }>;
    cast: Array<{ nconst: string; name: string; category: string; characters: string[] }>;
  };
  shortlistEntry: {
    tconst: string;
    priority: "P1" | "P2" | "P3";
    status: "watch" | "review" | "approve" | "hold";
    note: string;
  } | null;
  controls: {
    priorities: string[];
    statuses: string[];
  };
};

type ShortlistResponse = {
  items: Array<{
    tconst: string;
    priority: string;
    status: string;
    note: string;
    title: {
      primaryTitle: string;
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
        }
      | null;
  };
};

const emptyControls = {
  priorities: ["P1", "P2", "P3"],
  statuses: ["watch", "review", "approve", "hold"],
};

export function TitleDetailWorkbench({ tconst }: { tconst: string }) {
  const [detail, setDetail] = useState<DetailResponse | null>(null);
  const [shortlist, setShortlist] = useState<ShortlistResponse | null>(null);
  const [priority, setPriority] = useState("P2");
  const [status, setStatus] = useState("watch");
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function loadState() {
    setLoading(true);
    setError("");
    try {
      const [detailResponse, shortlistResponse] = await Promise.all([
        fetch(`/api/titles/${tconst}`, { cache: "no-store" }),
        fetch("/api/shortlist", { cache: "no-store" }),
      ]);

      if (!detailResponse.ok) {
        throw new Error(`detail request failed with ${detailResponse.status}`);
      }
      if (!shortlistResponse.ok) {
        throw new Error(`shortlist request failed with ${shortlistResponse.status}`);
      }

      const detailPayload = (await detailResponse.json()) as DetailResponse;
      const shortlistPayload = (await shortlistResponse.json()) as ShortlistResponse;
      setDetail(detailPayload);
      setShortlist(shortlistPayload);
      setPriority(detailPayload.shortlistEntry?.priority ?? "P2");
      setStatus(detailPayload.shortlistEntry?.status ?? "watch");
      setNote(detailPayload.shortlistEntry?.note ?? "");
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "failed to load detail");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadState();
  }, [tconst]);

  async function saveEntry() {
    setMessage("");
    setError("");
    const method = detail?.shortlistEntry ? "PATCH" : "POST";
    const endpoint = detail?.shortlistEntry ? `/api/shortlist/${tconst}` : "/api/shortlist";
    const payload =
      method === "POST"
        ? { tconst, priority, status, note }
        : { priority, status, note };

    const response = await fetch(endpoint, {
      method,
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      setError(`save failed with ${response.status}`);
      return;
    }

    setMessage("Shortlist entry saved");
    await loadState();
  }

  async function removeEntry() {
    setMessage("");
    setError("");
    const response = await fetch(`/api/shortlist/${tconst}`, { method: "DELETE" });
    if (!response.ok) {
      setError(`delete failed with ${response.status}`);
      return;
    }
    setMessage("Shortlist entry removed");
    await loadState();
  }

  const controls = detail?.controls ?? emptyControls;
  const statusSummary = shortlist?.summary.countsByStatus ?? { watch: 0, review: 0, approve: 0, hold: 0 };

  return (
    <main className="page-grid">
      <section className="split">
        <article className="panel">
          {loading ? <p className="muted">Loading title detail...</p> : null}
          {detail ? (
            <>
              <p className="eyebrow">{detail.title.titleType}</p>
              <h2 data-testid="detail-title">{detail.title.primaryTitle}</h2>
              <p className="muted">
                {detail.title.originalTitle} • {detail.title.startYear}
                {detail.title.endYear ? `-${detail.title.endYear}` : ""}
              </p>
              <div className="detail-grid">
                <div className="stat-card">
                  <p>Rating</p>
                  <strong>{detail.title.averageRating.toFixed(1)}</strong>
                </div>
                <div className="stat-card">
                  <p>Votes</p>
                  <strong>{detail.title.numVotes.toLocaleString()}</strong>
                </div>
                <div className="stat-card">
                  <p>Runtime</p>
                  <strong>{detail.title.runtimeMinutes ?? "n/a"}</strong>
                </div>
              </div>
              <div className="chip-row">
                {detail.title.genres.map((genre) => (
                  <span key={genre} className="chip">
                    {genre}
                  </span>
                ))}
              </div>
              <div className="meta-list" style={{ marginTop: "14px" }}>
                <p>
                  <strong>Directors</strong>
                  {detail.title.directors.map((person) => person.name).join(", ") || "n/a"}
                </p>
                <p>
                  <strong>Writers</strong>
                  {detail.title.writers.map((person) => person.name).join(", ") || "n/a"}
                </p>
                <p>
                  <strong>Cast</strong>
                  {detail.title.cast.slice(0, 5).map((person) => person.name).join(", ") || "n/a"}
                </p>
              </div>
            </>
          ) : null}
        </article>

        <aside className="panel">
          <h3>Shortlist entry</h3>
          <div className="field">
            <label htmlFor="priority">Priority</label>
            <select id="priority" value={priority} onChange={(event) => setPriority(event.target.value)}>
              {controls.priorities.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="status">Status</label>
            <select id="status" value={status} onChange={(event) => setStatus(event.target.value)}>
              {controls.statuses.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="note">Note</label>
            <textarea id="note" aria-label="Note" value={note} onChange={(event) => setNote(event.target.value)} />
          </div>
          <div className="button-row">
            <button
              type="button"
              className="button-primary"
              data-testid={`add-shortlist-${tconst}`}
              onClick={() => void saveEntry()}
              disabled={loading}
            >
              {detail?.shortlistEntry ? "Save shortlist entry" : "Add to shortlist"}
            </button>
            {detail?.shortlistEntry ? (
              <button type="button" className="button-danger" onClick={() => void removeEntry()}>
                Remove from shortlist
              </button>
            ) : null}
            <Link href="/shortlist" className="button-secondary">
              Go to shortlist
            </Link>
          </div>
          {message ? <p className="success">{message}</p> : null}
          {error ? <p className="error">{error}</p> : null}
        </aside>
      </section>

      <section className="panel">
        <h3>Current shortlist overview</h3>
        <div className="status-grid" data-testid="shortlist-status-grid">
          {Object.entries(statusSummary).map(([statusKey, count]) => (
            <div key={statusKey} className="stat-card">
              <p>{statusKey}</p>
              <strong>{count}</strong>
            </div>
          ))}
        </div>
        {shortlist?.summary.highestRated ? (
          <p className="muted">
            Highest rated: {shortlist.summary.highestRated.primaryTitle} (
            {shortlist.summary.highestRated.averageRating.toFixed(1)})
          </p>
        ) : null}
      </section>

      {detail?.shortlistEntry ? (
        <section className="panel" data-testid={`shortlist-item-${tconst}`}>
          <h3>Saved shortlist row</h3>
          <p>
            {detail.title.primaryTitle} • {detail.shortlistEntry.priority} • {detail.shortlistEntry.status}
          </p>
          <p className="muted">{detail.shortlistEntry.note || "No note provided."}</p>
        </section>
      ) : null}
    </main>
  );
}
