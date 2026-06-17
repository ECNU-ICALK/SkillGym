import { TitleDetailWorkbench } from "@/components/title-detail-workbench";

export default async function TitleDetailPage({
  params,
}: {
  params: Promise<{ tconst: string }>;
}) {
  const { tconst } = await params;
  return <TitleDetailWorkbench tconst={tconst} />;
}
