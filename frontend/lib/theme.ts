/**
 * PahadPulse design tokens.
 *
 * Centralised theme values mirrored by `tailwind.config.ts` and
 * `app/globals.css`. Importing from here keeps non-Tailwind code (charts,
 * inline styles, tests) consistent with the hill-town visual identity.
 */

export const palette = {
  // Crisp, fresh alpine green — the primary brand hue (teal-leaning,
  // higher saturation than the old muted forest).
  forest: {
    DEFAULT: "#1f8a5b",
    deep: "#0f5f44",
    mid: "#179467",
    bright: "#28c483",
  },
  // Cool glacier off-whites — the hill-town morning haze.
  mist: {
    DEFAULT: "#f1f7f6",
    white: "#fbfdfd",
    haze: "#e2efed",
  },
  // Livelier accent green.
  pine: "#17b47f",
  // Warm, vivid sunrise / golden-hour amber.
  dawn: "#f6a623",
  ink: "#123b2f",
  // New multi-hue accents — a vivid glacier/sky blue and a cool slate
  // for depth. Used across cards/badges/charts/stat tiles.
  sky: {
    DEFAULT: "#1d9bd1",
    deep: "#0c6fa0",
    bright: "#38bdf8",
  },
  slate: {
    DEFAULT: "#4b6472",
    deep: "#2b3f4a",
    bright: "#7a94a3",
  },
} as const;

export const brand = {
  name: "PahadPulse",
  tagline: "Guest intelligence for the hills",
  region: "Mussoorie · Uttarakhand",
} as const;

export type SubsystemGroup =
  | "Overview"
  | "Market Radar"
  | "Destination Lens"
  | "In-Stay Sentinel"
  | "Guest Compass"
  | "Bhasha Concierge";

export interface NavItem {
  label: string;
  href: string;
  group: SubsystemGroup;
  description: string;
}

/**
 * Navigation model for the single-website app shell. Every subsystem page is a
 * route in this one Next.js app.
 */
export const navItems: NavItem[] = [
  {
    label: "Metrics Overview",
    href: "/",
    group: "Overview",
    description: "Platform-wide KPIs and health at a glance",
  },
  {
    label: "Market Radar",
    href: "/market-radar",
    group: "Market Radar",
    description: "Competitor and cluster signal tracking",
  },
  {
    label: "Unmapped Categories",
    href: "/market-radar/unmapped-categories",
    group: "Market Radar",
    description: "Admin: cross-platform categories needing a canonical aspect",
  },
  {
    label: "Time Machine",
    href: "/time-machine",
    group: "Market Radar",
    description: "Replay how the market moved over time",
  },
  {
    label: "What-If Simulator",
    href: "/what-if",
    group: "Market Radar",
    description: "Model the impact of a change before you make it",
  },
  {
    label: "Playbook",
    href: "/playbook",
    group: "Market Radar",
    description: "Recommended actions mapped to signals",
  },
  {
    label: "Gap Finder",
    href: "/gap-finder",
    group: "Market Radar",
    description: "Surface unmet guest needs in your cluster",
  },
  {
    label: "Proof of Impact",
    href: "/proof-of-impact",
    group: "Market Radar",
    description: "Difference-in-differences effect of your interventions",
  },
  {
    label: "Authenticity Filter",
    href: "/authenticity",
    group: "Market Radar",
    description: "Suspicious-signal flags + authenticity-adjusted rankings",
  },
  {
    label: "Review Replies",
    href: "/review-replies",
    group: "Market Radar",
    description: "Closed-loop, fact-grounded review reply drafts",
  },
  {
    label: "Weekly Briefing",
    href: "/briefing",
    group: "Market Radar",
    description: "Owner's weekly Hindi voice briefing",
  },
  {
    label: "Destination Lens",
    href: "/destination",
    group: "Destination Lens",
    description: "Heatmap and evidence packets by location",
  },
  {
    label: "Checkout Shield",
    href: "/checkout-shield",
    group: "In-Stay Sentinel",
    description: "Catch at-risk stays before checkout",
  },
  {
    label: "Complaints",
    href: "/complaints",
    group: "In-Stay Sentinel",
    description: "Live in-stay complaints and resolution",
  },
  {
    label: "Complaint Forecast",
    href: "/forecast",
    group: "In-Stay Sentinel",
    description: "4-week negative-mention forecast with early warnings",
  },
  {
    label: "Guest Compass",
    href: "/guest-compass",
    group: "Guest Compass",
    description: "Guest journeys and preference signals",
  },
  {
    label: "Bhasha Concierge",
    href: "/concierge",
    group: "Bhasha Concierge",
    description: "Multilingual guest messaging assistant",
  },
  {
    label: "Hinglish Benchmark",
    href: "/benchmark",
    group: "Bhasha Concierge",
    description: "Model quality on the Hinglish test set",
  },
];
