import type { Metadata } from "next";

/**
 * Immersive landing homepage.
 *
 * Routing flow for the whole site:
 *   '/'          -> this cinematic PahaadPulse landing (NOT SessionGate-gated).
 *                   It embeds the fully self-contained experience served from
 *                   /public/pahaadpulse.html in a full-viewport iframe. The
 *                   experience's own CSS + JS stay inline inside that single
 *                   file (zero external JS/CSS libraries), even though it is
 *                   served inside the Next.js app.
 *   '/login'     -> auth. The landing's "Book Now" button and "Stays" nav
 *                   navigate the TOP window here via a tiny inline handler
 *                   (window.top/parent), so no external dependency is needed.
 *   '/dashboard' -> gated product home (Metrics Overview) plus every subsystem
 *                   route, all still wrapped by SessionGate + AppShell. After a
 *                   successful sign-in LoginForm redirects here.
 */
export const metadata: Metadata = {
  title: "PahaadPulse — Mountain & Forest Retreats",
  description:
    "A cinematic portal into PahaadPulse mountain and forest hotel retreats.",
};

export default function LandingPage() {
  return (
    <iframe
      src="/pahaadpulse.html"
      title="PahaadPulse immersive landing"
      style={{
        position: "fixed",
        inset: 0,
        width: "100vw",
        height: "100vh",
        border: 0,
      }}
    />
  );
}
