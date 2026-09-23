import { Suspense } from "react";
import { CatalogWorkbench } from "@/components/catalog-workbench";

export default function HomePage() {
  return (
    <Suspense fallback={<main className="panel">Loading catalog...</main>}>
      <CatalogWorkbench />
    </Suspense>
  );
}
