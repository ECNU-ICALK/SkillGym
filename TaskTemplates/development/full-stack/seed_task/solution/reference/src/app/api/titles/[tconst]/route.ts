import { NextResponse } from "next/server";
import { loadDataset } from "@/lib/imdb";
import { getShortlistPayload } from "@/lib/shortlist-store";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(
  _request: Request,
  context: { params: Promise<{ tconst: string }> },
) {
  const { tconst } = await context.params;
  const dataset = await loadDataset();
  const title = dataset.titleMap[tconst];

  if (!title) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }

  const shortlistPayload = await getShortlistPayload(dataset);
  const shortlistEntry = shortlistPayload.items.find((item) => item.tconst === tconst) ?? null;

  return NextResponse.json({
    title,
    shortlistEntry,
    controls: shortlistPayload.controls,
  });
}
