import { access, mkdir, readFile, writeFile } from "node:fs/promises";
import { constants } from "node:fs";
import { join } from "node:path";
import { loadDataset, summarizeTitleRecord, type Dataset } from "@/lib/imdb";

export const PRIORITIES = ["P1", "P2", "P3"] as const;
export const STATUSES = ["watch", "review", "approve", "hold"] as const;

export type Priority = (typeof PRIORITIES)[number];
export type ShortlistStatus = (typeof STATUSES)[number];

export type ShortlistEntry = {
  tconst: string;
  priority: Priority;
  status: ShortlistStatus;
  note: string;
};

export type ShortlistItem = ShortlistEntry & {
  title: ReturnType<typeof summarizeTitleRecord> | null;
};

function getStateDir() {
  return process.env.STATE_DIR || "/app/workspace/state";
}

function getStatePath() {
  return join(getStateDir(), "shortlist.json");
}

function getSeedPath() {
  return join(process.env.IMDB_DATA_DIR || "/app/data", "shortlist_seed.json");
}

async function ensureStateFile() {
  const stateDir = getStateDir();
  const statePath = getStatePath();
  await mkdir(stateDir, { recursive: true });
  try {
    await access(statePath, constants.F_OK);
  } catch {
    try {
      const seed = await readFile(getSeedPath(), "utf8");
      await writeFile(statePath, seed, "utf8");
    } catch {
      await writeFile(statePath, "[]\n", "utf8");
    }
  }
  return statePath;
}

function normalizeEntry(rawEntry: Partial<ShortlistEntry>): ShortlistEntry {
  const priority = PRIORITIES.includes(rawEntry.priority as Priority) ? (rawEntry.priority as Priority) : "P2";
  const status = STATUSES.includes(rawEntry.status as ShortlistStatus) ? (rawEntry.status as ShortlistStatus) : "watch";
  return {
    tconst: String(rawEntry.tconst ?? ""),
    priority,
    status,
    note: String(rawEntry.note ?? "").trim(),
  };
}

export async function readShortlistEntries(): Promise<ShortlistEntry[]> {
  const statePath = await ensureStateFile();
  const raw = await readFile(statePath, "utf8");
  const parsed = JSON.parse(raw) as Partial<ShortlistEntry>[];
  return parsed
    .map(normalizeEntry)
    .filter((entry) => entry.tconst && PRIORITIES.includes(entry.priority) && STATUSES.includes(entry.status));
}

async function writeShortlistEntries(entries: ShortlistEntry[]) {
  const statePath = await ensureStateFile();
  await writeFile(statePath, `${JSON.stringify(entries, null, 2)}\n`, "utf8");
}

export async function getShortlistPayload(dataset?: Dataset) {
  const resolvedDataset = dataset ?? (await loadDataset());
  const entries = await readShortlistEntries();
  const items: ShortlistItem[] = entries.map((entry) => ({
    ...entry,
    title: resolvedDataset.titleMap[entry.tconst] ? summarizeTitleRecord(resolvedDataset.titleMap[entry.tconst]) : null,
  }));

  const countsByStatus = {
    watch: 0,
    review: 0,
    approve: 0,
    hold: 0,
  };
  let totalRating = 0;
  let ratedCount = 0;

  for (const item of items) {
    countsByStatus[item.status] += 1;
    if (item.title) {
      totalRating += item.title.averageRating;
      ratedCount += 1;
    }
  }

  const highestRated = [...items]
    .filter((item) => item.title)
    .sort((left, right) => {
      const leftTitle = left.title!;
      const rightTitle = right.title!;
      return (
        rightTitle.averageRating - leftTitle.averageRating ||
        rightTitle.numVotes - leftTitle.numVotes ||
        leftTitle.primaryTitle.localeCompare(rightTitle.primaryTitle)
      );
    })[0];

  return {
    items,
    summary: {
      totalItems: items.length,
      countsByStatus,
      averageRating: ratedCount > 0 ? Number((totalRating / ratedCount).toFixed(2)) : null,
      highestRated: highestRated?.title
        ? {
            ...highestRated.title,
            status: highestRated.status,
            priority: highestRated.priority,
          }
        : null,
    },
    controls: {
      priorities: [...PRIORITIES],
      statuses: [...STATUSES],
    },
  };
}

export async function upsertShortlistEntry(input: Partial<ShortlistEntry>) {
  const dataset = await loadDataset();
  const title = dataset.titleMap[String(input.tconst ?? "")];
  if (!title) {
    throw new Error("unknown_tconst");
  }
  const normalized = normalizeEntry(input);
  const entries = await readShortlistEntries();
  const existingIndex = entries.findIndex((entry) => entry.tconst === normalized.tconst);
  const nextEntries = [...entries];

  if (existingIndex >= 0) {
    nextEntries[existingIndex] = normalized;
  } else {
    nextEntries.push(normalized);
  }

  await writeShortlistEntries(nextEntries);
  return {
    statusCode: existingIndex >= 0 ? 200 : 201,
    entry: normalized,
    payload: await getShortlistPayload(dataset),
  };
}

export async function patchShortlistEntry(tconst: string, input: Partial<ShortlistEntry>) {
  const dataset = await loadDataset();
  const entries = await readShortlistEntries();
  const existingIndex = entries.findIndex((entry) => entry.tconst === tconst);

  if (existingIndex < 0) {
    throw new Error("missing_entry");
  }

  const merged = normalizeEntry({
    ...entries[existingIndex],
    ...input,
    tconst,
  });
  const nextEntries = [...entries];
  nextEntries[existingIndex] = merged;
  await writeShortlistEntries(nextEntries);
  return {
    entry: merged,
    payload: await getShortlistPayload(dataset),
  };
}

export async function deleteShortlistEntry(tconst: string) {
  const dataset = await loadDataset();
  const entries = await readShortlistEntries();
  const nextEntries = entries.filter((entry) => entry.tconst !== tconst);
  const removed = nextEntries.length !== entries.length;
  await writeShortlistEntries(nextEntries);
  return {
    removed,
    payload: await getShortlistPayload(dataset),
  };
}
