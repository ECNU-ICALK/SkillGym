import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "IMDb Curation Workbench",
  description: "Candidate title curation workbench for shortlist review",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <div className="shell">
          <header className="topbar">
            <div>
              <p className="eyebrow">IMDb Snapshot</p>
              <h1>Curation Workbench</h1>
            </div>
            <nav className="topnav">
              <Link href="/">Catalog</Link>
              <Link href="/shortlist">Shortlist</Link>
            </nav>
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}
