import { NextRequest, NextResponse } from "next/server";
import { buildCatalogPayload, loadDataset } from "@/lib/imdb";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(request: NextRequest) {
  const dataset = await loadDataset();
  return NextResponse.json(buildCatalogPayload(dataset, request.nextUrl.searchParams));
}
