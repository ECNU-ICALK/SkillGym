import { NextResponse } from "next/server";
import { loadDataset } from "@/lib/imdb";
import { readShortlistEntries } from "@/lib/shortlist-store";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET() {
  const [dataset, entries] = await Promise.all([loadDataset(), readShortlistEntries()]);
  return NextResponse.json({
    ok: true,
    status: "ok",
    titleCount: dataset.titles.length,
    shortlistCount: entries.length,
  });
}
