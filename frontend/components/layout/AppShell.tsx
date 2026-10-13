import type { ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";

/**
 * The single-website app shell: a persistent sidebar linking to every
 * subsystem page plus a contextual header. Rendered consistently across all
 * routes via the root layout.
 */
export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="pp-scenery relative flex min-h-screen overflow-hidden">
      {/* Distant layered mountain ridge silhouette along the bottom so the
          frosted content reads as glass over scenery. Lightweight inline SVG,
          no raster asset. */}
      <svg
        aria-hidden
        viewBox="0 0 1440 320"
        preserveAspectRatio="none"
        className="pointer-events-none absolute inset-x-0 bottom-0 z-0 h-64 w-full opacity-60"
      >
        <path
          fill="#7fb069"
          fillOpacity="0.28"
          d="M0,224L120,197.3C240,171,480,117,720,122.7C960,128,1200,192,1320,224L1440,256L1440,320L0,320Z"
        />
        <path
          fill="#4e7a3f"
          fillOpacity="0.32"
          d="M0,288L160,250.7C320,213,640,139,960,138.7C1120,139,1280,181,1360,202.7L1440,224L1440,320L0,320Z"
        />
      </svg>
      <Sidebar />
      <div className="relative z-10 flex min-w-0 flex-1 flex-col">
        <Header />
        <main className="flex-1 px-6 py-8">
          <div className="mx-auto w-full max-w-6xl">{children}</div>
        </main>
      </div>
    </div>
  );
}
