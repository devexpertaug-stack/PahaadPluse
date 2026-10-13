import type { Metadata } from "next";

/**
 * Immersive landing homepage.
 *
 * Routing flow for the whole site:
 *   '/'          -> this cinematic PahaadPulse landing. It embeds the fully
 *                   self-contained experience served from
 *                   /public/pahaadpulse.html in a full-viewport iframe. The
 *                   experience's own CSS + JS stay inline inside that single
 *                   file (zero external JS/CSS libraries), even though it is
 *                   served inside the Next.js app.
 *   '/dashboard' -> product home (Metrics Overview) plus every subsystem route,
 *                   wrapped by AppShell. There is no sign-in gate: the landing's
 *                   "Enter dashboard" affordance, the "Book Now" button and the
 *                   "Stays" nav all navigate the TOP window straight here via a
 *                   tiny inline handler (window.top/parent), so no external
 *                   dependency is needed.
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
        Resilient entry affordances rendered by Next ITSELF (outside the iframe).
        These are real <a href="/dashboard"> anchors, so clicking them navigate
        the TOP window - they work even if the iframe's inline JS or the remote
        cinematic media never load. Both sit ABOVE the iframe (high zIndex,
        pointer-events auto) and are visible from first paint so a visitor is
        never trapped on a dark/loading screen with no way into the product.

        Top-right frosted pill: the primary, always-present entry button.
      */}
      <a
        href="/dashboard"
        aria-label="Enter the PahaadPulse dashboard"
        style={{
          position: "fixed",
          top: "clamp(18px, 3.1vh, 28px)",
          right: "clamp(18px, 1.95vw, 28px)",
          zIndex: 2147483647,
          pointerEvents: "auto",
          display: "inline-flex",
          alignItems: "center",
          gap: 8,
          height: 44,
          padding: "0 22px",
          borderRadius: 999,
          border: "1px solid rgba(207, 227, 212, 0.72)",
          background: "rgba(127, 176, 105, 0.92)",
          backdropFilter: "blur(12px)",
          WebkitBackdropFilter: "blur(12px)",
          color: "#0c1410",
          fontFamily: "var(--font-sans), Arial, sans-serif",
          fontSize: 15,
          fontWeight: 700,
          lineHeight: 1,
          letterSpacing: "0.01em",
          textDecoration: "none",
          boxShadow: "0 10px 30px rgba(6, 16, 10, 0.45)",
        }}
      >
        Enter dashboard <span aria-hidden="true">→</span>
      </a>
    </>
  );
}
