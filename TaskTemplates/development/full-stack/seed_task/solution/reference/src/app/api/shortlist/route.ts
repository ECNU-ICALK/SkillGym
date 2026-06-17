import { NextResponse } from "next/server";
import { getShortlistPayload, upsertShortlistEntry } from "@/lib/shortlist-store";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET() {
  return NextResponse.json(await getShortlistPayload());
}

export async function POST(request: Request) {
  const payload = (await request.json()) as Record<string, unknown>;

  try {
    const result = await upsertShortlistEntry({
      tconst: String(payload.tconst ?? ""),
      priority: String(payload.priority ?? "P2") as "P1" | "P2" | "P3",
      status: String(payload.status ?? "watch") as "watch" | "review" | "approve" | "hold",
      note: String(payload.note ?? ""),
    });
    return NextResponse.json(
      {
        entry: result.entry,
        summary: result.payload.summary,
        items: result.payload.items,
      },
      { status: result.statusCode },
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : "unknown_error";
    const status = message === "unknown_tconst" ? 400 : 500;
    return NextResponse.json({ error: message }, { status });
  }
}
