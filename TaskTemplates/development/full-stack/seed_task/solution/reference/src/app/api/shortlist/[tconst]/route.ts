import { NextResponse } from "next/server";
import { deleteShortlistEntry, patchShortlistEntry } from "@/lib/shortlist-store";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function PATCH(
  request: Request,
  context: { params: Promise<{ tconst: string }> },
) {
  const { tconst } = await context.params;
  const payload = (await request.json()) as Record<string, unknown>;

  try {
    const result = await patchShortlistEntry(tconst, {
      priority: String(payload.priority ?? "P2") as "P1" | "P2" | "P3",
      status: String(payload.status ?? "watch") as "watch" | "review" | "approve" | "hold",
      note: String(payload.note ?? ""),
    });
    return NextResponse.json({
      entry: result.entry,
      summary: result.payload.summary,
      items: result.payload.items,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "unknown_error";
    const status = message === "missing_entry" ? 404 : 500;
    return NextResponse.json({ error: message }, { status });
  }
}

export async function DELETE(
  _request: Request,
  context: { params: Promise<{ tconst: string }> },
) {
  const { tconst } = await context.params;
  const result = await deleteShortlistEntry(tconst);
  return NextResponse.json({
    removed: result.removed,
    summary: result.payload.summary,
    items: result.payload.items,
  });
}
