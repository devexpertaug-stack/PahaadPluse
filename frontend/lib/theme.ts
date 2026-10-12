/**
 * PahadPulse design tokens.
 *
 * Centralised theme values mirrored by `tailwind.config.ts` and
 * `app/globals.css`. Importing from here keeps non-Tailwind code (charts,
 * inline styles, tests) consistent with the hill-town visual identity.
 */

export const palette = {
  forest: {
    DEFAULT: "#275233",
    deep: "#1c3725",
    mid: "#2f663e",
    bright: "#3f8150",
  },
  mist: {
    DEFAULT: "#f4f8f4",
    white: "#fbfdfb",
    haze: "#e8f0e9",
  },
  pine: "#4f8a63",
  dawn: "#dca24c",
  ink: "#21422b",
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
