import type { Metadata } from "next";
import { LoginForm } from "@/components/auth/LoginForm";
import { brand } from "@/lib/theme";

export const metadata: Metadata = {
  title: "Sign in — PahadPulse",
  description:
    "Sign in to the PahadPulse guest-intelligence dashboard for The Forest Season Resort, Mussoorie.",
};

/**
 * Pretty, full-bleed login screen.
 *
 * The background is built entirely from the vibrant alpine theme (layered CSS
 * gradients) plus a lightweight inline SVG mountain/forest silhouette, so it
 * stays free and self-contained — no external/copyrighted image. To swap in a
 * real photo later, drop it into `frontend/public/` and set a single
 * `backgroundImage` on the root `<div>` (e.g. style={{ backgroundImage:
 * "url(/login-bg.jpg)" }}); the gradient overlay below is kept semi-transparent
 * so it still reads well over a photo.
 */
export default function LoginPage() {
  return (
    <div
      className="relative flex min-h-screen w-full items-center justify-center overflow-hidden px-4 py-10"
      style={{
        backgroundImage:
          "linear-gradient(160deg, #0a567c 0%, #0f5f44 46%, #1f8a5b 78%, #f6a623 140%)",
      }}
    >
      {/* Decorative glow blobs for depth. */}
      <div
        aria-hidden
        className="pointer-events-none absolute -left-24 top-10 h-72 w-72 rounded-full bg-sky-400/30 blur-3xl"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -right-16 top-1/3 h-80 w-80 rounded-full bg-dawn-400/25 blur-3xl"
      />

      {/* Layered mountain / forest silhouette along the bottom. */}
      <svg
        aria-hidden
        viewBox="0 0 1440 320"
        preserveAspectRatio="none"
        className="pointer-events-none absolute inset-x-0 bottom-0 h-56 w-full md:h-72"
      >
        <path
          fill="#0f5f44"
          fillOpacity="0.55"
          d="M0,224L120,197.3C240,171,480,117,720,122.7C960,128,1200,192,1320,224L1440,256L1440,320L0,320Z"
        />
        <path
          fill="#063b2b"
          fillOpacity="0.85"
          d="M0,288L160,250.7C320,213,640,139,960,138.7C1120,139,1280,181,1360,202.7L1440,224L1440,320L0,320Z"
        />
        {/* Simple pine-tree silhouettes on the near ridge. */}
        <g fill="#042019" fillOpacity="0.9">
          <polygon points="180,300 200,250 220,300" />
          <polygon points="186,282 200,245 214,282" />
          <polygon points="300,305 316,262 332,305" />
          <polygon points="1080,302 1098,258 1116,302" />
          <polygon points="1086,286 1098,254 1110,286" />
          <polygon points="1240,306 1256,266 1272,306" />
        </g>
      </svg>

      {/* Centered elevated/glassy branded card. */}
      <div className="relative z-10 w-full max-w-md">
        <div className="rounded-3xl border border-mist-white/40 bg-mist-white/90 p-8 shadow-ridge backdrop-blur-xl sm:p-10">
          <div className="mb-7 text-center">
            <span className="inline-flex items-center gap-2 rounded-full bg-forest-600/10 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-forest-700">
              {brand.region}
            </span>
            <h1 className="mt-4 font-display text-3xl font-bold text-forest-900">
              {brand.name}
            </h1>
            <p className="mt-1 text-sm font-medium text-sky-700">
              The Forest Season Resort
            </p>
            <div className="ridge-divider mx-auto mt-4 w-24" />
            <p className="mt-4 text-sm text-slate-500">{brand.tagline}</p>
          </div>

          <LoginForm />

          <p className="mt-6 text-center text-xs text-slate-400">
            Secure demo sign-in · session expires after 12 hours
          </p>
        </div>
      </div>
    </div>
  );
}
