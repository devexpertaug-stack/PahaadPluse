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
    <>
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
      {/*
        Resilient entry affordance rendered by Next itself (outside the iframe).
        A real <a href="/login"> so a visitor can always reach the product even
        if the iframe's inline JS or the remote media fail to load. It sits in
        the top-right corner as an on-brand frosted pill and is kept small so it
        never covers the "Book Now"/portal interactions in the normal case.
      */}
      <a
        href="/login"
        aria-label="Enter the PahaadPulse dashboard"
        style={{
          position: "fixed",
          top: "clamp(18px, 3.1vh, 28px)",
          right: "clamp(18px, 1.95vw, 28px)",
          zIndex: 50,
          display: "inline-flex",
          alignItems: "center",
          height: 36,
          padding: "0 18px",
          borderRadius: 999,
          border: "1px solid rgba(207, 227, 212, 0.45)",
          background: "rgba(27, 59, 42, 0.42)",
          backdropFilter: "blur(12px)",
          WebkitBackdropFilter: "blur(12px)",
          color: "#f3f7f1",
          fontFamily: "var(--font-sans), Arial, sans-serif",
          fontSize: 14,
          fontWeight: 600,
          lineHeight: 1,
          textDecoration: "none",
        }}
      >
        Enter dashboard
      </a>
    </>
  );
}
